# -*- coding: utf-8 -*-
"""
NOMAD ONE - conversion des rendus Blender en ressources web.

    python tools/build_assets.py

PNG 1600x1200 avec alpha  ->  WebP (les sequences)
PNG opaques 1600x900      ->  WebP + repli JPEG (les ambiances)
Un repli JPEG est aussi produit pour la premiere image du turntable, afin
qu'un navigateur sans WebP affiche au moins une image fixe.

N'utilise que ffmpeg : aucune bibliotheque Python a installer.
"""
import json, os, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REND = os.path.join(ROOT, "blender", "renders")
ASSETS = os.path.join(ROOT, "assets")
DECK_BG = "0x12162E"          # fond de la maquette, pour aplatir les replis
BUDGET_MB = 25.0

Q_SEQ = 80        # qualite WebP des sequences
Q_AMB = 84        # qualite WebP des ambiances (image plein cadre)
Q_JPG = 4         # qualite JPEG ffmpeg (2 = meilleur, 31 = pire)


def ffmpeg(args):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + args,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + (r.stderr or "").strip()[:400])


def to_webp(src, dst, quality, alpha=True):
    args = ["-i", src, "-c:v", "libwebp", "-quality", str(quality),
            "-compression_level", "6", "-preset", "picture"]
    args += ["-pix_fmt", "yuva420p"] if alpha else ["-pix_fmt", "yuv420p"]
    ffmpeg(args + [dst])


def to_jpg(src, dst, on_bg=False, size="1600x1200"):
    if on_bg:
        ffmpeg(["-f", "lavfi", "-i", "color=c=%s:s=%s" % (DECK_BG, size),
                "-i", src, "-filter_complex", "[0][1]overlay=format=auto",
                "-frames:v", "1", "-q:v", str(Q_JPG), dst])
    else:
        ffmpeg(["-i", src, "-q:v", str(Q_JPG), dst])


def seq(sub, prefix, out_sub, quality=Q_SEQ):
    src_dir = os.path.join(REND, sub)
    if not os.path.isdir(src_dir):
        return []
    files = sorted(f for f in os.listdir(src_dir) if f.endswith(".png"))
    dst_dir = os.path.join(ASSETS, out_sub)
    os.makedirs(dst_dir, exist_ok=True)
    made = []
    for i, f in enumerate(files):
        dst = os.path.join(dst_dir, "%s%02d.webp" % (prefix, i))
        to_webp(os.path.join(src_dir, f), dst, quality)
        made.append(dst)
        sys.stdout.write("\r  %s %d/%d" % (out_sub, i + 1, len(files)))
        sys.stdout.flush()
    print()
    return made


def size_mb(paths):
    return sum(os.path.getsize(p) for p in paths) / 1e6


def main():
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg introuvable dans le PATH.")
    os.makedirs(ASSETS, exist_ok=True)
    report, manifest = {}, {}

    turn = seq("turntable", "t", "turn")
    expl = seq("exploded", "e", "expl")
    report["turn"] = (len(turn), size_mb(turn))
    report["expl"] = (len(expl), size_mb(expl))
    manifest["turn"] = {"n": len(turn), "path": "assets/turn/t%02d.webp"}
    manifest["expl"] = {"n": len(expl), "path": "assets/expl/e%02d.webp"}

    # repli JPEG : premiere image du turntable, aplatie sur le fond de la maquette
    fallbacks = []
    src0 = os.path.join(REND, "turntable", "turn_000.png")
    if os.path.exists(src0):
        dst = os.path.join(ASSETS, "turn", "t00.jpg")
        to_jpg(src0, dst, on_bg=True, size="1600x1200")
        fallbacks.append(dst)

    amb_dir = os.path.join(REND, "ambience")
    ambs = {}
    if os.path.isdir(amb_dir):
        os.makedirs(os.path.join(ASSETS, "amb"), exist_ok=True)
        for f in sorted(os.listdir(amb_dir)):
            if not f.endswith(".png"):
                continue
            name = os.path.splitext(f)[0]
            src = os.path.join(amb_dir, f)
            w = os.path.join(ASSETS, "amb", name + ".webp")
            j = os.path.join(ASSETS, "amb", name + ".jpg")
            to_webp(src, w, Q_AMB, alpha=False)
            to_jpg(src, j)
            ambs[name] = ["assets/amb/%s.webp" % name, "assets/amb/%s.jpg" % name]
            fallbacks.append(j)
            report.setdefault("amb", [0, 0.0])
            report["amb"][0] += 1
            report["amb"][1] += (os.path.getsize(w) + os.path.getsize(j)) / 1e6
    manifest["amb"] = ambs

    s5 = os.path.join(REND, "slide5", "slide5.png")
    if os.path.exists(s5):
        w = os.path.join(ASSETS, "slide5.webp")
        to_webp(s5, w, Q_AMB)
        to_jpg(s5, w.replace(".webp", ".jpg"), on_bg=True, size="1600x1200")
        manifest["slide5"] = ["assets/slide5.webp", "assets/slide5.jpg"]
        report["slide5"] = (1, size_mb([w, w.replace(".webp", ".jpg")]))

    with open(os.path.join(ASSETS, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)

    total = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(ASSETS) for f in fs) / 1e6
    print("\n--- ressources web ---")
    for k, v in report.items():
        print("  %-8s %3d fichiers  %6.2f Mo" % (k, v[0], v[1]))
    print("  %-8s %s  %6.2f Mo" % ("TOTAL", " " * 12, total))
    vendor = os.path.join(ROOT, "vendor")
    if os.path.isdir(vendor):
        v = sum(os.path.getsize(os.path.join(dp, f))
                for dp, _, fs in os.walk(vendor) for f in fs) / 1e6
        print("  %-8s %s  %6.2f Mo  (three.js + polices)" % ("vendor", " " * 12, v))
        total += v
    print("  budget   %s  %6.2f Mo / %.0f Mo  -> %s"
          % (" " * 12, total, BUDGET_MB,
             "OK" if total <= BUDGET_MB else "DEPASSEMENT"))
    if total > BUDGET_MB:
        print("  !! reduire le NOMBRE d'images, pas leur qualite.")


if __name__ == "__main__":
    main()
