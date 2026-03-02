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

    Performs PCA on plate-level features (LOD, LOQ, R², RMSE, BIC, CV)
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

        Each plate = one observation. Features: LOD, LOQ, R², RMSE, BIC, CV.
        Groups plates by plate_group for coloring and ellipses.

        Args:
            results: Analysis results dict with curve_fits, lod_loq, qc_summary
            plate_groups: Dict mapping group_name -> list of plate_names

        Returns:
            Dict with scores, labels (group names), variance_explained, feature_names
            Or None if insufficient data (< 3 plates)
        """
        # Build plate-to-group mapping.
        # 2+ groups: colour by group. 0 or 1 group: each plate is its own labelled point.
        if len(plate_groups) >= 2:
            plate_to_group = {p: g for g, plates in plate_groups.items() for p in plates}
        else:
            plate_to_group = {pn: pn for pn in results.get('curve_fits', {})}

        # Extract features for each plate
        feature_rows = []
        labels = []
        plate_names = []

        for plate_name, curve in results.get('curve_fits', {}).items():
            if plate_name not in plate_to_group:
                continue
            if not curve.get('success'):
                continue

            lod_loq = results.get('lod_loq', {}).get(plate_name, {})
            qc = results.get('qc_summary', {}).get(plate_name, {})

            # Build feature vector
            got_cv = qc.get('CALIBRANT', {}).get('cv_percent')
            cv = got_cv if (got_cv is not None and np.isfinite(got_cv)) else np.nan
            # lod_od, loq_od = lod_loq.get('lod_od'), lod_loq.get('loq_od')
            lod, loq = lod_loq.get('lod'), lod_loq.get('loq')
            # log_lod, log_loq = (np.log10(lod_od) if (lod_od is not None and np.isfinite(lod_od) and lod_od > 0) else np.nan, np.log10(loq_od) if (loq_od is not None and np.isfinite(loq_od) and loq_od > 0) else np.nan)
            log_lod, log_loq = (np.log10(lod) if (lod is not None and np.isfinite(lod) and lod > 0) else np.nan, np.log10(loq) if (loq is not None and np.isfinite(loq) and loq > 0) else np.nan)

            F = results.get("plate_factors", {}).get(plate_name, None)
            logF = np.log10(F) if (F is not None and np.isfinite(F) and F > 0) else np.nan

            row = {
                'log(LOD)': log_lod,
                'log(LOQ)': log_loq,
                'R²': curve.get('r_squared'),
                'RMSE': curve.get('rmse'),
                'BIC': curve.get('bic'),
                'CV % Cal.': cv,
                "log(F_p)": logF
            }


            feature_rows.append(row)
            labels.append(plate_to_group[plate_name])
            plate_names.append(plate_name)

        if len(feature_rows) < 3:
            return None  # Need at least 3 plates for PCA because of lod loq 

        # Build feature matrix
        df = pd.DataFrame(feature_rows).apply(pd.to_numeric, errors="coerce")
        if 'cv_calibrant' in df.columns and df['cv_calibrant'].isna().any():
            df = df.drop(columns=['cv_calibrant'])
        df = df.dropna(axis=1, how='any')
        if df.shape[1] < 2:
            return None
        # Filter labels and plate_names 
        kept_idx = df.index.tolist()
        labels = [labels[i] for i in kept_idx]
        plate_names = [plate_names[i] for i in kept_idx]

        feature_names = list(df.columns)
        X = df.to_numpy(dtype=float)

        # Standardize and fit PCA
        X_scaled = self.scaler.fit_transform(X)
        scores = self.pca.fit_transform(X_scaled)

        return {
            'scores': scores,
            'labels': np.array(labels),
            'plate_names': np.array(plate_names),
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
