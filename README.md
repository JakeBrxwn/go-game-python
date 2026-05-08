# CMSC 14200 Course Project

Team members:
- Marcus Longo (malongo) (GUI)
- Aditya Singh (asingh23) (QA)
- Daniel Fields (dfields) (TUI)
- Jake Brown (jacobbrown) (Bot)

## Enhancements

Enhancement 1: We updated the GUI to play music in the background while it is running.
The music is Glorious Morning 2 by Waterflame, used with permission:
https://www.youtube.com/watch?v=yolbGaJD4AY
https://www.waterflame.com/contact-info

Enhancement 2: We added support for hints in the TUI. A user can request a hint and get a suggested move from the bot code.

Enhancement 3: We created a helper function in our tests that loads a board from a file on disk, and loads that board into a game.

## Improvements

### Game Logic:

  #### Rubric Item 1: "[Major] Did not implement load_game at all"
  To address this item, we implemented the load_game method in go.py, ensuring that it can load a new board into the current game as long as the board is valid.

  #### Rubric Item 2: "grid should return a deepcopy of the board grid so that manipulating it does not affect the original game board."
  To address this item, we modified the grid property in the Go class to ensure that it returns a deepcopy of the game board that will not affect the original board.

  #### Rubric Item 3: "legal_move seems to be invalidly claiming that some legal moves are illegal, which is likely due to your ko rule implementation. You should only save the state of the board after all captures have concluded."
  To address this item, we modified our apply_move method to save the state of the board after all captures have concluded, which helps to ensure that legal_move doesn't identify legal moves as illegal.

  #### Rubric Item 4: "Capturing should remove all connected pieces with no liberties within the territory surrounded by a single color, which requires determining these surrounded areas."
  To address this item, we implemented proper capture logic where all connected pieces with no liberties are removed from the board. We implemented this logic in the _capture_pieces method of go.py, which first captures groups of other players' pieces without liberties before performing self capture if necessary. The method uses a helper method called _find_contigious to help identify contigious groups of pieces of a single player that must be captured.

  #### Rubric Item 5: "scores should also take into account players' controlled territories, not just the pieces present on the board."
  To address this item, we modified the scores method of go.py, changing it to account for players' controlled territories along with the pieces on the board. The method uses a helper
  method called _find_contiguous to find contigious groups of empty intersections that represent a territory.

### GUI:
This component received two S's in Milestone 2

### TUI:
This component received two S's in Milestone 2

### Bot:
This component received two S's in Milestone 2

### QA:
This component received two S's in Milestone 2

