# NetHack Comprehensive Research Notes

Compiled from NetHack 3.6 source code (objects.c, monst.c, monflag.h, monattk.h,
trap.h, objclass.h, prop.h, pray.c, fountain.c, sit.c, lock.c, shk.c, shknam.c,
uhitm.c, eat.c, trap.c, spell.c, dokick.c, engrave.c, exper.c, dog.c, dungeon.def)
and the official Guidebook.

---

## Table of Contents

- Dungeon Structure
- Rooms, Corridors, and Map Symbols
- Doors
- Traps
- Dungeon Features (Fountains, Thrones, Altars, Shops)
- Character System (Roles, Races, Attributes, Alignment)
- Player Stats and Status Effects
- Hunger and Encumbrance
- Experience and Leveling
- Luck
- Combat
- Weapons (complete list)
- Armor (complete list)
- Rings (complete list)
- Amulets (complete list)
- Potions (complete list)
- Scrolls (complete list)
- Spellbooks and Spells
- Wands (complete list)
- Tools (complete list)
- Food (complete list)
- Gems and Stones (complete list)
- Monsters
- Pets
- BUC (Blessed/Uncursed/Cursed) System
- Identification
- Shops and Commerce
- Religion and Prayer
- Kicking
- Engraving and Elbereth
- Commands Reference

---

## Dungeon Structure

### Main Branches

- **The Dungeons of Doom** ("D") -- 25 levels + 5 sub-levels, unaligned
  - Gnomish Mines branch at levels 2-3
  - Oracle at levels 5-9, neutral alignment
  - Sokoban branching from Oracle area
  - The Quest branching from Oracle area
  - Rogue level at levels 15-18
  - Fort Ludios at levels 18-21 via portal
  - Medusa level at depth -5 (from bottom)
  - Castle at depth -1 (from bottom)
  - Gehennom chained from Castle

- **Gehennom** ("G") -- 20 levels + 5 sub-levels, mazelike, hellish
  - Valley of the Dead (entry)
  - Sanctum (bottom, houses the Amulet of Yendor)
  - Demon lairs: Juiblex, Baalzebub, Asmodeus, Orcus
  - Wizard's Tower (3 levels chained)
  - Fake Wizard levels
  - Vlad's Tower branches at level 9 going up

- **Gnomish Mines** ("M") -- 8 levels + 2 sub-levels, lawful, mazelike

- **The Quest** ("Q") -- 5 levels + 2 sub-levels, role-specific

- **Sokoban** -- 4 levels, neutral, mazelike (puzzle branch)

- **Fort Ludios** ("K") -- 1 level (Knox vault)

- **Vlad's Tower** ("T") -- 3 levels, chaotic, mazelike

- **The Elemental Planes** ("E") -- 6 levels
  - Earth, Air, Fire, Water, Astral Plane
  - Plus a surface dummy level

### Level Difficulty

Level difficulty is based on absolute depth in the dungeon. "Builds-up" dungeons
like Sokoban have adjusted difficulty reflecting effort to reach them.

### Special Levels

Special levels have names rather than numbers. They include fixed-layout levels
like the Oracle, the Castle, Medusa's Island, and more. Some have random generation
chances per playthrough.

---

## Rooms, Corridors, and Map Symbols

### Terrain Symbols

