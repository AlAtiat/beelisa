"""Statistical functions for clinical correlation analysis.
"""

import numpy as np
from .models.lowess import lowess as np_lowess


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
