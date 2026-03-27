// Copyright (c) 2026 Perry Kivolowitz. All rights reserved.

#pragma once

/*	Game Save Architecture — Design Notes
	======================================

	PNH already supports multiple dungeon levels persisted in memory
	(the boards vector in main.cpp). Save/load extends this to disk.

	The save file is a single binary file containing:

	1. HEADER
	   - Magic number (identifies file as PNH save)
	   - Version (for forward-compatible schema evolution)
	   - Timestamp
	   - Turn counter
	   - Current board index

	2. PLAYER BLOCK
	   - Name, role, race, alignment (length-prefixed strings)
	   - Position (r, c)
	   - Traits array (current and maximum)
	   - Inventory: for each of 52 slots, a bool (occupied) followed
	     by the serialized item if occupied

	3. BOARD BLOCKS (one per generated level)
	   - Board count (uint32_t)
	   - For each board:
	     - Upstairs/downstairs coordinates
	     - Cell array (BOARD_ROWS * BOARD_COLUMNS cells):
	       base_type, original_c, display_c, final_room_number,
	       is_known, door_state, door_horizontal
	     - Room vector (count + Room structs)
	     - GoodieMap: count of coordinates, then for each:
	       coordinate + item count + serialized items

	4. ITEM SERIALIZATION
	   - ItemType discriminant
	   - weight_per_item, number_of_like_items, symbol
	   - item_name (length-prefixed string)
	   - Subclass-specific data (none yet, but the discriminant
	     allows future extension for spell IDs, BUC status, etc.)

	WHY BINARY:
	JSON would be readable but the cell array alone is 21*80 = 1680
	cells with 7+ fields each. Binary is compact and fast. For
	debugging, a separate dump-to-text tool can be written.

	WHY ONE FILE:
	NetHack uses one file per save. No good reason to split across
	files — atomic save/restore is simpler with one file.

	SAVE INTEGRITY:
	A CRC32 or SHA-256 at the end of the file guards against
	corruption. On load, verify before deserializing.

	SAVE-ON-QUIT:
	Like NetHack, save happens on quit ('S' command). The save file
	is deleted on successful load (permadeath model). This prevents
	save-scumming.

	FUTURE:
	- RNG state serialization for deterministic replay
	- Action log for the RL training pipeline (state, action, reward
	  tuples written alongside or separately from save files)
	- Compression if save files grow large with many levels
*/

#include <string>
#include <vector>
#include "board.hpp"
#include "player.hpp"

// Version is bumped when the save format changes incompatibly.
static const uint32_t SAVE_MAGIC   = 0x504E4831;	// "PNH1"
static const uint32_t SAVE_VERSION = 1;

struct SaveHeader {
	uint32_t magic;
	uint32_t version;
	uint64_t timestamp;
	int32_t turn_counter;
	uint32_t current_board;
	uint32_t board_count;
};

// Serialize/deserialize the full game state. These will be
// implemented when save/load is wired up.
// bool SaveGame(const std::string & path,
//               const Player & player,
//               const std::vector<Board *> & boards,
//               uint32_t current_board,
//               int32_t turn_counter);
//
// bool LoadGame(const std::string & path,
//               Player & player,
//               std::vector<Board *> & boards,
//               uint32_t & current_board,
//               int32_t & turn_counter);
