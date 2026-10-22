"""Desktop level editor and launcher for the Enclose.Horse solver."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, ttk

from enclose_horse import Board, Cell, SolveResult, solve


CELL_SIZE = 54
MIN_BOARD_SIZE = 3
MAX_BOARD_SIZE = 30

BACKGROUND = "#111a17"
PANEL = "#1a2722"
PANEL_ALT = "#202f29"
TEXT = "#e8eee9"
MUTED = "#a2b0a8"
ACCENT = "#d6f36a"

CELL_COLORS: dict[Cell, str] = {
    Cell.GRASS: "#8da779",
    Cell.WATER: "#5f9ac0",
    Cell.HORSE: "#ece3cf",
    Cell.CHERRY: "#ca626b",
    Cell.GOLDEN_APPLE: "#e2b757",
    Cell.BEE: "#e09a49",
    Cell.PORTAL: "#9b82bf",
    Cell.WALL: "#4a5550",
}
CELL_LABELS: dict[Cell, str] = {
    Cell.GRASS: "Grass",
    Cell.WATER: "Water",
    Cell.HORSE: "Horse",
    Cell.CHERRY: "Cherry",
    Cell.GOLDEN_APPLE: "Golden apple",
    Cell.BEE: "Bee",
    Cell.PORTAL: "Portal",
    Cell.WALL: "Wall",
}
CELL_MARKS: dict[Cell, str] = {
    Cell.GRASS: ".",
    Cell.WATER: "~",
    Cell.HORSE: "H",
    Cell.CHERRY: "C",
    Cell.GOLDEN_APPLE: "A",
    Cell.BEE: "B",
    Cell.PORTAL: "P",
    Cell.WALL: "#",
}


class EncloseHorseApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Enclose.Horse | Level editor")
        self.root.geometry("1320x820")
        self.root.minsize(1080, 680)
        self.root.configure(bg=BACKGROUND)

        self.width = 11
        self.height = 9
        self.cells = [Cell.GRASS] * (self.width * self.height)
        self.cells[(self.height // 2) * self.width + self.width // 2] = Cell.HORSE
        self.selected_cell = Cell.WALL
        self.solution: SolveResult | None = None
        self.board_revision = 0
        self.is_solving = False
        self.palette_buttons: dict[Cell, tk.Button] = {}

        self.width_var = tk.StringVar(value=str(self.width))
        self.height_var = tk.StringVar(value=str(self.height))
        self.wall_budget_var = tk.StringVar(value="4")
        self.status_var = tk.StringVar(value="Select a tile, then click the board to paint.")
        self.result_var = tk.StringVar(value="No solution computed yet.")
        self.result_details_var = tk.StringVar(value="")
        self.wall_list_var = tk.StringVar(value="")

        self._configure_styles()
        self._build_layout()
        self._draw_board()
        self._select_palette_cell(Cell.WALL)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BACKGROUND)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BACKGROUND, foreground=TEXT, font=("Segoe UI Semibold", 23))
        style.configure("Section.TLabel", background=PANEL, foreground=ACCENT, font=("Segoe UI Semibold", 11))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(10, 7))
        style.configure("Accent.TButton", background=ACCENT, foreground="#172016", padding=(12, 9))
        style.map("Accent.TButton", background=[("disabled", "#59634d"), ("active", "#e4ff91")])
        style.configure("TEntry", fieldbackground=PANEL_ALT, foreground=TEXT, padding=5)
        style.configure("TSpinbox", fieldbackground=PANEL_ALT, foreground=TEXT, padding=5)

    def _build_layout(self) -> None:
        header = ttk.Frame(self.root, padding=(22, 18, 22, 12))
        header.grid(row=0, column=0, columnspan=3, sticky="ew")
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        ttk.Label(header, text="Enclose.Horse", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="LEVEL EDITOR  /  EXACT WALL SEARCH",
            foreground=MUTED,
            font=("Segoe UI Semibold", 9),
        ).pack(side="left", padx=(18, 0), pady=(8, 0))

        self._build_editor_panel().grid(row=1, column=0, sticky="nsw", padx=(22, 12), pady=(0, 18))
        self._build_board_panel().grid(row=1, column=1, sticky="nsew", pady=(0, 18))
        self._build_results_panel().grid(row=1, column=2, sticky="nse", padx=(12, 22), pady=(0, 18))

        status = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg=PANEL,
            fg=MUTED,
            anchor="w",
            padx=22,
            pady=8,
            font=("Segoe UI", 9),
        )
        status.grid(row=2, column=0, columnspan=3, sticky="ew")

    def _panel(self, width: int) -> tk.Frame:
        frame = tk.Frame(self.root, bg=PANEL, width=width, padx=16, pady=16)
        frame.grid_propagate(False)
        return frame

    def _build_editor_panel(self) -> tk.Frame:
        panel = self._panel(250)
        tk.Label(panel, text="PAINT TILES", bg=PANEL, fg=ACCENT, font=("Segoe UI Semibold", 10)).pack(anchor="w")
        tk.Label(
            panel,
            text="Choose a tile, then click the board.",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 12))

        palette = tk.Frame(panel, bg=PANEL)
        palette.pack(fill="x")
        for cell in Cell:
            button = tk.Button(
                palette,
                text=f"{CELL_MARKS[cell]}   {CELL_LABELS[cell]}",
                anchor="w",
                relief="flat",
                bd=0,
                padx=10,
                pady=8,
                bg=CELL_COLORS[cell],
                fg="#17201a",
                activebackground=CELL_COLORS[cell],
                activeforeground="#17201a",
                font=("Segoe UI Semibold", 9),
                command=lambda chosen=cell: self._select_palette_cell(chosen),
            )
            button.pack(fill="x", pady=2)
            self.palette_buttons[cell] = button

        tk.Frame(panel, bg="#334139", height=1).pack(fill="x", pady=14)
        tk.Label(panel, text="BOARD SIZE", bg=PANEL, fg=ACCENT, font=("Segoe UI Semibold", 10)).pack(anchor="w")

        dimensions = tk.Frame(panel, bg=PANEL)
        dimensions.pack(fill="x", pady=(8, 7))
        self._labeled_entry(dimensions, "Columns", self.width_var).pack(side="left", expand=True, fill="x", padx=(0, 8))
        self._labeled_entry(dimensions, "Rows", self.height_var).pack(side="left", expand=True, fill="x")
        ttk.Button(panel, text="Resize board", command=self._resize_board).pack(fill="x", pady=(1, 8))
        ttk.Button(panel, text="Reset level", command=self._reset_board).pack(fill="x")

        tk.Label(
            panel,
            text="Portal tiles must be placed in pairs. Painting a new horse moves the existing one.",
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=210,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(18, 0))
        return panel

    def _labeled_entry(self, parent: tk.Widget, label: str, variable: tk.StringVar) -> tk.Frame:
        wrapper = tk.Frame(parent, bg=PANEL)
        tk.Label(wrapper, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        ttk.Entry(wrapper, textvariable=variable, width=6).pack(fill="x", pady=(3, 0))
        return wrapper

    def _build_board_panel(self) -> tk.Frame:
        panel = tk.Frame(self.root, bg=BACKGROUND, padx=4)
        heading = tk.Frame(panel, bg=BACKGROUND)
        heading.pack(fill="x", pady=(3, 10))
        tk.Label(heading, text="PUZZLE BOARD", bg=BACKGROUND, fg=TEXT, font=("Segoe UI Semibold", 11)).pack(side="left")
        tk.Label(heading, text="CLICK TO PAINT", bg=BACKGROUND, fg=MUTED, font=("Segoe UI Semibold", 8)).pack(side="right")

        board_frame = tk.Frame(panel, bg="#0c1310", padx=2, pady=2)
        board_frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(board_frame, bg="#0c1310", highlightthickness=0, cursor="crosshair")
        vertical = ttk.Scrollbar(board_frame, orient="vertical", command=self.canvas.yview)
        horizontal = ttk.Scrollbar(board_frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        board_frame.grid_rowconfigure(0, weight=1)
        board_frame.grid_columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._paint_at_pointer)
        self.canvas.bind("<B1-Motion>", self._paint_at_pointer)
        self.canvas.bind("<MouseWheel>", self._scroll_board)
        return panel

    def _build_results_panel(self) -> tk.Frame:
        panel = self._panel(260)
        tk.Label(panel, text="SOLVER", bg=PANEL, fg=ACCENT, font=("Segoe UI Semibold", 10)).pack(anchor="w")
        tk.Label(
            panel,
            text="Find the highest-scoring enclosure within your wall limit.",
            bg=PANEL,
            fg=MUTED,
            justify="left",
            wraplength=220,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 14))

        tk.Label(panel, text="Maximum walls", bg=PANEL, fg=TEXT, font=("Segoe UI Semibold", 9)).pack(anchor="w")
        self.wall_budget_control = ttk.Spinbox(
            panel, from_=0, to=99, textvariable=self.wall_budget_var, width=8
        )
        self.wall_budget_control.pack(anchor="w", pady=(5, 12))
        self.solve_button = ttk.Button(panel, text="Run solver", style="Accent.TButton", command=self._start_solving)
        self.solve_button.pack(fill="x")

        tk.Frame(panel, bg="#334139", height=1).pack(fill="x", pady=16)
        tk.Label(panel, textvariable=self.result_var, bg=PANEL, fg=TEXT, justify="left", wraplength=220,
                 font=("Segoe UI Semibold", 13)).pack(anchor="w")
        tk.Label(panel, textvariable=self.result_details_var, bg=PANEL, fg=MUTED, justify="left", wraplength=220,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 0))
        tk.Label(panel, textvariable=self.wall_list_var, bg=PANEL, fg=TEXT, justify="left", wraplength=220,
                 font=("Consolas", 9)).pack(anchor="w", pady=(12, 0))

        self.apply_button = ttk.Button(panel, text="Apply suggested walls", command=self._apply_solution, state="disabled")
        self.apply_button.pack(fill="x", side="bottom", pady=(12, 0))
        return panel

    def _select_palette_cell(self, cell: Cell) -> None:
        self.selected_cell = cell
        for palette_cell, button in self.palette_buttons.items():
            button.configure(relief="sunken" if palette_cell is cell else "flat", bd=2 if palette_cell is cell else 0)
        self.status_var.set(f"Selected {CELL_LABELS[cell]}. Click or drag across the board to paint.")

    def _paint_at_pointer(self, event: tk.Event) -> None:
        column = int(self.canvas.canvasx(event.x) // CELL_SIZE)
        row = int(self.canvas.canvasy(event.y) // CELL_SIZE)
        if not (0 <= row < self.height and 0 <= column < self.width):
            return
        index = row * self.width + column
        current = self.cells[index]
        if current is self.selected_cell:
            return
        if current is Cell.HORSE and self.selected_cell is not Cell.HORSE:
            self.status_var.set("The horse must stay on the board. Select Horse to move it.")
            return

        if self.selected_cell is Cell.HORSE:
            old_horse = self.cells.index(Cell.HORSE)
            self.cells[old_horse] = Cell.GRASS
        elif self.selected_cell is Cell.PORTAL and current is not Cell.PORTAL:
            if sum(cell is Cell.PORTAL for cell in self.cells) >= 2:
                self.status_var.set("A level can have one portal pair. Remove a portal before placing another.")
                return

        self.cells[index] = self.selected_cell
        self._board_changed()

    def _board_changed(self) -> None:
        self.board_revision += 1
        self.solution = None
        self.apply_button.configure(state="disabled")
        self.result_var.set("No solution computed yet.")
        self.result_details_var.set("")
        self.wall_list_var.set("")
        self._draw_board()

    def _draw_board(self) -> None:
        self.canvas.delete("all")
        portal_indices = [index for index, cell in enumerate(self.cells) if cell is Cell.PORTAL]
        portal_names = {index: f"P{position + 1}" for position, index in enumerate(portal_indices)}

        for index, cell in enumerate(self.cells):
            row, column = divmod(index, self.width)
            x0, y0 = column * CELL_SIZE, row * CELL_SIZE
            x1, y1 = x0 + CELL_SIZE, y0 + CELL_SIZE
            self.canvas.create_rectangle(
                x0 + 1,
                y0 + 1,
                x1 - 1,
                y1 - 1,
                fill=CELL_COLORS[cell],
                outline="#25342c",
                width=2,
            )
            if self.solution and (row, column) in self.solution.wall_coordinates:
                self.canvas.create_rectangle(
                    x0 + 7,
                    y0 + 7,
                    x1 - 7,
                    y1 - 7,
                    fill="#3d4942",
                    outline="#f0f4dc",
                    width=2,
                )
                mark = "##"
                foreground = "#f0f4dc"
            else:
                mark = portal_names.get(index, CELL_MARKS[cell])
                foreground = "#17201a"
            self.canvas.create_text(
                (x0 + x1) / 2,
                (y0 + y1) / 2,
                text=mark,
                fill=foreground,
                font=("Segoe UI Semibold", 13 if len(mark) == 1 else 10),
            )

        self.canvas.configure(scrollregion=(0, 0, self.width * CELL_SIZE, self.height * CELL_SIZE))

    def _scroll_board(self, event: tk.Event) -> None:
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _resize_board(self) -> None:
        try:
            width, height = int(self.width_var.get()), int(self.height_var.get())
            if not MIN_BOARD_SIZE <= width <= MAX_BOARD_SIZE or not MIN_BOARD_SIZE <= height <= MAX_BOARD_SIZE:
                raise ValueError(f"Choose dimensions from {MIN_BOARD_SIZE} to {MAX_BOARD_SIZE}.")
        except ValueError as error:
            messagebox.showerror("Invalid board size", str(error), parent=self.root)
            return

        resized = [Cell.GRASS] * (width * height)
        for row in range(min(height, self.height)):
            for column in range(min(width, self.width)):
                resized[row * width + column] = self.cells[row * self.width + column]
        if not any(cell is Cell.HORSE for cell in resized):
            resized[(height // 2) * width + width // 2] = Cell.HORSE

        self.width, self.height, self.cells = width, height, resized
        self._board_changed()
        self.status_var.set(f"Board resized to {width} columns by {height} rows.")

    def _reset_board(self) -> None:
        self.cells = [Cell.GRASS] * (self.width * self.height)
        self.cells[(self.height // 2) * self.width + self.width // 2] = Cell.HORSE
        self._board_changed()
        self.status_var.set("Level reset. Paint tiles to rebuild your puzzle.")

    def _make_board(self) -> Board:
        portal_indices = [index for index, cell in enumerate(self.cells) if cell is Cell.PORTAL]
        if len(portal_indices) not in (0, 2):
            raise ValueError("Place exactly two portal tiles, or remove the unpaired portal.")
        portal_pairs = ((portal_indices[0], portal_indices[1]),) if portal_indices else ()
        return Board(self.width, self.height, tuple(self.cells), portal_pairs)

    def _start_solving(self) -> None:
        if self.is_solving:
            return
        try:
            board = self._make_board()
            wall_budget = int(self.wall_budget_var.get())
            if wall_budget < 0:
                raise ValueError("Maximum walls must be zero or greater.")
        except ValueError as error:
            messagebox.showerror("Cannot solve this level", str(error), parent=self.root)
            return

        revision = self.board_revision
        self.is_solving = True
        self.solve_button.configure(state="disabled", text="Solving...")
        self.wall_budget_control.configure(state="disabled")
        self.status_var.set("Searching wall placements. The editor will remain responsive.")

        def worker() -> None:
            try:
                result = solve(board, wall_budget)
                self.root.after(0, self._finish_solving, revision, result, None)
            except Exception as error:
                self.root.after(0, self._finish_solving, revision, None, error)

        threading.Thread(target=worker, name="enclose-horse-solver", daemon=True).start()

    def _finish_solving(
        self,
        revision: int,
        result: SolveResult | None,
        error: Exception | None,
    ) -> None:
        self.is_solving = False
        self.solve_button.configure(state="normal", text="Run solver")
        self.wall_budget_control.configure(state="normal")
        if revision != self.board_revision:
            self.status_var.set("Board changed while solving. Run the solver again for the updated level.")
            return
        if error is not None:
            messagebox.showerror("Solver error", str(error), parent=self.root)
            self.status_var.set("The solver stopped because of an error.")
            return
        if result is None:
            return

        self.solution = result
        self._draw_board()
        if not result.valid_solution:
            self.result_var.set("No valid enclosure")
            self.result_details_var.set(f"No wall placement within this budget can block every route to the border.\n\nStates checked: {result.explored_states:,}")
            self.wall_list_var.set("")
            self.apply_button.configure(state="disabled")
            self.status_var.set("No valid solution found for this wall budget.")
            return

        self.result_var.set(f"Best score   {result.best_score}")
        self.result_details_var.set(
            f"Enclosed tiles     {result.enclosed_area}\n"
            f"Cherries           {result.collected_cherries}\n"
            f"Golden apples      {result.collected_apples}\n"
            f"Trapped bees       {result.trapped_bees}\n"
            f"Walls used         {len(result.wall_coordinates)}\n"
            f"States checked     {result.explored_states:,}"
        )
        wall_lines = [f"({row}, {column})" for row, column in result.wall_coordinates]
        self.wall_list_var.set("Suggested walls\n" + (", ".join(wall_lines) if wall_lines else "None needed"))
        self.apply_button.configure(state="normal" if result.wall_coordinates else "disabled")
        self.status_var.set("Solution found. Suggested walls are outlined on the board.")

    def _apply_solution(self) -> None:
        if self.solution is None or not self.solution.valid_solution:
            return
        for row, column in self.solution.wall_coordinates:
            self.cells[row * self.width + column] = Cell.WALL
        self._board_changed()
        self.status_var.set("Suggested walls applied to the level.")


def main() -> None:
    root = tk.Tk()
    EncloseHorseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()