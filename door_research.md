# NetHack Door Research

Research compiled from the NetHack Wiki (nethackwiki.com) pages on Door, Kick, Force,
and related topics. All information refers to NetHack 3.6.x unless noted otherwise.

---

## Door States and Transitions

A doorway position can be in one of these states:

- **No door (empty doorway)** -- just an opening in the wall
- **Broken door** -- a door that has been damaged but not destroyed
- **Open door** -- an intact door in the open position
- **Closed door (unlocked)** -- an intact door, shut but not locked
- **Closed door (locked)** -- an intact door, shut and locked
- **Closed door (trapped)** -- a closed door with a booby trap on it
- **Secret door** -- looks like a wall until discovered; once found, becomes a closed door (locked)

### State transition diagram

```
Secret Door ---[search/detect]--> Closed (locked)

                                  Closed (locked)
                                    |
                    [unlock]--------+--------[kick/force/destroy]
                    v                                v
                  Closed (unlocked)            Broken door --or-- Empty doorway
                    |         ^
             [open] |         | [close]
                    v         |
                  Open door
                    |
             [wand of locking / wizard lock]
                    v
                  Closed (locked)

Empty doorway ---[wand of locking / wizard lock]--> Closed (locked)

Broken door ---[wand of locking / wizard lock]--> Closed (locked)
  ("The broken door reassembles and locks!")
```

Key transitions:

- **Kicking** a closed door can either break it (leaving an empty doorway) or crash it open (leaving a broken door)
- **Wands/spells of fire, cold, lightning, disintegration** destroy a door entirely (empty doorway)
- **Wand of striking / force bolt** breaks a door (broken door)
- **Wand of locking / wizard lock** can create a door from nothing, repair a broken door, close an open door, or lock a closed door -- all in one zap
- **Wand of opening / knock spell** unlocks a locked door but does NOT open it
- **Applying an axe, pick-axe, or dwarvish mattock** destroys a door

---

## Rendering / Display

| State | Symbol | Notes |
|-------|--------|-------|
| Closed door | `+` | Same symbol regardless of locked/unlocked/trapped |
| Open door (vertical wall) | `-` | Looks like a horizontal wall segment |
| Open door (horizontal wall) | `\|` | Looks like a vertical wall segment |
| Empty doorway (no door) | `.` | Looks like floor |
| Broken door | `.` | Same as doorway / floor |
| Secret door | `-` or `\|` | Appears as wall until discovered |

Notes:
- Open doors look like wall segments in the perpendicular direction. An open door in a vertical (north-south) wall renders as `-`; in a horizontal (east-west) wall, as `|`.
- Closed doors always show as `+` whether locked, unlocked, or trapped.
- Secret doors are indistinguishable from walls until found.

---

## Player Interactions

### Opening Doors

**Unlocked closed doors:**
- Use the `o` (open) command
- Or simply walk into them if the `autoopen` option is TRUE
- May resist opening (exercises strength when it does)
- Tiny creatures are too small to pull doors open

**Locked closed doors -- non-destructive methods:**
- **Skeleton key (apply):** Per-action success = `(70 + Dex)%` for all roles
- **Lock pick (apply):** Per-action success = `(3*Dex)%` for non-Rogues; `(3*Dex + 30)%` for Rogues
- **Credit card (apply):** Per-action success = `(2*Dex)%` for non-Rogues; `(2*Dex + 20)%` for Rogues. Can unlock but CANNOT lock.
- **Wand of opening / knock spell:** Unlocks instantly but does not open the door
- **Blessed Bell of Opening (apply):** Unlocks nearby doors
- If unlocking takes more than one turn in Minetown, watchmen may warn you
- After 50 turns of failed attempts, you give up automatically
- The Master Key of Thievery can also detect and disarm door traps while unlocking

**Locked closed doors -- destructive methods:**
- **Kicking (Ctrl+D):** Noisy. May break open or shatter the door. Exercises dexterity (always) and strength (on success). See Kicking section below.
- **Wand of striking / force bolt spell:** Noisy. Breaks the door.
- **Wand of fire / fireball spell:** Quiet. Destroys the door. ("The door is consumed in flames!")
- **Wand of cold / cone of cold spell:** Quiet. Destroys the door. ("The door freezes and shatters!")
- **Wand of lightning:** Quiet. Breaks the door. ("The door splinters!")
- **Wand of digging / dig spell:** Destroys the door. ("The door is razed!")
- **Wand of disintegration:** Destroys the door. ("The door disintegrates!")
- **Applying an axe, pick-axe, or dwarvish mattock:** Destroys the door. Shop doors are "too hard" to chop.

