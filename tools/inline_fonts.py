# -*- coding: utf-8 -*-
"""
Integre les polices directement dans vendor/fonts.css (data: URI en base64).

Pourquoi : ouverte par double-clic (file://), la page a une origine "null".
Chrome et Edge refusent alors de charger une police depuis un fichier voisin
(blocage CORS) et le titre retombe sur une police systeme. Une police integree
au CSS n'est pas un fichier separe : elle s'affiche dans tous les cas.

    python tools/inline_fonts.py
"""
import base64, io, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS = os.path.join(ROOT, "vendor", "fonts.css")

css = io.open(CSS, encoding="utf-8-sig").read()
cache = {}


def inline(m):
    rel = m.group(1)
    if rel not in cache:
        with open(os.path.join(ROOT, "vendor", rel), "rb") as fh:
            cache[rel] = base64.b64encode(fh.read()).decode("ascii")
    return "url(data:font/woff2;base64,%s)" % cache[rel]


new, n = re.subn(r"url\((f/[^)]+\.woff2)\)", inline, css)
if n == 0 and "data:font/woff2" in css:
    print("deja integre, rien a faire")
else:
    io.open(CSS, "w", encoding="utf-8").write(new)
    print("polices integrees : %d references, %d fichiers, css = %d Ko"
          % (n, len(cache), os.path.getsize(CSS) // 1024))
