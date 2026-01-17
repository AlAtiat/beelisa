"""Principal Component Analysis for ELISA batch effect detection and sample clustering."""

from typing import Optional, Dict, List
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


class ELISAPCAAnalyzer:
    """
    PCA analysis for ELISA data.

    Two main use cases:
    1. Sample clustering: Identify outliers and cluster similar samples
    2. Batch effect detection: Detect plate-to-plate systematic variation
    """

    def __init__(self, n_components: int = 2):
        """
        Initialize PCA analyzer.

        Args:
            n_components: Number of principal components to compute (default: 2 for visualization)
        """
        self.n_components = n_components
        self.scaler = StandardScaler()
        self.pca = PCA(n_components=n_components)

    def analyze_samples(
        self,
        results_df: pd.DataFrame,
        use_dilution_corrected: bool = True
    ) -> Optional[Dict]:
        """
        Perform PCA on sample concentrations for clustering and outlier detection.

        Args:
            results_df: DataFrame with analysis results (must have 'concentration' columns)
            use_dilution_corrected: Use dilution-corrected concentrations (default: True)

        Returns:
            Dictionary with:
                - scores: PCA scores (n_samples × n_components)
                - loadings: PCA loadings (feature contributions)
                - variance_explained: Variance explained by each PC
                - labels: Sample labels for plotting
                - feature_names: Names of features used
            Or None if insufficient data
        """
        # Filter to only SAMPLE wells with valid concentrations
        samples = results_df[results_df['well_type'] == 'SAMPLE'].copy()

        conc_col = 'concentration_dilution_corrected' if use_dilution_corrected else 'concentration'

        if conc_col not in samples.columns:
            return None

        # Filter out invalid concentrations
        valid_samples = samples.dropna(subset=[conc_col])
        valid_samples = valid_samples[np.isfinite(valid_samples[conc_col])]

        if len(valid_samples) < 3:
            return None  # Need at least 3 samples for PCA

        # For now, we'll use each sample as a single feature
        # In a more advanced version, we could pivot by sample_id if there are replicates
        # For simplicity, treat each well as an observation

        # Create feature matrix (each row = sample, each column = a feature)
        # Since we have single concentration values, we need to create features
        # Option: Use plate_name as grouping and concentration as feature
        # For initial implementation, let's use a simple approach:
        # Features could be: concentration, od_value, and potentially others

        feature_cols = [conc_col]
        if 'od_value' in valid_samples.columns:
            feature_cols.append('od_value')

        X = valid_samples[feature_cols].values

        if X.shape[0] < self.n_components:
            return None  # Not enough samples for requested components

        # Standardize features
        X_scaled = self.scaler.fit_transform(X)

        # Fit PCA
        scores = self.pca.fit_transform(X_scaled)

        # Create labels for samples
        if 'sample_id' in valid_samples.columns:
            labels = valid_samples['sample_id'].values
        elif 'well_position' in valid_samples.columns:
            labels = valid_samples['well_position'].values
        else:
            labels = [f'Sample {i+1}' for i in range(len(valid_samples))]

        return {
            'scores': scores,
            'loadings': self.pca.components_,
            'variance_explained': self.pca.explained_variance_ratio_,
            'labels': labels,
            'feature_names': feature_cols
        }

    def analyze_multi_plate_variation(
        self,
        results_df: pd.DataFrame
    ) -> Optional[Dict]:
        """
        Perform PCA on calibrant OD values to detect batch effects across plates.

        Creates a pivot table where:
        - Rows = calibrant orders (concentration levels)
        - Columns = plate names
        - Values = mean OD values

        PCA reveals if certain plates cluster together (batch effects).

        Args:
            results_df: DataFrame with analysis results

        Returns:
            Dictionary with:
                - scores: PCA scores (n_plates × n_components)
                - loadings: PCA loadings
                - variance_explained: Variance explained by each PC
                - labels: Plate names for plotting
                - pivot_table: The data matrix used for PCA
            Or None if insufficient data
        """
        # Filter to only CALIBRANT wells
        calibrants = results_df[results_df['well_type'] == 'CALIBRANT'].copy()

        if calibrants.empty:
            return None

        # Check if we have multiple plates
        if 'plate_name' not in calibrants.columns:
            return None

        plate_names = calibrants['plate_name'].unique()
        if len(plate_names) < 2:
            return None  # Need at least 2 plates for batch comparison

        # Create pivot table: orders × plates
        if 'order' in calibrants.columns and 'od_value' in calibrants.columns:
            pivot = calibrants.pivot_table(
                index='order',
                columns='plate_name',
                values='od_value',
                aggfunc='mean'
            )
        else:
            return None

        # Remove rows/columns with all NaN
        pivot = pivot.dropna(how='all', axis=0).dropna(how='all', axis=1)

        # Fill remaining NaN with column mean (imputation)
        pivot = pivot.fillna(pivot.mean())

        if pivot.shape[0] < 2 or pivot.shape[1] < 2:
            return None

        # Transpose so plates are rows (observations)
        X = pivot.T.values

        if X.shape[0] < self.n_components:
            # Reduce n_components if we don't have enough plates
            n_comp = min(self.n_components, X.shape[0])
            pca = PCA(n_components=n_comp)
        else:
            pca = self.pca

        # Standardize features
        X_scaled = self.scaler.fit_transform(X)

        # Fit PCA
        scores = pca.fit_transform(X_scaled)

        return {
            'scores': scores,
            'loadings': pca.components_,
            'variance_explained': pca.explained_variance_ratio_,
            'labels': pivot.columns.values,  # Plate names
            'pivot_table': pivot
        }

    def analyze_by_metadata(
        self,
        data_df: pd.DataFrame,
        grouping_column: str,
        feature_columns: Optional[List[str]] = None
    ) -> Optional[Dict]:
        """
        Perform PCA grouped by metadata column.

        Allows analyzing samples based on any metadata column (e.g., treatment,
        timepoint, condition) instead of just plate-based batch effects.

        Args:
            data_df: Analysis results dataframe
            grouping_column: Column to use for grouping (e.g., 'treatment', 'sample_id')
            feature_columns: Columns to use as features (default: OD and concentration)

        Returns:
            Dictionary with:
                - scores: PCA scores (n_samples × n_components)
                - labels: Group labels from metadata column
                - variance_explained: Variance explained by each PC
                - loadings: PCA loadings
                - feature_names: Names of features used
                - grouping_column: Name of the grouping column used
            Or None if insufficient data
        """
        # Filter samples only
        samples = data_df[data_df['well_type'] == 'SAMPLE'].copy()

        if samples.empty or grouping_column not in samples.columns:
            return None

        # Default features: od_value and concentration_dilution_corrected
        if feature_columns is None:
            feature_columns = ['od_value', 'concentration_dilution_corrected']

        # Filter to only include existing columns
        feature_columns = [col for col in feature_columns if col in samples.columns]

        if not feature_columns:
            return None

        # Prepare feature matrix (drop rows with any NaN in features)
        X = samples[feature_columns].dropna()

        if len(X) < 3:
            return None  # Need at least 3 samples for meaningful PCA

        # Get labels for the samples that have valid features
        labels = samples.loc[X.index, grouping_column].values

        # Standardize and perform PCA
        X_scaled = self.scaler.fit_transform(X)
        scores = self.pca.fit_transform(X_scaled)

        return {
            'scores': scores,
            'labels': labels,
            'variance_explained': self.pca.explained_variance_ratio_,
            'loadings': self.pca.components_,
            'feature_names': feature_columns,
            'grouping_column': grouping_column
        }

    def detect_outliers(
        self,
        pca_result: Dict,
        n_std: float = 2.0
    ) -> np.ndarray:
        """
        Detect outliers in PCA space using Mahalanobis-like distance.

        Args:
            pca_result: Result from analyze_samples() or analyze_multi_plate_variation()
            n_std: Number of standard deviations for outlier threshold (default: 2.0)

        Returns:
            Boolean array indicating outliers (True = outlier)
        """
        scores = pca_result.get('scores')
        if scores is None:
            return np.array([])

        # Calculate distance from origin in PC space
        # Simple approach: Euclidean distance in standardized PC space
        distances = np.sqrt(np.sum(scores ** 2, axis=1))

        # Outlier threshold: mean + n_std * std
        threshold = np.mean(distances) + n_std * np.std(distances)

        outliers = distances > threshold
        return outliers

    def get_top_contributing_features(
        self,
        pca_result: Dict,
        pc_index: int = 0,
        n_features: int = 5
    ) -> List[tuple]:
        """
        Get top contributing features for a given principal component.

        Args:
            pca_result: Result from PCA analysis
            pc_index: Which PC to analyze (0 = PC1, 1 = PC2, etc.)
            n_features: Number of top features to return

        Returns:
            List of (feature_name, loading) tuples sorted by absolute loading
        """
        loadings = pca_result.get('loadings')
        feature_names = pca_result.get('feature_names')

        if loadings is None or feature_names is None:
            return []

        if pc_index >= loadings.shape[0]:
            return []

        # Get loadings for this PC
        pc_loadings = loadings[pc_index, :]

        # Sort by absolute value
        sorted_indices = np.argsort(np.abs(pc_loadings))[::-1]

        # Get top n
        top_indices = sorted_indices[:n_features]

        return [(feature_names[i], pc_loadings[i]) for i in top_indices]