### Closing Doors

- Use the `c` (close) command on an open door
- Cannot close if a monster, object, or the player is in the doorway
- May resist closing (exercises strength when it does)
- Tiny creatures are too small to push doors closed
- A wand of locking or wizard lock spell will close AND lock an open door in one action

### Locking Doors

- **Skeleton key (apply):** Works on closed (unlocked) doors
- **Lock pick (apply):** Works on closed (unlocked) doors
- **Credit card:** CANNOT lock doors (only unlock)
- **Wand of locking / wizard lock:** Locks a closed door; closes and locks an open door; repairs, closes, and locks a broken door; creates a locked door from an empty doorway

### Diagonal Movement Through Doors

**Critical rule:** You cannot move diagonally into or out of an intact doorway. Only vertical and horizontal moves are allowed through door positions. This applies to both open and closed doors. Messages:
- "You can't move diagonally into an intact doorway."
- "You can't move diagonally out of an intact doorway."

This is a major tactical consideration -- it means a door position is effectively a chokepoint that forces single-file movement.

---

## Kicking Doors

Command: `Ctrl+D` (or `k` with `number_pad` option)

### Restrictions

You cannot kick if:
- Carrying too much (stressed or greater encumbrance)
- Trapped in a pit, web, or bear trap
- One of your legs is wounded
- Polymorphed into a reptile, tiny creature, or legless creature
- Riding a steed (can only kick the steed)

### Effects on Closed Doors

- Kicking a closed door may:
  - **Shatter it** completely (empty doorway) -- "As you kick the door, it shatters to pieces!"
  - **Crash it open** and break it (broken door) -- "As you kick the door, it crashes open!"
  - **Fail** -- "WHAMMM!!!" (does NOT injure your legs, unlike kicking walls)
- Kicking always exercises dexterity
- Successfully breaking a door exercises strength
- Kicking is always noisy -- wakes nearby monsters

### Kicking in Minetown

- If the Watch sees you kick a door: first offense gets a warning ("Hey, stop damaging that door!")
- Second offense: "Halt, vandal! You're under arrest!" (Watch becomes hostile)
- Successfully kicking open a door: "Halt, thief! You're under arrest!" (immediate arrest)

### Kicking Secret Doors

- Kicking a wall that is actually a secret door may reveal it
- "Crash! You kick open a secret door!" or "Crash! You uncover a secret door!"
- Can be faster than searching when luck is low

### Kicking Dungeon Walls (for comparison)

- Does small damage to the player ("Ouch! That hurts!")
- May wound your leg (reduces carrying capacity, prevents further kicks)

---

## Lock Picking Probabilities (Full Table)

Per-action success chance for unlocking:

