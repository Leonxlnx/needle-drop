"""Luminance / hue stats of test PNGs (decoded via ffmpeg). Run with Blender's bundled python -I.
usage: lumstats.py a.png b.png ..."""
import sys, subprocess, numpy as np
for f in sys.argv[1:]:
    w, h = 640, 360
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vf', f'scale={w}:{h}', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(float) / 255.0
    lin = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    Y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]   # display-referred luma
    mx = a.max(-1); mn = a.min(-1); sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    hue = np.zeros_like(mx)
    d = np.maximum(mx - mn, 1e-6)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    teal = ((hue > 160) & (hue < 200) & (sat > 0.3) & (mx > 0.2)).mean() * 100
    print('%s meanY %.3f dark<0.06 %4.1f%% top30 %.3f sat %.2f teal %.2f%% clip %.1f%%' % (
        f.split('/')[-1], Y.mean(), (Y < 0.06).mean() * 100, Y[:int(h * 0.3)].mean(), sat.mean(), teal, (mx > 0.98).mean() * 100))
