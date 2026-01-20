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

    def __init__(self, concentration_unit: str = 'U/mL'):
        """
        Initialize visualizer.

        Args:
            concentration_unit: Unit for concentration display (e.g., 'ng/mL', 'µg/mL')
        """
        self.concentration_unit = concentration_unit
        self.temp_dir = tempfile.gettempdir()

        # Set matplotlib style https://matplotlib.org/stable/gallery/style_sheets/
        plt.style.use('ggplot')

    def _generate_unique_filename(self, prefix: str) -> str:
        """Generate unique filename to avoid file locking issues on Windows."""
        timestamp = int(time.time())
        return os.path.join(self.temp_dir, f'{prefix}_{timestamp}.png')

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
        ax.set_ylabel('Optical Density (OD)', fontsize=12, fontweight='bold')
        ax.set_title(f'Standard Curve - {plate_name}', fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Save to temp file with unique name to avoid file locking
        temp_file = self._generate_unique_filename(f'standard_curve_{plate_name}')
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
        colormap: str = 'viridis'
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

        # Center lines
        ax.axhline(y=0, color='grey', lw=0.5, linestyle='--')
        ax.axvline(x=0, color='grey', lw=0.5, linestyle='--')

        # Axis labels with variance explained
        pc1_var = variance_explained[0] * 100
        pc2_var = variance_explained[1] * 100
        ax.set_xlabel(f'PC1 ({pc1_var:.1f}% variance)', fontsize=12, fontweight='bold')
        ax.set_ylabel(f'PC2 ({pc2_var:.1f}% variance)', fontsize=12, fontweight='bold')

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
        size_column: Optional[str] = None
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

                        # Build text: color value, optionally add size value
                        display_text = f'{value:.1f}'
                        if original_size_matrix is not None:
                            orig_size = original_size_matrix[i, j]
                            if orig_size != 0.42:  # 0.42 is default (no size data)
                                display_text += f'\n({orig_size:.1f})'

                        ax.text(j, i, display_text, ha='center', va='center',
                                fontsize=6, color=text_color, fontweight='bold')

        # Colorbar use display names
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        cbar = plt.colorbar(sm, ax=ax, shrink=0.8)
        cbar_label = DISPLAY_NAMES.get(value_column, value_column.replace('_', ' ').title())
        if value_column in ['concentration', 'concentration_dilution_corrected']:
            cbar_label += f' ({self.concentration_unit})'
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
