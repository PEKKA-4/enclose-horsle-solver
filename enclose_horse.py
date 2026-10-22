"""Exact solver for Enclose.Horse grid puzzles."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import comb
from typing import Callable, Iterable, Sequence


class Cell(str, Enum):
    GRASS = "grass"
    WATER = "water"
    HORSE = "horse"
    CHERRY = "cherry"
    GOLDEN_APPLE = "golden_apple"
    BEE = "bee"
    PORTAL = "portal"
    WALL = "wall"


@dataclass(frozen=True, slots=True)
class Board:
    width: int
    height: int
    cells: tuple[Cell, ...]
    portal_pairs: tuple[tuple[int, int], ...] = ()

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Board dimensions must be positive.")
        if len(self.cells) != self.width * self.height:
            raise ValueError("Cell count must match board dimensions.")
        if sum(cell is Cell.HORSE for cell in self.cells) != 1:
            raise ValueError("Board must contain exactly one horse.")

        portal_indices = {index for index, cell in enumerate(self.cells) if cell is Cell.PORTAL}
        paired_indices = {index for pair in self.portal_pairs for index in pair}
        if portal_indices != paired_indices or len(paired_indices) != 2 * len(self.portal_pairs):
            raise ValueError("Every portal must belong to exactly one pair.")

    @property
    def horse_index(self) -> int:
        return self.cells.index(Cell.HORSE)

    def coordinate(self, index: int) -> tuple[int, int]:
        return divmod(index, self.width)


@dataclass(frozen=True, slots=True)
class SolveResult:
    best_score: int
    wall_coordinates: tuple[tuple[int, int], ...]
    enclosed_area: int
    collected_cherries: int
    collected_apples: int
    trapped_bees: int
    valid_solution: bool
    explored_states: int
    wall_set_upper_bound: int


@dataclass(frozen=True, slots=True)
class _Analysis:
    reachable: tuple[int, ...]
    escape_path: tuple[int, ...] | None
    bee_wall_candidates: tuple[int, ...]


_TOKENS: dict[str, Cell] = {
    ".": Cell.GRASS,
    "g": Cell.GRASS,
    "grass": Cell.GRASS,
    "~": Cell.WATER,
    "w": Cell.WATER,
    "water": Cell.WATER,
    "h": Cell.HORSE,
    "horse": Cell.HORSE,
    "c": Cell.CHERRY,
    "cherry": Cell.CHERRY,
    "a": Cell.GOLDEN_APPLE,
    "apple": Cell.GOLDEN_APPLE,
    "golden_apple": Cell.GOLDEN_APPLE,
    "b": Cell.BEE,
    "bee": Cell.BEE,
    "#": Cell.WALL,
    "wall": Cell.WALL,
}


def _split_row(row: str) -> list[str]:
    stripped = row.strip()
    if not stripped:
        return []
    return stripped.split() if any(character.isspace() for character in stripped) else list(stripped)


def parse_board(source: str | Sequence[str] | Sequence[Sequence[str]]) -> Board:
    """Parse compact rows or whitespace-separated cell tokens.

    Portal tokens are ``P`` (paired in reading order), ``P:<id>``, ``P<id>``,
    or ``portal:<id>``. Each identified portal must occur exactly twice.
    """
    if isinstance(source, str):
        rows = [_split_row(line) for line in source.splitlines() if line.strip()]
    else:
        rows = []
        for row in source:
            rows.append(_split_row(row) if isinstance(row, str) else [str(token) for token in row])

    if not rows or not rows[0]:
        raise ValueError("Board cannot be empty.")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("Board rows must all have the same width.")

    cells: list[Cell] = []
    portal_groups: dict[str, list[int]] = {}
    for row in rows:
        for token in row:
            normalized = token.strip().lower()
            portal_id: str | None = None
            if normalized in {"p", "portal"}:
                portal_id = ""
            elif normalized.startswith("portal:"):
                portal_id = normalized.removeprefix("portal:")
            elif normalized.startswith("p:"):
                portal_id = normalized.removeprefix("p:")
            elif len(normalized) > 1 and normalized.startswith("p"):
                portal_id = normalized[1:]

            if portal_id is not None:
                if portal_id == "":
                    portal_id = "__unlabeled__"
                portal_groups.setdefault(portal_id, []).append(len(cells))
                cells.append(Cell.PORTAL)
                continue

            try:
                cells.append(_TOKENS[normalized])
            except KeyError as error:
                raise ValueError(f"Unknown board token: {token!r}") from error

    portal_pairs: list[tuple[int, int]] = []
    for portal_id, indices in portal_groups.items():
        if len(indices) != 2:
            label = "unlabeled" if portal_id == "__unlabeled__" else repr(portal_id)
            raise ValueError(f"Portal pair {label} must occur exactly twice.")
        portal_pairs.append((indices[0], indices[1]))

    return Board(width, len(rows), tuple(cells), tuple(portal_pairs))


def _build_graph(board: Board) -> tuple[tuple[int, ...], ...]:
    neighbors: list[set[int]] = [set() for _ in board.cells]
    portal_mates = {
        endpoint: mate
        for first, second in board.portal_pairs
        for endpoint, mate in ((first, second), (second, first))
    }
    for index in range(len(board.cells)):
        row, column = board.coordinate(index)
        adjacent: list[int] = []
        if row > 0:
            adjacent.append(index - board.width)
        if row + 1 < board.height:
            adjacent.append(index + board.width)
        if column > 0:
            adjacent.append(index - 1)
        if column + 1 < board.width:
            adjacent.append(index + 1)
        for target in adjacent:
            neighbors[index].add(portal_mates.get(target, target))
    return tuple(tuple(adjacent) for adjacent in neighbors)


def _is_border(board: Board, index: int) -> bool:
    row, column = board.coordinate(index)
    return row == 0 or column == 0 or row == board.height - 1 or column == board.width - 1


def _score(board: Board, reachable: Iterable[int]) -> tuple[int, int, int, int, int]:
    grass = cherries = apples = bees = area = 0
    for index in reachable:
        area += 1
        cell = board.cells[index]
        if cell is Cell.GRASS:
            grass += 1
        elif cell is Cell.CHERRY:
            cherries += 1
        elif cell is Cell.GOLDEN_APPLE:
            apples += 1
        elif cell is Cell.BEE:
            bees += 1
    return grass + 3 * cherries + 10 * apples - 5 * bees, area, cherries, apples, bees


def solve(
    board: Board,
    max_walls: int,
    progress_callback: Callable[[int, int], None] | None = None,
    best_callback: Callable[[SolveResult], None] | None = None,
) -> SolveResult:
    """Find an exact maximum-score enclosure using at most ``max_walls``.

    Coordinates in the result are zero-based ``(row, column)`` pairs.
    The optional callback receives (checked_states, wall_set_upper_bound).
    ``best_callback`` receives each improved valid result as soon as it is found.
    """
    if isinstance(max_walls, bool) or not isinstance(max_walls, int) or max_walls < 0:
        raise ValueError("max_walls must be a non-negative integer.")

    graph = _build_graph(board)
    grass_count = sum(cell is Cell.GRASS for cell in board.cells)
    wall_set_upper_bound = sum(
        comb(grass_count, wall_count)
        for wall_count in range(min(max_walls, grass_count) + 1)
    )
    if progress_callback is not None:
        progress_callback(0, wall_set_upper_bound)

    visited_states: set[int] = set()
    evaluated_regions: set[tuple[int, int]] = set()
    states_checked = 0

    wall_free_reachable = {board.horse_index}
    wall_free_queue = deque([board.horse_index])
    while wall_free_queue:
        current = wall_free_queue.popleft()
        for neighbor in graph[current]:
            if board.cells[neighbor] in (Cell.WATER, Cell.WALL, Cell.GRASS):
                continue
            if neighbor not in wall_free_reachable:
                wall_free_reachable.add(neighbor)
                wall_free_queue.append(neighbor)
    unavoidable_bees = sum(board.cells[index] is Cell.BEE for index in wall_free_reachable)

    def analyze(wall_mask: int) -> _Analysis:
        start = board.horse_index
        parent = [-2] * len(board.cells)
        parent[start] = -1
        queue = deque([start])
        reachable: list[int] = []
        first_border: int | None = None

        while queue:
            current = queue.popleft()
            reachable.append(current)
            if first_border is None and _is_border(board, current):
                first_border = current
            for neighbor in graph[current]:
                cell = board.cells[neighbor]
                if cell is Cell.WATER or cell is Cell.WALL or wall_mask & (1 << neighbor):
                    continue
                if parent[neighbor] != -2:
                    continue
                parent[neighbor] = current
                queue.append(neighbor)

        escape_path: tuple[int, ...] | None = None
        if first_border is not None:
            path: list[int] = []
            current = first_border
            while current != -1:
                path.append(current)
                current = parent[current]
            escape_path = tuple(reversed(path))

        bee_wall_candidates: set[int] = set()
        if first_border is None:
            for bee_index in reachable:
                if board.cells[bee_index] is not Cell.BEE:
                    continue
                current = bee_index
                while current != -1:
                    if board.cells[current] is Cell.GRASS:
                        bee_wall_candidates.add(current)
                    current = parent[current]

        return _Analysis(tuple(reachable), escape_path, tuple(sorted(bee_wall_candidates)))

    def optimistic_score(reachable: Iterable[int]) -> int:
        upper_bound = 0
        for index in reachable:
            cell = board.cells[index]
            if cell is Cell.GRASS:
                upper_bound += 1
            elif cell is Cell.CHERRY:
                upper_bound += 3
            elif cell is Cell.GOLDEN_APPLE:
                upper_bound += 10
        return upper_bound - 5 * unavoidable_bees

    best: tuple[int, int, tuple[int, ...], tuple[int, int, int]] | None = None

    def result_from_best(
        current_best: tuple[int, int, tuple[int, ...], tuple[int, int, int]],
        explored: int,
    ) -> SolveResult:
        score, area, wall_indices, collected = current_best
        return SolveResult(
            score,
            tuple(board.coordinate(index) for index in wall_indices),
            area,
            collected[0],
            collected[1],
            collected[2],
            True,
            explored,
            wall_set_upper_bound,
        )

    def search(wall_mask: int) -> None:
        nonlocal best, states_checked
        if wall_mask in visited_states:
            return
        visited_states.add(wall_mask)

        walls_used = wall_mask.bit_count()
        if walls_used > max_walls:
            return

        states_checked += 1
        if progress_callback is not None and states_checked % 128 == 0:
            progress_callback(states_checked, wall_set_upper_bound)

        analysis = analyze(wall_mask)
        reachable_mask = 0
        for index in analysis.reachable:
            reachable_mask |= 1 << index
        region_key = (reachable_mask, walls_used)
        if region_key in evaluated_regions:
            return
        evaluated_regions.add(region_key)

        upper_bound = optimistic_score(analysis.reachable)
        if best is not None and (
            upper_bound < best[0]
            or (upper_bound == best[0] and walls_used >= len(best[2]))
        ):
            return

        if analysis.escape_path is None:
            score, area, cherries, apples, bees = _score(board, analysis.reachable)
            if best is None or score > best[0] or (score == best[0] and walls_used < len(best[2])):
                wall_indices = tuple(
                    index for index in range(len(board.cells)) if wall_mask & (1 << index)
                )
                best = (score, area, wall_indices, (cherries, apples, bees))
                if best_callback is not None:
                    best_callback(result_from_best(best, states_checked))

            if walls_used == max_walls:
                return
            candidates = analysis.bee_wall_candidates
        else:
            if walls_used == max_walls:
                return
            candidates = [
                index
                for index in analysis.escape_path
                if board.cells[index] is Cell.GRASS and not wall_mask & (1 << index)
            ]

        for index in candidates:
            search(wall_mask | (1 << index))

    search(0)
    if progress_callback is not None:
        progress_callback(states_checked, wall_set_upper_bound)

    if best is None:
        return SolveResult(0, (), 0, 0, 0, 0, False, states_checked, wall_set_upper_bound)

    return result_from_best(best, states_checked)