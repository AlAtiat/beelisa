import io
import json
import zipfile
from collections import OrderedDict
from datetime import datetime

import pandas as pd


class SessionIO:
    """Save and load complete BeELISA sessions to/from a .beelisa ZIP archive."""

    SESSION_VERSION = "1.0"

    @staticmethod
    def save(app, path: str) -> None:
        """Serialize all app state to a .beelisa ZIP file."""
        plate_model = app.view.plate_widget.model

        # Serialize selection_order (WellType enum → int, tuple coords → list)
        selection_order_data = []
        for entry in plate_model.selection_order:
            selection_order_data.append({
                'index': entry['index'],
                'well': entry['well'],
                'row': entry['row'],
                'col': entry['col'],
                'type': entry['type'].value,
                'coords': list(entry['coords']),
                'replicate_round': entry.get('replicate_round', 0),
            })

        plate_model_state = {
            'grid': [[cell.value for cell in row] for row in plate_model.grid],
            'active_key': plate_model.active_key.value,
            'selection_order': selection_order_data,
        }

        session_data = {
            'version': SessionIO.SESSION_VERSION,
            'created': datetime.now().isoformat(),
            'metadata_sample_id_column': app.view.sample_id_md.value if app.view else 'TM',
            'calibrant_count': app.calibrant_count,
            'plate_groups': app.plate_groups,
            'analysis_config': app.analysis_config,
            'plates': [
                {
                    'index': i,
                    'name': p['name'],
                    'raw_filename': p.get('raw_filename'),
                    'plate_id_filename': p.get('plate_id_filename'),
                }
                for i, p in enumerate(app.plates)
            ],
            'plate_model_state': plate_model_state,
        }

        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('session.json', json.dumps(session_data, indent=2))

            if app.metadata_df is not None:
                zf.writestr('metadata.csv', app.metadata_df.to_csv(index=True))

            if app.plate_design_df is not None:
                zf.writestr('plate_design.csv', app.plate_design_df.to_csv(index=False))

            for i, plate in enumerate(app.plates):
                if plate.get('raw_df') is not None:
                    zf.writestr(f'plates/{i}_raw.csv', plate['raw_df'].to_csv(index=True))
                if plate.get('id_df') is not None:
                    zf.writestr(f'plates/{i}_id.csv', plate['id_df'].to_csv(index=True))

    @staticmethod
    def load(path: str) -> dict:
        """Load session from a .beelisa ZIP file. Returns a dict with restored state."""
        with zipfile.ZipFile(path, 'r') as zf:
            names = zf.namelist()

            session_data = json.loads(zf.read('session.json'))

            metadata_df = None
            if 'metadata.csv' in names:
                metadata_df = pd.read_csv(io.BytesIO(zf.read('metadata.csv')), index_col=0)
                # Ensure sample_id stays as string — pd.read_csv auto-infers numeric IDs as float64
                if 'sample_id' in metadata_df.columns:
                    metadata_df['sample_id'] = (
                        metadata_df['sample_id']
                        .astype(str)
                        .str.strip()
                        .str.replace(r'\.0$', '', regex=True)
                    )

            plate_design_df = None
            if 'plate_design.csv' in names:
                plate_design_df = pd.read_csv(io.BytesIO(zf.read('plate_design.csv')))

            plates = []
            for plate_meta in session_data.get('plates', []):
                i = plate_meta['index']
                raw_df = None
                id_df = None
                raw_key = f'plates/{i}_raw.csv'
                id_key = f'plates/{i}_id.csv'
                if raw_key in names:
                    raw_df = pd.read_csv(io.BytesIO(zf.read(raw_key)), index_col=0)
                if id_key in names:
                    id_df = pd.read_csv(io.BytesIO(zf.read(id_key)), index_col=0)
                plates.append({
                    'name': plate_meta['name'],
                    'raw_df': raw_df,
                    'id_df': id_df,
                    'raw_filename': plate_meta.get('raw_filename'),
                    'plate_id_filename': plate_meta.get('plate_id_filename'),
                })

        return {
            'session_data': session_data,
            'metadata_df': metadata_df,
            'plate_design_df': plate_design_df,
            'plates': plates,
        }

    @staticmethod
    def restore_plate_model(plate_model, state: dict) -> None:
        """Restore PlateModel grid and selection state from a saved state dict."""
        from ..ui.models.plate_model import WellType

        grid_data = state.get('grid', [])
        plate_model.grid = [[WellType(v) for v in row] for row in grid_data]
        plate_model.active_key = WellType(state.get('active_key', WellType.SAMPLE.value))

        plate_model.selection_order = []
        plate_model.selection_history = OrderedDict()
        for entry in state.get('selection_order', []):
            restored = {
                'index': entry['index'],
                'well': entry['well'],
                'row': entry['row'],
                'col': entry['col'],
                'type': WellType(entry['type']),
                'coords': tuple(entry['coords']),
                'replicate_round': entry.get('replicate_round', 0),
            }
            plate_model.selection_order.append(restored)
            plate_model.selection_history[tuple(entry['coords'])] = entry['index']

        # Rebuild well count cache and regenerate plate_design_df
        plate_model._well_count_cache = {wt: 0 for wt in WellType}
        plate_model._initialize_well_counts()

    @staticmethod
    def restore_analysis_config(analysis_view, config: dict) -> None:
        """Restore analysis UI widget values from a saved analysis_config dict."""
        from ..ui.analysis_view import COLUMN_DISPLAY_NAMES

        av  = analysis_view
        cfg = config

        def _to_display(actual):
            if not actual or actual == 'None':
                return 'None'
            return COLUMN_DISPLAY_NAMES.get(actual, actual.replace('_', ' ').title())

        dilution = cfg.get('dilution_factor_text') or cfg.get('dilution_factor', '')
        if dilution and hasattr(av, 'dilution_input'):
            av.dilution_input.value = str(dilution)

        unit = cfg.get('concentration_unit', '')
        if unit and hasattr(av, 'unit_input'):
            av.unit_input.value = unit

        od = cfg.get('od_wavelength', '')
        if od and hasattr(av, 'od_input'):
            av.od_input.value = od

        lod_map = {'per_plate': 'Per Plate', 'global': 'Global'}
        lod = cfg.get('lod_loq_mode')
        if lod and hasattr(av, 'lod_mode_select'):
            av.lod_mode_select.value = lod_map.get(lod, lod)

        cmap = cfg.get('plots_colormap')
        if cmap and hasattr(av, 'plots_colormap'):
            av.plots_colormap.value = cmap

        for attr, key in [
            ('pca_show_plate_names',          'pca_show_plate_names'),
            ('apply_blank_subtraction',       'apply_blank_subtraction'),
            ('apply_plate_factor_correction', 'apply_plate_factor_correction'),
            ('per_group_plots_switch',        'per_group_plots'),
            ('std_curve_log_x',               'std_curve_log_x'),
            ('std_curve_log_y',               'std_curve_log_y'),
        ]:
            val = cfg.get(key)
            if val is not None and hasattr(av, attr):
                getattr(av, attr).value = bool(val)

        for attr, key in [
            ('heatmap_color_var',     'heatmap_color_var'),
            ('heatmap_size_var',      'heatmap_size_var'),
            ('heatmap_label_var',     'heatmap_label_var'),
            ('trend_date_var',        'trend_date_var'),
            ('trend_value_var',       'trend_value_var'),
            ('trend_grouping_var',    'trend_grouping_var'),
            ('correlation_value_var', 'tnm_biomarker'),
        ]:
            actual = cfg.get(key)
            if actual and hasattr(av, attr):
                try:
                    getattr(av, attr).value = _to_display(actual)
                except Exception:
                    pass

        tnm_cols = set(cfg.get('tnm_columns', []))
        if tnm_cols and hasattr(av, 'correlation_column_switches'):
            col_map = getattr(av, 'column_name_mapping', {})
            for dn, sw in av.correlation_column_switches.items():
                sw.value = col_map.get(dn, dn) in tnm_cols

        cal_concs = cfg.get('calibrant_concentrations', {})
        if cal_concs and hasattr(av, 'calibrant_rows'):
            for row in av.calibrant_rows:
                val = cal_concs.get(row['order'])
                if val is not None:
                    row['input'].value = str(int(val) if val == int(val) else val)
