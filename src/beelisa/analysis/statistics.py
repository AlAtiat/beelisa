"""Statistical functions for clinical correlation analysis.
"""

import numpy as np
from .models.lowess import lowess as np_lowess
import pandas as pd

def spearman_correlation(x, y):
    """Compute Spearman rho and p-value.

    Args:
        x: Array-like of x values
        y: Array-like of y values

    Returns:
        (rho, pval, n) or (None, None, n) if insufficient data
    """
    from scipy import stats

    x = np.asarray(x, float)
    y = np.asarray(y, float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    n = len(x)

    if n < 5:
        return None, None, n

    try:
        rho, pval = stats.spearmanr(x, y)
        return rho, pval, n
    except Exception:
        return None, None, n


def benjamini_hochberg(pvals):
    """Benjamini-Hochberg FDR correction (step-up procedure).

    Args:
        pvals: 1D array of raw p-values

    Returns:
        Array of FDR-adjusted p-values (q-values)
    """
    pvals = np.asarray(pvals, dtype=float)
    m = len(pvals)
    if m == 0:
        return pvals

    sorted_idx = np.argsort(pvals)
    sorted_pvals = pvals[sorted_idx]
    adjusted = np.zeros(m)

    # BH step-up: q_k = p_k * m / rank_k
    for k in range(m - 1, -1, -1):
        rank = k + 1
        adjusted[k] = sorted_pvals[k] * m / rank

    # Enforce monotonicity (cumulative min from right to left)
    for k in range(m - 2, -1, -1):
        adjusted[k] = min(adjusted[k], adjusted[k + 1])

    adjusted = np.minimum(adjusted, 1.0)

    # Map back to original order
    result = np.zeros(m)
    result[sorted_idx] = adjusted
    return result


def lowess_with_band(x, y, use_log_y=False, frac=0.3):
    """LOWESS smoothing with rolling IQR band.

    Args:
        x: Numeric x values
        y: Numeric y values
        use_log_y: If True, fit LOWESS on log(y) and exponentiate back
        frac: LOWESS smoothing fraction (0-1)

    Returns:
        (x_smooth, y_smooth, x_band, y_q25, y_q75) or (None,)*5
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)

    valid = np.isfinite(x) & np.isfinite(y)
    if use_log_y:
        valid &= (y > 0)
    x, y = x[valid], y[valid]

    if len(x) < 5:
        return None, None, None, None, None

    y_fit = np.log(y) if use_log_y else y.copy()

    # LOWESS smoothing
    x_smooth, y_smooth = np_lowess(x, y_fit, frac=frac)

    # Rolling IQR band on sorted raw data
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y_fit[order]

    n = len(x_sorted)
    window = max(5, int(0.2 * n))
    half = window // 2

    x_band, q25_band, q75_band = [], [], []
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half)
        x_band.append(x_sorted[i])
        q25_band.append(np.percentile(y_sorted[lo:hi], 25))
        q75_band.append(np.percentile(y_sorted[lo:hi], 75))

    # Convert back from log-space
    if use_log_y:
        y_smooth = np.exp(y_smooth)
        q25_band = np.exp(np.array(q25_band))
        q75_band = np.exp(np.array(q75_band))

    return x_smooth, y_smooth, np.array(x_band), np.array(q25_band), np.array(q75_band)


def descriptive_stats(y, confidence=0.95):
    """Descriptive statistics for a data array.

    Computes mean, median, sample SD (ddof=1), IQR (Q25/Q75), and a
    parametric confidence interval for the mean using the t-distribution
    (two-sided, df = n-1), which is valid for any sample size.

    Args:
        y: Array-like of numeric values
        confidence: CI level, default 0.95

    Returns:
        dict with keys mean, median, sd, q25, q75, ci_low, ci_high, n
        or None if n < 2
    """
    from scipy import stats as scipy_stats

    y = np.asarray(y, float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 2:
        return None

    mean   = float(np.mean(y))
    median = float(np.median(y))
    sd     = float(np.std(y, ddof=1))
    q25    = float(np.percentile(y, 25))
    q75    = float(np.percentile(y, 75))

    se     = sd / np.sqrt(n)
    t_crit = scipy_stats.t.ppf((1 + confidence) / 2, df=n - 1)
    ci_low  = mean - t_crit * se
    ci_high = mean + t_crit * se

    return dict(mean=mean, median=median, sd=sd,
                q25=q25, q75=q75,
                ci_low=ci_low, ci_high=ci_high, n=n)


def roc_analysis(df, score_col, label_col, positive_label, negative_label):
    """Compute ROC curve, AUC, and Youden-optimal cutoff for binary classification.

    Args:
        df: DataFrame with analysis results (must contain well_type column)
        score_col: Numeric predictor column (e.g. 'concentration_dilution_corrected')
        label_col: Binary outcome column (e.g. 'Diagnosis')
        positive_label: Value mapped to 1 (disease / case)
        negative_label: Value mapped to 0 (control / reference)

    Returns:
        dict with keys: success, score_column, label_column, positive_label, negative_label,
        n_pos, n_neg, auc, auc_ci95, best_threshold, sensitivity, specificity,
        roc_points (DataFrame with fpr/tpr/threshold), notes, error (on failure)
    """
    from sklearn.metrics import roc_curve, auc as sk_auc

    if positive_label == negative_label:
        return {'success': False, 'error': 'Positive and negative class must differ.'}

    # Restrict to SAMPLE wells
    if 'well_type' in df.columns:
        working = df[df['well_type'] == 'SAMPLE'].copy()
    else:
        working = df.copy()

    # Keep only rows with both score and label present
    working = working[working[score_col].notna() & working[label_col].notna()]

    # Keep only the two chosen classes (safe for multi-class columns)
    working = working[working[label_col].astype(str).isin(
        {str(positive_label), str(negative_label)}
    )]

    y_score = working[score_col].to_numpy(dtype=float)
    y_label = working[label_col].astype(str).to_numpy()

    y_true = np.where(y_label == str(positive_label), 1, 0)

    n_pos = int(np.sum(y_true == 1))
    n_neg = int(np.sum(y_true == 0))

    if n_pos < 5 or n_neg < 5:
        return {
            'success': False,
            'error': (
                f'Too few samples: {n_pos} positive, {n_neg} negative. '
                'Need at least 5 per class to compute a meaningful ROC curve.'
            ),
        }

    fpr, tpr, thresholds = roc_curve(y_true, y_score, pos_label=1)
    roc_auc = float(sk_auc(fpr, tpr))

    # 95% CI band for the ROC curve (bootstrap, same 95% level as auc_ci95)
    rng = np.random.default_rng(0)
    fpr_grid = np.linspace(0.0, 1.0, 200)
    tprs = []

    for _ in range(500):
        idx = rng.integers(0, len(y_true), len(y_true))
        yt = y_true[idx]
        ys = y_score[idx]
        if yt.sum() == 0 or yt.sum() == len(yt):  # skip resamples missing a class
            continue
        fpr_b, tpr_b, _ = roc_curve(yt, ys, pos_label=1)
        tpr_i = np.interp(fpr_grid, fpr_b, tpr_b)
        tpr_i[0] = 0.0
        tpr_i[-1] = 1.0
        tprs.append(tpr_i)

    roc_curve_ci95 = None
    if len(tprs) >= 30:
        tprs = np.vstack(tprs)
        roc_curve_ci95 = (
            fpr_grid,
            np.percentile(tprs, 2.5, axis=0),
            np.percentile(tprs, 97.5, axis=0),
        )
        
    # Youden index: maximise sensitivity + specificity simultaneously
    youden = tpr - fpr
    i = int(np.argmax(youden))
    best_threshold = float(thresholds[i])
    sensitivity = float(tpr[i])
    specificity = float(1.0 - fpr[i])

    # Hanley–McNeil SE approximation for 95% CI
    Q1 = roc_auc / (2.0 - roc_auc)
    Q2 = 2.0 * roc_auc ** 2 / (1.0 + roc_auc)
    var = (
        roc_auc * (1.0 - roc_auc)
        + (n_pos - 1) * (Q1 - roc_auc ** 2)
        + (n_neg - 1) * (Q2 - roc_auc ** 2)
    ) / (n_pos * n_neg)
    se = float(np.sqrt(max(var, 0.0)))
    ci_low = float(np.clip(roc_auc - 1.96 * se, 0.0, 1.0))
    ci_high = float(np.clip(roc_auc + 1.96 * se, 0.0, 1.0))

    roc_points = pd.DataFrame({'fpr': fpr, 'tpr': tpr, 'threshold': thresholds})

    return {
        'success': True,
        'score_column': score_col,
        'label_column': label_col,
        'positive_label': positive_label,
        'negative_label': negative_label,
        'n_pos': n_pos,
        'n_neg': n_neg,
        'auc': roc_auc,
        'auc_ci95': (ci_low, ci_high),
        'best_threshold': best_threshold,
        'sensitivity': sensitivity,
        'specificity': specificity,
        'roc_points': roc_points,
        'roc_curve_ci95': roc_curve_ci95,
    }
