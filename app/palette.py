"""Цветовой «отпечаток» картинки и расстояние между ними."""
import numpy as np
from PIL import Image

BINS = 12


def features(img):
    im = img.convert('RGB').resize((96, 96))
    a = np.asarray(im).astype(float) / 255
    mask = a.min(2) < 0.94                      # без белого фона
    if mask.sum() < 50:
        mask = np.ones(mask.shape, bool)
    px = a[mask]
    mx, mn = px.max(1), px.min(1)
    v = mx
    s = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    r, g, b = px[:, 0], px[:, 1], px[:, 2]
    d = np.maximum(mx - mn, 1e-6)
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
    w = s * v
    hist, _ = np.histogram(h, bins=BINS, range=(0, 1), weights=w)
    hist = hist / max(hist.sum(), 1e-6)
    return {'hue': hist.round(4).tolist(), 'sat': float(s.mean()), 'light': float(v.mean()),
            'mean': px.mean(0).round(4).tolist()}


def distance(f1, f2):
    h1, h2 = np.array(f1['hue']), np.array(f2['hue'])
    # круговое сглаживание: соседние оттенки считаются близкими
    k = np.array([0.25, 0.5, 0.25])
    sm = lambda h: np.convolve(np.r_[h[-1], h, h[0]], k, 'valid')
    hd = 0.5 * np.abs(sm(h1) - sm(h2)).sum()
    return float(hd + 0.6 * abs(f1['light'] - f2['light']) + 0.6 * abs(f1['sat'] - f2['sat']))


def group_distance(fs, f):
    return float(np.mean([distance(x, f) for x in fs])) if fs else 0.0