| Symbol | Meaning |
|--------|---------|
| `-` / `\|` | Wall (horizontal/vertical) or open door |
| `.` | Floor, ice, doorless passage |
| `#` | Corridor, iron bars, tree, or furniture |
| `>` | Stairs down |
| `<` | Stairs up |
| `+` | Closed door or spellbook |
| `^` | Detected trap |
| `{` | Fountain |
| `}` | Water, moat, or lava pool |
| `_` | Altar or iron chain |
| `\\` | Throne |
| `` ` `` | Boulder or statue |
| `0` | Iron ball |

### Object Symbols

| Symbol | Class |
|--------|-------|
| `)` | Weapon |
| `[` | Armor |
| `=` | Ring |
| `"` | Amulet |
| `(` | Tool |
| `%` | Food |
| `!` | Potion |
| `?` | Scroll |
| `+` | Spellbook |
| `/` | Wand |
| `$` | Coins |
| `*` | Gem |
| `` ` `` | Rock/Boulder/Statue |

---

## Doors

### Door States

- **D_NODOOR** -- No door present (empty doorway)
- **D_ISOPEN** -- Open door
- **D_CLOSED** -- Closed door
- **D_LOCKED** -- Locked door
- **D_BROKEN** -- Broken door (cannot be closed)
- Doors may also carry the **D_TRAPPED** flag

### Opening Doors

Command: `o` (open)

Success formula: `rnl(20) < (STR + DEX + CON) / 3`

Trapped doors trigger damage when opened. Very small creatures cannot open doors.
Blind players get tactile feedback about door status.

### Closing Doors

Command: `c` (close)

Success formula: `rn2(25) < (STR + DEX + CON) / 3`

Mounted creatures get an advantage. Cannot close if obstructed by monsters or
objects. Broken doors cannot be closed.

### Lock Picking

Three tools: lock pick, skeleton key, credit card.

**Door lock success chances:**
- Skeleton key: `70 + DEX`
- Lock pick: `3 * DEX + 30 * (is_rogue)`
- Credit card: `2 * DEX + 20 * (is_rogue)`

**Container lock success chances:**
- Skeleton key: `75 + DEX`
- Lock pick: `4 * DEX + 25 * (is_rogue)`
- Credit card: `2 * DEX + 20 * (is_rogue)`

Rogues receive significant bonuses. Cursed tools halve success chances. Picking
takes up to 50 turns; interruption resets progress.

### Forced Entry

Wielding blades or blunt weapons allows forcing chests. Blade weapons risk breakage
(~67% survival for +0 weapon over 50 attempts). Blunt weapons alert nearby
creatures. 33% chance to destroy the chest entirely.

### Magic Effects on Doors

- **Wizard Lock / Wand of Locking**: Locks doors
- **Knock / Wand of Opening**: Unlocks doors
- **Force Bolt / Wand of Striking**: Breaks doors
- On Rogue levels, locking converts doors to secret doors

### Kicking Doors

Success: `rnl(35) < avrg_attrib + (martial ? DEX : 0)`

Where `avrg_attrib = (STR + DEX + CON) / 3` (or 99 with kicking boots)

Trapped doors trigger on successful kick. Shop doors incur damage costs.

### Secret Doors

Found by searching (`s` command). Searching is not guaranteed to find them on
each attempt. Once found, they function as normal closed doors.

### Monster Interactions

Most monsters cannot open doors. Ghosts and similar creatures phase through them.
Amorphous creatures (M1_AMORPHOUS) can flow under doors. Wall-walking creatures
(M1_WALLWALK) can phase through rock and doors.

---

## Traps

### All 24 Trap Types

| Trap | Effect |
|------|--------|
| **ARROW_TRAP** | Fires an arrow. Damage from arrow weapon stats. 1-in-5 dodge chance if seen. |
| **DART_TRAP** | Fires a poisoned dart. 1-in-6 chance of CON loss (up to 10 points). |
| **ROCKTRAP** | Rock falls from ceiling. d(2,6) damage. Metal helms reduce to 2 damage. |
| **SQKY_BOARD** | Makes noise, wakes nearby creatures. No damage. |
| **BEAR_TRAP** | d(2,4) damage. Immobilizes for rn1(4,4) turns. Small creatures escape. Amorphous creatures pass through. |
| **LANDMINE** | rnd(16) damage. Wounds both legs for rn1(35,41) turns each. Converts to pit after detonation. |
| **ROLLING_BOULDER_TRAP** | Launches boulder at target. Can trigger chain reactions. |
| **SLP_GAS_TRAP** | Induces sleep for rnd(25) turns. Sleep resistance or breathlessness protects. |
| **RUST_TRAP** | Gush of water. Randomly targets head, shield/weapon, weapon, or body armor. Causes erosion. Iron golems killed. Gremlins split. |
| **FIRE_TRAP** | d(2,4) damage. Fire resistance protects. Can destroy scrolls, books, potions. Paper/straw/wood golems immolate. |
| **PIT** | Fall damage. Trapped for rn1(6,2) turns. |
| **SPIKED_PIT** | Like pit but rnd(4-10) additional spike damage. May poison (CON loss up to 8). |
| **HOLE** | Fall to next dungeon level. Levitating/flying creatures may avoid. |
| **TRAPDOOR** | Fall to next dungeon level. Cannot exist on non-fall-through levels. |
| **TELEP_TRAP** | Random teleportation on current level. |
| **LEVEL_TELEP** | Teleport to different dungeon level. |
| **MAGIC_PORTAL** | Special teleport between dungeon branches. |
| **WEB** | Traps victim. Duration based on STR: STR<=3 = rn1(6,6) turns; STR 15-17 = rnd(2); STR>=69 = instant break. Amorphous/flaming/acidic creatures destroy webs. Giants, dragons, large worms tear through. |
| **STATUE_TRAP** | Animates statue as living monster. |
| **MAGIC_TRAP** | 1-in-30 chance: rnd(10) damage + 2 spell points. Otherwise random magic effect. |
| **ANTI_MAGIC** | Without magic resistance: lose rnd(level) + 1 spell points. With resistance: take rnd(4) to rnd(12) damage. |
| **POLY_TRAP** | Forces polymorph. Antimagic or Unchanging protects. |
| **VIBRATING_SQUARE** | Special marker for endgame puzzle. Not harmful. |

### Detection

Traps are invisible until:
- Triggered by stepping on them
- Observed when someone else triggers them
- Found via `s` (search) command
- Found via magic (wand of secret door detection, etc.)

### Disarming

`#untrap` command attempts disarming. Success depends on untrap_prob() calculation.
Rogues have bonuses. Some traps can be disarmed for useful items (land mines,
bear traps become tools).

### Monster Trap Interactions

- Metallivorous creatures consume bear traps/spikes
- Iron golems are killed by rust traps
- Gremlins split when hit by water (rust trap)
- Flyers/levitators bypass pit traps unless forced
- Monsters escape traps at 1-in-4 chance (1-in-40 if boulder in pit)

---

## Dungeon Features

### Fountains

Symbol: `{`

**Drinking (quaff from fountain)** -- Rolls 1d30:

| Roll | Effect |
|------|--------|
| < 10 | Refreshing drink, restores 1d10 hunger |
| 19 | Self-knowledge (exercises Wisdom) |
| 20 | Foul water: vomiting, +11-30 hunger |
| 21 | Poisoned water: 3-6 damage (10 without poison res), -3 to -6 STR |
| 22 | Spawns 2-6 water moccasins |
| 23 | Summons water demon (small chance for a wish based on depth) |
| 24 | Curses all inventory items (1/5 chance each) |
| 25 | Grants see invisible |
| 26 | Monster detection |
| 27 | Find a gem (if fountain not already looted) |
| 28 | Summons water nymph |
| 29 | Scare effect on all monsters |
| 30 | Gushing fountain: creates water pools |

Fountain may dry up after drinking.

**Dipping items in fountain** -- Rolls 1d30:

| Roll | Effect |
|------|--------|
| 16 | Curse the dipped item |
| 17-20 | Uncurse if cursed |
| 21 | Water demon |
| 22 | Water nymph |
| 23 | Snakes |
| 24 | Gem discovery |
| 25 | Water gushes forth |
| 26-28 | Strange sensations |
| 29 | Coin discovery (based on depth) |

**Special**: Dipping a longsword at character level 5+ has a 1/6 chance to create
Excalibur (lawful players) or curse it (non-lawful).

### Thrones

Symbol: `\\`

**Sitting on a throne** -- 66% chance of triggering an effect (rnd(6) > 4).
Otherwise "you feel out of place" (or "very comfortable" if a prince).

13 possible effects (equal probability):

- Reduce random attribute by 3-6, lose 1-10 HP
- Increase random attribute by 1
- Electric shock: 6 HP (with resistance) or 1-30 HP (without)
- Full healing: restore all HP/MP, cure blindness/sickness/leg injuries
- Gold loss
- Luck gain or wish (if luck is neutral/positive)
- Summon 1-10 courtier monsters
- Trigger genocide effect
- Inflict blindness (100-350 turns), reduce luck
- Grant see invisible OR mapping/confusion (luck-dependent)
- Teleportation or aggravation (luck-dependent)
- Identify 0-4 random inventory items
- Confusion for 23-39 turns

33% chance the throne vanishes after any effect.

### Altars

Symbol: `_`

Used for sacrificing (`#offer`), praying (`#pray`), and detecting BUC status
(by dropping items on altars).

Altars have alignment: lawful, neutral, or chaotic. Items dropped on altars flash
to reveal BUC status (amber = cursed, no flash = uncursed, white = blessed -- or
similar visual indicator).

**Sacrifice Mechanics:**
- Base corpse value = monster difficulty + 1 (max 24)
- Sacrificing your own race: -5 alignment, +3 god anger (unless chaotic)
- Unicorn sacrifices provide alignment-dependent bonuses
- Real Amulet of Yendor on coaligned high altar triggers ascension
- Fake Amulet: -1 luck (unknowing) or -3 luck (deliberate)

### Shops

12 shop types with generation probabilities:

| Shop Type | Probability | Primary Stock |
|-----------|------------|---------------|
| General Store | 42% | Random |
| Used Armor Dealership | 14% | 90% armor, 10% weapons |
| Second-hand Bookstore | 10% | 90% scrolls, 10% spellbooks |
| Liquor Emporium | 10% | 100% potions |
| Antique Weapons Outlet | 5% | 90% weapons, 10% armor |
| Delicatessen | 5% | 83% food + drinks |
| Jewelers | 3% | 85% rings, 10% gems, 5% amulets |
| Quality Apparel | 3% | 90% wands + leather/elven items |
| Hardware Store | 3% | 100% tools |
| Rare Books | 3% | 90% spellbooks, 10% scrolls |
| Health Food Store | 2% | 70% veggie, 20% juice + healing |
| Lighting Store | 0% | Candles, lamps (special level only) |

**Pricing Factors:**
- Unidentified items: +33% surcharge
- Dunce cap: 4x price
- Tourist (low level) or visible tourist shirt: +33%
- Charisma modifiers: CHA > 18 = 50% discount; CHA <= 5 = doubled price
- Angry shopkeeper: +33% surcharge
- Artifacts: 4x price
- Selling: typically half buying price

**Shop Mechanics:**
- Pick up items to buy, `p` to pay
- Drop items to sell
- Shopkeeper watches hero; prevents departure until debt paid
- Maximum 20 unpaid items per shopkeeper
- Credit system when shopkeeper lacks gold
- Theft triggers: angry shopkeeper, Keystone Kops summoned, alignment penalty

**Restrictions:**
- Cannot enter with pick-axe or dwarvish mattock
- Cannot enter while mounted
- Invisible players barred from service

---

## Character System

### Roles (12)

- **Archaeologist**: Quick, stealthy, exploration-equipped
- **Barbarian**: High STR, great two-handed swords, heavy armor
- **Caveman/woman**: Exceptional STR, primitive weapons
- **Healer**: Medical expertise, diagnostic tools, money
- **Knight**: Superior armor, chivalrous
- **Monk**: Unarmed combat expert, no armor, high mobility
- **Priest/Priestess**: Divine magic, sense BUC status naturally
- **Ranger**: Archery mastery, tracking, stealthy
- **Rogue**: Lock picking, trap knowledge, stealth
- **Samurai**: Dual swords, light armor, quick
- **Tourist**: Gold, credit card, camera, food
- **Valkyrie**: Hardy, cold-resistant, strong
- **Wizard**: Magical knowledge, spellcasting focus

### Races (5)

- **Human**: No special abilities, can play any role
- **Dwarf**: Mining/metalwork, sturdy builds
- **Elf**: Agile, perceptive, quality gear
- **Gnome**: Similar to dwarf, mine access
- **Orc**: Barbaric, hate elves, inferior gear

### Attributes (6)

| Attribute | Effect |
|-----------|--------|
| **Strength (St)** | Damage bonus, carrying capacity, door forcing |
| **Dexterity (Dx)** | Hit accuracy, trap avoidance, lock picking |
| **Constitution (Co)** | HP recovery, stamina, carrying capacity |
| **Intelligence (In)** | Spell casting, spellbook reading |
| **Wisdom (Wi)** | Spell power, magical energy |
| **Charisma (Ch)** | Monster reactions, shop prices |

Range: typically 3-18 for humans. Can go higher with magic/enchantment.

### Alignment

Three alignments: **Lawful**, **Neutral**, **Chaotic**

- Affects monster reactions (same alignment = less hostile)
- Determines which gods respond to prayer
- Some actions shift alignment (e.g., murder, cannibalism, sacrifice)

---

## Player Stats and Status Effects

### Player Properties / Intrinsics

**Resistances (12):**
FIRE_RES, COLD_RES, SLEEP_RES, DISINT_RES, SHOCK_RES, POISON_RES, ACID_RES,
STONE_RES, DRAIN_RES, SICK_RES, INVULNERABLE, ANTIMAGIC

**Status Ailments (16):**
STUNNED, CONFUSION, BLINDED, DEAF, SICK, STONED, STRANGLED, VOMITING, GLIB,
SLIMED, HALLUC, HALLUC_RES, FUMBLING, WOUNDED_LEGS, SLEEPY, HUNGER

**Sensory/Detection (9):**
SEE_INVIS, TELEPAT, WARNING, WARN_OF_MON, WARN_UNDEAD, SEARCHING, CLAIRVOYANT,
INFRAVISION, DETECT_MONSTERS

**Appearance/Behavior (6):**
ADORNED, INVIS, DISPLACED, STEALTH, AGGRAVATE_MONSTER, CONFLICT

**Movement (9):**
JUMPING, TELEPORT, TELEPORT_CONTROL, LEVITATION, FLYING, WWALKING, SWIMMING,
MAGICAL_BREATHING, PASSES_WALLS

**Physical (15):**
SLOW_DIGESTION, HALF_SPDAM, HALF_PHDAM, REGENERATION, ENERGY_REGENERATION,
PROTECTION, PROT_FROM_SHAPE_CHANGERS, POLYMORPH, POLYMORPH_CONTROL, UNCHANGING,
FAST, REFLECTING, FREE_ACTION, FIXED_ABIL, LIFESAVED

### Fatal Status Conditions

- **Stoned (Petrifying)**: Progressive 5-stage transformation. Eating lizard corpse cures.
- **Slimed**: Turning into green slime. Progressive messages. Prayer or burning cures.
- **Strangled**: Suffocating. Fatal at timeout zero. Remove amulet of strangulation.
- **Food Poisoning**: Fatal illness from bad food. Prayer, unicorn horn, or cure sickness.
- **Terminal Illness**: From sickness attack. Same cures as food poisoning.

### Non-Fatal Conditions

- **Blind**: Cannot see. Caused by yellow light, cream pie, potion, etc.
- **Deaf**: Cannot hear. Limited interface for messages.
- **Stunned**: Reduced accuracy, random movement errors.
- **Confused**: Actions may go wrong, misdirected movement.
- **Hallucinating**: False perceptions, random monster/item descriptions.
- **Wounded Legs**: Reduced kick effectiveness, movement penalties.
- **Fumbling**: Risk of tripping, dropping items.
- **Glib**: Slippery hands, risk of dropping wielded weapon.

---

## Hunger and Encumbrance

### Hunger Thresholds

| State | Hunger Value | Effect |
|-------|-------------|--------|
| Satiated | > 1000 | Risk of choking if eating more (>= 2000 deadly) |
| Not Hungry | > 150 | Normal |
| Hungry | > 50 | Warning messages |
| Weak | > 0 | Movement affected |
| Fainting | <= 0 | Risk of starvation, passing out |

### Encumbrance Levels

- **Unencumbered**: Normal movement
- **Encumbered**: Slight penalties
- **Stressed**: Moderate penalties
- **Strained**: Severe penalties
- **Overtaxed**: Very restricted
- **Overloaded**: Cannot move

Encumbrance affects combat to-hit: penalty = -(capacity * 2 - 1)

### Food Nutrition Values (selected)

| Food | Weight | Nutrition |
|------|--------|-----------|
| Food Ration | 20 | 800 |
| Lembas Wafer | 5 | 800 (+25% for elves, -25% for orcs) |
| Cram Ration | 15 | 600 (+17% for dwarves) |
| K-Ration | 10 | 400 |
| C-Ration | 10 | 300 |
| Slime Mold | 5 | 250 |
| Lump of Royal Jelly | 2 | 200 |
| Pancake | 2 | 200 |
| Tripe Ration | 10 | 200 |
| Melon | 5 | 100 |
| Candy Bar | 2 | 100 |
| Cream Pie | 10 | 100 |
| Egg | 1 | 80 |
| Orange | 2 | 80 |
| Banana | 2 | 80 |
| Apple | 2 | 50 |
| Carrot | 2 | 50 (+ vision enhancement) |
| Fortune Cookie | 1 | 40 |
| Sprig of Wolfsbane | 1 | 40 |
| Clove of Garlic | 1 | 40 |
| Kelp Frond | 1 | 30 |
| Eucalyptus Leaf | 1 | 30 |
| Huge Chunk of Meat | 400 | 2000 |

### Corpse Effects

Eating corpses can grant intrinsics based on monster type:
- Fire/Cold/Shock/Poison/Disintegration Resistance
- Telepathy, Teleportation, Teleport Control
- Strength (from giants, 50% chance)
- Medusa/Cockatrice corpses cause petrification
- Lizard corpses cure stoning
- Green slime causes sliming
- Rider corpses (Death/Pestilence/Famine) are instantly fatal

**Corpse Rot**: `rotted = (turns_since_death) / (10 + random(20))`
- Rotted > 5: vomiting and sickness (10-20 turns)
- Curses add +2 rot; blessings subtract -2

**Cannibal Penalties**: Eating same-species: -2 to -5 luck, aggravates monsters.
Exceptions for Caveman and Orc. Monks suffer alignment loss from non-vegetarian food.

---

## Experience and Leveling

### XP Formula for Killing Monsters

Base: `1 + (monster_level)^2`

Bonuses:
- AC < 3: extra points
- Speed > normal: +3 to +5
- Weapon attacks: +5 per attack
- Magic attacks: +10 per attack
- Other attacks: +3 per attack
- Special damage (drain, petrification, slime): +50
- Heavy damage (>23 dice): + monster level
- "Extra nasty" creatures: +7x monster level
- Monster level > 8: +50

**Diminishing returns**: Same monster type killed repeatedly: XP halved after
thresholds (1/2, 1/4, 1/8, 1/16, 1/32, 1/64).

### Level Thresholds

- Levels 1-9: `10 * 2^level` XP
- Levels 10-19: `10,000 * 2^(level-10)` XP
- Levels 20+: `10,000,000 * (level-19)` XP

Can only advance one level per threshold; excess XP capped at one below next.

### Level-Up Gains

- **Hit Points**: Calculated by newhp() function, role/race dependent
- **Spell Power (Energy)**: Wisdom/2 + role/race bonuses
  - Priests/Wizards: 2x energy gain
  - Healers/Knights: 1.5x
  - Barbarians/Valkyries: 0.75x

### Level Drain

- Lose current XP (reset to one below prior threshold)
- Lose max HP, current HP, max energy, current energy
- Level cannot drop below 1 (except fatal drain attacks)
- Drain resistance (DRAIN_RES) protects

---

## Luck

### Luck Range and Baseline

Luck ranges from -13 to +13. Baseline is 0, modified by:
- Full moon: +1 baseline
- Friday the 13th: -1 baseline

### Luck Timeout

Without a luckstone, luck drifts toward baseline:
- Every 600 turns normally
- Every 300 turns if carrying Amulet of Yendor or under divine anger

### Luckstone Effects

- **Blessed luckstone**: Prevents good luck from decaying
- **Cursed luckstone**: Prevents bad luck from decaying
- **Uncursed luckstone**: Prevents both from decaying

### Luck Modifiers

Luck affects nearly everything: to-hit rolls, prayer success, throne outcomes,
wish chances, trap avoidance, and many other random rolls via the rnl() function.

Common luck changes:
- Sacrificing unicorn horn (right alignment): positive
- Sacrificing unicorn horn (wrong alignment): negative
- Breaking Sokoban rules: negative
- Cannibalism: -2 to -5
- Fake Amulet sacrifice: -1 or -3

---

## Combat

### To-Hit Calculation

```
to_hit = 1 + Luck + abon() + find_mac(target) + u.uhitinc + character_level
```

Additional modifiers:
- Stunned/fleeing monster: +2
- Sleeping monster: +2
- Immobilized monster: +4
- Encumbrance penalty: -(capacity * 2 - 1)
- In trap: -3
- Monk wearing armor: -urole.spelarmr
- Monk unarmed (unarmored): +(level/3) + 2
- Elf vs Orc: +1

**Hit determination**: Hit if to_hit > d20 roll

### Damage Calculation

- Base damage from weapon dice (vs. small or large monsters)
- + weapon enchantment bonus
- + strength bonus (dbon())
- + weapon skill bonus
- - encumbrance reduction
- Silver weapons do extra damage to undead/demons

### Weapon Proficiency Levels

- **Restricted**: Cannot advance, penalties
- **Unskilled**: Hit and damage penalties
- **Basic**: No penalty or bonus
- **Skilled**: Hit and damage bonuses
- **Expert**: Increased bonuses
- **Master/Grand Master**: Unarmed/martial arts only

Successful hits advance skill training. `#enhance` command spends training.

### Two-Weapon Fighting

- Secondary weapon uses same calculation
- Hit penalty for dual wielding vs. single weapon
- Available to eligible roles only

### Jousting (Mounted Combat)

Success by skill:
- Expert: 80%
- Skilled: 60%
- Basic: 40%
- Unskilled: 20%

Bonus damage: d(2,10) for primary or d(2,2) for secondary
2.5% chance to shatter defender's weapon

### Armor Class

Base AC: 10 (unarmored). Lower is better.
AC = 10 - (armor bonuses) - (enchantment bonuses) - (dexterity bonus) - (other modifiers)

---

## Weapons (Complete List)

### Missiles

| Weapon | Damage (sm/lg) | Weight | Cost | Material | Notes |
|--------|----------------|--------|------|----------|-------|
| Arrow | 6/6 | 1 | 2 | Iron | |
| Elven Arrow | 7/6 | 1 | 2 | Wood | |
| Orcish Arrow | 5/6 | 1 | 2 | Iron | |
| Silver Arrow | 6/6 | 1 | 5 | Silver | |
| Ya | 7/7 | 1 | 4 | Metal | +1 hit |
| Crossbow Bolt | 4/6 | 1 | 2 | Iron | |

### Handheld Missiles

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Dart | 3/2 | 1 | 2 | Iron | |
| Shuriken | 8/6 | 1 | 5 | Iron | +2 hit |
| Boomerang | 9/9 | 5 | 20 | Wood | |

### Spears

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Spear | 6/8 | 30 | 3 | Iron | |
| Elven Spear | 7/8 | 30 | 3 | Wood | |
| Orcish Spear | 5/8 | 30 | 3 | Iron | |
| Dwarvish Spear | 8/8 | 35 | 3 | Iron | |
| Silver Spear | 6/8 | 36 | 40 | Silver | |
| Javelin | 6/6 | 20 | 3 | Iron | |
| Trident | 6+1/4+2d4 | 25 | 5 | Iron | |

### Daggers

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Dagger | 4/3 | 10 | 4 | Iron | +2 hit |
| Elven Dagger | 5/3 | 10 | 4 | Wood | +2 hit |
| Orcish Dagger | 3/3 | 10 | 4 | Iron | +2 hit |
| Silver Dagger | 4/3 | 12 | 40 | Silver | +2 hit |
| Athame | 4/3 | 10 | 4 | Iron | +2 hit, slash |
| Scalpel | 3/3 | 5 | 6 | Metal | +2 hit, slash |
| Knife | 3/2 | 5 | 4 | Iron | pierce/slash |
| Stiletto | 3/2 | 5 | 4 | Iron | pierce/slash |
| Worm Tooth | 2/2 | 20 | 2 | Mineral | |
| Crysknife | 10/10 | 20 | 100 | Mineral | +3 hit |

### Axes

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Axe | 6/4 | 60 | 8 | Iron | slash |
| Battle-axe | 8/6 | 120 | 40 | Iron | slash, two-handed |

### Swords

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Short Sword | 6/8 | 30 | 10 | Iron | |
| Elven Short Sword | 8/8 | 30 | 10 | Wood | |
| Orcish Short Sword | 5/8 | 30 | 10 | Iron | |
| Dwarvish Short Sword | 7/8 | 30 | 10 | Iron | |
| Scimitar | 8/8 | 40 | 15 | Iron | slash |
| Silver Saber | 8/8 | 40 | 75 | Silver | slash |
| Broadsword | 4+d4/6+1 | 70 | 10 | Iron | slash |
| Elven Broadsword | 6+d4/6+1 | 70 | 10 | Wood | slash |
| Long Sword | 8/12 | 40 | 15 | Iron | slash |
| Two-Handed Sword | 12/6+2d6 | 150 | 50 | Iron | slash, two-handed |
| Katana | 10/12 | 40 | 80 | Iron | slash, +1 hit |
| Tsurugi | 16/8+2d6 | 60 | 500 | Metal | slash, +2 hit, two-handed |
| Runesword | 4/6 | 40 | 300 | Iron | slash, artifact-capable |

### Polearms

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Partisan | 6/6+1 | 80 | 10 | Iron | |
| Ranseur | 4+d4/4+d4 | 50 | 6 | Iron | |
| Spetum | 6+1/6+d6 | 50 | 5 | Iron | |
| Glaive | 6/10 | 75 | 6 | Iron | slash |
| Lance | 6/8 | 180 | 10 | Iron | +2d10 jousting |
| Halberd | 10/6+d6 | 150 | 10 | Iron | pierce/slash |
| Bardiche | 4+d4/4+2d4 | 120 | 7 | Iron | slash |
| Voulge | 4+d4/4+d4 | 125 | 5 | Iron | slash |
| Fauchard | 6/8 | 60 | 5 | Iron | pierce/slash |
| Guisarme | 4+d4/8 | 80 | 5 | Iron | slash |
| Bill-Guisarme | 4+d4/10 | 120 | 7 | Iron | pierce/slash |
| Lucern Hammer | 4+d4/6 | 150 | 7 | Iron | whack/pierce |
| Bec de Corbin | 8/6 | 100 | 8 | Iron | whack/pierce |
| Dwarvish Mattock | 12/8 | 120 | 50 | Iron | whack, -1 hit |

### Bludgeons

| Weapon | Damage | Weight | Cost | Material | Notes |
|--------|--------|--------|------|----------|-------|
| Mace | 6+1/6 | 30 | 5 | Iron | whack |
| Morning Star | 4+d4/6+1 | 120 | 10 | Iron | whack |
| War Hammer | 4+1/4 | 50 | 5 | Iron | whack |
| Club | 6/3 | 30 | 3 | Wood | whack |
| Rubber Hose | 4/3 | 20 | 3 | Plastic | whack |
| Quarterstaff | 6/6 | 40 | 5 | Wood | whack |
| Aklys | 6/3 | 15 | 4 | Iron | whack |
| Flail | 6+1/4+d4 | 15 | 4 | Iron | whack |

### Whips

| Weapon | Damage | Weight | Cost | Material |
|--------|--------|--------|------|----------|
| Bullwhip | 2/1 | 20 | 4 | Leather |

### Bows and Launchers

| Weapon | Damage | Weight | Cost | Material |
|--------|--------|--------|------|----------|
| Bow | 2/2 | 30 | 60 | Wood |
| Elven Bow | 2/2 | 30 | 60 | Wood |
| Orcish Bow | 2/2 | 30 | 60 | Wood |
| Yumi | 2/2 | 30 | 60 | Wood |
| Sling | 2/2 | 3 | 20 | Leather |
| Crossbow | 2/2 | 50 | 40 | Wood |

---

## Armor (Complete List)

### Body Armor (Suits)

| Armor | AC | Weight | Cost | Material | Power |
|-------|-----|--------|------|----------|-------|
| Leather Jacket | 9 | 30 | 10 | Leather | |
| Leather Armor | 8 | 150 | 5 | Leather | |
| Orcish Ring Mail | 8 | 250 | 80 | Iron | |
| Studded Leather | 7 | 200 | 15 | Leather | |
| Ring Mail | 7 | 250 | 100 | Iron | |
| Scale Mail | 6 | 250 | 45 | Iron | |
| Orcish Chain Mail | 6 | 300 | 75 | Iron | |
| Chain Mail | 5 | 300 | 75 | Iron | |
| Elven Mithril-Coat | 5 | 150 | 240 | Mithril | |
| Banded Mail | 4 | 350 | 90 | Iron | |
| Splint Mail | 4 | 400 | 80 | Iron | |
| Dwarvish Mithril-Coat | 4 | 150 | 240 | Mithril | |
| Bronze Plate Mail | 4 | 450 | 400 | Copper | |
| Plate Mail | 3 | 450 | 600 | Iron | |
| Crystal Plate Mail | 3 | 450 | 820 | Glass | |
| Dragon Scale Mail (all) | 1 | 40 | 900-1200 | Dragon Hide | (see below) |

### Dragon Scale Mail Powers

| Color | Cost | Power |
|-------|------|-------|
| Gray | 1200 | Antimagic |
| Silver | 1200 | Reflecting |
| Red | 900 | Fire Resistance |
| White | 900 | Cold Resistance |
| Orange | 900 | Sleep Resistance |
| Black | 1200 | Disintegration Resistance |
| Blue | 900 | Shock Resistance |
| Green | 900 | Poison Resistance |
| Yellow | 900 | Acid Resistance |

Dragon Scales (unprocessed) provide AC 7 instead of AC 1 but same powers, cost 500-700.

### Shirts

| Armor | AC | Weight | Cost | Material |
|-------|-----|--------|------|----------|
| Hawaiian Shirt | 10 | 5 | 3 | Cloth |
| T-Shirt | 10 | 5 | 2 | Cloth |

### Cloaks

| Cloak | AC | Weight | Cost | Material | Power |
|-------|-----|--------|------|----------|-------|
| Mummy Wrapping | 10 | 3 | 2 | Cloth | |
| Orcish Cloak | 10 | 10 | 40 | Cloth | |
| Dwarvish Cloak | 10 | 10 | 50 | Cloth | |
| Leather Cloak | 9 | 15 | 40 | Leather | |
| Oilskin Cloak | 9 | 10 | 50 | Cloth | |
| Elven Cloak | 9 | 10 | 60 | Cloth | Stealth |
| Alchemy Smock | 9 | 10 | 50 | Cloth | Poison Resistance |
| Robe | 8 | 15 | 50 | Cloth | Magical |
| Cloak of Protection | 7 | 10 | 50 | Cloth | Protection, MC +3 |
| Cloak of Invisibility | 9 | 10 | 60 | Cloth | Invisibility |
| Cloak of Magic Resistance | 9 | 10 | 60 | Cloth | Antimagic |
| Cloak of Displacement | 9 | 10 | 50 | Cloth | Displacement |

### Helmets

| Helmet | AC | Weight | Cost | Material | Power |
|--------|-----|--------|------|----------|-------|
| Fedora | 10 | 3 | 1 | Cloth | |
| Cornuthaum | 10 | 4 | 80 | Cloth | Clairvoyant |
| Dunce Cap | 10 | 4 | 1 | Cloth | |
| Elven Leather Helm | 9 | 3 | 8 | Leather | |
| Orcish Helm | 9 | 30 | 10 | Iron | |
| Dented Pot | 9 | 10 | 8 | Iron | |
| Helmet | 9 | 30 | 10 | Iron | |
| Dwarvish Iron Helm | 8 | 40 | 20 | Iron | |
| Helm of Brilliance | 9 | 50 | 50 | Iron | Magical |
| Helm of Opp. Alignment | 9 | 50 | 50 | Iron | Magical |
| Helm of Telepathy | 9 | 50 | 50 | Iron | Telepathy |

### Shields

| Shield | AC | Weight | Cost | Material | Power |
|--------|-----|--------|------|----------|-------|
| Small Shield | 9 | 30 | 3 | Wood | |
| Elven Shield | 8 | 40 | 7 | Wood | |
| Orcish Shield | 9 | 50 | 7 | Iron | |
| Uruk-hai Shield | 9 | 50 | 7 | Iron | |
| Dwarvish Roundshield | 8 | 100 | 10 | Iron | |
| Large Shield | 8 | 100 | 10 | Iron | |
| Shield of Reflection | 8 | 50 | 50 | Silver | Reflecting |

### Gloves

| Gloves | AC | Weight | Cost | Material | Power |
|--------|-----|--------|------|----------|-------|
| Leather Gloves | 9 | 10 | 8 | Leather | |
| Gauntlets of Fumbling | 9 | 10 | 50 | Leather | Fumbling |
| Gauntlets of Power | 9 | 30 | 50 | Iron | STR 25 |
| Gauntlets of Dexterity | 9 | 10 | 50 | Leather | DEX boost |

### Boots

| Boots | AC | Weight | Cost | Material | Power |
|-------|-----|--------|------|----------|-------|
| Low Boots | 9 | 10 | 8 | Leather | |
| High Boots | 8 | 20 | 12 | Leather | |
| Iron Shoes | 8 | 50 | 16 | Iron | |
| Elven Boots | 9 | 15 | 8 | Leather | Stealth |
| Kicking Boots | 9 | 50 | 8 | Iron | Kick bonus |
| Speed Boots | 9 | 20 | 50 | Leather | Fast |
| Water Walking Boots | 9 | 15 | 50 | Leather | Water Walking |
| Jumping Boots | 9 | 20 | 50 | Leather | Jumping |
| Fumble Boots | 9 | 20 | 30 | Leather | Fumbling |
| Levitation Boots | 9 | 15 | 30 | Leather | Levitation |

---

## Rings (Complete List)

| Ring | Cost | Material | Power |
|------|------|----------|-------|
| Adornment | 100 | Wood | Adorned (CHA boost) |
| Gain Strength | 150 | Mineral | STR +enchantment |
| Gain Constitution | 150 | Mineral | CON +enchantment |
| Increase Accuracy | 150 | Mineral | To-hit +enchantment |
| Increase Damage | 150 | Mineral | Damage +enchantment |
| Protection | 100 | Mineral | Protection, MC +1 |
| Regeneration | 200 | Mineral | Regeneration |
| Searching | 200 | Gemstone | Searching |
| Stealth | 100 | Gemstone | Stealth |
| Sustain Ability | 100 | Copper | Fixed Abilities |
| Levitation | 200 | Gemstone | Levitation |
| Hunger | 100 | Gemstone | Hunger (bad) |
| Aggravate Monster | 150 | Gemstone | Aggravate (bad) |
| Conflict | 300 | Gemstone | Conflict |
| Warning | 100 | Gemstone | Warning |
| Poison Resistance | 150 | Bone | Poison Resistance |
| Fire Resistance | 200 | Iron | Fire Resistance |
| Cold Resistance | 150 | Copper | Cold Resistance |
| Shock Resistance | 150 | Copper | Shock Resistance |
| Free Action | 200 | Iron | Free Action |
| Slow Digestion | 200 | Iron | Slow Digestion |
| Teleportation | 200 | Silver | Teleport (random) |
| Teleport Control | 300 | Gold | Teleport Control |
| Polymorph | 300 | Bone | Polymorph (random) |
| Polymorph Control | 300 | Gemstone | Polymorph Control |
| Invisibility | 150 | Iron | Invisibility |
| See Invisible | 150 | Iron | See Invisible |
| Prot. from Shape Changers | 100 | Iron | Shape Changer Protection |

Most rings increase hunger rate while worn (proportional to power level).
Maximum 2 rings worn simultaneously.

---

## Amulets (Complete List)

| Amulet | Cost | Material | Effect |
|--------|------|----------|--------|
| ESP | 150 | Iron | Telepathy |
| Life Saving | 150 | Iron | Revives on death |
| Strangulation | 150 | Iron | Slowly chokes (CURSED) |
| Restful Sleep | 150 | Iron | Forces sleep (CURSED) |
| Versus Poison | 150 | Iron | Poison Resistance |
| Change | 150 | Iron | Changes gender |
| Unchanging | 150 | Iron | Prevents polymorph |
| Reflection | 150 | Iron | Reflects beams |
| Magical Breathing | 150 | Iron | Breathe underwater/choke-immune |
| Cheap Plastic Imitation | 0 | Plastic | Worthless fake |
| Amulet of Yendor | 30000 | Mithril | Win condition artifact |

Maximum 1 amulet worn at a time.

---

## Potions (Complete List)

| Potion | Cost | Effect |
|--------|------|--------|
| Gain Ability | 300 | Increase random attribute |
| Restore Ability | 100 | Restore drained attributes |
| Confusion | 100 | Causes confusion |
| Blindness | 150 | Causes blindness |
| Paralysis | 300 | Causes paralysis |
| Speed | 200 | Grants speed |
| Levitation | 200 | Grants levitation |
| Hallucination | 100 | Causes hallucination |
| Invisibility | 150 | Grants invisibility |
| See Invisible | 50 | Grants see invisible |
| Healing | 100 | Restores HP |
| Extra Healing | 100 | Restores more HP |
| Full Healing | 200 | Restores all HP |
| Gain Level | 300 | Gain one experience level |
| Enlightenment | 200 | Shows character details |
| Monster Detection | 150 | Reveals all monsters |
| Object Detection | 150 | Reveals all objects |
| Gain Energy | 150 | Restores spell power |
| Sleeping | 100 | Causes sleep |
| Polymorph | 200 | Polymorphs drinker |
| Booze | 50 | Confusion + some nutrition |
| Sickness | 50 | Causes illness |
| Fruit Juice | 50 | Minor nutrition |
| Acid | 250 | Acid damage (cures stoning) |
| Oil | 250 | Fuel, can be applied as light source |
| Water | 100 | Holy (blessed) or unholy (cursed) |

All potions weigh 20. Identified by color (randomized per game).
Blessed/cursed status modifies effects (e.g., blessed healing heals more).

### Special Potion Mechanics

- Holy water (blessed): Damages undead, blesses dipped items
- Unholy water (cursed): Curses dipped items
- Potions can be thrown at monsters for various effects
- Potions can be dipped into each other (alchemy)
- Potions shatter when frozen (cold damage in inventory)

---

## Scrolls (Complete List)

| Scroll | Cost | Effect |
|--------|------|--------|
| Enchant Armor | 80 | +1 to worn armor |
| Destroy Armor | 100 | Destroys piece of armor |
| Confuse Monster | 100 | Next hit confuses target |
| Scare Monster | 100 | Monsters avoid the tile (when on floor) |
| Remove Curse | 80 | Uncurses inventory items |
| Enchant Weapon | 60 | +1 to wielded weapon |
| Create Monster | 200 | Creates random monsters |
| Taming | 200 | Tames adjacent monsters |
| Genocide | 300 | Eliminate a monster species |
| Light | 50 | Lights the area |
| Teleportation | 100 | Teleports reader |
| Gold Detection | 100 | Detects gold (or traps if confused) |
| Food Detection | 100 | Detects food |
| Identify | 20 | Identifies items |
| Magic Mapping | 100 | Reveals entire level map |
| Amnesia | 200 | Forgets map/discoveries |
| Fire | 100 | Fire damage in area |
| Earth | 200 | Boulders fall from ceiling |
| Punishment | 300 | Ball and chain attached |
| Charging | 300 | Recharges wands/tools |
| Stinking Cloud | 300 | Creates poison cloud |
| Blank Paper | 60 | Nothing (can write on with marker) |
| Mail | 0 | Delivers message |

All scrolls weigh 5. Identified by random label (randomized per game).
Reading while confused can produce different effects for many scrolls.

---

## Spellbooks and Spells (Complete List)

### Spell Schools

Seven categories: Attack, Healing, Divination, Enchantment, Clerical, Escape, Matter

### All Spells

| Spell | Level | Cost | School |
|-------|-------|------|--------|
| Protection | 1 | 100 | Clerical |
| Jumping | 1 | 100 | Escape |
| Light | 1 | 100 | Divination |
| Detect Monsters | 1 | 100 | Divination |
| Healing | 1 | 100 | Healing |
| Knock | 1 | 100 | Matter |
| Force Bolt | 1 | 100 | Attack |
| Sleep | 1 | 100 | Enchantment |
| Confuse Monster | 2 | 200 | Enchantment |
| Cure Blindness | 2 | 200 | Healing |
| Drain Life | 2 | 200 | Attack |
| Slow Monster | 2 | 200 | Enchantment |
| Wizard Lock | 2 | 200 | Matter |
| Create Monster | 2 | 200 | Clerical |
| Detect Food | 2 | 200 | Divination |
| Magic Missile | 2 | 200 | Attack |
| Cause Fear | 3 | 300 | Enchantment |
| Clairvoyance | 3 | 300 | Divination |
| Cure Sickness | 3 | 300 | Healing |
| Charm Monster | 3 | 300 | Enchantment |
| Haste Self | 3 | 300 | Escape |
| Detect Unseen | 3 | 300 | Divination |
| Extra Healing | 3 | 300 | Healing |
| Remove Curse | 3 | 300 | Clerical |
| Stone to Flesh | 3 | 300 | Healing |
| Identify | 3 | 300 | Divination |
| Levitation | 4 | 400 | Escape |
| Restore Ability | 4 | 400 | Healing |
| Invisibility | 4 | 400 | Escape |
| Detect Treasure | 4 | 400 | Divination |
| Cone of Cold | 4 | 400 | Attack |
| Fireball | 4 | 400 | Attack |
| Dig | 5 | 500 | Matter |
| Magic Mapping | 5 | 500 | Divination |
| Turn Undead | 6 | 600 | Clerical |
| Polymorph | 6 | 600 | Matter |
| Teleport Away | 6 | 600 | Escape |
| Create Familiar | 6 | 600 | Clerical |
| Cancellation | 7 | 700 | Matter |
| Finger of Death | 7 | 700 | Attack |

Plus: Book of the Dead (level 7, 10000 cost, artifact)

All spellbooks weigh 50.

### Spell Mechanics

**Energy Cost**: spell_level * 5 (range 5-35)

**Hunger Cost**: 2x energy value, halved for Wizards with INT 15+

**Memory Retention**: Base 20,000 turns (KEEN constant). Decays over time.
Must relearn when memory drops below threshold.

**Failure Rate Factors**:
- Role base casting value
- Metallic armor penalties: body armor -2 to -4; shields -2 to -4; helmets +4;
  gauntlets +6; footwear +2
- Non-light shields: divide success by 2 (role spells) or 4 (other spells)
- Robes partially offset armor penalties
- Character stat (INT or WIS): base 5.5x score
- Spell level difficulty relative to caster level
- Skill level: up to +20 bonus at expert

**Skill Effects**:
- Unskilled: baseline only
- Skilled: blessed effects on certain spells
- Expert: significant power increases, fireball/cone scatter targeting

---

## Wands (Complete List)

| Wand | Cost | Material | Type |
|------|------|----------|------|
| Light | 100 | Glass | Non-directional |
| Secret Door Detection | 150 | Wood | Non-directional |
| Enlightenment | 150 | Glass | Non-directional |
| Create Monster | 200 | Wood | Non-directional |
| Wishing | 500 | Wood | Non-directional |
| Nothing | 100 | Wood | Non-directional |
| Striking | 150 | Wood | Immediate |
| Make Invisible | 150 | Mineral | Immediate |
| Slow Monster | 150 | Metal | Immediate |
| Speed Monster | 150 | Copper | Immediate |
| Undead Turning | 150 | Copper | Immediate |
| Polymorph | 200 | Silver | Immediate |
| Cancellation | 200 | Platinum | Immediate |
| Teleportation | 200 | Metal | Immediate |
| Opening | 150 | Metal | Immediate |
| Locking | 150 | Metal | Immediate |
| Probing | 150 | Metal | Immediate |
| Digging | 150 | Iron | Ray |
| Magic Missile | 150 | Iron | Ray |
| Fire | 175 | Iron | Ray |
| Cold | 175 | Iron | Ray |
| Sleep | 175 | Iron | Ray |
| Death | 500 | Iron | Ray |
| Lightning | 175 | Iron | Ray |

All wands weigh 7.

### Wand Mechanics

- **Charges**: Finite, decrease per use
- **Recharging**: Via scroll of charging. Risk of explosion increases per recharge.
- **Zero charges**: Usually fail; rare squeeze possibility (destroys wand)
- **Breaking** (via `a` apply command): Releases catastrophic magic burst
- **Self-targeting**: `.` or `s` direction
- **Wand types**: NODIR (non-directional), IMMEDIATE (beam to target), RAY (bouncing beam)
- Inventory display shows (recharges:charges), -1 charge = cancelled

---

## Tools (Complete List)

### Containers

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Large Box | 350 | 8 | Wood |
| Chest | 600 | 16 | Wood |
| Ice Box | 900 | 42 | Plastic |
| Sack | 15 | 2 | Cloth |
| Oilskin Sack | 15 | 100 | Cloth |
| Bag of Holding | 15 | 100 | Cloth (magical) |
| Bag of Tricks | 15 | 100 | Cloth (magical) |

### Lock Tools

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Skeleton Key | 3 | 10 | Iron |
| Lock Pick | 4 | 20 | Iron |
| Credit Card | 1 | 10 | Plastic |

### Light Sources

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Tallow Candle | 2 | 10 | Wax |
| Wax Candle | 2 | 20 | Wax |
| Brass Lantern | 30 | 12 | Copper |
| Oil Lamp | 20 | 10 | Copper |
| Magic Lamp | 20 | 50 | Copper (magical) |

### Instruments

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Tin Whistle | 3 | 10 | Metal |
| Magic Whistle | 3 | 10 | Metal (magical) |
| Wooden Flute | 5 | 12 | Wood |
| Magic Flute | 5 | 36 | Wood (magical) |
| Tooled Horn | 18 | 15 | Bone |
| Frost Horn | 18 | 50 | Bone (magical) |
| Fire Horn | 18 | 50 | Bone (magical) |
| Horn of Plenty | 18 | 50 | Bone (magical) |
| Wooden Harp | 30 | 50 | Wood |
| Magic Harp | 30 | 50 | Wood (magical) |
| Bell | 30 | 50 | Copper |
| Bugle | 10 | 15 | Copper |
| Leather Drum | 25 | 25 | Leather |
| Drum of Earthquake | 25 | 25 | Leather (magical) |

### Other Tools

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Expensive Camera | 12 | 200 | Plastic |
| Mirror | 13 | 10 | Glass |
| Crystal Ball | 150 | 60 | Glass (magical) |
| Lenses | 3 | 80 | Glass |
| Blindfold | 2 | 20 | Cloth |
| Towel | 2 | 50 | Cloth |
| Saddle | 200 | 150 | Leather |
| Leash | 12 | 20 | Leather |
| Stethoscope | 4 | 75 | Iron |
| Tinning Kit | 100 | 30 | Iron |
| Tin Opener | 4 | 30 | Iron |
| Can of Grease | 15 | 20 | Iron |
| Figurine | 50 | 80 | Mineral (magical) |
| Magic Marker | 2 | 50 | Plastic (magical) |

### Trap Tools

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Land Mine | 300 | 180 | Iron |
| Beartrap | 200 | 60 | Iron |

### Weapon-Tools

| Tool | Damage | Weight | Cost | Material |
|------|--------|--------|------|----------|
| Pick-Axe | 6/3 | 100 | 50 | Iron |
| Grappling Hook | 2/6 | 30 | 50 | Iron |
| Unicorn Horn | 12/12 | 20 | 100 | Bone (magical) |

### Unique Artifacts

| Tool | Weight | Cost | Material |
|------|--------|------|----------|
| Candelabrum of Invocation | 10 | 5000 | Gold |
| Bell of Opening | 10 | 5000 | Silver |

---

## Food (Complete List)

### Meat

| Food | Weight | Nutrition | Material |
|------|--------|-----------|----------|
| Tripe Ration | 10 | 200 | Flesh |
| Corpse | 0 | varies | Flesh |
| Egg | 1 | 80 | Flesh |
| Meatball | 1 | 5 | Flesh |
| Meat Stick | 1 | 5 | Flesh |
| Huge Chunk of Meat | 400 | 2000 | Flesh |
| Meat Ring | 5 | 5 | Flesh |

### Pudding Globs

| Food | Weight | Nutrition | Material |
|------|--------|-----------|----------|
| Glob of Gray Ooze | 20 | 20 | Flesh |
| Glob of Brown Pudding | 20 | 20 | Flesh |
| Glob of Green Slime | 20 | 20 | Flesh |
| Glob of Black Pudding | 20 | 20 | Flesh |

### Fruits and Vegetables

| Food | Weight | Nutrition | Material |
|------|--------|-----------|----------|
| Kelp Frond | 1 | 30 | Veggy |
| Eucalyptus Leaf | 1 | 30 | Veggy |
| Apple | 2 | 50 | Veggy |
| Orange | 2 | 80 | Veggy |
| Pear | 2 | 50 | Veggy |
| Melon | 5 | 100 | Veggy |
| Banana | 2 | 80 | Veggy |
| Carrot | 2 | 50 | Veggy |
| Sprig of Wolfsbane | 1 | 40 | Veggy |
| Clove of Garlic | 1 | 40 | Veggy |
| Slime Mold | 5 | 250 | Veggy |

### Prepared Food

| Food | Weight | Nutrition | Material |
|------|--------|-----------|----------|
| Lump of Royal Jelly | 2 | 200 | Veggy |
| Cream Pie | 10 | 100 | Veggy |
| Candy Bar | 2 | 100 | Veggy |
| Fortune Cookie | 1 | 40 | Veggy |
| Pancake | 2 | 200 | Veggy |
| Lembas Wafer | 5 | 800 | Veggy |
| Cram Ration | 15 | 600 | Veggy |
| Food Ration | 20 | 800 | Veggy |
| K-Ration | 10 | 400 | Veggy |
| C-Ration | 10 | 300 | Veggy |

### Tinned Food

| Food | Weight | Nutrition | Material |
|------|--------|-----------|----------|
| Tin | 10 | varies | Metal |

Tin nutrition depends on preparation: rotten (-50) to pureed (500).
Spinach tins grant STR bonus (400-600 nutrition).

---

## Gems and Stones (Complete List)

### Valuable Gems (all weigh 1, Gemstone material)

| Gem | Cost |
|-----|------|
| Dilithium Crystal | 4500 |
| Diamond | 4000 |
| Ruby | 3500 |
| Jacinth | 3250 |
| Sapphire | 3000 |
| Black Opal | 2500 |
| Emerald | 2500 |
| Turquoise | 2000 |
| Citrine | 1500 |
| Aquamarine | 1500 |
| Amber | 1000 |
| Topaz | 900 |
| Jet | 850 |
| Opal | 800 |
| Chrysoberyl | 700 |
| Garnet | 700 |
| Amethyst | 600 |
| Jasper | 500 |
| Fluorite | 400 |
| Jade | 300 |
| Obsidian | 200 |
| Agate | 200 |

9 colors of Worthless Glass (cost 0, Glass material)

### Stones (all Mineral material)

| Stone | Weight | Cost | Damage | Special |
|-------|--------|------|--------|---------|
| Luckstone | 10 | 60 | 3/3 | Prevents luck decay |
| Loadstone | 500 | 1 | 3/3 | Cursed, extremely heavy |
| Touchstone | 10 | 45 | 3/3 | Identifies gems |
| Flint | 10 | 1 | 6/6 | Ammo for slings |
| Rock | 10 | 0 | 3/3 | Basic ammo |

### Large Rocks

| Item | Weight | Damage | Notes |
|------|--------|--------|-------|
| Boulder | 6000 | 20/20 | Thrown by giants |
| Statue | 2500 | 20/20 | Can be container, statue trap |

---

## Monsters

### Monster Classes by Symbol

| Symbol | Class | Examples |
|--------|-------|---------|
| a | Ants | Giant ant, killer bee, soldier ant, fire ant, queen bee |
| b | Blobs | Acid blob, quivering blob, gelatinous cube |
| c | Cockatrices | Chickatrice, cockatrice, pyrolisk |
| d | Canines | Jackal, fox, coyote, werejackal, dogs, wolves, hell hound |
| e | Eyes | Gas spore, floating eye, freezing/flaming/shocking sphere |
| f | Felines | Kitten, housecat, jaguar, panther, tiger |
| g | Gremlins | Gremlin, gargoyle, winged gargoyle |
| h | Humanoids | Hobbit, dwarf, bugbear, mind flayer, master mind flayer |
| i | Imps | Manes, homunculus, imp, lemure, quasit, tengu |
| j | Jellies | Blue jelly, spotted jelly, ochre jelly |
| k | Kobolds | Kobold, large kobold, kobold lord, kobold shaman |
| l | Leprechauns | Leprechaun |
| m | Mimics | Small, large, giant mimics |
| n | Nymphs | Wood, water, mountain nymphs |
| o | Orcs | Goblin, hobgoblin, orc, hill orc, Mordor orc, Uruk-hai |
| p | Piercers | Rock, iron, glass piercers |
| q | Quadrupeds | Rothe, mumak, leocrotta, wumpus, titanothere, mastodon |
| r | Rodents | Sewer rat, giant rat, rabid rat, wererat, rock mole |
| s | Spiders | Cave spider, centipede, giant spider, scorpion |
| t | Trappers | Lurker above, trapper |
| u | Unicorns | Pony, white/gray/black unicorn, horse, warhorse |
| v | Vortices | Fog cloud, dust/ice/energy/steam/fire vortex |
| w | Worms | Baby/adult long worm, baby/adult purple worm |
| x | Xan | Grid bug, xan |
| y | Lights | Yellow light, black light |
| z | Zruty | Zruty |
| A | Angels | Couatl, Aleax, Angel, ki-rin, Archon |
| B | Bats | Bat, giant bat, raven, vampire bat |
| C | Centaurs | Plains, forest, mountain centaurs |
| D | Dragons | 9 colors (baby and adult): gray, silver, red, white, orange, black, blue, green, yellow |
| E | Elementals | Stalker, air/fire/earth/water elementals |
| F | Fungi | Lichen, brown/yellow/green/red mold, shrieker, violet fungus |
| G | Gnomes | Gnome, gnome lord, gnomish wizard, gnome king |
| H | Giants | Giant, stone/hill/fire/frost giant, ettin, storm giant, titan, minotaur |
| I | (invisible marker) | Not a monster class |
| J | Jabberwock | Jabberwock |
| K | Kops | Keystone Kop, Kop Sergeant, Kop Lieutenant, Kop Kaptain |
| L | Liches | Lich, demilich, master lich, arch-lich |
| M | Mummies | Kobold, gnome, orc, dwarf, elf, human, ettin, giant mummies |
| N | Nagas | Red, black, golden, guardian nagas (hatchling + adult) |
| O | Ogres | Ogre, ogre lord, ogre king |
| P | Puddings | Gray ooze, brown pudding, green slime, black pudding |
| Q | Quantum mechanic | Quantum mechanic |
| R | Rust monsters | Rust monster, disenchanter |
| S | Snakes | Garter snake, snake, water moccasin, python, pit viper, cobra |
| T | Trolls | Troll, ice/rock/water troll, Olog-hai |
| U | Umber hulk | Umber hulk |
| V | Vampires | Vampire, vampire lord, Vlad the Impaler |
| W | Wraiths | Barrow wight, wraith, Nazgul |
| X | Xorn | Xorn |
| Y | (not used) | |
| Z | Zombies | (various) |

### Monster Attack Types

| Code | Type |
|------|------|
| AT_NONE | Passive (acid blob) |
| AT_CLAW | Claw/punch/hit |
| AT_BITE | Bite |
| AT_KICK | Kick |
| AT_BUTT | Head butt (unicorn) |
| AT_TUCH | Touch |
| AT_STNG | Sting |
| AT_HUGS | Crushing bearhug |
| AT_SPIT | Spit (ranged) |
| AT_ENGL | Engulf/swallow |
| AT_BREA | Breath (ranged) |
| AT_EXPL | Explode (proximity) |
| AT_BOOM | Explode on death |
| AT_GAZE | Gaze (ranged) |
| AT_TENT | Tentacles |
| AT_WEAP | Uses weapon |
| AT_MAGC | Uses magic spells |

### Monster Damage Types

| Code | Effect |
|------|--------|
| AD_PHYS | Physical damage |
| AD_MAGM | Magic missiles |
| AD_FIRE | Fire damage |
| AD_COLD | Frost damage |
| AD_SLEE | Sleep |
| AD_DISN | Disintegration |
| AD_ELEC | Shock |
| AD_DRST | Drain STR (poison) |
| AD_ACID | Acid |
| AD_BLND | Blind |
| AD_STUN | Stun |
| AD_SLOW | Slow |
| AD_PLYS | Paralyze |
| AD_DRLI | Drain life levels |
| AD_DREN | Drain magic energy |
| AD_LEGS | Damage legs |
| AD_STON | Petrify |
| AD_STCK | Stick (mimic) |
| AD_SGLD | Steal gold |
| AD_SITM | Steal item |
| AD_SEDU | Seduce and steal multiple |
| AD_TLPT | Teleport target |
| AD_RUST | Rust armor |
| AD_CONF | Confuse |
| AD_DGST | Digest (swallow) |
| AD_HEAL | Heal target (nurse) |
| AD_WRAP | Eel wrap/stick |
| AD_WERE | Confer lycanthropy |
| AD_DRDX | Drain DEX |
| AD_DRCO | Drain CON |
| AD_DRIN | Drain INT (mind flayer) |
| AD_DISE | Confer disease |
| AD_DCAY | Decay organics |
| AD_SSEX | Succubus seduction |
| AD_HALU | Hallucination |
| AD_DETH | Death (for Death only) |
| AD_PEST | Pestilence (for Pestilence only) |
| AD_FAMN | Famine (for Famine only) |
| AD_SLIM | Turn to green slime |
| AD_ENCH | Remove enchantment |
| AD_CORR | Corrode armor |
| AD_CLRC | Random clerical spell |
| AD_SPEL | Random magic spell |
| AD_RBRE | Random breath weapon |
| AD_SAMU | Hit + steal Amulet (Wizard) |
| AD_CURS | Random curse (gremlin) |

### Monster Resistances

Primary: MR_FIRE, MR_COLD, MR_SLEEP, MR_DISINT, MR_ELEC, MR_POISON, MR_ACID, MR_STONE

Secondary: SEE_INVIS, LEVITATE, WATERWALK, MAGICAL_BREATHING, DISPLACED, STRENGTH, FUMBLING

### Monster Movement and Ability Flags

- FLY, SWIM, AMORPHOUS (flow under doors), WALLWALK (phase through rock)
- CLING (ceiling), TUNNEL, NEEDPICK (needs pick to tunnel)
- CONCEAL (hides under objects), HIDE (mimics/ceiling blenders)
- AMPHIBIOUS, BREATHLESS, NOTAKE (can't pick up)
- NOEYES, NOHANDS, NOLIMBS, NOHEAD, MINDLESS
- HUMANOID, ANIMAL, SLITHY (serpent), UNSOLID
- THICK_HIDE, OVIPAROUS (lays eggs), REGEN (regenerates)
- SEE_INVIS, TPORT, TPORT_CNTRL
- ACID (acidic to eat), POIS (poisonous to eat)
- CARNIVORE, HERBIVORE, OMNIVORE, METALLIVORE

### Monster Behavior Flags

- NOPOLY, UNDEAD, WERE (lycanthrope), DEMON
- HUMAN, ELF, DWARF, GNOME, ORC (race flags)
- MERC (guard/soldier), LORD, PRINCE, MINION
- GIANT, SHAPESHIFTER
- MALE, FEMALE, NEUTER, PNAME (proper name)
- HOSTILE (always hostile), PEACEFUL (always peaceful)
- DOMESTIC (tameable by feeding), WANDER, STALK (follows levels)
- NASTY (extra XP), STRONG, ROCKTHROW
- GREEDY (likes gold), JEWELS (likes gems)
- COLLECT (picks up weapons/food), MAGIC (picks up magic items)

### Monster Generation Flags

- G_UNIQ: Generated only once
- G_NOHELL: Not in Gehennom
- G_HELL: Only in Gehennom
- G_NOGEN: Only via special generation
- G_SGROUP: Appears in small groups
- G_LGROUP: Appears in large groups
- G_GENO: Can be genocided
- G_NOCORPSE: Never leaves a corpse

### Monster Sizes

- MZ_TINY: < 2 feet
- MZ_SMALL: 2-4 feet
- MZ_MEDIUM/HUMAN: 4-7 feet
- MZ_LARGE: 7-12 feet
- MZ_HUGE: 12-25 feet
- MZ_GIGANTIC: Off the scale

---

## Pets

### Creation

Starting pet is role-dependent (dog, cat, or pony). Can also be created via
figurines, taming scrolls, charm monster spell, and feeding domestic monsters.

### Tameness

- Domestic creatures start at tameness 10
- Others start at tameness 5
- Range: 0 (wild) to domestic rating
- Feeding appropriate food increases tameness
- Abuse decreases tameness

### Pet AI Behavior

- Equips weapons (martial-capable pets)
- Follows player between levels when nearby and awake
- Eats based on diet: carnivores eat meat, herbivores eat plants
- Starving pets eat almost anything
- Pets gain XP from kills and can grow/evolve

### Level Transitions

Pets follow if:
- Adjacent to player
- Conscious and mobile
- Not eating or trapped
- Leashed pets always follow

Migrating pets heal proportionally to separation duration.

### Abuse System

- Attacking pet reduces tameness
- Aggravate Monster amplifies abuse
- Conflict aura halves abuse rate
- Abuse counter > 2: permanent feral on revival
- Killed-by-player pets revive wild unless abuse was minimal

### Taming Rules

Cannot tame: Wizard of Yendor, Medusa, artifact-desiring creatures, humanoids
(most), some demons, quest nemeses.

---

## BUC (Blessed / Uncursed / Cursed) System

### Three States

- **Blessed**: Enhanced positive effects, holy water is blessed water
- **Uncursed**: Standard behavior
- **Cursed**: Negative effects, items may stick when worn/wielded

### Detection Methods

- Priests/Priestesses sense BUC status naturally
- Drop items on altars: flash indicates curse status
- Scroll of identify reveals BUC
- Pet behavior near items (pets avoid cursed, approach blessed)

### Key BUC Interactions

**Weapons**: Cursed weapons weld to hands (cannot unwield)
**Armor**: Cursed armor sticks to body (cannot remove)
**Rings/Amulets**: Cursed accessories cannot be removed
**Scrolls**: BUC modifies many scroll effects
**Potions**: Blessed healing heals more; cursed less
**Tools**: Cursed tools malfunction or have negative effects
**Holy Water**: Blessed water blesses items dipped in it
**Unholy Water**: Cursed water curses items dipped in it

### Changing BUC Status

- Dip in holy water: uncursed -> blessed, cursed -> uncursed
- Dip in unholy water: uncursed -> cursed, blessed -> uncursed
- Scroll of remove curse: uncurses inventory items (blessed = all items)
- Prayer: may uncurse items when god is pleased
- Cancellation: resets BUC to uncursed

---

## Identification

### Unknown Items

Items start unidentified with random appearances:
- Scrolls have random labels (e.g., "READ ME", "THANX MAUD")
- Potions have random colors
- Rings have random materials/colors
- Wands have random materials
- Spellbooks have random colors
- Gems may appear as colored stones

### Identification Methods

- **Scroll of Identify**: Reveals item type, BUC, charges/enchantment
- **Spellbook of Identify**: Same as scroll, reusable
- **Use-testing**: Using an item reveals its type through effects
- **Price identification**: Shop prices can narrow down item type
- **Naming** (`#name`): Player can assign custom labels
- **Stethoscope**: Reveals monster stats
- **Touchstone**: Identifies gems when rubbed
- **Altar testing**: Reveals BUC status

### Formal Identification

Reveals: item type, BUC status, enchantment level, remaining charges,
erosion level, and other hidden properties.

---

## Religion and Prayer

### Prayer Mechanics

Prayer takes 3 turns. During prayer, character may become invulnerable
(if coaligned altar, not in Gehennom).

### Prayer Timeout

- Starting the game counts as receiving divine help
- Praying too soon after help: gods become upset (+250 turns to bless counter, -3 luck)
- Safe prayer requires bless counter below threshold

### Prayer Outcomes (based on alignment, luck, and timing)

**Successful Prayer** fixes troubles in priority order:

14 major troubles (highest priority):
- Fatal conditions (stoning, sliming, strangulation, sickness)
- Starvation
- Being engulfed
- Being stuck in lava

Minor troubles (lower priority):
- Punished (ball and chain)
- Blindness, confusion, hallucination
- Cursed items, wounded legs

**Action levels**:
- Action 5: Fix all troubles + special favor
- Action 4: Fix all troubles
- Action 3: Fix worst major + attempt others
- Action 1-2: Fix worst only
- Action 0: Rejection

### Sacrifice at Altars

- Corpse value = monster difficulty + 1 (max 24)
- Same-race sacrifice: -5 alignment, +3 anger (unless chaotic)
- Unicorn horn sacrifice: alignment bonus based on color/deity match
- Real Amulet of Yendor on coaligned high altar = ascension victory

### Crowning

At DEVOUT alignment (14+), prayer success grants crowning with artifact weapon:
- **Lawful**: Excalibur (Hand of Elbereth)
- **Neutral**: Vorpal Blade (Envoy of Balance)
- **Chaotic**: Stormbringer (Soul Stealer)

All crowning grants: fire/cold/shock/sleep/poison resistance, see invisible.

### God Anger

Maximum anger = `3 * anger + luck_adjustments` (capped at 15)

Responses escalate:
- Minor: Displeasure
- Moderate: Wisdom loss, XP drain, random curses
- Severe: Punishment, summoned minions, divine lightning

---

## Kicking

### Command

`^D` or `#kick`

### Kicking Monsters

Base damage: `(STR + DEX + CON) / 15`

Modifiers:
- Kicking boots: +5
- Encumbrance: halves damage
- Martial arts: +rn2(DEX/2 + 1)
- Ring of increase damage adds bonus
- Boot enchantment adds spe

Monster evasion requires: can see, not trapped, speed >= 12, not stunned/sleeping.

Martial kick: 30% chance to knock non-giant monster back one square.

### Kicking Doors

Success: `rnl(35) < avrg_attrib + (martial ? DEX : 0)`
Where avrg_attrib = `(STR + DEX + CON) / 3` (or 99 with kicking boots)

### Kicking Objects

Range: `(STR / 2) - (weight / 40) + martial_bonus`
- Ice/grease adds rnd(3) range
- Coins scatter in multiple directions
- Glass items may break
- Containers may pop open or trigger traps

### Kicking Environmental Features

- **Thrones**: Destroy for gold or luck penalty
- **Altars**: Trigger divine wrath
- **Fountains**: Risk contaminated water damage
- **Graves**: Alignment penalties for desecration
- **Trees**: Yield fruit or trigger killer bee swarm
- **Sinks**: Summon pudding, dish washer, or ring
- **Walls**: Hurt yourself (usually)

### Restrictions

Cannot kick if: no limbs, serpentine, too small, riding, wounded legs,
overloaded, polymorphed into lizard, submerged, or trapped.

---

## Engraving and Elbereth

### Engraving Commands

`E` or `#engrave`

### Tools for Engraving

- **Fingers**: Dust engraving (fragile)
- **Bladed weapons**: Permanent engraving (requires enchantment > -3)
- **Wands**: Various effects (fire = burn, digging = carved, others may have special effects)
- **Gems/Rings**: Hard materials work
- **Magic Markers**: Graffiti-type marks (uses charges)
- **Towel**: Wipes existing engravings

### Elbereth

Engraving "Elbereth" exercises Wisdom and deters most monsters from stepping
on the square. Effectiveness depends on engraving type:
- Dust: Fragile, erased by walking over
- Burned/Carved: More durable
- Effect: Monsters flee from Elbereth squares (most, not all -- Elbereth-ignoring monsters include the Riders, Vlad, and some others)

### Engraving Degradation

Characters are randomly corrupted over time via wipeout_text function.
Dust engravings degrade fastest.

---

## Commands Reference

### Movement

| Key | Action |
|-----|--------|
| y/k/u/h/l/b/j/n | Move one step (or numpad) |
| Y/K/U/H/L/B/J/N | Move until obstacle |
| m+dir | Move without fighting/pickup |
| F+dir | Force fight at location |
| g+dir | Move until interesting |
| G+dir | Move, ignore corridor forks |
| `<` | Go up stairs |
| `>` | Go down stairs |
| `.` | Wait/rest one turn |
| `_` | Travel (pathfinding) |

### Items

| Key | Action |
|-----|--------|
| i | Inventory |
| I | Inventory by type |
| `,` | Pick up |
| d | Drop |
| D | Drop by type |
| w | Wield weapon |
| W | Wear armor |
| T | Take off armor |
| P | Put on ring/amulet |
| R | Remove ring/amulet |
| A | Remove all equipment |
| x | Exchange primary/secondary |
| X | Toggle two-weapon |
| Q | Select quiver |

### Combat and Magic

| Key | Action |
|-----|--------|
| t | Throw |
| f | Fire quivered ammo |
| Z | Cast spell |
| z | Zap wand |
| r | Read scroll/spellbook |
| `+` | List known spells |

### Consumables

| Key | Action |
|-----|--------|
| e | Eat |
| q | Quaff potion |

### Interaction

| Key | Action |
|-----|--------|
| o | Open door |
| c | Close door |
| ^D | Kick |
| a | Apply tool |
| E | Engrave |
| s | Search |
| p | Pay shop bill |

### Information

| Key | Action |
|-----|--------|
| `:` | Look at current location |
| `;` | Show symbol at location |
| `/` | Identify symbol type |
| `\` | Show discovered items |
| `$` | Count gold |
| ^X | Character info |
| ^P | Repeat previous message |

### Extended Commands (#)

| Command | Action |
|---------|--------|
| #pray | Request divine help |
| #offer | Sacrifice at altar |
| #turn | Turn undead |
| #chat | Talk to adjacent NPC |
| #dip | Dip item in substance |
| #force | Force lock |
| #loot | Open container on floor |
| #tip | Pour out container |
| #untrap | Disarm trap |
| #enhance | Advance skills |
| #adjust | Reorganize inventory |
| #name / #call | Name things |
| #jump | Jump |
| #kick | Kick |
| #ride | Mount/dismount |
| #sit | Sit down |
| #wipe | Clean face |
| #monster | Use polymorphed abilities |
| #conduct | Show voluntary challenges |
| #overview | Show visited levels |
| #annotate | Add level notes |
| #teleport | Self-teleport (if able) |

---

## Object Materials

21 material types: liquid, wax, veggy, flesh, paper, cloth, leather, wood,
bone, dragon_hide, iron, metal, copper, silver, gold, platinum, mithril,
plastic, glass, gemstone, mineral.

Material properties:
- **Organic**: veggy, flesh, paper, cloth, leather, wood
- **Metallic**: iron, metal, copper, silver, gold, platinum, mithril
- **Rust-prone**: iron
- **Corrodeable**: iron, copper
- **Silver**: Extra damage to undead and demons
- **Mithril**: Does not rust, lightweight

---

## Weapon Damage Types

- **Pierce** (1): Spears, daggers, arrows
- **Slash** (2): Swords, axes, most bladed weapons
- **Whack** (0): Maces, clubs, hammers

---

## Voluntary Challenges (Conducts)

Players can self-impose for bragging rights:

- **Foodless**: No eating (except beverages/divine help)
- **Vegetarian**: No animal corpses/products
- **Vegan**: Plant matter only
- **Atheist**: No praying, sacrificing, undead-turning
- **Pacifist**: No killing monsters
- **Weaponless**: No wielded weapons
- **Illiterate**: No reading/writing
- **Genocide-free**: No species elimination
- **Polymorph-free**: No self-polymorph
- **Wishless**: No wishes

---

## Winning the Game

- Descend through the Dungeons of Doom (25+ levels)
- Navigate Gehennom (hellish maze)
- Retrieve the Amulet of Yendor from the Sanctum
- Ascend back through the dungeon
- Travel through the Elemental Planes (Earth, Air, Fire, Water)
- Reach the Astral Plane
- Offer the Amulet of Yendor at your aligned deity's altar
- Ascend to demigod status