| Tool | Rogues (Door) | Rogues (Box) | Non-Rogues (Door) | Non-Rogues (Box) |
|------|---------------|--------------|--------------------|--------------------|
| Skeleton key | (70+Dex)% | (75+Dex)% | (70+Dex)% | (75+Dex)% |
| Lock pick | (3*Dex+30)% | (4*Dex+25)% | (3*Dex)% | (4*Dex)% |
| Credit card | (2*Dex+20)% | (Dex+20)% | (2*Dex)% | (Dex)% |
| Weapon (#force) | N/A for doors | 2*wldam | N/A for doors | 2*wldam |

Notes:
- `wldam` = die size of weapon's damage against large monsters (e.g., dagger = 1d3, so 6% per action)
- Weapons CANNOT be used to force doors open in vanilla NetHack (only containers)
- In SLASH'EM, doors CAN be forced open with weapons
- Credit cards can unlock but not lock
- Maximum 50 actions before giving up

---

## Secret Doors

### Generation

- Secret doors are generated during dungeon creation as part of room walls
- They appear identical to walls (`-` or `|`) until discovered
- In NetHack 3.7.0+: secret doors never generate on dungeon levels 1 or 2
- In xNetHack: secret doors are less likely on earlier levels, none before level 4

### Detection Methods

**Searching (s command):**
- Base chance modified by Luck
- Aided by: ring of searching (passive), lenses (passive), wielding Excalibur
- Must be adjacent to the secret door
- May require multiple searches

**Guaranteed detection:**
- **Stethoscope (apply to wall):** Always reveals whether it is a secret door
- **Wand of secret door detection:** Reveals all nearby secret doors immediately
- **Spell of detect unseen:** Reveals nearby secret doors
- **Bell of Opening (blessed):** Reveals nearby secret doors
- **Blessed scroll of magic mapping:** Reveals ALL secret doors on the entire level

**Brute force detection:**
- Kicking a wall that is a secret door may reveal it
- Pick-axe applied to it
- Force bolt or wand of striking zapped at it
- Any wand/spell/breath weapon that hits a secret door reveals it ("Your blast reveals a secret door" / "You feel a draft")

### Secret Door Behavior on the Rogue Level

- Attempting to create a door on the Rogue level: "A cloud of dust springs up in the older, more primitive doorway."
- If successful: "The doorway vanishes!" -- creates a secret door
- If obstructed: "The cloud quickly dissipates."

---

## Door Traps

- Appear at dungeon level 5 and below
- About 3% of non-shop doors are booby-trapped
- Damage: `1d(2 + level^2)` -- scales quadratically with depth, very dangerous at deeper levels
- Additional effects: stunning, abuses strength, abuses constitution
- Detection: use `#untrap` command on a closed door
  - May find a trap ("You find a trap on the door!")
  - May fail to find one ("You find no traps on the door.")
- Disarming: after finding a trap, attempt to disarm
  - Success: "You disarm it!" (In 3.7.0+: awards 8 XP)
  - Failure: "You set it off!" (takes full trap damage)
- Trap triggers when the door is opened (by player or monster)
- The Master Key of Thievery can detect and disarm door traps during unlock
- Monsters can also trigger door traps ("KABOOM!! You see a door explode." / "You hear a distant explosion.")

### Strategy Note

The Sokoban zoo door is worth untrapping -- the real dungeon level of Sokoban floors is higher than displayed, so it is well past the threshold for booby traps, and there are many monsters behind the door who will attack a stunned player.

---

## Effects on Movement and Line of Sight

### Movement

| Door State | Can walk through? | Can move diagonally through? |
|------------|-------------------|------------------------------|
| Open door | Yes | NO |
| Closed (unlocked) | No (must open first) | NO |
| Closed (locked) | No (must unlock first) | NO |
| Broken door | Yes | NO (still an "intact doorway") |
| Empty doorway | Yes | Depends -- if doorway position has no door at all, diagonal is blocked only if it is a "doorway" type tile |
| Secret door | No (is a wall) | N/A |

The diagonal movement restriction is the key tactical property of doors. It means:
- Fighting in a doorway forces enemies through one at a time
- Ranged attacks and breath weapons can still pass through open doors
- This makes doors excellent defensive positions

### Line of Sight

- **Closed doors** block line of sight completely
- **Open doors** do not block line of sight
- **Secret doors** block line of sight (they are walls)

### Special Movement Cases

- **Blind/stunned/fumbling/low-dexterity:** Walking into a closed door gives "Ouch! You bump into a door."
- **Riding:** "You can't lead [mount] through that closed door."
- **Underwater:** "There is an obstacle there."
- **Running:** You stop in front of doors ("You stop in front of the door.")
- **Oozing (amorphous form):** Can ooze under closed doors, but not if carrying too much ("You try to ooze under the door, but can't squeeze your possessions through.")
- **Chewing (xorn, etc.):** Can chew through doors over several turns

---

## How Doors Relate to Rooms and Corridors

- Doors are generated at the junction between rooms and corridors during dungeon creation
- Each room wall may have one or more doors or secret doors
- A door occupies exactly one tile in a room's wall
- Doors connect rooms to corridors, or occasionally rooms to rooms
- Shop doors are special: locked shop doors have "Closed for inventory" written in dust next to them
- Shopkeepers can magically repair their shop doors ("The shop door reappears!" / "Suddenly, the shop door reappears!")
- You can create a door in any destroyed wall section that connects a room to a corridor (using wand of locking or wizard lock)

---

## Monster Interactions with Doors

### Opening Doors

Monsters can open unlocked doors if they:
- Are larger than tiny
- Have hands

When a monster opens a door, you get messages depending on what you can perceive:
- In sight: "[monster] opens a door." or "You see a door open."
- Out of sight: "You hear a door open."

### Unlocking Doors

Monsters can unlock locked doors if they:
- Are larger than tiny
- Have hands
- Have a key in their inventory

Messages: "[monster] unlocks and opens a door." / "You see a door unlock and open." / "You hear a door unlock and open."

**Tip:** If you lock the Minetown Watch behind doors, dispose of any keys on the ground -- monsters will pick them up and use them.

### Bypassing Doors (no key needed)

Several monster types can get through ANY door, even locked:

- **Giants:** Can bust down doors ("smashes down a door" / "You see/hear a door crash open")
- **Tunneling monsters:** Bore through doors
- **Amoeboids and fog clouds:** Flow beneath locked doors
- **Vampires:** Can shapeshift into fog clouds to pass under doors
- **Phasing monsters:** Pass right through doors (e.g., xorn, ghost)
- **The Riders and the Wizard of Yendor:** Can unlock doors without a key
- **Monsters with breath weapons (fire, cold, lightning, disintegration):** Can destroy a door if their breath hits it, but they usually will not attack through a door that separates them from the player

### Monsters and Door Traps

- Monsters can trigger door traps when opening doors
- If you see it: "KABOOM!! You see a door explode."
- If out of sight: "You hear a distant explosion."

---

## Wand and Spell Effects on Doors (Summary)

| Effect | Result | Noise? | Message (seen) | Message (unseen) |
|--------|--------|--------|----------------|-------------------|
| Fire | Destroyed (empty doorway) | No | "The door is consumed in flames!" | "You smell smoke." |
| Cold | Destroyed (empty doorway) | No | "The door freezes and shatters!" | "You feel cold." |
| Lightning | Broken (broken door) | No | "The door splinters!" | "You hear crackling." |
| Disintegration | Destroyed (empty doorway) | No | "The door disintegrates!" | "You hear crashing wood." |
| Striking / force bolt | Broken (broken door) | Yes | "The door crashes open!" | "You hear a crashing sound." |
| Digging | Destroyed (empty doorway) | -- | "The door is razed!" | -- |
| Opening / knock | Unlocked (still closed) | No | "The door unlocks!" | -- |
| Locking / wizard lock | Locked (repairs/creates if needed) | No | Various (see state transitions) | -- |
| Secret door detection | Reveals secret door | No | "A door appears in the wall!" | -- |

If a ray hits a door but fails to affect it: "The door absorbs your blast!" / "You feel vibrations."

---

## Miscellaneous Mechanics

### Exercising Strength via Doors

- Opening or closing a door that resists exercises strength
- Kicking a door exercises dexterity (always) and strength (on success)
- This is noted as "of little practical use" for grinding

### Mimics Disguised as Doors

- A mimic can disguise as a door (`+` symbol)
- Attempting to lock/unlock reveals it: "The door actually was a mimic!"

### Rolling Boulders

- A rolling boulder can destroy a door: "The boulder crashes through a door."

### The Rogue Level

- Door creation on the Rogue level produces special flavor text
- Successfully created doors become secret doors

### Items in Doorways

- Objects in a doorway prevent closing the door ("Something's in the way")
- You cannot close a door while standing in it ("You are in the way!")
- Monsters in the doorway prevent closing ("Some creature blocks the way!")
- You cannot pick up a door from a doorway ("It won't come off the hinges")

### Shop Doors

- Breaking a shop door angers the shopkeeper unless you immediately pay 400 zorkmids
- Shop doors are "too hard" to chop with axes/picks
- Shopkeepers can magically repair their doors
- Locked shop doors have "Closed for inventory" written in dust
- Damaging a shop door: shopkeeper says "How dare you damage my door?"
- Shopkeeper anger levels: "quite upset" / "ticked off" / "furious"

---

## Design Implications for PNH

Key mechanics to consider implementing:

- **State machine:** no_door -> open -> closed_unlocked -> closed_locked, plus broken and secret states
- **Diagonal blocking:** The single most important tactical property of doors
- **Line of sight:** Closed doors block LoS; open doors do not
- **Monster AI:** Needs to handle door-opening behavior based on monster properties (size, hands, keys, special abilities like phasing/oozing/busting)
- **Noise system:** Kicking and striking are noisy; fire/cold/lightning are not
- **Trap system on doors:** Scales with depth, rare (3%), very dangerous
- **Shop door special cases:** Self-repairing, anger mechanics, payment for damage
- **Secret doors:** Search probability affected by Luck and equipment; multiple detection methods
- **Lock picking as an occupation:** Takes multiple turns, can be interrupted, different tools have different probabilities based on Dexterity
