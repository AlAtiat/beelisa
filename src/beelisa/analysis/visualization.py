""" image plot visualization for ELISA analysis using matplotlib."""

import os
import tempfile
import time
from typing import Optional, Dict, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.patches import Circle, Ellipse
from .parsers.base import sort_key as _smart_sort_key
from .statistics import spearman_correlation, benjamini_hochberg, lowess_with_band


# Use non-interactive
matplotlib.use('Agg')


# Column name to display name mapping for visualization labels
DISPLAY_NAMES = {
    'concentration_dilution_corrected': 'Concentration',
    'od_value': 'Optical Density (OD)',
    'concentration': 'Raw Concentration',
    'plate_name': 'Plate Name',
    'well_id': 'Well ID',
    'well_type': 'Well Type',
    'sample_id': 'Sample ID',
    'detection_status': 'Detection Status',
}


class ELISAVisualizer:
    """Generate static PNG plots for ELISA analysis results."""

    def __init__(self, concentration_unit: str = 'U/mL', od_wavelength: str = '450/620 nm'):
        """
        Initialize visualizer.

        Args:
            concentration_unit: Unit for concentration display (e.g., 'ng/mL', 'µg/mL')
            od_wavelength: Unit and wavelength display (e.g., '450 nm')
        """
        self.concentration_unit = concentration_unit
        self.od_wavelength = od_wavelength
        self.temp_dir = tempfile.gettempdir()

        # Set matplotlib style https://matplotlib.org/stable/gallery/style_sheets/
        plt.style.use('ggplot')

    _file_counter = 0

    def _generate_unique_filename(self, prefix: str) -> str:
        """Generate unique filename to avoid file locking issues on Windows."""
        ELISAVisualizer._file_counter += 1
        timestamp = int(time.time())
        return os.path.join(self.temp_dir, f'{prefix}_{timestamp}_{ELISAVisualizer._file_counter}.png')

    def create_standard_curve_plot(
        self,
        calibrant_concentrations: np.ndarray,
        calibrant_od_values: np.ndarray,
        curve_result: Dict,
        plate_name: str = "Plate",
        colormap: str = 'viridis'
    ) -> str:
        """
        Create standard curve plot with fitted curve overlay.

        Args:
            calibrant_concentrations: Array of calibrant concentrations
            calibrant_od_values: Array of calibrant OD values
            curve_result: Dictionary with curve fitting results
            plate_name: Name of the plate for title
            colormap: Matplotlib colormap name for curve color

        Returns:
            Path to PNG file
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        # Get curve color from colormap
        cmap = plt.get_cmap(colormap)
        dots_color = cmap(0.3)
        curve_color = cmap(0.7)
            
        # Scatter plot of calibrant data
        ax.scatter(calibrant_concentrations, calibrant_od_values, s=100, color=dots_color,
                   label='Calibrant Data', edgecolors='grey', linewidths=1.5, alpha=0.7)

        # Generate fitted curve
        if curve_result.get('success'):
            model = curve_result.get('model')
            params = curve_result.get('params')

            # Generate smooth curve
            x_range = np.linspace(
                calibrant_concentrations.min(),
                calibrant_concentrations.max(),
                200
            )
            y_fitted = model.equation(x_range, *params)



            ax.plot(x_range, y_fitted, color=curve_color, linewidth=2.5, label='Fitted Curve', alpha=0.8)

            # Add text annotation with model info
            model_name = curve_result.get('model_name', 'Unknown')
            r_squared = curve_result.get('r_squared')
            bic = curve_result.get('bic')
            rmse = curve_result.get('rmse')
            adjusted_r_squared = curve_result.get('adjusted_r_squared')

            # Handle None values gracefully
            r2_str = f"{r_squared:.4f}" if r_squared is not None else 'N/A'
            bic_str = f"{bic:.2f}" if bic is not None else 'N/A'
            rmse_str = f"{rmse:.2f}" if rmse is not None else 'N/A'
            adjusted_r_squared_str = f"{adjusted_r_squared:.4f}" if adjusted_r_squared is not None else 'N/A'

            textstr = f'Model: {model_name}\nR²: {r2_str}\nBIC: {bic_str}\nRMSE: {rmse_str}\nAdj. R²: {adjusted_r_squared_str}'
            ax.text(0.05, 0.95, textstr, transform=ax.transAxes,
                    verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8), fontsize=10, family='monospace')

        # Formatting
        ax.set_xscale('log')
        ax.set_xlabel(f'Concentration ({self.concentration_unit})', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'Optical Density (OD) ({self.od_wavelength})', fontsize=12, fontweight='bold')
        ax.set_title(f'Standard Curve - {plate_name}', fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Save to temp file with unique name to avoid file locking
        temp_file = self._generate_unique_filename(f'standard_curve_{plate_name}')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file

    def create_all_standard_curves_plot(
        self,
        all_curve_data: List[Dict],
        colormap: str = 'viridis'
    ) -> str:
        """
        Overlay all plates' standard curves on one plot.

        Args:
            all_curve_data: list of dicts, each with keys:
                'plate_name', 'concentrations', 'od_values', 'curve_result'
            colormap: Matplotlib colormap name

        Returns:
            Path to PNG file
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        cmap = plt.get_cmap(colormap)
        n = len(all_curve_data)
        annotation_lines = []

        for i, entry in enumerate(all_curve_data):
            color = cmap(i / max(n - 1, 1))
            plate_name = entry['plate_name']
            conc = entry['concentrations']
            od = entry['od_values']
            curve_result = entry['curve_result']

            # Scatter calibrant points
            ax.scatter(conc, od, s=40, color=color, alpha=0.5, edgecolors='grey',
                       linewidths=0.5)
            
            
            model_name = curve_result.get('model_name', '?')
            r2 = curve_result.get('r_squared')
            r2_str = f"{r2:.4f}" if r2 is not None else 'N/A'
            annotation_label = (f'{plate_name}: {model_name} (R\u00b2={r2_str})')
            
            # Smooth fitted curve
            if curve_result.get('success'):
                model = curve_result.get('model')
                params = curve_result.get('params')
                x_range = np.linspace(conc.min(), conc.max(), 200)
                y_fitted = model.equation(x_range, *params)
                ax.plot(x_range, y_fitted, color=color, linewidth=2, alpha=0.8,
                        label=annotation_label)


        #         annotation_lines.append(f'{plate_name}: {model_name} (R\u00b2={r2_str})')

        # # Annotation box
        # if annotation_lines:
        #     ax.text(0.05, 0.95, '\n'.join(annotation_lines), transform=ax.transAxes,
        #             verticalalignment='top', fontsize=8, family='monospace',
        #             bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))

        ax.set_xscale('log')
        ax.set_xlabel(f'Concentration ({self.concentration_unit})', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'Optical Density (OD) ({self.od_wavelength})', fontsize=12, fontweight='bold')
        ax.set_title('Standard Curves - All Plates', fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3, linestyle='--')

        temp_file = self._generate_unique_filename('standard_curves_all')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file

    def _draw_confidence_ellipses(self, ax, ellipse_data: List[Dict], colors: List, alpha=0.15):
        """
        Draw precomputed 95% confidence ellipses.

        Args:
            ax: Matplotlib axis
            ellipse_data: List of dicts with keys: label, center, width, height, angle
            colors: List of colors for each group
            alpha: Fill transparency
        """
        for i, ell in enumerate(ellipse_data):
            color = colors[i] if i < len(colors) else 'gray'
            ellipse = Ellipse(
                ell['center'], ell['width'], ell['height'], angle=ell['angle'],
                facecolor=color, alpha=alpha,
                edgecolor=color, linewidth=2, linestyle='--'
            )
            ax.add_patch(ellipse)

    def create_pca_plot(
        self,
        pca_result: Dict,
        title: str = "PCA Analysis",
        color_values: Optional[np.ndarray] = None,
        color_labels: Optional[np.ndarray] = None,
        color_name: str = "Value",
        alpha: float = 0.6,
        ellipse_data: Optional[List[Dict]] = None,
        max_legend_items: int = 15,
        point_size: int = 30,
        colormap: str = 'viridis',
        point_labels: Optional[np.ndarray] = None
    ) -> str:
        """
        Create PCA biplot (PC1 vs PC2)

        Args:
            pca_result: Dictionary with PCA results (scores, variance_explained, labels)
            title: Plot title
            color_values: Optional continuous values for color gradient (e.g., concentration)
            color_labels: Optional categorical labels for coloring (e.g., batch, condition)
            color_name: Label for colorbar/legend
            alpha: Point transparency (0-1), lower for dense data
            ellipse_data: Precomputed 95% confidence ellipse data from pca.compute_confidence_ellipses()
            max_legend_items: Maximum number of legend entries (hide legend if exceeded)
            point_size: Size of scatter points
            colormap: Matplotlib colormap name

        Returns:
            Path to PNG file
        """
        scores = pca_result.get('scores')
        variance_explained = pca_result.get('variance_explained')
        labels = pca_result.get('labels')

        if scores is None or variance_explained is None:
            return None

        fig, ax = plt.subplots(figsize=(10, 7))

        # Scatter plot with transparency and coloring options
        colors_used = None
        if color_values is not None and len(color_values) == len(scores):
            # Continuous coloring (e.g., concentration)
            scatter = ax.scatter(scores[:, 0], scores[:, 1],
                                c=color_values, cmap=colormap,
                                s=point_size, alpha=alpha, edgecolors='none')
            cbar = plt.colorbar(scatter, ax=ax, shrink=0.8)
            cbar.ax.set_ylabel(color_name, fontsize=10)
        elif color_labels is not None and len(color_labels) == len(scores):
            # Categorical coloring (e.g., batch, condition)
            unique_labels = np.unique(color_labels)
            cmap = plt.get_cmap(colormap)
            colors_used = [cmap(i / max(len(unique_labels) - 1, 1)) for i in range(len(unique_labels))]
            show_legend = len(unique_labels) <= max_legend_items

            for i, lbl in enumerate(unique_labels):
                mask = color_labels == lbl
                ax.scatter(scores[mask, 0], scores[mask, 1],
                          c=[colors_used[i]], s=point_size, alpha=alpha,
                          label=str(lbl) if show_legend else None,
                          edgecolors='none')

            # Draw 95% confidence ellipses (precomputed)
            if ellipse_data and colors_used:
                self._draw_confidence_ellipses(ax, ellipse_data, colors_used)

            if show_legend:
                ax.legend(loc='best', fontsize=8)
        else:
            # Default: single color
            ax.scatter(scores[:, 0], scores[:, 1],
                      s=point_size, alpha=alpha, edgecolors='none', c='steelblue')

        # Annotate points with labels (e.g., plate names)
        if point_labels is not None and len(point_labels) == len(scores):
            for idx in range(len(scores)):
                ax.annotate(
                    str(point_labels[idx]),
                    (scores[idx, 0], scores[idx, 1]),
                    fontsize=6, alpha=0.7,
                    textcoords='offset points', xytext=(4, 4)
                )

        # Center lines
        ax.axhline(y=0, color='grey', lw=0.5, linestyle='--')
        ax.axvline(x=0, color='grey', lw=0.5, linestyle='--')

        # Axis labels with variance explained
        pc1_var = variance_explained[0] * 100
        pc2_var = variance_explained[1] * 100
        ax.set_xlabel(f'PC1 ({pc1_var:.1f}% variance)', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'PC2 ({pc2_var:.1f}% variance)', fontsize=12, fontweight='bold')


        # Biplot arrows (feature loadings)
        from matplotlib.patches import FancyArrowPatch
        loadings = pca_result.get('loadings')
        feature_names = pca_result.get('feature_names', [])
        if loadings is not None and len(feature_names) == loadings.shape[1]:
            L = loadings[:2].T
            mags = np.linalg.norm(L, axis=1)
            cmap = plt.get_cmap(colormap)
            norm = plt.Normalize(mags.min(), mags.max())

            s = 0.9 * min(np.ptp(scores[:, 0]), np.ptp(scores[:, 1])) / (mags.max() + 1e-12)

            for (x, y), m, name in zip(L * s, mags, feature_names):
                color = cmap(norm(m))

                # dotted line
                ax.plot([0, x], [0, y], linestyle=':', linewidth=1.0,
                        color=color, alpha=0.7)

                # small arrow head
                arrow = FancyArrowPatch(
                    (0, 0), (x, y),
                    arrowstyle='-|>',
                    mutation_scale=8,   # smaller head
                    linewidth=0,
                    color=color,
                    alpha=0.7
                )
                ax.add_patch(arrow)

                # label near tip
                ha = 'left' if x > 0 else 'right'
                va = 'bottom' if y > 0 else 'top'
                
                ax.text(x * 1.05, y * 1.05, name, fontsize=7, color=color, ha=ha, va=va)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Save to temp file
        temp_file = self._generate_unique_filename('pca_plot')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file

    def create_plate_heatmap(
        self,
        data_df: pd.DataFrame,
        value_column: str,
        plate_name: str = "Plate",
        colormap: str = 'viridis',
        show_values: bool = True,
        size_column: Optional[str] = None,
        label_column: Optional[str] = None
    ) -> str:
        """
        Create 96-well plate heatmap with round wells.

        Args:
            data_df: DataFrame with well_id and value columns
            value_column: Column name for color gradient
            plate_name: Plate identifier
            colormap: Matplotlib colormap name
            show_values: Whether to display values in wells
            size_column: Optional column for circle size (dual variable encoding)
            label_column: Optional column for text label (strings like sample_id)

        Returns:
            Path to PNG file
        """
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        cols = list(range(1, 13))

        # Filter for this plate
        if 'plate_name' in data_df.columns:
            plate_data = data_df[data_df['plate_name'] == plate_name].copy()
        else:
            plate_data = data_df.copy()

        # Build value matrix for color
        value_matrix = np.full((8, 12), np.nan)
        for _, row in plate_data.iterrows():
            well_id = str(row.get('well_id', ''))
            if len(well_id) < 2:
                continue
            try:
                row_idx = rows.index(well_id[0].upper())
                col_idx = int(well_id[1:]) - 1
                if 0 <= col_idx < 12:
                    val = row.get(value_column)
                    if pd.notna(val):
                        value_matrix[row_idx, col_idx] = float(val)
            except (ValueError, IndexError):
                continue

        # Build size matrix if size_column provided
        size_matrix = np.full((8, 12), 0.42)  # default radius
        original_size_matrix = None  # Will store original values before normalization
        if size_column and size_column != 'None' and size_column in plate_data.columns:
            for _, row in plate_data.iterrows():
                well_id = str(row.get('well_id', ''))
                if len(well_id) < 2:
                    continue
                try:
                    row_idx = rows.index(well_id[0].upper())
                    col_idx = int(well_id[1:]) - 1
                    if 0 <= col_idx < 12:
                        val = row.get(size_column)
                        if pd.notna(val):
                            size_matrix[row_idx, col_idx] = float(val)
                except (ValueError, IndexError):
                    continue

            # Store original size values before normalization
            original_size_matrix = size_matrix.copy()

            # Normalize sizes to radius range [0.2, 0.45]
            valid_sizes = size_matrix[size_matrix != 0.42]
            if len(valid_sizes) > 0:
                smin, smax = np.min(valid_sizes), np.max(valid_sizes)
                if smax > smin:
                    for i in range(8):
                        for j in range(12):
                            if size_matrix[i, j] != 0.42:
                                size_matrix[i, j] = 0.2 + 0.25 * (size_matrix[i, j] - smin) / (smax - smin)

        # Build label matrix for string metadata (sample_id, condition, etc.)
        label_matrix = None
        if label_column and label_column != 'None' and label_column in plate_data.columns:
            label_matrix = np.empty((8, 12), dtype=object)
            label_matrix[:] = None
            for _, row in plate_data.iterrows():
                well_id = str(row.get('well_id', ''))
                if len(well_id) >= 2:
                    try:
                        row_idx = rows.index(well_id[0].upper())
                        col_idx = int(well_id[1:]) - 1
                        if 0 <= col_idx < 12:
                            label_val = row.get(label_column)
                            if pd.notna(label_val):
                                label_matrix[row_idx, col_idx] = str(label_val)[:8]  # Truncate to 8 chars
                    except (ValueError, IndexError):
                        continue

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 8))
        ax.set_xlim(-0.6, 11.6)
        ax.set_ylim(7.6, -0.6)
        ax.set_aspect('equal')
        ax.set_facecolor('#e8e8e8')

        # Normalize color values
        valid_vals = value_matrix[~np.isnan(value_matrix)]
        if len(valid_vals) > 0:
            vmin, vmax = np.min(valid_vals), np.max(valid_vals)
        else:
            vmin, vmax = 0, 1
        norm = plt.Normalize(vmin, vmax)
        cmap = plt.get_cmap(colormap)

        # Draw round wells
        for i in range(8):
            for j in range(12):
                value = value_matrix[i, j]
                radius = size_matrix[i, j]

                if np.isnan(value):
                    color, edge = 'white', 'lightgray'
                else:
                    color, edge = cmap(norm(value)), 'gray'

                circle = Circle((j, i), radius, facecolor=color, edgecolor=edge, linewidth=1.5)
                ax.add_patch(circle)

                # Text
                if show_values:
                    if np.isnan(value):
                        ax.text(j, i, f'{rows[i]}{cols[j]}', ha='center', va='center', fontsize=6, color='gray')
                    else:
                        threshold = (vmin + vmax) / 2
                        text_color = 'white' if value > threshold else 'black'

                        # Build text: color value, size value, and label
                        display_text = f'{value:.1f}'
                        if original_size_matrix is not None:
                            orig_size = original_size_matrix[i, j]
                            if orig_size != 0.42:  # 0.42 is default (no size data)
                                display_text += f'\n({orig_size:.1f})'
                        if label_matrix is not None and label_matrix[i, j] is not None:
                            display_text += f'\n{label_matrix[i, j]}'

                        # Adjust font size if showing multiple lines
                        fontsize = 5 if (label_matrix is not None or original_size_matrix is not None) else 6
                        ax.text(j, i, display_text, ha='center', va='center',
                                fontsize=fontsize, color=text_color, fontweight='bold')

        # Colorbar use display names
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar_label = DISPLAY_NAMES.get(value_column, value_column.replace('_', ' ').title())
        if value_column in ['concentration', 'concentration_dilution_corrected']:
            cbar_label += f' ({self.concentration_unit})'
        if value_column in ['od_value']:
            cbar_label += f' ({self.od_wavelength})'
        cbar.ax.set_ylabel(cbar_label, fontsize=12, fontweight='bold')

        # Labels
        ax.set_xticks(range(12))
        ax.set_yticks(range(8))
        ax.set_xticklabels([str(c) for c in cols], fontsize=11, fontweight='bold')
        ax.set_yticklabels(rows, fontsize=11, fontweight='bold')
        ax.xaxis.set_ticks_position('top')

        # Title - use display names
        title_var = DISPLAY_NAMES.get(value_column, value_column.replace('_', ' ').title())
        title = f'{plate_name} - {title_var}'
        if size_column and size_column != 'None':
            size_title = DISPLAY_NAMES.get(size_column, size_column.replace('_', ' ').title())
            title += f' (size: {size_title})'
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        for spine in ax.spines.values():
            spine.set_visible(False)

        plt.tight_layout()
        temp_file = self._generate_unique_filename(f'heatmap_{plate_name}')
        fig.savefig(temp_file, dpi=200, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file

    def _compute_lowess_with_band(self, x, y, use_log_y=False, frac=0.3):
        """LOWESS smoothing with rolling IQR band """
        return lowess_with_band(x, y, use_log_y=use_log_y, frac=frac)

    def _compute_spearman(self, x, y):
        """Compute Spearman rho and p-value"""
        return spearman_correlation(x, y)

    def _build_trend_groups_info(self, plot_df, value_column, grouping_column,
                                  plate_groups, plate_to_group, has_color, has_shape, cmap):
        """Build group metadata list for trend plot rendering.

        Returns list of dicts with keys: label, subset, color, marker, linestyle.
        """
        MARKERS = ['o', 's', '^', 'D', 'v', 'p', '*', 'X', 'P', 'h']
        LINE_STYLES = ['-', '--', ':', '-.', (0, (3, 1, 1, 1))]
        groups = []

        if has_color and has_shape:
            color_groups = plot_df[grouping_column].unique()
            shape_groups = list(plate_groups.keys())
            n_colors = len(color_groups)
            colors = {g: cmap(i / max(n_colors - 1, 1)) for i, g in enumerate(color_groups)}
            for i, sg in enumerate(shape_groups):
                for cg in color_groups:
                    subset = plot_df[(plot_df['_plate_group'] == sg) &
                                     (plot_df[grouping_column] == cg)]
                    if len(subset) > 0:
                        groups.append({
                            'label': f'{cg} / {sg}', 'subset': subset,
                            'color': colors[cg],
                            'marker': MARKERS[i % len(MARKERS)],
                            'linestyle': LINE_STYLES[i % len(LINE_STYLES)],
                        })
        elif has_color:
            unique_groups = plot_df[grouping_column].unique()
            n = len(unique_groups)
            colors = [cmap(i / max(n - 1, 1)) for i in range(n)]
            for i, g in enumerate(unique_groups):
                subset = plot_df[plot_df[grouping_column] == g].sort_values('_x_num')
                groups.append({
                    'label': str(g), 'subset': subset, 'color': colors[i],
                    'marker': 'o', 'linestyle': '-',
                })
        elif has_shape:
            shape_groups = list(plate_groups.keys())
            n = len(shape_groups)
            colors = [cmap(i / max(n - 1, 1)) for i in range(n)]
            for i, sg in enumerate(shape_groups):
                subset = plot_df[plot_df['_plate_group'] == sg].sort_values('_x_num')
                if len(subset) > 0:
                    groups.append({
                        'label': str(sg), 'subset': subset, 'color': colors[i],
                        'marker': MARKERS[i % len(MARKERS)],
                        'linestyle': LINE_STYLES[i % len(LINE_STYLES)],
                    })
        else:
            groups.append({
                'label': 'All', 'subset': plot_df, 'color': cmap(0.6),
                'marker': 'o', 'linestyle': '-',
            })

        return groups

    def _format_trend_axes(self, ax, categorical_x, unique_x, use_log_y,
                            x_label, y_axis_label, title, small=False):
        """Apply common axis formatting for trend plots."""
        fs = 8 if small else 12
        ts = 10 if small else 14
        if categorical_x and unique_x is not None:
            ax.set_xticks(range(len(unique_x)))
            ax.set_xticklabels([str(v) for v in unique_x], rotation=45, ha='right',
                               fontsize=7 if small else 10)
        else:
            ax.tick_params(axis='x', rotation=45, labelsize=7 if small else 10)
        if use_log_y:
            ax.set_yscale('log')
        ax.set_xlabel(x_label, fontsize=fs, fontweight='bold')
        ax.set_ylabel(y_axis_label, fontsize=fs, fontweight='bold')
        ax.set_title(title, fontsize=ts, fontweight='bold', pad=10)
        ax.grid(True, alpha=0.3)

    def _create_trend_scatter_only(self, groups_info, value_column,
                                    categorical_x, unique_x, use_log_y,
                                    x_label, y_axis_label, title):
        """Create scatter-only plot (no trend lines or IQR bands)."""
        import seaborn as sns
        sns.set_style("whitegrid")
        fig, ax = plt.subplots(figsize=(12, 6))

        for group in groups_info:
            ax.scatter(group['subset']['_x_num'], group['subset'][value_column],
                       marker=group['marker'], facecolors='none', edgecolors=group['color'],
                       s=20, alpha=0.8, linewidths=1, label=group['label'])

        ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
        self._format_trend_axes(ax, categorical_x, unique_x, use_log_y,
                                 x_label, y_axis_label, title)

        temp_file = self._generate_unique_filename('trend_scatter')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return temp_file

    def _create_trend_single_group(self, group, value_column,
                                     categorical_x, unique_x, use_log_y,
                                     x_label, y_axis_label, title):
        """Create individual trend plot for one group with scatter + LOWESS + IQR."""
        import seaborn as sns
        sns.set_style("whitegrid")
        fig, ax = plt.subplots(figsize=(12, 6))

        x_vals = group['subset']['_x_num'].values
        y_vals = group['subset'][value_column].values

        ax.scatter(x_vals, y_vals,
                   marker=group['marker'], facecolors='none', edgecolors=group['color'],
                   s=20, alpha=0.8, linewidths=1)

        # LOWESS trend + IQR band
        x_t, y_t, x_b, y_25, y_75 = self._compute_lowess_with_band(
            x_vals, y_vals, use_log_y=use_log_y)
        if x_t is not None:
            ax.plot(x_t, y_t, color=group['color'], linewidth=2, alpha=0.8,
                    linestyle=group['linestyle'])
            ax.fill_between(x_b, y_25, y_75, alpha=0.15,
                            color=group['color'], edgecolor='none')

        group_title = f'{title} - {group["label"]}'
        self._format_trend_axes(ax, categorical_x, unique_x, use_log_y,
                                 x_label, y_axis_label, group_title)

        # Spearman annotation
        rho, pval, n = self._compute_spearman(x_vals, y_vals)
        ann_lines = [f'LOWESS ({"log" if use_log_y else "linear"})']
        if rho is not None:
            ann_lines.append(f'Spearman \u03c1 = {rho:.2f}')
            pval_str = f'p = {pval:.3f}' if pval >= 0.001 else 'p < 0.001'
            ann_lines.append(pval_str)
        ann_lines.append(f'n = {n}')
        ax.text(0.02, 0.98, '\n'.join(ann_lines), transform=ax.transAxes,
                ha='left', va='top', fontsize=8, family='monospace',
                bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))

        safe_label = group['label'].replace(' ', '_').replace('/', '_')
        temp_file = self._generate_unique_filename(f'trend_group_{safe_label}')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return temp_file

    def _create_trend_grid(self, groups_info, value_column,
                            categorical_x, unique_x, use_log_y,
                            x_label, y_axis_label, title):
        """Create grid of subplots, one per group with scatter + LOWESS + IQR."""
        import seaborn as sns
        sns.set_style("whitegrid")

        n = len(groups_info)
        n_cols = min(3, n)
        n_rows = int(np.ceil(n / n_cols))
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        if n_rows == 1 and n_cols == 1:
            axes = np.array([axes])
        axes_flat = np.array(axes).flatten()

        for idx, group in enumerate(groups_info):
            ax = axes_flat[idx]
            x_vals = group['subset']['_x_num'].values
            y_vals = group['subset'][value_column].values

            ax.scatter(x_vals, y_vals,
                       marker=group['marker'], facecolors='none', edgecolors=group['color'],
                       s=15, alpha=0.8, linewidths=0.8)

            # LOWESS trend + IQR band
            x_t, y_t, x_b, y_25, y_75 = self._compute_lowess_with_band(
                x_vals, y_vals, use_log_y=use_log_y)
            if x_t is not None:
                ax.plot(x_t, y_t, color=group['color'], linewidth=2, alpha=0.8,
                        linestyle=group['linestyle'])
                ax.fill_between(x_b, y_25, y_75, alpha=0.15,
                                color=group['color'], edgecolor='none')

            self._format_trend_axes(ax, categorical_x, unique_x, use_log_y,
                                     x_label, y_axis_label, group['label'], small=True)

            # Spearman annotation per facet
            rho, pval, n_pts = self._compute_spearman(x_vals, y_vals)
            ann_lines = [f'LOWESS ({"log" if use_log_y else "lin"})']
            if rho is not None:
                ann_lines.append(f'\u03c1={rho:.2f}')
                pval_str = f'p={pval:.3f}' if pval >= 0.001 else 'p<.001'
                ann_lines.append(pval_str)
            ann_lines.append(f'n={n_pts}')
            ax.text(0.02, 0.98, '\n'.join(ann_lines), transform=ax.transAxes,
                    ha='left', va='top', fontsize=7, family='monospace',
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))

        for idx in range(n, len(axes_flat)):
            axes_flat[idx].set_visible(False)

        fig.suptitle(f'{title} - All Groups', fontsize=16, fontweight='bold')
        fig.tight_layout()

        temp_file = self._generate_unique_filename('trend_grid')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        return temp_file

    def create_trend_plot(
        self,
        plot_df: pd.DataFrame,
        value_column: str,
        grouping_column: str = None,
        plate_groups: dict = None,
        title: str = "Pattern",
        colormap: str = "viridis",
        y_label: str = None,
        x_label: str = None
    ) -> Dict[str, str]:
        """
        Create cyclable Pattern plot images: scatter-only, per-group, and grid.

        Returns a dict of {key: png_path} with sorted keys for cycling order:
        - trend_0_scatter: all data, no trend lines
        - trend_1_group_*: individual group plots with model fit + IQR band
        - trend_N_grid: all groups tiled as subplots (only if >1 group)
        """
        # --- Common setup ---
        if y_label is None:
            y_label = DISPLAY_NAMES.get(value_column, value_column.replace('_', ' ').title())

        y_axis_label = y_label
        use_log_y = False
        if value_column in ['concentration', 'concentration_dilution_corrected']:
            y_axis_label = f'{y_label} ({self.concentration_unit})'
            use_log_y = True
        elif value_column == 'od_value':
            y_axis_label = f'{y_label} ({self.od_wavelength})'

        if x_label is None:
            x_label = 'X'

        plot_df = plot_df.copy()
        categorical_x = not pd.api.types.is_numeric_dtype(plot_df['_x'])
        if categorical_x:
            unique_x = sorted(plot_df['_x'].unique(), key=_smart_sort_key)
            x_map = {v: i for i, v in enumerate(unique_x)}
            plot_df['_x_num'] = plot_df['_x'].map(x_map)
        else:
            unique_x = None
            plot_df['_x_num'] = plot_df['_x'].astype(float)

        plate_to_group = {}
        if plate_groups and 'plate_name' in plot_df.columns:
            for group_name, plates in plate_groups.items():
                for plate in plates:
                    plate_to_group[plate] = group_name
            plot_df['_plate_group'] = plot_df['plate_name'].map(plate_to_group)

        has_color = grouping_column and grouping_column != 'None'
        has_shape = plate_groups and plate_to_group
        cmap = plt.get_cmap(colormap)

        # Build groups info
        groups_info = self._build_trend_groups_info(
            plot_df, value_column, grouping_column, plate_groups,
            plate_to_group, has_color, has_shape, cmap)

        if not groups_info:
            return {}

        # Common params for helpers
        common = dict(
            categorical_x=categorical_x, unique_x=unique_x,
            use_log_y=use_log_y, x_label=x_label, y_axis_label=y_axis_label,
        )

        results = {}

        # 1. Scatter-only
        results['trend_0_scatter'] = self._create_trend_scatter_only(
            groups_info, value_column, title=title, **common)

        # 2. Individual group plots (LOWESS + Spearman)
        for i, group in enumerate(groups_info):
            safe_label = group['label'].replace(' ', '_').replace('/', '_')
            results[f'trend_{i + 1}_group_{safe_label}'] = self._create_trend_single_group(
                group, value_column, title=title, **common)

        # 3. Grid (only if >1 group)
        if len(groups_info) > 1:
            results[f'trend_{len(groups_info) + 1}_grid'] = self._create_trend_grid(
                groups_info, value_column, title=title, **common)

        return results

    def create_violin_plot(
        self,
        df: pd.DataFrame,
        stage_column: str,
        biomarker_column: str,
        title: str = None,
        colormap: str = 'viridis',
        log_y: bool = True,
        plate_groups: dict = None
    ) -> str:
        """
        Create violin plot with individual points (shape-coded by plate group),
        boxplot overlay, and p-value annotation.

        Args:
            df: DataFrame with stage and biomarker columns
            stage_column: Grouping column (can be string categories or numeric)
            biomarker_column: Biomarker concentration column
            title: Plot title
            colormap: Matplotlib colormap name
            log_y: Whether to use log scale for y-axis
            plate_groups: Optional dict {"Group": ["Plate1", ...]} for marker shapes

        Returns:
            Path to PNG file
        """
        import seaborn as sns
        from scipy import stats

        MARKERS = ['o', 's', '^', 'D', 'v', 'p', '*', 'X', 'P', 'h']

        # Keep plate_name if available for shape grouping
        cols_needed = [stage_column, biomarker_column]
        if plate_groups and 'plate_name' in df.columns:
            cols_needed.append('plate_name')

        plot_df = df[cols_needed].dropna(subset=[stage_column, biomarker_column]).copy()
        if len(plot_df) < 5:
            return None

        # Convert numeric floats to int for clean x-axis (1.0 → 1)
        if pd.api.types.is_numeric_dtype(plot_df[stage_column]):
            try:
                if (plot_df[stage_column].dropna() == plot_df[stage_column].dropna().astype(int)).all():
                    plot_df[stage_column] = plot_df[stage_column].astype(int)
            except (ValueError, OverflowError):
                pass

        # Sort categories using smart sort (handles Roman numerals, numbers, natural sort)
        sorted_categories = sorted(plot_df[stage_column].dropna().unique(), key=_smart_sort_key)

        fig, ax = plt.subplots(figsize=(10, 6))

        # 1. Violin
        sns.violinplot(
            data=plot_df, x=stage_column, y=biomarker_column,
            hue=stage_column, palette=colormap, inner=None,
            alpha=0.4, ax=ax, cut=0, legend=False,
            order=sorted_categories
        )

        # 2. Individual data points shaped coded by plate group if available
        has_plate_shapes = (plate_groups and 'plate_name' in plot_df.columns)
        if has_plate_shapes:
            # Map plate_name to plate group
            plate_to_group = {}
            for group_name, plates in plate_groups.items():
                for plate in plates:
                    plate_to_group[plate] = group_name
            plot_df['_plate_group'] = plot_df['plate_name'].map(plate_to_group)

            x_to_idx = {cat: i for i, cat in enumerate(sorted_categories)}

            shape_groups = list(plate_groups.keys())
            for i, group_name in enumerate(shape_groups):
                marker = MARKERS[i % len(MARKERS)]
                subset = plot_df[plot_df['_plate_group'] == group_name]
                if len(subset) == 0:
                    continue
                # Jitter x positions
                x_pos = subset[stage_column].map(x_to_idx).values.astype(float)
                x_pos += np.random.uniform(-0.15, 0.15, size=len(x_pos))
                ax.scatter(x_pos, subset[biomarker_column].values,
                           marker=marker, s=25, alpha=0.7, edgecolors='gray',
                           linewidths=0.5, facecolors='none', label=group_name, zorder=3)

            ax.legend(title='Plate Group', fontsize=8, title_fontsize=9,
                      loc='upper left', framealpha=0.8)
        else:
            # No plate groups — plain swarm/stripplot (outline-only dots)
            n_before = len(ax.collections)
            if len(plot_df) > 100:
                sns.stripplot(
                    data=plot_df, x=stage_column, y=biomarker_column,
                    color="black", size=3, alpha=0.7, jitter=True, ax=ax, legend=False,
                    order=sorted_categories
                )
            else:
                sns.swarmplot(
                    data=plot_df, x=stage_column, y=biomarker_column,
                    color="black", size=4, ax=ax, legend=False, warn_thresh=0.8,
                    order=sorted_categories
                )
            # Make dots outline-only (no fill)
            for collection in ax.collections[n_before:]:
                collection.set_facecolor('none')
                collection.set_edgecolor('black')
                collection.set_linewidths(0.5)

        # 3. Box plot overlay (median + IQR) — orient='v' fixes vert deprecation
        sns.boxplot(
            data=plot_df, x=stage_column, y=biomarker_column,
            width=0.15, color="white", ax=ax, legend=False, orient='v',
            boxprops={'zorder': 2}, fliersize=0,
            medianprops={'color': 'black', 'linewidth': 2},
            order=sorted_categories
        )

        # 4. P-value annotation (Kruskal-Wallis for ≥3 groups, Mann-Whitney for 2)
        groups = []
        for cat in sorted_categories:
            g = plot_df[plot_df[stage_column] == cat][biomarker_column].values
            if len(g) >= 2:
                groups.append(g)
        if len(groups) >= 2:
            try:
                if len(groups) == 2:
                    stat, pval = stats.mannwhitneyu(groups[0], groups[1], alternative='two-sided')
                    test_name = 'Mann-Whitney U'
                else:
                    stat, pval = stats.kruskal(*groups)
                    test_name = 'Kruskal-Wallis'
                pval_str = f'p = {pval:.3f}' if pval >= 0.001 else 'p < 0.001'
                ax.text(0.98, 0.98, f'{test_name}: {pval_str}',
                        transform=ax.transAxes, ha='right', va='top', fontsize=9,
                        bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray'))
            except Exception:
                pass  # Skip p-value if calculation fails

        # Labels
        stage_name = stage_column.replace('_num', '').replace('_', ' ')
        biomarker_name = DISPLAY_NAMES.get(biomarker_column, biomarker_column.replace('_', ' ').title())

        y_label = biomarker_name
        if biomarker_column in ['concentration', 'concentration_dilution_corrected']:
            y_label = f'{biomarker_name} ({self.concentration_unit})'

        if log_y:
            ax.set_yscale('log')

        ax.set_xlabel(stage_name, fontsize=12, fontweight='bold')
        ax.set_ylabel(y_label, fontsize=12, fontweight='bold')

        if title is None:
            title = f'{biomarker_name} Distribution by {stage_name}'
        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3, axis='y')

        temp_file = self._generate_unique_filename(f'violin_{stage_column}')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file

    def _benjamini_hochberg(self, pvals):
        """Benjamini-Hochberg FDR correction"""
        return benjamini_hochberg(pvals)

    def create_correlation_heatmap(
        self,
        df: pd.DataFrame,
        stage_columns: list,
        biomarker_column: str,
        title: str = "Clinical Stage vs Biomarker Correlation",
        colormap: str = 'coolwarm',
        display_mapping: dict = None,
        column_groups: dict = None
    ) -> str:
        """
        Create ellipse-based correlation plot for clinical stages vs biomarker.

        Ellipse properties indicate correlation:
        - Orientation: Top-right (↗) = positive, Top-left (↖) = negative
        - Width: Thinner = stronger correlation
        - Color: Darker = stronger correlation (uses colormap)
        - Annotation: Shows rho, FDR-adjusted q-value, binary tie marker

        Args:
            df: DataFrame with stage and biomarker columns
            stage_columns: List of numeric stage columns (e.g., ['T_Stage_num', 'N_Stage_num'])
            biomarker_column: Biomarker concentration column
            title: Plot title
            colormap: Matplotlib colormap name
            display_mapping: {col: display_label} for axis labels
            column_groups: {col: source_group} — columns sharing same group are
                           one-hot encoded from the same variable and should not
                           be cross-correlated

        Returns:
            Path to PNG file
        """
        from scipy import stats

        # Filter to columns that exist and have data
        valid_cols = [c for c in stage_columns if c in df.columns and df[c].notna().sum() >= 5]
        if not valid_cols or biomarker_column not in df.columns:
            return None

        # Combine with biomarker
        cols_to_use = valid_cols + [biomarker_column]

        # Pairwise deletion: compute per-pair to maximize data usage
        n = len(cols_to_use)
        corr_matrix = np.full((n, n), np.nan)
        pval_matrix = np.full((n, n), np.nan)
        n_matrix = np.full((n, n), 0, dtype=int)
        binary_cols = set()

        for i, col1 in enumerate(cols_to_use):
            col1_valid = df[col1].notna().sum()
            n_matrix[i, i] = col1_valid
            if df[col1].dropna().nunique() <= 2:
                binary_cols.add(col1)

            for j, col2 in enumerate(cols_to_use):
                if i == j:
                    corr_matrix[i, j] = 1.0
                    pval_matrix[i, j] = 0.0
                    continue

                # Skip one-hot cross-correlations (same source group)
                if column_groups:
                    g1 = column_groups.get(col1)
                    g2 = column_groups.get(col2)
                    if g1 and g2 and g1 == g2:
                        continue  # Leave as NaN

                pair_df = df[[col1, col2]].dropna()
                n_pair = len(pair_df)
                n_matrix[i, j] = n_pair

                if n_pair < 5:
                    continue

                rho, pval = stats.spearmanr(pair_df[col1], pair_df[col2])
                corr_matrix[i, j] = rho
                pval_matrix[i, j] = pval

        # Check that at least one pair has data
        if np.all(np.isnan(corr_matrix[np.triu_indices(n, k=1)])):
            return None

        # FDR correction (Benjamini-Hochberg) on upper triangle p-values
        raw_pvals = []
        pval_positions = []
        for i in range(n):
            for j in range(i + 1, n):
                if not np.isnan(pval_matrix[i, j]):
                    raw_pvals.append(pval_matrix[i, j])
                    pval_positions.append((i, j))

        adj_pval_matrix = np.full((n, n), np.nan)
        has_fdr = False
        if raw_pvals:
            q_values = self._benjamini_hochberg(np.array(raw_pvals))
            has_fdr = True
            for idx, (i, j) in enumerate(pval_positions):
                adj_pval_matrix[i, j] = q_values[idx]
                adj_pval_matrix[j, i] = q_values[idx]

        # Create display names for axes
        display_names = []
        has_binary = False
        for col in cols_to_use:
            name = ''
            if col == biomarker_column:
                name = DISPLAY_NAMES.get(col, col.replace('_', ' ').title())
            elif display_mapping and col in display_mapping:
                name = display_mapping[col]
            else:
                name = col.replace('_num', '').replace('_', ' ')
            if col in binary_cols:
                name += '*'
                has_binary = True
            display_names.append(name)

        fig, ax = plt.subplots(figsize=(10, 8))
        cmap = plt.get_cmap(colormap)

        # Draw ellipses for each cell
        for i in range(n):
            for j in range(n):
                # Cell position (centered in cell)
                x_pos = j + 0.5
                y_pos = n - i - 0.5

                if i == j:
                    # Diagonal - perfect correlation (circle)
                    circle = Circle(
                        (x_pos, y_pos), 0.35,
                        facecolor=cmap(1.0),
                        edgecolor='gray',
                        linewidth=1
                    )
                    ax.add_patch(circle)
                    diag_n = n_matrix[i, i]
                    ax.text(x_pos, y_pos, f'1.00\nn={diag_n}', ha='center', va='center',
                            fontsize=7, fontweight='bold', color='white')
                elif np.isnan(corr_matrix[i, j]):
                    # Skipped cell (one-hot cross-correlation) — draw grey X
                    ax.plot([j + 0.2, j + 0.8], [y_pos - 0.3, y_pos + 0.3],
                            color='lightgray', linewidth=1.5)
                    ax.plot([j + 0.2, j + 0.8], [y_pos + 0.3, y_pos - 0.3],
                            color='lightgray', linewidth=1.5)
                else:
                    rho = corr_matrix[i, j]

                    # Ellipse properties based on correlation
                    angle = 45 if rho >= 0 else -45
                    width = 0.85 - 0.7 * abs(rho)
                    height = 0.85
                    color = cmap((rho + 1) / 2)

                    ellipse = Ellipse(
                        (x_pos, y_pos),
                        width, height,
                        angle=angle,
                        facecolor=color,
                        edgecolor='gray',
                        linewidth=0.5,
                        alpha=0.9
                    )
                    ax.add_patch(ellipse)

                    # Annotation: rho + FDR-adjusted q-value
                    if has_fdr and not np.isnan(adj_pval_matrix[i, j]):
                        q = adj_pval_matrix[i, j]
                        qval_str = f'q={q:.3f}' if q >= 0.001 else 'q<0.001'
                    else:
                        pval = pval_matrix[i, j]
                        qval_str = f'p={pval:.3f}' if pval >= 0.001 else 'p<0.001'

                    cell_n = n_matrix[i, j]
                    brightness = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
                    text_color = 'white' if brightness < 0.2 else 'black'
                    ax.text(x_pos, y_pos, f'{rho:.2f}\n{qval_str}\nn={cell_n}',
                            ha='center', va='center', fontsize=6, color=text_color)

        # Set axis limits and labels
        ax.set_xlim(0, n)
        ax.set_ylim(0, n)
        ax.set_aspect('equal')

        # Labels on axes
        ax.set_xticks([i + 0.5 for i in range(n)])
        ax.set_yticks([i + 0.5 for i in range(n)])
        ax.set_xticklabels(display_names, rotation=45, ha='right', fontsize=8)
        ax.set_yticklabels(display_names[::-1], fontsize=8)

        # Add grid
        for i in range(n + 1):
            ax.axhline(i, color='lightgray', linewidth=0.5)
            ax.axvline(i, color='lightgray', linewidth=0.5)

        # Add colorbar
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(-1, 1))
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar.ax.set_ylabel('Spearman Correlation (\u03c1)', fontsize=10)

        ax.set_title(title, fontsize=14, fontweight='bold', pad=15)

        # Footnotes
        footnotes = []
        if has_fdr:
            footnotes.append('q = FDR-corrected p-value (Benjamini\u2013Hochberg)')
        if has_binary:
            footnotes.append('* = binary variable (p-value approximate due to ties)')
        if footnotes:
            fig.text(0.5, 0.01, '  |  '.join(footnotes),
                     ha='center', va='bottom', fontsize=7, style='italic', color='gray')

        # Remove spines
        for spine in ax.spines.values():
            spine.set_visible(False)

        temp_file = self._generate_unique_filename('tnm_correlation')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file
