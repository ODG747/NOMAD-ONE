# NOMAD ONE — état d'avancement

_Dernière mise à jour : 9 septembre 2026, fin de session._

## Reprendre demain — en une commande

```bash
pwsh -File blender\run_all.ps1
```

Elle relance les rendus **et reprend là où ils se sont arrêtés** : les images
déjà produites ne sont pas recalculées. Blender n'a pas besoin d'être ouvert,
tout tourne en tâche de fond. Compter environ **1 h 45** pour le reste.

Ensuite :

```bash
python tools\build_assets.py
```

---

## Où on en est

| Phase | État |
|---|---|
| 1 — Modélisation | **terminée** |
| 2 — Matériaux et lumière | **terminée, rendu de test validé** |
| 3 — Production des rendus | **en cours : 22 / 116 images** |
| 4 — Intégration web | outillage prêt, `index.html` pas encore modifié |
| 5 — Finitions | QR code fait ; le reste existait déjà |
| 6 — Qualité et livraison | pas commencée |

### Détail de la phase 3

| Séquence | Fait | Total |
|---|---|---|
| Turntable 360° | 22 | 72 |
| Vue éclatée | 0 | 40 |
| Ambiances (rocher, sac, tente) | 0 | 3 |
| Plan slide 5 | 0 | 1 |

Les quatre décors sont **construits et validés en aperçu basse résolution** ;
il ne reste qu'à les rendre en qualité finale.

---

## Ce qui est déjà en place

- `blender/nomad_lib.py` — géométrie (révolution, balayage, biseaux, normales)
- `blender/build_model.py` — l'enceinte, 15 pièces nommées, avec contrôle
  automatique d'enveloppe (aucun organe interne ne peut transpercer la coque)
- `blender/materials.py` — caoutchouc, grille perforée, métal brossé, tissu
- `blender/studio.py` — plateau de prise de vue, caméra, réglages Cycles
- `blender/scenes.py` — les trois décors d'ambiance
- `blender/phone.py` — le plan de la slide 5
- `blender/render_jobs.py` — les six travaux de rendu, reprise incluse
- `blender/postfx.py` — grain, vignettage, composite
- `tools/build_assets.py` — PNG → WebP + repli JPEG, avec contrôle du budget
- `tools/make_qr.py` — QR code vérifié, écrit dans `assets/qr.svg`
- `vendor/` — Three.js et les polices en local (712 Ko) pour le hors-ligne

## Décisions prises et validées

- Ombre de contact conservée : l'enceinte est posée, pas en lévitation.
- WebP seul pour les 112 images de séquence ; repli JPEG sur les 3 ambiances
  et la première image du turntable.
- Grain et vignettage en surimpression CSS, pas cuits dans les images, pour
  que les slides 4 et 5 en 3D temps réel aient le même rendu.
- Environnement de studio procédural, aucun HDRI téléchargé.
- Éclairage figé après validation du rendu de test.

## À vérifier toi-même

- **Scanner le QR code de `assets/qr.svg` avec ton téléphone.** Il est généré
  par du code écrit ici et contrôlé (Reed-Solomon vérifié mathématiquement,
  structure contrôlée), mais seul un vrai scan prouve qu'il est lisible.

## Rien n'est commité

Le dépôt est intact : aucun `commit`, aucun `push`. La mise en ligne se fera
à la phase 6, quand tout sera testé.
