# -*- coding: utf-8 -*-
"""
NOMAD ONE - finition d'image (execute dans Blender, numpy embarque).

  vignette()  : assombrissement doux des bords
  grain()     : grain de capteur fixe (meme motif a chaque image, comme un
                vrai capteur : il appartient a l'appareil, pas au sujet)
  over()      : composite sur un fond opaque, pour juger le rendu final

Les images PNG sont lues et reecrites en Non-Color : les valeurs manipulees
sont celles de l'affichage, deja passees par AgX.
"""
import bpy, numpy as np, os


def _load(path):
    img = bpy.data.images.load(path, check_existing=False)
    img.colorspace_settings.name = 'Non-Color'
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def _save(arr, path):
    h, w, _ = arr.shape
    name = "_out_" + os.path.basename(path)
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=False)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.clip(arr, 0.0, 1.0).ravel())
    img.filepath_raw = path
    img.file_format = 'PNG'
    img.save()
    bpy.data.images.remove(img)
    return path


_VIG_CACHE = {}
_GRAIN_CACHE = {}


def vignette_mask(h, w, amount=0.20, radius=0.78, soft=0.55):
    key = (h, w, amount, radius, soft)
    if key not in _VIG_CACHE:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
        r = np.sqrt(((xx - cx) / (w / 2.0)) ** 2 + ((yy - cy) / (h / 2.0)) ** 2)
        t = np.clip((r - radius) / max(1e-6, soft), 0.0, 1.0)
        _VIG_CACHE[key] = (1.0 - amount * (t * t * (3 - 2 * t)))[..., None]
    return _VIG_CACHE[key]


def grain_field(h, w, seed=1789):
    key = (h, w, seed)
    if key not in _GRAIN_CACHE:
        rng = np.random.default_rng(seed)
        g = rng.normal(0.0, 1.0, (h, w)).astype(np.float32)
        # deux octaves : un grain fin et un grumeau plus lent
        g2 = rng.normal(0.0, 1.0, ((h + 1) // 2, (w + 1) // 2)).astype(np.float32)
        g2 = np.repeat(np.repeat(g2, 2, 0), 2, 1)[:h, :w]
        _GRAIN_CACHE[key] = 0.72 * g + 0.28 * g2
    return _GRAIN_CACHE[key]


def finish(src, dst, vig=0.20, grain=0.011, bg=None, seed=1789):
    """vig : force du vignettage. grain : ecart-type du bruit (0 = aucun).
    bg : (r, g, b) en 0..1 pour aplatir sur un fond opaque, sinon alpha garde."""
    a = _load(src)
    h, w, _ = a.shape
    rgb, al = a[..., :3], a[..., 3:4]
    if bg is not None:
        rgb = rgb * al + np.array(bg, dtype=np.float32) * (1.0 - al)
        al = np.ones_like(al)
    rgb = rgb * vignette_mask(h, w, vig)
    if grain > 0.0:
        g = grain_field(h, w, seed)[..., None]
        # le grain se voit surtout dans les demi-teintes, moins dans les noirs
        weight = 0.35 + 0.65 * np.clip(rgb.mean(axis=2, keepdims=True) * 2.4, 0, 1)
        rgb = rgb + g * grain * weight
    return _save(np.concatenate([rgb, al], axis=2), dst)
