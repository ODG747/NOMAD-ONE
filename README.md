# NOMAD ONE

Présentation web interactive (oral de 2 min 30, 1re STI2D) pour NOMAD ONE,
une enceinte Bluetooth qui sert aussi de batterie externe.

**En ligne :** https://odg747.github.io/NOMAD-ONE/

## Contenu

| Fichier | Rôle |
|---|---|
| `index.html` | La présentation entière : 7 sections, scène 3D Three.js, CSS et JS en inline |
| `NOTES.md` | Déroulé de l'oral, touches clavier, marche à suivre en cas de problème |
| `NomadOne.pptx` | Ancienne version PowerPoint, conservée en secours |

## Utilisation

Ouvrir `index.html` par double-clic — aucun serveur nécessaire.

| Touche | Effet |
|---|---|
| `→` `Espace` | Section suivante |
| `←` | Section précédente |
| `Échap` | Plan des sections |
| `N` | Notes de l'orateur |
| `P` | Mode impression (toutes les sections empilées) |
| `T` | Remettre le minuteur à zéro |

## Technique

- Three.js r128 chargé depuis cdnjs (version épinglée), tout le reste est autonome
- Aucune image externe : géométries, textures et icônes générées en code
- Mode dégradé automatique si les fps passent sous 30
