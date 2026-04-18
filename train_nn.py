#!/usr/bin/env python3
# Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

"""Offline DQN trainer that converts JSONL trajectories into ONNX models.

Reads a trajectory log written by ``train.py --record-to ...`` and fits
a small MLP Q-network per species using fitted-Q iteration with a target
network and action masking.  Exports each trained model to
``~/.pnh/models/<species>.onnx`` for ``PolicyBrain`` to pick up.

Usage:
    python train_nn.py --trajectories /tmp/pnh_traj.jsonl \
                       [--epochs 10] [--batch-size 256] [--gamma 0.95]
"""

from __future__ import annotations

__version__ = "0.1.0"

import argparse
import json
import os
import time
from collections import defaultdict
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from game.nn_features import (
    NUM_ACTIONS, get_extractor,
    GRID_SIDE, GRID_CHANNELS, GRID_DIM,
)


DEFAULT_MODEL_DIR: str = "~/.pnh/models"


class QMLP(nn.Module):
    """Two-hidden-layer MLP mapping feature vector → Q-values.

    Small enough to run in microseconds on CPU but expressive enough
    to generalize across perception bins that tabular Q-tables must
    treat as unrelated.  Does not exploit the spatial structure of
    the 7x7 local grid — if the grid matters, use ``QGridCNN``.
    """

    def __init__(self, in_dim: int, hidden: int = 64,
                 out_dim: int = NUM_ACTIONS) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class QGridCNN(nn.Module):
    """Dual-head network: CNN over the 7x7 spatial grid + MLP over scalars.

    The feature vector layout is fixed by the extractors:
        [0:scalar_dim]                  scalar perception
        [scalar_dim:scalar_dim+GRID_DIM] flattened 7x7x8 one-hot grid

    The grid branch learns convolutional filters with translation
    invariance — "wall to the N" and "wall to the S" share weights —
    which the flat-MLP cannot.  Outputs of both branches are
    concatenated and fed to a shared head that produces Q-values.
    """

    def __init__(self, in_dim: int, scalar_dim: int,
                 conv_channels: tuple[int, int] = (16, 32),
                 scalar_hidden: int = 64,
                 head_hidden: int = 128,
                 out_dim: int = NUM_ACTIONS) -> None:
        super().__init__()
        assert in_dim == scalar_dim + GRID_DIM, (
            f"QGridCNN expects in_dim = scalar_dim + GRID_DIM, got "
            f"{in_dim} != {scalar_dim} + {GRID_DIM}"
        )
        self.scalar_dim = scalar_dim

        self.scalar_mlp = nn.Sequential(
            nn.Linear(scalar_dim, scalar_hidden),
            nn.ReLU(),
        )

        c1, c2 = conv_channels
        self.conv = nn.Sequential(
            nn.Conv2d(GRID_CHANNELS, c1, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(c1, c2, kernel_size=3, padding=1),
            nn.ReLU(),
        )
        conv_flat = c2 * GRID_SIDE * GRID_SIDE

        self.head = nn.Sequential(
            nn.Linear(scalar_hidden + conv_flat, head_hidden),
            nn.ReLU(),
            nn.Linear(head_hidden, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Split.
        scalar = x[:, :self.scalar_dim]
        grid = x[:, self.scalar_dim:]
        # (batch, GRID_DIM) → (batch, GRID_SIDE, GRID_SIDE, GRID_CHANNELS)
        #                  → (batch, GRID_CHANNELS, GRID_SIDE, GRID_SIDE)
        batch = x.size(0)
        grid = grid.view(batch, GRID_SIDE, GRID_SIDE, GRID_CHANNELS)
        grid = grid.permute(0, 3, 1, 2).contiguous()

        scalar_feat = self.scalar_mlp(scalar)
        conv_feat = self.conv(grid).flatten(start_dim=1)
        combined = torch.cat([scalar_feat, conv_feat], dim=1)
        return self.head(combined)


def build_qnet(arch: str, feat_dim: int, scalar_dim: int,
               hidden: int) -> nn.Module:
    """Construct the Q-network specified by *arch*."""
    if arch == "mlp":
        return QMLP(feat_dim, hidden=hidden)
    if arch == "cnn":
        return QGridCNN(feat_dim, scalar_dim=scalar_dim,
                        scalar_hidden=hidden // 2,
                        head_hidden=hidden)
    raise ValueError(f"unknown arch {arch!r}")


def load_trajectories(paths: list[str],
                      max_per_species: Optional[int] = None) -> dict[str, dict[str, np.ndarray]]:
    """Parse one or more JSONL files into per-species numpy arrays.

    Memory-efficient two-pass loader: pass 1 counts lines per species,
    pass 2 allocates numpy arrays upfront and parses each record
    directly into them.  This avoids the memory blowup of building
    Python lists of floats (~28 bytes per element) before converting.

    If *max_per_species* is set, randomly subsamples that many records
    per species, which makes giant combined corpora fit in RAM.

    Records with mismatched feature dimensions are skipped (stale
    corpora from earlier architectures).  Returns a dict
    ``species → {s, a, r, sp, d, m, mp}``.
    """
    # Pass 1: count valid records per species.
    counts: dict[str, int] = defaultdict(int)
    skipped: dict[str, int] = defaultdict(int)
    expected_dims: dict[str, int] = {}
    for path in paths:
        with open(os.path.expanduser(path), "r") as f:
            for line in f:
                if not line:
                    continue
                # Cheap parse — just need species and feature length.
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sp_name = rec.get("species")
                if sp_name is None:
                    continue
                try:
                    want = expected_dims.setdefault(
                        sp_name, get_extractor(sp_name).feature_dim,
                    )
                except KeyError:
                    continue
                if len(rec["s"]) != want:
                    skipped[sp_name] += 1
                    continue
                counts[sp_name] += 1

    if skipped:
        for sp, n in skipped.items():
            print(f"[load] skipped {n} {sp} records with wrong feature dim",
                  flush=True)

    for sp, n in counts.items():
        print(f"[load] {sp}: {n:,} valid records to load", flush=True)

    # Decide per-species capacity, possibly subsampled.
    capacity: dict[str, int] = {}
    sample_indices: dict[str, Optional[np.ndarray]] = {}
    rng = np.random.default_rng(12345)
    for sp, n in counts.items():
        if max_per_species is not None and n > max_per_species:
            capacity[sp] = max_per_species
            # Pick random indices to keep; parse in order and accept if in set.
            keep = rng.choice(n, size=max_per_species, replace=False)
            sample_indices[sp] = np.sort(keep)
            print(f"[load] {sp}: subsampling {max_per_species:,} of {n:,}",
                  flush=True)
        else:
            capacity[sp] = n
            sample_indices[sp] = None

    # Pass 2: allocate and fill.
    per_species: dict[str, dict[str, np.ndarray]] = {}
    fill_pos: dict[str, int] = {sp: 0 for sp in capacity}
    seen_idx: dict[str, int] = {sp: 0 for sp in capacity}
    sample_cursor: dict[str, int] = {sp: 0 for sp in capacity}
    for sp in capacity:
        dim = expected_dims[sp]
        cap = capacity[sp]
        per_species[sp] = {
            "s": np.empty((cap, dim), dtype=np.float32),
            "a": np.empty(cap, dtype=np.int64),
            "r": np.empty(cap, dtype=np.float32),
            "sp": np.empty((cap, dim), dtype=np.float32),
            "d": np.empty(cap, dtype=np.bool_),
            "m": np.empty((cap, NUM_ACTIONS), dtype=np.bool_),
            "mp": np.empty((cap, NUM_ACTIONS), dtype=np.bool_),
        }

    for path in paths:
        with open(os.path.expanduser(path), "r") as f:
            for line in f:
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sp_name = rec.get("species")
                if sp_name is None or sp_name not in expected_dims:
                    continue
                if len(rec["s"]) != expected_dims[sp_name]:
                    continue

                cur_idx = seen_idx[sp_name]
                seen_idx[sp_name] += 1
                idx_keep = sample_indices[sp_name]
                if idx_keep is not None:
                    cursor = sample_cursor[sp_name]
                    if cursor >= len(idx_keep) or idx_keep[cursor] != cur_idx:
                        continue
                    sample_cursor[sp_name] = cursor + 1

                pos = fill_pos[sp_name]
                bucket = per_species[sp_name]
                bucket["s"][pos] = rec["s"]
                bucket["a"][pos] = rec["a"]
                bucket["r"][pos] = rec["r"]
                bucket["sp"][pos] = rec["sp"]
                bucket["d"][pos] = rec["d"]
                bucket["m"][pos] = rec["m"]
                bucket["mp"][pos] = rec["mp"]
                fill_pos[sp_name] = pos + 1

    # Trim to actual fill length in case pass 2 saw fewer records
    # than pass 1 (files shouldn't change, but be safe).
    for sp, bucket in per_species.items():
        filled = fill_pos[sp]
        if filled < capacity[sp]:
            for key in bucket:
                bucket[key] = bucket[key][:filled]

    return per_species


def train_species(species: str, data: dict[str, np.ndarray], *,
                  epochs: int, batch_size: int, lr: float,
                  gamma: float, target_sync_steps: int,
                  hidden: int, model_dir: str, device: str,
                  arch: str = "mlp",
                  double_dqn: bool = True,
                  reward_clip: float = 2.0) -> str:
    """Fit a Q-network on *data* and export to ONNX.  Returns model path.

    Uses Double DQN by default (online net selects next action, target
    net evaluates it) to curb the overestimation that makes vanilla
    DQN unstable on long runs.  Rewards are clipped to ±reward_clip to
    keep the bootstrap target from blowing up on occasional outliers.
    ``arch`` chooses the Q-network topology: ``"mlp"`` is a flat MLP
    over the whole feature vector; ``"cnn"`` splits scalar + grid and
    puts a Conv2d stack on the spatial branch.
    """
    extractor = get_extractor(species)
    feat_dim = extractor.feature_dim
    scalar_dim = extractor.SCALAR_DIM
    assert data["s"].shape[1] == feat_dim, (
        f"{species} features have dim {data['s'].shape[1]}, "
        f"extractor expects {feat_dim}"
    )

    n = data["s"].shape[0]
    # Reward distribution sanity check — printed so you can see whether
    # clipping is actually eating into the signal.
    r_arr = data["r"]
    r_min, r_max, r_mean = float(r_arr.min()), float(r_arr.max()), float(r_arr.mean())
    above_clip = float((np.abs(r_arr) > reward_clip).mean())
    print(
        f"[{species}] training on {n:,} transitions "
        f"(dim={feat_dim}, arch={arch}, hidden={hidden}, epochs={epochs}, "
        f"double_dqn={double_dqn}, clip=±{reward_clip})"
    )
    print(
        f"[{species}] reward stats min={r_min:.3f} max={r_max:.3f} "
        f"mean={r_mean:.3f} |r|>clip={above_clip:.2%}"
    )

    model = build_qnet(arch, feat_dim, scalar_dim, hidden).to(device)
    target = build_qnet(arch, feat_dim, scalar_dim, hidden).to(device)
    target.load_state_dict(model.state_dict())
    target.eval()
    param_count = sum(p.numel() for p in model.parameters())
    print(f"[{species}] params={param_count:,}")
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    s_all = torch.from_numpy(data["s"]).to(device)
    a_all = torch.from_numpy(data["a"]).to(device)
    r_all = torch.clamp(
        torch.from_numpy(data["r"]).to(device),
        min=-reward_clip, max=reward_clip,
    )
    sp_all = torch.from_numpy(data["sp"]).to(device)
    d_all = torch.from_numpy(data["d"]).to(device)
    mp_all = torch.from_numpy(data["mp"]).to(device)

    step: int = 0
    t0 = time.time()
    for epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        total_loss: float = 0.0
        batches: int = 0
        q_means: list[float] = []
        q_maxes: list[float] = []
        for start in range(0, n, batch_size):
            idx = perm[start:start + batch_size]
            s = s_all[idx]
            a = a_all[idx]
            r = r_all[idx]
            sp = sp_all[idx]
            done = d_all[idx]
            mp = mp_all[idx]

            q_all = model(s)
            q_s = q_all.gather(1, a.unsqueeze(1)).squeeze(1)

            with torch.no_grad():
                if double_dqn:
                    # Online net selects, target net evaluates.
                    q_sp_online = model(sp).masked_fill(~mp, -1e9)
                    next_actions = q_sp_online.argmax(dim=1)
                    q_sp_target = target(sp)
                    best_next = q_sp_target.gather(
                        1, next_actions.unsqueeze(1),
                    ).squeeze(1)
                else:
                    q_sp = target(sp).masked_fill(~mp, -1e9)
                    best_next = q_sp.max(dim=1).values
                q_target = r + gamma * (1.0 - done.float()) * best_next

            loss = F.smooth_l1_loss(q_s, q_target)
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            opt.step()
            step += 1
            total_loss += float(loss.item())
            batches += 1
            q_means.append(float(q_all.mean().item()))
            q_maxes.append(float(q_all.max().item()))
            if step % target_sync_steps == 0:
                target.load_state_dict(model.state_dict())

        avg = total_loss / max(1, batches)
        print(
            f"  epoch {epoch + 1}/{epochs} loss={avg:.4f} "
            f"q_mean={np.mean(q_means):+.3f} q_max={np.mean(q_maxes):+.3f} "
            f"({time.time() - t0:.1f}s)",
            flush=True,
        )

    # Quick post-training action histogram on a held-out slice.
    model.eval()
    with torch.no_grad():
        sample = min(2048, n)
        q = model(s_all[:sample]).cpu().numpy()
        mask = mp_all[:sample].cpu().numpy()
        q_masked = np.where(mask, q, -1e9)
        # Actually mask current-state legal actions instead — mp is
        # next-state mask.  Use the recorded current mask.
        cur_mask = data["m"][:sample].astype(bool)
        q_masked = np.where(cur_mask, q, -1e9)
        chosen = q_masked.argmax(axis=1)
        hist = np.bincount(chosen, minlength=NUM_ACTIONS)
        from game.actions import Action
        names = {
            0: "WAIT",
            1: "MOVE_N", 2: "MOVE_S", 3: "MOVE_E", 4: "MOVE_W",
            5: "MOVE_NE", 6: "MOVE_NW", 7: "MOVE_SE", 8: "MOVE_SW",
        }
        print(
            f"[{species}] action distribution on {sample} sampled states:"
        )
        for i in range(NUM_ACTIONS):
            pct = 100.0 * hist[i] / max(1, hist.sum())
            print(f"    {names[i]:<8} {hist[i]:>5} ({pct:4.1f}%)")

    # -- export to ONNX ----------------------------------------------------
    model.eval()
    model.cpu()
    model_dir_ex = os.path.expanduser(model_dir)
    os.makedirs(model_dir_ex, exist_ok=True)
    out_path = os.path.join(model_dir_ex, f"{species}.onnx")
    dummy = torch.zeros(1, feat_dim, dtype=torch.float32)
    torch.onnx.export(
        model, dummy, out_path,
        input_names=["features"],
        output_names=["q_values"],
        dynamic_axes={"features": {0: "batch"}, "q_values": {0: "batch"}},
        opset_version=17,
        external_data=False,
        dynamo=True,
    )
    print(f"[{species}] exported {out_path}")
    return out_path


def main() -> None:
    p = argparse.ArgumentParser(description="PNH offline DQN trainer")
    p.add_argument("--trajectories", type=str, nargs="+", required=True,
                   help="Path(s) to JSONL trajectory log(s); multiple files "
                        "are concatenated")
    p.add_argument("--max-per-species", type=int, default=None,
                   help="Randomly subsample this many records per species "
                        "(memory-friendly for giant corpora)")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch-size", type=int, default=512)
    p.add_argument("--lr", type=float, default=5e-4)
    p.add_argument("--gamma", type=float, default=0.9)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--target-sync", type=int, default=500,
                   help="Steps between target-network copies")
    p.add_argument("--reward-clip", type=float, default=2.0,
                   help="Absolute reward clip (0 disables)")
    p.add_argument("--no-double-dqn", dest="double_dqn",
                   action="store_false",
                   help="Disable Double DQN (revert to vanilla)")
    p.add_argument("--arch", choices=["mlp", "cnn"], default="mlp",
                   help="Q-network architecture: flat MLP or dual-head "
                        "CNN+MLP over the spatial grid")
    p.add_argument("--model-dir", type=str, default=DEFAULT_MODEL_DIR)
    p.add_argument("--device", type=str, default=None,
                   help="torch device; auto-select if omitted")
    p.add_argument("--species", type=str, default="",
                   help="Restrict training to one species (default: all)")
    args = p.parse_args()

    device = args.device
    if device is None:
        if torch.cuda.is_available():
            device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    print(f"device: {device}")

    all_data = load_trajectories(args.trajectories,
                                 max_per_species=args.max_per_species)
    if not all_data:
        print("no trajectories found", flush=True)
        return
    print(f"species in log: {list(all_data.keys())}")

    targets = [args.species] if args.species else list(all_data.keys())
    for sp in targets:
        if sp not in all_data:
            print(f"[warn] no data for species {sp!r}", flush=True)
            continue
        train_species(
            sp, all_data[sp],
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            gamma=args.gamma,
            target_sync_steps=args.target_sync,
            hidden=args.hidden,
            model_dir=args.model_dir,
            device=device,
            arch=args.arch,
            double_dqn=args.double_dqn,
            reward_clip=args.reward_clip,
        )


if __name__ == "__main__":
    main()
