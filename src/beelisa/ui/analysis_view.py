import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW


# Column name to display name mapping
COLUMN_DISPLAY_NAMES = {
    'concentration_dilution_corrected': 'Concentration',
    'od_value': 'OD Value',
    'concentration': 'Raw Concentration',
    'plate_name': 'Plate Name',
    'well_id': 'Well ID',
    'well_type': 'Well Type',
    'sample_id': 'Sample ID',
    'detection_status': 'Detection Status',
    'order': 'Order',
}


class AnalysisView:
    """ELISA analysis interface with configuration and plate grouping."""

    def __init__(self, app):
        self.app = app
        self.calibrant_rows = []
        self.calibrant_container = []

        # Plate grouping UI elements
        self.plate_switches = {}  # {plate_name: toga.Switch}
        self.plates_container = None
        self.groups_list_container = None
        self.group_name_input = None

    def create_layout(self):
        """Create analysis view layout."""
        
        left_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        left_container = toga.ScrollContainer(content=left_box, style=Pack(flex=1))
        right_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        right_container = toga.ScrollContainer(content=right_box, flex=1)
        container = toga.SplitContainer(content=[left_container, right_container], style=Pack(direction=COLUMN, flex=1, margin=10))

        # Configuration section
        config = self.create_configuration_section()
        left_box.add(config)

        # Action buttons
        buttons = self.create_action_buttons()
        left_box.add(buttons)

        # Plate Grouping
        grouping = self.create_plate_grouping_section()
        right_box.add(grouping)
        self.container = container

        return container

    def create_configuration_section(self):
        """Create calibrant input, dilution factor, and LOD/LOQ mode."""
        config_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Header
        header = toga.Label(
            'ANALYSIS CONFIGURATION',
            style=Pack(margin=5, font_weight='bold', font_size=14)
        )
        config_box.add(header)
        config_box.add(toga.Divider())

        # Calibrant concentrations
        calib_label = toga.Label(
            'Calibrant Concentrations:',
            style=Pack(margin=5, font_weight='bold')
        )
        config_box.add(calib_label)

        # Calibrant input container
        self.calibrant_container = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Start with 5 rows 
        calibrants_range = range(5)
        for order in calibrants_range:
            row = self.create_calibrant_row(order)
            self.calibrant_container.add(row)

        config_box.add(self.calibrant_container)

        # Dilution factor
        dilution_box = toga.Box(style=Pack(direction=ROW, margin=5))
        dilution_label = toga.Label(
            'Dilution Factor:',
            style=Pack(margin=5, width=150)
        )
        self.dilution_input = toga.TextInput(
            value='101',
            placeholder='1:101 (z. B. 10 µL Probe + 1000 µL Puffer → Verdünnungsfaktor 101)',
            style=Pack(flex=1, margin=5)
        )
        dilution_box.add(dilution_label, self.dilution_input)
        config_box.add(dilution_box)

        # LOD/LOQ mode
        lod_box = toga.Box(style=Pack(direction=ROW, margin=5))
        lod_label = toga.Label(
            'LOD/LOQ Calculation:',
            style=Pack(margin=5, width=150)
        )
        self.lod_mode_select = toga.Selection(
            items=['Per Plate', 'Global'],
            style=Pack(flex=1, margin=5)
        )
        lod_box.add(lod_label, self.lod_mode_select)
        config_box.add(lod_box)

        # Concentration unit
        unit_box = toga.Box(style=Pack(direction=ROW, margin=5))
        unit_label = toga.Label(
            'Concentration Unit:',
            style=Pack(margin=5, width=150)
        )
        self.unit_input = toga.TextInput(
            value='U/mL',
            placeholder='e.g., ng/mL, µg/mL, pM',
            style=Pack(flex=1, margin=5)
        )
        unit_box.add(unit_label, self.unit_input)
        config_box.add(unit_box)

        # Heatmap configuration header
        config_box.add(toga.Divider())
        heatmap_header = toga.Label(
            'Plate Heatmap Settings:',
            style=Pack(margin=5, font_weight='bold')
        )
        config_box.add(heatmap_header)

        # Heatmap color variable
        heatmap_var_box = toga.Box(style=Pack(direction=ROW, margin=5))
        heatmap_var_label = toga.Label(
            'Color Variable:',
            style=Pack(margin=5, width=150)
        )
        self.heatmap_color_var = toga.Selection(
            items=['None', 'od_value', 'concentration', 'concentration_dilution_corrected'],
            style=Pack(flex=1, margin=5)
        )
        self.heatmap_color_var.value = 'od_value'
        heatmap_var_box.add(heatmap_var_label, self.heatmap_color_var)
        config_box.add(heatmap_var_box)

        # Heatmap size variable
        heatmap_size_box = toga.Box(style=Pack(direction=ROW, margin=5))
        heatmap_size_label = toga.Label(
            'Size Variable:',
            style=Pack(margin=5, width=150)
        )
        self.heatmap_size_var = toga.Selection(
            items=['None', 'od_value', 'concentration', 'concentration_dilution_corrected'],
            style=Pack(flex=1, margin=5)
        )
        self.heatmap_size_var.value = 'None'
        heatmap_size_box.add(heatmap_size_label, self.heatmap_size_var)
        config_box.add(heatmap_size_box)

        # Heatmap label variable (for string metadata like sample_id, condition)
        heatmap_label_box = toga.Box(style=Pack(direction=ROW, margin=5))
        heatmap_label_label = toga.Label(
            'Label Variable:',
            style=Pack(margin=5, width=150)
        )
        self.heatmap_label_var = toga.Selection(
            items=['None'],
            style=Pack(flex=1, margin=5)
        )
        self.heatmap_label_var.value = 'None'
        heatmap_label_box.add(heatmap_label_label, self.heatmap_label_var)
        config_box.add(heatmap_label_box)

        # Heatmap colormap
        heatmap_cmap_box = toga.Box(style=Pack(direction=ROW, margin=5))
        heatmap_cmap_label = toga.Label(
            'Colormap:',
            style=Pack(margin=5, width=150)
        )
        self.heatmap_colormap = toga.Selection(
            items=['viridis', 'YlGnBu', 'Greys', 'coolwarm', 'berlin', 'binary', 'Wistia'],
            style=Pack(flex=1, margin=5)
        )
        self.heatmap_colormap.value = 'viridis'
        heatmap_cmap_box.add(heatmap_cmap_label, self.heatmap_colormap)
        config_box.add(heatmap_cmap_box)

        return config_box

    def create_plate_grouping_section(self):
        """Create plate grouping panel for organizing plates into groups."""
        grouping_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

        # Header
        header = toga.Label(
            'PLATE GROUPS',
            style=Pack(margin=5, font_weight='bold', font_size=14)
        )
        grouping_box.add(header)
        grouping_box.add(toga.Divider())

        # Available Plates section
        available_label = toga.Label(
            'Available Plates (unassigned):',
            style=Pack(margin=5, font_weight='bold')
        )
        grouping_box.add(available_label)

        # Container for plate checkboxes (will be populated dynamically)
        self.plates_container = toga.Box(style=Pack(direction=COLUMN, margin=5))
        plates_scroll = toga.ScrollContainer(
            content=self.plates_container,
            style=Pack(height=120, margin=5)
        )
        grouping_box.add(plates_scroll)

        # Group creation section
        create_label = toga.Label(
            'Create New Group:',
            style=Pack(margin=5, font_weight='bold')
        )
        grouping_box.add(create_label)

        # Group name input row
        create_row = toga.Box(style=Pack(direction=ROW, margin=5))
        self.group_name_input = toga.TextInput(
            placeholder='Enter group name...',
            style=Pack(flex=1, margin=2)
        )
        create_btn = toga.Button(
            '+ Create Group',
            on_press=self.on_create_group,
            style=Pack(margin=2)
        )
        create_row.add(self.group_name_input, create_btn)
        grouping_box.add(create_row)

        grouping_box.add(toga.Divider())

        # Existing Groups section
        groups_label = toga.Label(
            'Created Groups:',
            style=Pack(margin=5, font_weight='bold')
        )
        grouping_box.add(groups_label)

        # Container for groups list (will be populated dynamically)
        self.groups_list_container = toga.Box(style=Pack(direction=COLUMN, margin=5))
        groups_scroll = toga.ScrollContainer(
            content=self.groups_list_container,
            style=Pack(height=150, margin=5)
        )
        grouping_box.add(groups_scroll)

        # Clear all groups button
        clear_btn = toga.Button(
            'Clear All Groups',
            on_press=self.on_clear_all_groups,
            style=Pack(margin=5)
        )
        grouping_box.add(clear_btn)

        return grouping_box

    def update_variable_selection(self):
        """Update variable dropdowns with available columns."""
        if getattr(self.app, "connected_df", None) is None:
            return

        df_headers = list(self.app.connected_df.columns.values)

        # Add known analysis result columns
        analysis_columns = ['concentration_dilution_corrected', 'concentration', 'detection_status']
        for col in analysis_columns:
            if col not in df_headers:
                df_headers.append(col)

        # Create display items with names
        display_items = []
        self.column_name_mapping = {}  # display_name -> actual_name

        for col in df_headers:
            display_name = COLUMN_DISPLAY_NAMES.get(col, col.replace('_', ' ').title())
            display_items.append(display_name)
            self.column_name_mapping[display_name] = col

        # Update heatmap variable selectors with display names
        if hasattr(self, 'heatmap_color_var') and self.heatmap_color_var:
            self.heatmap_color_var.items = display_items
            od_display = COLUMN_DISPLAY_NAMES.get('od_value', 'Od Value')
            if od_display in display_items:
                self.heatmap_color_var.value = od_display

        if hasattr(self, 'heatmap_size_var') and self.heatmap_size_var:
            self.heatmap_size_var.items = ['None'] + display_items
            self.heatmap_size_var.value = 'None'

        if hasattr(self, 'heatmap_label_var') and self.heatmap_label_var:
            self.heatmap_label_var.items = ['None'] + display_items
            self.heatmap_label_var.value = 'None'

    def rebuild_calibrant_rows(self):
        """ Rebuild count of calibrants"""
        cal_count = int(self.app.calibrant_count or 0)
        self.calibrant_container.clear()
        self.calibrant_rows.clear()
        for order in range(cal_count):
            row = self.create_calibrant_row(order)
            self.calibrant_container.add(row)

    # ==================== PLATE GROUPING METHODS ====================

    def refresh_plate_checkboxes(self):
        """Rebuild available plates list (only unassigned plates)."""
        if self.plates_container is None:
            return

        self.plates_container.clear()
        self.plate_switches.clear()

        # Get plates already in groups
        grouped_plates = set()
        for plates in self.app.plate_groups.values():
            grouped_plates.update(plates)

        # Show only unassigned plates
        for plate in self.app.plates:
            plate_name = plate["name"]
            if plate_name not in grouped_plates:
                switch = toga.Switch(
                    plate_name,
                    style=Pack(margin=2)
                )
                self.plate_switches[plate_name] = switch
                self.plates_container.add(switch)

        # Show message if no plates available
        if not self.plate_switches:
            if len(self.app.plates) == 0:
                msg = toga.Label(
                    'No plates loaded yet.',
                    style=Pack(margin=5, font_style='italic')
                )
            else:
                msg = toga.Label(
                    'All plates are assigned to groups.',
                    style=Pack(margin=5, font_style='italic')
                )
            self.plates_container.add(msg)

    def refresh_groups_display(self):
        """Rebuild the groups list display."""
        if self.groups_list_container is None:
            return

        self.groups_list_container.clear()

        if not self.app.plate_groups:
            msg = toga.Label(
                'No groups created yet.',
                style=Pack(margin=5, font_style='italic')
            )
            self.groups_list_container.add(msg)
            return

        for group_name, plates in self.app.plate_groups.items():
            group_box = toga.Box(style=Pack(direction=COLUMN, margin=5))

            # Header row with name and remove button
            header_row = toga.Box(style=Pack(direction=ROW))
            header_label = toga.Label(
                f'{group_name} ({len(plates)} plates)',
                style=Pack(flex=1, font_weight='bold', margin=2)
            )
            remove_btn = toga.Button(
                'Remove',
                on_press=lambda w, gn=group_name: self.on_remove_group(gn),
                style=Pack(margin=2)
            )
            header_row.add(header_label, remove_btn)

            # Plates list
            plates_str = ', '.join(plates) if len(plates) <= 5 else ', '.join(plates[:5]) + f'... (+{len(plates)-5})'
            plates_label = toga.Label(
                f'  {plates_str}',
                style=Pack(margin=2)
            )

            group_box.add(header_row, plates_label)
            group_box.add(toga.Divider())
            self.groups_list_container.add(group_box)

    async def on_create_group(self, widget):
        """Create a new group from selected plates."""
        group_name = self.group_name_input.value.strip() if self.group_name_input else ''

        # Validate group name
        if not group_name:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Invalid Name', 'Please enter a group name.')
            )
            return

        if len(group_name) > 50:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Invalid Name', 'Group name must be 50 characters or less.')
            )
            return

        if group_name in self.app.plate_groups:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Duplicate Name', f'A group named "{group_name}" already exists.')
            )
            return

        # Collect selected plates
        selected = [name for name, switch in self.plate_switches.items() if switch.value]

        if not selected:
            await self.app.main_window.dialog(
                toga.ErrorDialog('No Plates Selected', 'Please select at least one plate to create a group.')
            )
            return

        # Create the group
        self.app.plate_groups[group_name] = selected
        self.app.log(f'Created group "{group_name}" with {len(selected)} plate(s): {", ".join(selected)}')

        # Clear input and refresh UI
        self.group_name_input.value = ''
        self.refresh_plate_checkboxes()
        self.refresh_groups_display()

    def on_remove_group(self, group_name):
        """Remove a group and return plates to available pool."""
        if group_name in self.app.plate_groups:
            plates = self.app.plate_groups[group_name]
            del self.app.plate_groups[group_name]
            self.app.log(f'Removed group "{group_name}", {len(plates)} plate(s) returned to available')

            # Refresh UI
            self.refresh_plate_checkboxes()
            self.refresh_groups_display()

    async def on_clear_all_groups(self, widget):
        """Clear all groups and return all plates to available."""
        if not self.app.plate_groups:
            await self.app.main_window.dialog(
                toga.InfoDialog('No Groups', 'There are no groups to clear.')
            )
            return

        # Confirm action
        confirm = await self.app.main_window.dialog(
            toga.QuestionDialog(
                'Confirm Clear',
                f'Are you sure you want to remove all {len(self.app.plate_groups)} group(s)?'
            )
        )

        if confirm:
            count = len(self.app.plate_groups)
            self.app.plate_groups.clear()
            self.app.log(f'Cleared all {count} group(s)')

            # Refresh UI
            self.refresh_plate_checkboxes()
            self.refresh_groups_display()

    # ==================== END PLATE GROUPING METHODS ====================

    def create_calibrant_row(self, order):
        """Create a single calibrant input row."""
        row = toga.Box(style=Pack(direction=ROW, margin=2))

        order_label = toga.Label(
            f'CAL {order}:',
            style=Pack(margin=5, width=80)
        )
        conc_input = toga.TextInput(
            placeholder='Concentration',
            style=Pack(flex=1, margin=5)
        )

        row.add(order_label, conc_input)
        self.calibrant_rows.append({'order': order, 'input': conc_input, 'row_widget': row})

        return row


    def create_action_buttons(self):
        """Create Run Analysis, Clear, Export buttons."""
        btn_box = toga.Box(style=Pack(direction=ROW, margin=10))

        run_btn = toga.Button(
            'Run Analysis',
            on_press=self.on_run_analysis,
            style=Pack(margin=5, flex=1)
        )

        btn_box.add(run_btn)
        return btn_box

    async def on_run_analysis(self, widget=None):
        """Trigger analysis workflow."""
        
        if getattr(self.app, 'results_view') is not None and self.app.analysis_results is not None:
            await self.app.results_view.on_clear_results()
            
        # Collect calibrant concentrations
        calibrant_config = {}
        for row in self.calibrant_rows:
            value = row['input'].value
            if value and value.strip():
                try:
                    calibrant_config[row['order']] = float(value)
                except ValueError:
                    await self.app.main_window.dialog(
                        toga.ErrorDialog(
                            'Invalid Input',
                            f"Invalid concentration for Order {row['order']}: '{value}'"
                        )
                    )

                    return

        # Collect dilution factor
        try:
            dilution_factor = float(self.dilution_input.value)
            if dilution_factor <= 0:
                raise ValueError("Dilution factor must be positive")
        except ValueError as e:
            await self.app.main_window.dialog(
                toga.ErrorDialog('Invalid Input', f'Dilution factor error: {str(e)}')
            )
            self.app.log('Invalid Input: Check Calibrant Concentrations')


            return

        # Get LOD/LOQ mode
        lod_mode = 'per_plate' if self.lod_mode_select.value == 'Per Plate' else 'global'

        # Get concentration unit
        concentration_unit = self.unit_input.value.strip() or 'U/mL'

            
        # Check if data is loaded
        if self.app.connected_df is None or self.app.connected_df.empty:
            await self.app.main_window.dialog(
                toga.ErrorDialog('No Data', 'Please load and merge plate data first.')
            )
            self.app.log('No Data: Please load and merge plate data first.')

            return

        # Get heatmap settings - convert display names back to column names
        heatmap_color_display = self.heatmap_color_var.value if hasattr(self, 'heatmap_color_var') else 'OD Value'
        heatmap_size_display = self.heatmap_size_var.value if hasattr(self, 'heatmap_size_var') else 'None'
        heatmap_label_display = self.heatmap_label_var.value if hasattr(self, 'heatmap_label_var') else 'None'
        heatmap_colormap = self.heatmap_colormap.value if hasattr(self, 'heatmap_colormap') else 'viridis'

        mapping = getattr(self, 'column_name_mapping', {})
        heatmap_color_var = mapping.get(heatmap_color_display, 'concentration_dilution_corrected')
        heatmap_size_var = mapping.get(heatmap_size_display, 'None') if heatmap_size_display != 'None' else 'None'
        heatmap_label_var = mapping.get(heatmap_label_display, 'None') if heatmap_label_display != 'None' else 'None'

        # Update app config
        self.app.analysis_config = {
            'calibrant_concentrations': calibrant_config,
            'dilution_factor': dilution_factor,
            'lod_loq_mode': lod_mode,
            'concentration_unit': concentration_unit,
            'heatmap_color_var': heatmap_color_var,
            'heatmap_size_var': heatmap_size_var,
            'heatmap_label_var': heatmap_label_var,
            'heatmap_colormap': heatmap_colormap
        }

        # Run analysis
 
 
        self.app.engine.calibrant_concentrations = calibrant_config
        self.app.engine.dilution_factor = dilution_factor
        self.app.engine.lod_loq_mode = lod_mode

        try:
            self.app.log('Starting ELISA analysis...')
            results = self.app.engine.run_analysis(self.app.connected_df)

            if not results['success']:
                error_msg = '\n'.join(results.get('errors', ['Unknown error']))
                await self.app.main_window.dialog(
                    toga.ErrorDialog('Analysis Error', error_msg)
                )
                self.app.log('Analysis Error')

                return

            # Store results
            self.app.analysis_results = results
            self.app.log(f'Analysis completed for {len(results["curve_fits"])} plate(s)')

            # Update display in results view
            self.app.results_view.update_results_display(results)

            await self.app.main_window.dialog(
                toga.InfoDialog('Success', 'Analysis completed successfully!')
            )
            self.app.log('Success: Analysis completed successfully!')

        except Exception as e:
            self.app.log(f'Analysis error: {str(e)}')
            await self.app.main_window.dialog(
                toga.ErrorDialog('Analysis Error', str(e))
            )
