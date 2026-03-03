"""Clinical analysis.

"""

import pandas as pd
from .tnm import TNMProcessor, ClinicalDataProcessor
from .visualization import DISPLAY_NAMES


# Pattern Analysis helper

def build_trend_jobs(plot_df, trend_date, trend_value, trend_group):
    """Build a list of trend-plot jobs after detecting TNM / UICC columns.

    Each job is a dict with keys:
        df, x_col, group, x_label, title, prefix

    Args:
        plot_df: DataFrame (SAMPLE rows only)
        trend_date: x-axis column name
        trend_value: y-axis column name
        trend_group: grouping column name or None

    Returns:
        list[dict]
    """
    group = trend_group if trend_group and trend_group != 'None' else None
    y_label = DISPLAY_NAMES.get(trend_value, trend_value.replace('_', ' ').title())
    x_label = DISPLAY_NAMES.get(trend_date, trend_date.replace('_', ' ').title())

    detector = ClinicalDataProcessor()
    x_is_tnm = detector.detect_column_type(plot_df[trend_date]) == 'tnm'
    group_is_tnm = (group and group in plot_df.columns
                    and detector.detect_column_type(plot_df[group]) == 'tnm')
    x_is_uicc = (not x_is_tnm and detector._is_uicc_like(plot_df[trend_date]))
    group_is_uicc = (not group_is_tnm and group and group in plot_df.columns
                     and detector._is_uicc_like(plot_df[group]))

    jobs = []
    tnm = TNMProcessor()

    if x_is_tnm:
        parsed_df = tnm.process(plot_df, trend_date)
        for stage_col in tnm.get_display_columns():
            if stage_col in parsed_df.columns and parsed_df[stage_col].notna().sum() >= 5:
                stage_display = stage_col.replace('_display', '').replace('_', ' ')
                jobs.append({
                    'df': parsed_df, 'x_col': stage_col, 'group': group,
                    'x_label': stage_display,
                    'title': f'Pattern: {y_label} by {stage_display}',
                    'prefix': stage_col.replace('_Stage_display', '').replace('_', ''),
                })
    elif group_is_tnm:
        parsed_df = tnm.process(plot_df, group)
        for stage_col in tnm.get_display_columns():
            if stage_col in parsed_df.columns and parsed_df[stage_col].notna().sum() >= 5:
                stage_display = stage_col.replace('_display', '').replace('_', ' ')
                jobs.append({
                    'df': parsed_df, 'x_col': trend_date, 'group': stage_col,
                    'x_label': x_label,
                    'title': f'Pattern: {y_label} grouped by {stage_display}',
                    'prefix': stage_col.replace('_Stage_display', '').replace('_', ''),
                })
    else:
        job_df = plot_df.copy()
        if x_is_uicc:
            job_df[trend_date] = job_df[trend_date].apply(detector._clean_uicc_value)
        if group_is_uicc and group:
            job_df[group] = job_df[group].apply(detector._clean_uicc_value)
        jobs.append({
            'df': job_df, 'x_col': trend_date, 'group': group,
            'x_label': x_label,
            'title': f'Pattern: {y_label} vs {x_label}',
            'prefix': None,
        })

    return jobs, y_label


def prepare_trend_df(job, trend_value):
    """Prepare a single trend job's DataFrame for plotting.

    Cleans whole-number floats, coerces y to numeric, drops NaN, sorts by x.

    Returns:
        Cleaned DataFrame or None if fewer than 5 rows survive.
    """
    job_df = job['df'].copy()
    job_df['_x'] = job_df[job['x_col']]

    # Clean whole-number floats to int
    if job_df['_x'].dtype == 'float64':
        non_null = job_df['_x'].dropna()
        if len(non_null) > 0:
            try:
                if (non_null == non_null.astype(int)).all():
                    job_df['_x'] = job_df['_x'].apply(
                        lambda v: int(v) if pd.notna(v) else v
                    )
            except (ValueError, OverflowError):
                pass

    job_df[trend_value] = pd.to_numeric(job_df[trend_value], errors='coerce')

    cols_to_check = ['_x', trend_value]
    if job['group']:
        cols_to_check.append(job['group'])
    job_df = job_df.dropna(subset=cols_to_check).sort_values('_x')

    if len(job_df) < 5:
        return None
    return job_df


# Clinical column processing
def process_clinical_columns(data_df, clinical_columns, clinical_biomarker):
    """Process multiple clinical columns and collect analysis metadata.

    Args:
        data_df: Full results DataFrame
        clinical_columns: list of column names to process
        clinical_biomarker: biomarker column name for correlation

    Returns:
        (clinical_df, all_analysis_cols, all_display_mapping,
         all_column_groups, biomarker_display, per_column_violin_info)

        per_column_violin_info is a list of dicts:
            {col, col_display, col_safe}
        for each violin-eligible column.
    """
    biomarker_display = DISPLAY_NAMES.get(
        clinical_biomarker,
        clinical_biomarker.replace('_', ' ').title()
    )

    all_analysis_cols = []
    all_display_mapping = {}
    all_column_groups = {}
    violin_info = []

    clinical_df = data_df.copy()
    if 'well_type' in clinical_df.columns:
        clinical_df = clinical_df[clinical_df['well_type'] == 'SAMPLE']

    for clinical_column in clinical_columns:
        if clinical_column not in clinical_df.columns:
            continue

        processor = ClinicalDataProcessor()
        clinical_df = processor.process(clinical_df, clinical_column)

        for col in processor.get_violin_columns():
            if col in clinical_df.columns and clinical_df[col].notna().sum() >= 5:
                col_display = (col.replace('_display', '')
                               .replace('_num', '')
                               .replace('_clean', '')
                               .replace('_', ' '))
                col_safe = (col.replace('_display', '')
                            .replace('_num', '')
                            .replace('_clean', '')
                            .lower().replace(' ', '_'))
                violin_info.append({
                    'col': col,
                    'col_display': col_display,
                    'col_safe': col_safe,
                })

        all_analysis_cols.extend(processor.get_analysis_columns())
        all_display_mapping.update(processor.get_display_mapping())
        all_column_groups.update(processor.get_column_groups())

    return (clinical_df, all_analysis_cols, all_display_mapping,
            all_column_groups, biomarker_display, violin_info)


def get_pattern_x_columns(df, col_list):
    """Return the subset of col_list that is valid as X-axis for Pattern Analysis.

    A column qualifies if it is:
      - numeric dtype (continuous measurements, cleaned ordinal ranks), OR
      - TNM-formatted strings (ordinal by clinical convention; processed by
        build_trend_jobs into ordered stage sub-jobs), OR
      - UICC-like strings (e.g. I/II/III/IV; cleaned to integers by build_trend_jobs)

    Nominal string columns (Diagnosis, Sex, Treatment group, etc.) are excluded
    because alphabetical sorting of nominal labels produces arbitrary numeric
    ranks and scientifically invalid Spearman correlations.
    """
    detector = ClinicalDataProcessor()
    valid = []
    for col in col_list:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue
        if pd.api.types.is_numeric_dtype(s):
            valid.append(col)
        elif detector.detect_column_type(s) == 'tnm' or detector._is_uicc_like(s):
            valid.append(col)
    return valid
