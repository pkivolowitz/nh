# PNH - Perry's NetHack

## Stairways

Unlike NetHack, up and down stairs in PNH can be in the same room.

Stairways are automatically entered into your notebook as you
encounter them (and will remain visible after you leave the room
in which they are found).

## Doorways

There are no doors in PNH. You're roaming underground caverns.

This also means there are no secret doors.

You can still block critters from entering a room using the more general
*blocking spell* which makes it difficult or impossible for critters to
cross into.

*Design Note:* Doors in NetHack were, in our view, mostly a time
wasting nuisance. We have chosen to remove them entirely.

## Illumination

Lighting in PNH is very different from NetHack in that in PNH all rooms
are dark.

Nothing beyond your torch is visible unless it has been noted
in your notebook. Walls and corridors you encounter are entered into
your notebook automatically so that as you explore, your notebook builds
up a map of each level. Stairways are also automatically entered into
your notebook.

You may choose to manually enter specific locations into your notebook.
Such locations will continue to be drawn after you leave the room in
which they are found.

The NetHack lighting spells would cause all locations within a certain
radius to remain illuminated even after you left the room. This is not
modeled in PNH. In PNH, a lighting spell simply increases the range of
your torch. This has the advantage of you being able to see farther but
it also means critters can see *you* from further away.

*Gameplay Note:* That all rooms are dark has the consequence that a
player peeking into a lit room will *not* see the whole room - the
room will <u>have</u> to be explored.

*Design Note:* These decisions were made to regularize how lighting
is handled - all room cells are handled the same way and honor a more
"real-world" ethos. The idea of keeping a notebook is a reasonable one.
Marking stairs, walls and corridors would make sense to add to your
notebook as you explore the caves.

## Spells

There are many spells in NetHack. There are anticipated to be fewer in
PNH however, the way in which spells are cast in PNH allows for one PNH
spell to do the work of potentially several from NetHack.

NetHack spellcasting requires:

* knowledge of a spell

* sufficient player level to master a spell

* sufficient power points to cast a spell

NetHack spell knowledge expires after a fixed number of turns past
learning or relearning.

A small number of NetHack spells vary their behavior based upon the
mastery of the spell class (attack, for example).

All NetHack spells require a single turn to cast.

Spellcasting in PNH requires:

* knowledge of a spell

* sufficient player level to cast at desired power

* sufficient Concentration points to cast at desired power

Most PNH spells vary their behavior based upon the amount of
Concentration the caster is willing to spend.

PNH spell knowledge retention is based on practice and use of the spell.
Spells used frequently, for example, become second nature and will never
be forgotten.

Higher Concentration expends more concentration points, takes longer
to cast and imparts more powerful effects.

### Spells and Concentration

The NetHack Power stat is replaced in PNH by the Concentration stat
(CStat). The CStat factors into many aspects of the player's capability,
not just spellcasting.

Spells maybe be cast at varying levels of Concentration, ranging from 1
to 5 roughly equating to the power of the spell.

### Fireball --> Fire

Fireball in NH is an attack spell. Fire in PNH serves multiple roles
depending upon the Concentration applied by the caster.

Concentration 1 Fire spells require 1 turn to cast and have a maximum
range of 0. That is, it is akin to lighting a match (and as
such can minimally illuminate your surroundings briefly or light
something in your possession on fire).

Concentration 2 through 4 Fire spells require 2 turns to cast and have
a maximum range of twice the Concentration used subject to practice.

Fire cast at Concentration levels 2 through 5 continue to burn for
up to four times the Concentration used turns subject to practice. While
burning, the fire illuminates its surroundings and continues to do
damage to anything within its flames. Damage caused by a fire spell is
similarly enhanced by increased Concentration.
