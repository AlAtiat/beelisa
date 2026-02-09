"""LOWESS (Locally Weighted Scatterplot Smoothing) implementation using numpy."""

import numpy as np


def lowess(x, y, frac=0.3):
    """LOWESS smoother using tricube weights and local linear regression.

    Args:
        x: 1D array of x values
        y: 1D array of y values
        frac: Fraction of data used for each local regression (0-1)

    Returns:
        (x_sorted, y_smoothed) — both sorted by x
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    k = max(int(np.ceil(frac * n)), 3)
    k = min(k, n)

    order = np.argsort(x)
    x_s = x[order]
    y_s = y[order]
    y_smooth = np.zeros(n)

    for i in range(n):
        dists = np.abs(x_s - x_s[i])
        # k nearest neighbours
        idx = np.argsort(dists)[:k]
        max_dist = dists[idx[-1]] + 1e-10

        # Tricube weight function
        u = dists[idx] / max_dist
        w = (1.0 - u ** 3) ** 3

        # Weighted local linear regression: y = a + b*x
        xi = x_s[idx]
        yi = y_s[idx]
        sw = w.sum()
        sx = (w * xi).sum()
        sy = (w * yi).sum()
        sxx = (w * xi * xi).sum()
        sxy = (w * xi * yi).sum()

        denom = sw * sxx - sx * sx
        if abs(denom) > 1e-12:
            b = (sw * sxy - sx * sy) / denom
            a = (sy - b * sx) / sw
            y_smooth[i] = a + b * x_s[i]
        else:
            # Fallback to weighted mean
            y_smooth[i] = sy / sw if sw > 0 else np.mean(yi)

    return x_s, y_smooth
