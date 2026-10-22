# Enclose.Horse Solver

An exact, dependency-free Python solver for Enclose.Horse boards.

## Desktop App

Launch the level editor from this folder:

```powershell
python app.py
```

Choose a tile from the palette, then click or drag over the board to paint it.
Place two portal tiles to create a pair, set the maximum wall count, and select
**Run solver**. Suggested walls are outlined on the board; **Apply suggested
walls** places them into the level. Board dimensions can be resized from 3 to
30 tiles in each direction. The solver runs in a background thread so the
editor remains responsive while searching. During the search, the results
panel shows evaluated placements and an upper bound on combinations not yet
evaluated. The bound includes combinations that pruning may skip entirely, so
it is not an exact countdown.
Use **Copy board** to put the current level in the clipboard as readable text,
or **Load board from clipboard** to restore a board from that format. The
serialized rows include every tile and portal pair.

```text
# # # # #
# H P:portal0 C #
# ~ A B P:portal0 #
# # # # #
```

```python
from enclose_horse import parse_board, solve

board = parse_board("#####\n#...#\n#.H.#\n#C..#\n##.##")
result = solve(board, max_walls=1)
print(result.best_score, result.wall_coordinates)
```

## Board Format

Compact rows use `.`, `~`, `H`, `C`, `A`, `B`, and `#` for grass, water,
horse, cherry, golden apple, bee, and wall. Rows may also contain
whitespace-separated names such as `grass`, `water`, and `golden_apple`.
Portals use `P` for an unlabeled pair, or matching tokens such as `P:blue`
and `P:blue` (also accepted: `P1` / `P1` or `portal:blue`). Every pair must
occur exactly twice. There must be exactly one horse and the board must be
rectangular.

Water and walls block movement. Movement edges that enter a portal are
redirected to its paired endpoint, so the entry endpoint cannot be used as a
normal tile. Reaching any border cell, including a portal destination on the
border, makes a wall placement invalid. `enclosed_area` counts every
reachable traversable tile, including the horse and portal destinations;
scoring counts only reachable grass, cherries, golden apples, and bees.

`wall_coordinates` are zero-based `(row, column)` pairs. If no valid wall
placement exists within the budget, `valid_solution` is false and the score
and enclosure counts are zero. Equal scores prefer fewer placed walls.

## Search and Complexity

The solver runs BFS on the board graph for each distinct wall placement. If
the horse can escape, any valid completion must block at least one grass cell
on the discovered escape path, so the search branches only on those cells.
Once enclosed, a score improvement requires isolating at least one bee. The
search therefore branches only on grass cells along BFS paths to reachable
bees, not every reachable grass tile. Candidate walls are ordered by an
estimated score impact from their BFS-tree subregion, so branches likely to
preserve or improve the score are explored first. This estimate only changes
search order: no candidate is discarded based on its estimated value.
States with identical reachable regions and wall counts are memoized. Its
score upper bound assumes all reachable
positive-value tiles remain reachable and subtracts bees that have a route
containing no wallable grass; those bees cannot be isolated by any wall
placement. Both pruning rules preserve exactness.

`SolveResult.explored_states` counts distinct wall placements actually
analyzed. `SolveResult.wall_set_upper_bound` is the total number of possible
grass-wall combinations up to the budget. The optional progress callback
passed to `solve(board, max_walls, progress_callback)` receives those two
search counts. An optional `best_callback` receives each improved valid
`SolveResult` immediately, which the desktop app uses to update the board
preview while the search continues. The difference between the upper bound
and analyzed placements is not a count of work still required:
branch-and-bound may prove those placements unnecessary.

For `V` board cells and `E` movement edges, one BFS costs `O(V + E)`. With
`G` candidate grass cells and budget `N`, the worst case remains exponential:
`O((V + E) * sum(C(G, k), k=0..N))` time and `O(V * S)` space in the worst
case, where `S` is the number of distinct search states. Escape-path and
bee-path branching, region memoization, and score bounds often avoid much of
that upper-bound search space, but the exact optimization problem has no
general polynomial-time guarantee.

Run the tests with `python -m unittest -v`.