# PNH - Perry's NetHack

## Doorways

There are no doors in PNH. You're roaming underground caverns.

*Design Note:* Doors in NetHack were, in our view, mostly a time wasting
nuisance.

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

[Development_Notes](./devnotes/development_notes.md)
