"""Static plot visualization for ELISA analysis using matplotlib."""

import os
import tempfile
from typing import Optional, Dict, List
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib


# Use non-interactive 
matplotlib.use('Agg')


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

    def create_standard_curve_plot(
        self,
        calibrant_concentrations: np.ndarray,
        calibrant_od_values: np.ndarray,
        curve_result: Dict,
        plate_name: str = "Plate"
    ) -> str:
        """
        Create standard curve plot with fitted curve overlay.

        Args:
            calibrant_concentrations: Array of calibrant concentrations
            calibrant_od_values: Array of calibrant OD values
            curve_result: Dictionary with curve fitting results
            plate_name: Name of the plate for title

        Returns:
            Path to PNG file
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        # Scatter plot of calibrant data
        ax.scatter(calibrant_concentrations, calibrant_od_values, s=100, color='black',
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

            ax.plot(x_range, y_fitted, 'r-', linewidth=2.5, label='Fitted Curve', alpha=0.8)

            # Add text annotation with model info
            model_name = curve_result.get('model_name', 'Unknown')
            r_squared = curve_result.get('r_squared')
            bic = curve_result.get('bic')
            rmse = curve_result.get('rmse')
            adjusted_r_squared = curve_result.get('adjusted_r_squared')

            # Handle None values gracefully
            r2_str = f"{r_squared:.4f}" if r_squared is not None else 'N/A'
            bic_str = f"{bic:.2f}" if bic is not None else 'N/A'
            textstr = f'Model: {model_name}\nR²: {r2_str}\nBIC: {bic_str}\nRMSE: {rmse}\nAdj. R²: {adjusted_r_squared}'
            ax.text(0.05, 0.95, textstr, transform=ax.transAxes,
                    verticalalignment='top', bbox=dict(boxstyle='round',
                    facecolor='wheat', alpha=0.8), fontsize=10, family='monospace')

        # Formatting
        ax.set_xscale('log')
        ax.set_xlabel(f'Concentration ({self.concentration_unit})', fontsize=12, fontweight='bold')
        ax.set_ylabel('Optical Density (OD)', fontsize=12, fontweight='bold')
        ax.set_title(f'Standard Curve - {plate_name}', fontsize=14, fontweight='bold', pad=15)
        ax.legend(loc='best', framealpha=0.9)
        ax.grid(True, alpha=0.3, linestyle='--')

        # Save to temp file
        temp_file = os.path.join(self.temp_dir, f'standard_curve_{plate_name}.png')
        fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close(fig)

        return temp_file


    # def create_pca_plot(
    #     self,
    #     pca_result: Dict,
    #     title: str = "PCA Analysis"
    # ) -> str:
    #     """
    #     Create PCA biplot (PC1 vs PC2).

    #     Args:
    #         pca_result: Dictionary with PCA results
    #         title: Plot title

    #     Returns:
    #         Path to PNG file
    #     """
    #     fig, ax = plt.subplots(figsize=(10, 7))

    #     scores = pca_result.get('scores')
    #     variance_explained = pca_result.get('variance_explained')
    #     labels = pca_result.get('labels')

    #     if scores is not None and variance_explained is not None:
    #         # Scatter plot of PC scores
    #         ax.scatter(scores[:, 0], scores[:, 1], s=120, marker='$\u25EF$')

    #         # Add labels to points
    #         if labels is not None:
    #             for i, label in enumerate(labels):
    #                 ax.annotate(label, (scores[i, 0], scores[i, 1]),
    #                             xytext=(5, 5), textcoords='offset points',
    #                             fontsize=9, alpha=0.8)

    #         # Add center lines
    #         ax.axhline(y=0, color='grey', lw=1)
    #         ax.axvline(x=0, color='grey', lw=1)

    #         # Axis labels with variance explained
    #         pc1_var = variance_explained[0] * 100
    #         pc2_var = variance_explained[1] * 100

    #         ax.set_xlabel(f'PC1 ({pc1_var:.1f}% variance)', fontsize=12, fontweight='bold')
    #         ax.set_ylabel(f'PC2 ({pc2_var:.1f}% variance)', fontsize=12, fontweight='bold')
    #     else:
    #         ax.set_xlabel('PC1', fontsize=12, fontweight='bold')
    #         ax.set_ylabel('PC2', fontsize=12, fontweight='bold')

    #     ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    #     ax.grid(True, alpha=0.3, linestyle='--')

    #     # Save to temp file
    #     temp_file = os.path.join(self.temp_dir, 'pca_plot.png')
    #     fig.savefig(temp_file, dpi=150, bbox_inches='tight', facecolor='white')
    #     plt.close(fig)

    #     return temp_file
