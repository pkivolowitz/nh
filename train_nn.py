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

from game.nn_features import NUM_ACTIONS, get_extractor


DEFAULT_MODEL_DIR: str = "~/.pnh/models"


class QMLP(nn.Module):
    """Two-hidden-layer MLP mapping feature vector → Q-values.

    Small enough to run in microseconds on CPU but expressive enough
    to generalize across perception bins that tabular Q-tables must
    treat as unrelated.
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


def load_trajectories(path: str) -> dict[str, dict[str, np.ndarray]]:
    """Parse the JSONL file into per-species numpy arrays.

    Returns a dict ``species → {s, a, r, sp, d, m, mp}`` where each
    value is a stacked numpy array ready for tensor conversion.
    """
    per_species: dict[str, dict[str, list]] = defaultdict(
        lambda: {"s": [], "a": [], "r": [], "sp": [],
                 "d": [], "m": [], "mp": []},
    )
    with open(os.path.expanduser(path), "r") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            sp_name = rec["species"]
            bucket = per_species[sp_name]
            bucket["s"].append(rec["s"])
            bucket["a"].append(rec["a"])
            bucket["r"].append(rec["r"])
            bucket["sp"].append(rec["sp"])
            bucket["d"].append(rec["d"])
            bucket["m"].append(rec["m"])
            bucket["mp"].append(rec["mp"])

    out: dict[str, dict[str, np.ndarray]] = {}
    for name, b in per_species.items():
        out[name] = {
            "s": np.asarray(b["s"], dtype=np.float32),
            "a": np.asarray(b["a"], dtype=np.int64),
            "r": np.asarray(b["r"], dtype=np.float32),
            "sp": np.asarray(b["sp"], dtype=np.float32),
            "d": np.asarray(b["d"], dtype=np.bool_),
            "m": np.asarray(b["m"], dtype=np.bool_),
            "mp": np.asarray(b["mp"], dtype=np.bool_),
        }
    return out


def train_species(species: str, data: dict[str, np.ndarray], *,
                  epochs: int, batch_size: int, lr: float,
                  gamma: float, target_sync_steps: int,
                  hidden: int, model_dir: str, device: str) -> str:
    """Fit a Q-network on *data* and export to ONNX.  Returns model path."""
    extractor = get_extractor(species)
    feat_dim = extractor.feature_dim
    assert data["s"].shape[1] == feat_dim, (
        f"{species} features have dim {data['s'].shape[1]}, "
        f"extractor expects {feat_dim}"
    )

    n = data["s"].shape[0]
    print(f"[{species}] training on {n:,} transitions "
          f"(dim={feat_dim}, hidden={hidden}, epochs={epochs})")

    model = QMLP(feat_dim, hidden=hidden).to(device)
    target = QMLP(feat_dim, hidden=hidden).to(device)
    target.load_state_dict(model.state_dict())
    target.eval()
    opt = torch.optim.Adam(model.parameters(), lr=lr)

    s_all = torch.from_numpy(data["s"]).to(device)
    a_all = torch.from_numpy(data["a"]).to(device)
    r_all = torch.from_numpy(data["r"]).to(device)
    sp_all = torch.from_numpy(data["sp"]).to(device)
    d_all = torch.from_numpy(data["d"]).to(device)
    mp_all = torch.from_numpy(data["mp"]).to(device)

    step: int = 0
    t0 = time.time()
    for epoch in range(epochs):
        perm = torch.randperm(n, device=device)
        total_loss: float = 0.0
        batches: int = 0
        for start in range(0, n, batch_size):
            idx = perm[start:start + batch_size]
            s = s_all[idx]
            a = a_all[idx]
            r = r_all[idx]
            sp = sp_all[idx]
            done = d_all[idx]
            mp = mp_all[idx]

            # Q(s, a)
            q_s = model(s).gather(1, a.unsqueeze(1)).squeeze(1)
            # Target: r + gamma * max_{a' legal} Q_target(s', a')
            with torch.no_grad():
                q_sp = target(sp)
                # Mask illegal next-actions with a very negative number.
                q_sp = q_sp.masked_fill(~mp, -1e9)
                # If every next-action is illegal (dead state), the max
                # would be -1e9; the (1 - done) factor handles this.
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
            if step % target_sync_steps == 0:
                target.load_state_dict(model.state_dict())

        avg = total_loss / max(1, batches)
        print(f"  epoch {epoch + 1}/{epochs} loss={avg:.4f} "
              f"({time.time() - t0:.1f}s elapsed)")

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
    p.add_argument("--trajectories", type=str, required=True,
                   help="Path to the JSONL trajectory log")
    p.add_argument("--epochs", type=int, default=10)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--gamma", type=float, default=0.95)
    p.add_argument("--hidden", type=int, default=64)
    p.add_argument("--target-sync", type=int, default=200,
                   help="Steps between target-network copies")
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

    all_data = load_trajectories(args.trajectories)
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
        )


if __name__ == "__main__":
    main()
