import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from ..models.plate_model import PlateModel, WellType


class PlateWidget:
    """Interactive 96-well plate widget for Toga."""

    def __init__(self, app, model=None):
        self.app = app
        self.model = model or PlateModel(app, 8, 12)
        self.container = None
        self.well_count_label = None

        # Controls
        self.well_type_dropdown = None
        self.row_dropdown = None
        self.col_dropdown = None
        self.range_row_from = None
        self.range_col_from = None
        self.range_row_to = None
        self.range_col_to = None

        # Interactive well buttons
        self.well_buttons = {}  # {(row, col): button}

        # Range selection state machine (two-click selection)
        self.range_selection_mode = False  # True when waiting for second click
        self.range_start_well = None       # (row, col) of first click

    def create_layout(self):
        """Create Toga widget layout."""
        container = toga.Box(style=Pack(direction=COLUMN, flex=1))

        # Control section
        controls = self._create_controls()
        container.add(controls)

        # Interactive well plate grid
        plate_grid = self._create_interactive_plate()
        container.add(plate_grid)

        # Well count display
        self.well_count_label = toga.Label(
            '',
            style=Pack(margin=5, font_size=10)
        )
        container.add(self.well_count_label)


        # Initial render
        self.refresh_visualization()

        self.container = container
        return container

    def _create_interactive_plate(self):
        """Create interactive clickable well plate grid."""
        plate_container = toga.Box(style=Pack(direction=COLUMN, margin=10, flex=1))

        # Create grid container with row and column labels
        grid_with_labels = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Column headers (1-12)
        header_row = toga.Box(style=Pack(direction=ROW, margin=2))
        header_row.add(toga.Label('', style=Pack(width=30)))  # Spacer for row labels
        for col in range(12):
            col_label = toga.Label(
                str(col + 1),
                style=Pack(width=37, text_align='center', font_size=10)
            )
            header_row.add(col_label)
        grid_with_labels.add(header_row)

        # Create rows with wells
        for row in range(8):
            row_box = toga.Box(style=Pack(direction=ROW, margin=2))

            # Row label (A-H)
            row_label = toga.Label(
                chr(65 + row),
                style=Pack(width=30, text_align='center', font_weight='bold', font_size=10)
            )
            row_box.add(row_label)

            # Create well buttons for this row
            for col in range(12):
                # Create a wrapper function to capture row, col properly
                def create_handler(r, c):
                    async def handler(widget):
                        await self.on_well_click(widget, r, c)
                    return handler

                well_btn = toga.Button(
                    '',
                    on_press=create_handler(row, col),
                    style=Pack(
                        width=35,
                        height=35,
                        margin=1,
                        background_color='#FFFFFF',
                        color='#000000'
                    )
                )
                self.well_buttons[(row, col)] = well_btn
                row_box.add(well_btn)

            grid_with_labels.add(row_box)

        plate_container.add(grid_with_labels)

        # Update button colors to match initial state
        self._update_well_button_colors()

        return plate_container

    def _create_controls(self):
        """Create well type selector and action buttons."""
        controls_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Well type selector row
        type_row = toga.Box(style=Pack(direction=ROW, margin=5))
        type_label = toga.Label('Well Type:', style=Pack(margin_right=10, width=80))

        self.well_type_dropdown = toga.Selection(
            items=['Empty', 'Blank', 'Calibrant', 'Sample', 'Positive Control', 'Negative Control'],
            on_change=self.on_well_type_changed,
            style=Pack(flex=1, margin_right=10)
        )
        self.well_type_dropdown.value = 'Sample'  # Default to Sample

        type_row.add(type_label, self.well_type_dropdown)
        controls_box.add(type_row)

        # Action buttons row
        actions_row = toga.Box(style=Pack(direction=ROW, margin=5))

        select_all_btn = toga.Button(
            'Select All',
            on_press=self.on_select_all,
            style=Pack(margin=5, flex=1)
        )

        clear_btn = toga.Button(
            'Clear Plate',
            on_press=self.on_clear_plate,
            style=Pack(margin=5, flex=1)
        )

        cancel_range_btn = toga.Button(
            'Cancel Range',
            on_press=self.on_cancel_range_selection,
            style=Pack(margin=5, flex=1)
        )

        actions_row.add(select_all_btn, clear_btn, cancel_range_btn)
        controls_box.add(actions_row)

        return controls_box

    
    def refresh_visualization(self, changed_wells=None):
        """
        Update visualization (differential updates only).

        Args:
            changed_wells: Set of (row, col) tuples that changed.
                          If None, updates all wells.
        """
        # Update only changed buttons (or all if None)
        if changed_wells is None:
            self._update_well_button_colors()
        else:
            self._update_specific_buttons(changed_wells)

        # Update well count display using cached counts
        self._update_well_count_display()

    def _update_well_button_colors(self):
        """Update well button colors and labels based on model state."""
        for (row, col), button in self.well_buttons.items():
            self._update_single_button(button, row, col)

    def _update_specific_buttons(self, wells_set):
        """Update only specific well buttons (performance optimization)."""
        for (row, col) in wells_set:
            if (row, col) in self.well_buttons:
                button = self.well_buttons[(row, col)]
                self._update_single_button(button, row, col)

    def _update_single_button(self, button, row, col):
        """Update a single button's appearance."""
        well_type = self.model.grid[row][col]
        color = self.model.colors[well_type]

        # Check for range selection highlighting
        is_range_start = (self.range_selection_mode and
                         self.range_start_well == (row, col))

        # Check if well has a selection number
        selection_num = self.model.get_selection_number(row, col)
        if selection_num is not None:
            button.text = str(selection_num)
            button.style.color = '#FFFFFF'
        else:
            button.text = ''
            button.style.color = '#000000'

        button.style.background_color = color

        # Add visual indicator for range start (⊙ symbol)
        if is_range_start:
            button.text = '⊙' if not selection_num else f'⊙{selection_num}'

    def _update_well_count_display(self):
        """Update well count label using cached counts."""
        counts = self.model.get_well_counts()
        count_text = (
            f"Empty: {counts[WellType.EMPTY]} | "
            f"Blank: {counts[WellType.BLANK]} | "
            f"Calibrant: {counts[WellType.CALIBRANT]} | "
            f"Sample: {counts[WellType.SAMPLE]} | "
            f"Pos: {counts[WellType.POSITIVE_CONTROL]} | "
            f"Neg: {counts[WellType.NEGATIVE_CONTROL]}"
        )
        self.well_count_label.text = count_text
        
    def _well_name(self, row, col):
        """Return well name like A01, B12."""
        return f"{chr(65 + row)}{col + 1:02d}"

    async def on_well_click(self, widget, row, col):
        """
        Handle well button click with two-click range selection.

        State machine:
        - First click: Mark range start (visual feedback with ⊙ symbol)
        - Second click: Select rectangular range from start to end
        """
        if not self.range_selection_mode:
            # First click - enter range selection mode
            self.range_selection_mode = True
            self.range_start_well = (row, col)
            self.app.log(f"Range start selected: {self._well_name(row, col)}")

            # Visual feedback - update only this button
            self._update_specific_buttons({(row, col)})

        else:
            # Second click - complete range selection
            row_start, col_start = self.range_start_well
            row_end, col_end = (row, col)
            active = self.model.active_key.name
            self.app.log(
                f"Apply range {self._well_name(row_start, col_start)} → {self._well_name(row_end, col_end)} as {active}"
            )
            # Select the range and get affected wells
            affected_wells = self.model.select_range(
                row_start, col_start, row_end, col_end
            )
            self.app.log(f"Updated {len(affected_wells)} wells to {active}.")


            # Exit range selection mode
            self.range_selection_mode = False
            old_start = self.range_start_well
            self.range_start_well = None

            # Update only affected buttons plus old range start
            affected_wells.add(old_start)
            self.refresh_visualization(changed_wells=affected_wells)

    async def on_cancel_range_selection(self, widget=None):
        """Cancel ongoing range selection."""
        if self.range_selection_mode:
            old_start = self.range_start_well
            self.range_selection_mode = False
            self.range_start_well = None

            # Update only the former range start button
            if old_start:
                self._update_specific_buttons({old_start})
            
            self.app.log("Canceled range selection")

    def on_well_type_changed(self, widget):
        """Handle well type dropdown change."""
        type_map = {
            'Empty': WellType.EMPTY,
            'Blank': WellType.BLANK,
            'Calibrant': WellType.CALIBRANT,
            'Sample': WellType.SAMPLE,
            'Positive Control': WellType.POSITIVE_CONTROL,
            'Negative Control': WellType.NEGATIVE_CONTROL,
        }
        self.model.active_key = type_map[widget.value]
        self.app.log(f"well type changed to {widget.value}")

    async def on_select_all(self, widget):
        """Handle Select All button."""
        self.model.select_all()
        self.refresh_visualization()
        self.app.log("All wells have been filled")



    async def on_clear_plate(self, widget):
        """Handle Clear Plate button."""
        self.model.select_none()
        self.refresh_visualization()
        self.app.log("Well Plate Cleared")


