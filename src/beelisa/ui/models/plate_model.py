from enum import Enum
from collections import OrderedDict
import pandas as pd

class WellType(Enum):
    """Well type enumeration for 96-well plate."""
    EMPTY = 0
    BLANK = 1
    CALIBRANT = 2
    SAMPLE = 3
    POSITIVE_CONTROL = 4
    NEGATIVE_CONTROL = 5


class PlateModel:
    """Framework-agnostic state management for 96-well plate."""

    def __init__(self, app, rows=8, cols=12):
        self.app = app
        self.rows = rows
        self.cols = cols
        self.margin = 5
        self.show_labels = True
        self.show_well_labels = True
        self.show_legend = False

        # Labels for well types
        self.labels = {
            WellType.EMPTY: 'Empty',
            WellType.BLANK: 'Blank',
            WellType.CALIBRANT: 'Calibrant',
            WellType.SAMPLE: 'Sample',
            WellType.POSITIVE_CONTROL: 'Positive Control',
            WellType.NEGATIVE_CONTROL: 'Negative Control',
        }

        # Colors in hex format for matplotlib (converted from RGB tuples)
        self.colors = {
            WellType.EMPTY: "#FFFFFF48",            # White
            WellType.BLANK: "#6666FF39",            # Blue
            WellType.CALIBRANT: "#33CC3339",        # Green
            WellType.SAMPLE: "#CC33334F",           # Red
            WellType.POSITIVE_CONTROL: "#FFB84D4F", # Orange
            WellType.NEGATIVE_CONTROL: "#9966CC4A", # Purple
        }

        self.menu_items = []
        self.active_key = WellType.SAMPLE
        self.grid = [[WellType.EMPTY] * self.cols for _ in range(self.rows)]

        # Selection order tracking
        self.selection_order = []  # List of selection entries
        self.selection_history = OrderedDict()  # {(row, col): selection_index}

        # Incremental well count cache (performance optimization)
        self._well_count_cache = {well_type: 0 for well_type in WellType}
        self._initialize_well_counts()

    def select(self, row, col):
        """Set well at (row, col) to active well type."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.add_to_selection_order(row, col)  # Use order tracking

    def toggle(self, row, col):
        """Toggle well between active type and empty."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            old_type = self.grid[row][col]

            if old_type == self.active_key:
                new_type = WellType.EMPTY
                self.grid[row][col] = new_type
                self.remove_from_selection_order(row, col)  # Remove from order
            else:
                new_type = self.active_key
                self.add_to_selection_order(row, col)  # Add with order

    def select_all(self):
        """Set all wells to active well type."""
        for row in range(self.rows):
            for col in range(self.cols):
                old_type = self.grid[row][col]
                if old_type != self.active_key:
                    self.add_to_selection_order(row, col)
        self.grid = [[self.active_key] * self.cols for _ in range(self.rows)]

    def select_none(self):
        """Clear all wells to empty."""
        for row in range(self.rows):
            for col in range(self.cols):
                old_type = self.grid[row][col]
                if old_type != WellType.EMPTY:
                    self.add_to_selection_order(row, col)
        self.grid = [[WellType.EMPTY] * self.cols for _ in range(self.rows)]
        self.clear_selection_order()

    def select_row(self, row):
        """Set all wells in a row to active well type."""
        if 0 <= row < self.rows:
            for col in range(self.cols):
                old_type = self.grid[row][col]
                if old_type != self.active_key:
                    self.grid[row][col] = self.active_key

    def select_column(self, col):
        """Set all wells in a column to active well type."""
        if 0 <= col < self.cols:
            for row in range(self.rows):
                old_type = self.grid[row][col]
                if old_type != self.active_key:
                    self.grid[row][col] = self.active_key

    def select_range(self, row_start, col_start, row_end, col_end, replicate_round=None):
        """
        Set all wells in a rectangular range to active well type.
        Returns set of affected (row, col) tuples for differential updates.
        """
        row_start = max(0, min(row_start, row_end))
        row_end = min(self.rows - 1, max(row_start, row_end))
        col_start = max(0, min(col_start, col_end))
        col_end = min(self.cols - 1, max(col_start, col_end))

        affected_wells = set()
        for row in range(row_start, row_end + 1):
            for col in range(col_start, col_end + 1):
                old_type = self.grid[row][col]
                if old_type != self.active_key:
                    self.add_to_selection_order(row, col, self.active_key, replicate_round)
                    affected_wells.add((row, col))

        return affected_wells

    def add_to_selection_order(self, row, col, well_type=None, replicate_round=None):
        """Add well to selection order, tracking sequence."""
        if well_type is None:
            well_type = self.active_key

        old_type = self.grid[row][col]

        # If already selected with same type, don't add again
        if (row, col) in self.selection_history and self.grid[row][col] == well_type:
            return

        # If well type is changing or it's a new selection
        if (row, col) in self.selection_history:
            # Remove old entry
            old_index = self.selection_history[(row, col)]
            self.selection_order = [s for s in self.selection_order if s['index'] != old_index]
            # Renumber remaining selections
            for i, entry in enumerate(self.selection_order, 1):
                entry['index'] = i
                self.selection_history[entry['coords']] = i

        if old_type != well_type:
            self._update_well_count(old_type, well_type)
            self.grid[row][col] = well_type

        # Add new selection
        index = len(self.selection_order) + 1
        rep_round = replicate_round if replicate_round is not None else 0
        self.selection_order.append({
            'index': index,
            'well': '%s%02d' % (chr(65 + row), col + 1),
            'row': row,
            'col': col,
            'type': well_type,
            'coords': (row, col),
            'replicate_round': rep_round
        })
        self.selection_history[(row, col)] = index

        self.plate_design()
                    
    def get_selection_order_for_type(self, well_type):
        """Get ordered list of wells for a specific type."""
        return [s for s in self.selection_order if s['type'] == well_type]

    def get_selection_number(self, row, col):
        """Get the selection number for a well (or None if not selected with order)."""
        return self.selection_history.get((row, col), None)

    def clear_selection_order(self):
        """Clear selection order tracking."""
        self.selection_order = []
        self.selection_history = OrderedDict()

    def remove_from_selection_order(self, row, col):
        """Remove a well from selection order."""
        if (row, col) in self.selection_history:
            self.selection_order = [s for s in self.selection_order if s['coords'] != (row, col)]
            del self.selection_history[(row, col)]

            # Renumber remaining selections
            for i, entry in enumerate(self.selection_order, 1):
                entry['index'] = i
                self.selection_history[entry['coords']] = i

    def get_replicate_round(self, row, col):
        """Get replicate round for a well (0=original, 1=replicate, etc.)."""
        for w in self.selection_order:
            if w['coords'] == (row, col):
                return w.get('replicate_round', 0)
        return 0

    def has_originals_for_type(self, well_type):
        """Check if any original wells (replicate_round=0) exist for given type."""
        for entry in self.selection_order:
            if entry['type'] == well_type and entry.get('replicate_round', 0) == 0:
                return True
        return False

    def get_well_order(self, row, col):
        """Get the order number for a well (0-based, cycles for replicates)."""
        # Don't return order for empty wells
        if self.grid[row][col] == WellType.EMPTY:
            return None

        if self.app.plate_design_df is None:
            return None
        well_id = f"{chr(65 + row)}{col + 1:02d}"
        match = self.app.plate_design_df[self.app.plate_design_df['well_id'] == well_id]
        if not match.empty:
            order = match.iloc[0].get('order')
            return order if pd.notna(order) else None
        return None

    def get_unique_calibrant_count(self):
        """Get count of unique calibrant concentration levels (not including replicates)."""
        calibrant_wells = [w for w in self.selection_order
                           if w['type'] == WellType.CALIBRANT and w.get('replicate_round', 0) == 0]
        return len(calibrant_wells)

    def check_cell(self, row, col, key=None):
        """Check if cell matches given key, or return cell value if key is None."""
        if key is None:
            return self.grid[row][col]
        else:
            return self.grid[row][col] == key

    def get_col_major_indexes(self, key=None):
        """Get column-major well indexes (1-based) for wells matching key."""
        result = []
        index = 1
        for col in range(self.cols):
            for row in range(self.rows):
                if self.check_cell(row, col, key):
                    result.append(index)
                index += 1
        return result

    def get_row_major_indexes(self, key=None):
        """Get row-major well indexes (1-based) for wells matching key."""
        result = []
        index = 1
        for row in range(self.rows):
            for col in range(self.cols):
                if self.check_cell(row, col, key):
                    result.append(index)
                index += 1
        return result

    def get_names(self, key=None):
        """Get well names (e.g., A01, B12) for wells matching key."""
        result = []
        for row in range(self.rows):
            for col in range(self.cols):
                if self.check_cell(row, col, key):
                    name = '%s%02d' % (chr(ord('A') + row), col + 1)
                    result.append(name)
        return result

    def get_well_counts(self):
        """Get count of wells for each well type."""
        counts = {well_type: 0 for well_type in WellType}
        for row in range(self.rows):
            for col in range(self.cols):
                counts[self.grid[row][col]] += 1

        return counts

    def to_dict(self):
        """Export plate configuration to dictionary."""
        return {
            'grid': [[well.value for well in row] for row in self.grid],
            'active_key': self.active_key.value,
        }

    def plate_design(self, key=None):
        # Count originals (replicate_round=0) for each type
        original_counts = {}
        for well in self.selection_order:
            t = well["type"]
            if well.get('replicate_round', 0) == 0:
                original_counts[t] = original_counts.get(t, 0) + 1

        # Assign order cyclically (replicates get same order as originals)
        plate_order = {}
        plate_rep_round = {}
        well_type_counter = {t: 0 for t in WellType}

        for well in self.selection_order:
            t = well["type"]
            rc = well["coords"]
            rep_round = well.get('replicate_round', 0)

            # Order cycles: 0,1,2,3,4,0,1,2,3,4,0,1,2,3,4...
            max_order = original_counts.get(t, 1)
            order = well_type_counter[t] % max_order if max_order > 0 else well_type_counter[t]
            well_type_counter[t] += 1

            plate_order[rc] = order
            plate_rep_round[rc] = rep_round

        result = []
        for row in range(self.rows):
            for col in range(self.cols):
                t = self.grid[row][col]
                if key is not None and t != key:
                    continue
                well_id = f"{chr(65 + row)}{col + 1:02d}"
                order = plate_order.get((row, col))
                rep_round = plate_rep_round.get((row, col), 0)

                result.append({
                    "well_id": well_id,
                    "well_type": t.name,
                    "order": order,
                    "replicate_round": rep_round,
                    "is_replicate": rep_round > 0
                })
        self.app.plate_design_df = pd.DataFrame(result)

        return result
                        
    # def from_dict(self, config):
    #     """Load plate configuration from dictionary."""
    #     self.grid = [[WellType(well) for well in row] for row in config['grid']]
    #     self.active_key = WellType(config['active_key'])
    #     self._well_count_cache = {well_type: 0 for well_type in WellType}
    #     self._initialize_well_counts()

    def _initialize_well_counts(self):
        """Initialize well count cache by scanning grid once."""
        for row in range(self.rows):
            for col in range(self.cols):
                self._well_count_cache[self.grid[row][col]] += 1
        self.plate_design()
        
    def _update_well_count(self, old_type, new_type):
        """Incrementally update well counts when a well changes."""
        if old_type != new_type:
            self._well_count_cache[old_type] -= 1
            self._well_count_cache[new_type] += 1


