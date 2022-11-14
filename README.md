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

## Running

You cannot run *into* a room. Even if you are standing in a corridor
which is leading into a room, you will have to walk into the room before
you can run in the room.

Once you're in a hallway, you can run in the hallway but you will stop
prior to transitioning into a room.
