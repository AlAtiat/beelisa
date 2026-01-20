"""Principal Component Analysis for ELISA plate-level QC metrics."""

from typing import Optional, Dict, List
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from scipy.stats import chi2


class ELISAPCAAnalyzer:
    """
    PCA analysis for ELISA plate-level QC metrics.

    Performs PCA on plate-level features (LOD, LOQ, R², RMSE, BIC, CV, curve params)
    to detect batch effects and protocol differences between plate groups.
    """

    def __init__(self, n_components: int = 2):
        """
        Initialize PCA analyzer.

        Args:
            n_components: Number of principal components (default: 2 for visualization)
        """
        self.n_components = n_components
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_components)

    def analyze_plates(
        self,
        results: Dict,
        plate_groups: Dict[str, List[str]]
    ) -> Optional[Dict]:
        """
        Plate-level PCA using QC metrics.

        Each plate = one observation. Features: LOD, LOQ, R², RMSE, BIC, CV, curve params.
        Groups plates by plate_group for coloring and ellipses.

        Args:
            results: Analysis results dict with curve_fits, lod_loq, qc_summary
            plate_groups: Dict mapping group_name -> list of plate_names

        Returns:
            Dict with scores, labels (group names), variance_explained, feature_names
            Or None if insufficient data (< 3 plates)
        """
        # Build plate-to-group mapping
        plate_to_group = {}
        for group, plates in plate_groups.items():
            for plate in plates:
                plate_to_group[plate] = group

        # Extract features for each plate
        feature_rows = []
        labels = []

        for plate_name, curve in results.get('curve_fits', {}).items():
            if plate_name not in plate_to_group:
                continue
            if not curve.get('success'):
                continue

            lod_loq = results.get('lod_loq', {}).get(plate_name, {})
            qc = results.get('qc_summary', {}).get(plate_name, {})

            # Build feature vector
            row = {
                'log_lod': np.log10(max(lod_loq.get('lod_od', 1e-10), 1e-10)),
                'log_loq': np.log10(max(lod_loq.get('loq_od', 1e-10), 1e-10)),
                'r_squared': curve.get('r_squared', 0),
                'rmse': curve.get('rmse', 0),
                'bic': curve.get('bic', 0),
                'cv_calibrant': qc.get('CALIBRANT', {}).get('cv_percent', 0),
            }

            # Add curve parameters (padded to 4 for consistency across models)
            params = curve.get('params', [])
            for i, p in enumerate(params[:4]):
                row[f'param_{i}'] = p
            for i in range(len(params), 4):
                row[f'param_{i}'] = 0

            feature_rows.append(row)
            labels.append(plate_to_group[plate_name])

        if len(feature_rows) < 3:
            return None  # Need at least 3 plates for PCA because of lod loq

        # Build feature matrix
        df = pd.DataFrame(feature_rows)
        feature_names = list(df.columns)
        X = df.values

        # Standardize and fit PCA
        X_scaled = self.scaler.fit_transform(X)
        scores = self.pca.fit_transform(X_scaled)

        return {
            'scores': scores,
            'labels': np.array(labels),
            'variance_explained': self.pca.explained_variance_ratio_,
            'loadings': self.pca.components_,
            'feature_names': feature_names
        }

    def compute_confidence_ellipses(
        self,
        scores: np.ndarray,
        labels: np.ndarray,
        confidence: float = 0.95
    ) -> List[Dict]:
        """
        Compute 95% confidence ellipse parameters for each group.

        Uses chi-square distribution with df=2 for proper 2D confidence scaling.
        For 95% confidence: chi2(2, 0.95) = 5.991, scale = sqrt(5.991) = 2.448


        Args:
            scores: PCA scores array (n_samples x 2)
            labels: Group labels for each sample
            confidence: Confidence level (default: 0.95)

        Returns:
            List of dicts with keys: label, center, width, height, angle
        """
        chi2_val = chi2.ppf(confidence, df=2)
        scale = np.sqrt(chi2_val)

        ellipses = []
        unique_labels = np.unique(labels)

        for lbl in unique_labels:
            mask = labels == lbl
            group_scores = scores[mask]

            if len(group_scores) < 3:
                continue  # Need at least 3 points for covariance

            # Mean (center of ellipse)
            center = group_scores.mean(axis=0)

            # Covariance matrix
            cov = np.cov(group_scores.T)

            try:
                # Eigendecomposition
                eigenvalues, eigenvectors = np.linalg.eigh(cov)

                # Sort by eigenvalue descending (largest first for major axis)
                order = eigenvalues.argsort()[::-1]
                eigenvalues = eigenvalues[order]
                eigenvectors = eigenvectors[:, order]

                # Check for valid eigenvalues
                if np.any(eigenvalues <= 0):
                    continue

                # Ellipse dimensions (scaled by chi-square for proper 95% CI)
                width = 2 * scale * np.sqrt(eigenvalues[0])   # major axis
                height = 2 * scale * np.sqrt(eigenvalues[1])  # minor axis

                # Angle from major eigenvector (first column after sorting)
                angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))

                ellipses.append({
                    'label': lbl,
                    'center': center,
                    'width': width,
                    'height': height,
                    'angle': angle
                })
            except Exception:
                continue

        return ellipses
