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
editor remains responsive while searching.

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

The solver runs BFS on the board graph for each distinct wall set. If the
horse can escape, any valid completion must block at least one grass cell on
the discovered escape path, so the search branches only on those cells. Once
enclosed, it explores reachable grass placements as well, since a wall can
separate a bee from the horse and improve the score. A positive-reward upper
bound ignores bee penalties and assumes all currently reachable grass and
fruit remain reachable; adding walls cannot increase reachability, so the
bound is safe. Wall-set analyses and duplicate search states are memoized.

For `V` board cells and `E` movement edges, one BFS costs `O(V + E)`. With
`G` candidate grass cells and budget `N`, the worst case remains exponential:
`O((V + E) * sum(C(G, k), k=0..N))` time and `O(V * S)` space in the worst
case, where `S` is the number of distinct wall sets visited. Branching on
escape paths and score bounds usually prunes much of that space, but the exact
optimization problem has no general polynomial-time guarantee.

Run the tests with `python -m unittest -v`.