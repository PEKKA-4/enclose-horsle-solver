import unittest

from enclose_horse import Cell, format_board, parse_board, solve


class ParseBoardTests(unittest.TestCase):
    def test_parses_compact_and_named_cells(self) -> None:
        board = parse_board("#####\n#HCA#\n#####")
        self.assertEqual(board.width, 5)
        self.assertEqual(board.height, 3)
        self.assertEqual(board.cells[6:9], (Cell.HORSE, Cell.CHERRY, Cell.GOLDEN_APPLE))

    def test_parses_and_pairs_portals(self) -> None:
        board = parse_board("# # # # #\n# H P:gate # #\n# # # P:gate #\n# # # # #")
        self.assertEqual(len(board.portal_pairs), 1)
        result = solve(board, 0)
        self.assertTrue(result.valid_solution)
        self.assertEqual(result.enclosed_area, 2)

    def test_formatted_board_can_be_parsed_back_without_losing_tiles_or_portals(self) -> None:
        board = parse_board(
            "# # # # # #\n"
            "# H P:gate C # #\n"
            "# ~ A B P:gate #\n"
            "# # # # # #"
        )
        self.assertEqual(parse_board(format_board(board)), board)

    def test_entering_a_portal_does_not_allow_leaving_its_entry_endpoint(self) -> None:
        board = parse_board("#######\n#HP.###\n#######\n#######\n#######\n#####P#\n#######")
        result = solve(board, 0)
        self.assertTrue(result.valid_solution)
        self.assertEqual(result.enclosed_area, 2)
        self.assertEqual(result.best_score, 0)

    def test_rejects_unpaired_portals(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly twice"):
            parse_board("H P:only")


class SolverTests(unittest.TestCase):
    def test_computes_enclosed_score_and_counts(self) -> None:
        board = parse_board("#######\n#.C...#\n#.HA..#\n#.B...#\n#######")
        result = solve(board, 0)
        self.assertEqual(result.best_score, 19)
        self.assertEqual(result.enclosed_area, 15)
        self.assertEqual(result.collected_cherries, 1)
        self.assertEqual(result.collected_apples, 1)
        self.assertEqual(result.trapped_bees, 1)
        self.assertTrue(result.valid_solution)

    def test_places_a_wall_to_block_border_escape(self) -> None:
        board = parse_board("#####\n#...#\n#.H.#\n#C..#\n##.##")
        result = solve(board, 1)
        self.assertEqual(result.best_score, 10)
        self.assertEqual(result.wall_coordinates, ((4, 2),))
        self.assertTrue(result.valid_solution)

    def test_returns_no_solution_when_wall_budget_is_insufficient(self) -> None:
        board = parse_board("#####\n#...#\n#.H.#\n#C..#\n##.##")
        result = solve(board, 0)
        self.assertFalse(result.valid_solution)
        self.assertEqual(result.best_score, 0)

    def test_water_blocks_movement(self) -> None:
        board = parse_board("#####\n#H~.#\n#####")
        result = solve(board, 0)
        self.assertTrue(result.valid_solution)
        self.assertEqual(result.enclosed_area, 1)
        self.assertEqual(result.best_score, 0)

    def test_can_place_walls_to_trap_a_bee(self) -> None:
        board = parse_board("#######\n#..H..#\n###.###\n###B###\n#######")
        result = solve(board, 1)
        self.assertEqual(result.best_score, 4)
        self.assertEqual(result.wall_coordinates, ((2, 3),))
        self.assertEqual(result.trapped_bees, 0)
        self.assertLess(result.explored_states, result.wall_set_upper_bound)

    def test_does_not_try_extra_walls_when_enclosure_has_no_bees(self) -> None:
        board = parse_board("#######\n#.....#\n#.....#\n#..H..#\n#.....#\n#.....#\n#######")
        result = solve(board, 4)
        self.assertTrue(result.valid_solution)
        self.assertEqual(result.explored_states, 1)

    def test_progress_callback_reports_checked_and_upper_bound(self) -> None:
        board = parse_board("#####\n#H..#\n#...#\n#####")
        progress: list[tuple[int, int]] = []
        result = solve(board, 0, lambda checked, total: progress.append((checked, total)))
        self.assertEqual(progress[0], (0, result.wall_set_upper_bound))
        self.assertEqual(progress[-1], (result.explored_states, result.wall_set_upper_bound))
        self.assertTrue(result.valid_solution)

    def test_best_callback_receives_improvements_during_search(self) -> None:
        board = parse_board("#####\n#...#\n#.H.#\n#C..#\n##.##")
        improvements = []
        result = solve(board, 1, best_callback=improvements.append)
        self.assertGreaterEqual(len(improvements), 1)
        self.assertEqual(improvements[-1].best_score, result.best_score)
        self.assertEqual(improvements[-1].wall_coordinates, result.wall_coordinates)
        self.assertTrue(all(item.valid_solution for item in improvements))


if __name__ == "__main__":
    unittest.main()