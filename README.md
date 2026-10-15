# Chambéry Triathlon

Application du club, installable sur téléphone : planning de la semaine, calculateur d'allures et zones cardiaques, traces GPX vélo et trail, calendrier de la saison.

## Installer l'app

Ouvrir l'adresse de l'app sur le téléphone, puis :
- iPhone (Safari) : Partager → « Sur l'écran d'accueil » ;
- Android (Chrome) : menu ⋮ → « Installer l'application » ou « Ajouter à l'écran d'accueil ».

## Mise à jour des données

- Le planning et la saison viennent du Google Sheet « Plan adulte 2026-2027 » (`outils/update_planning.py`).
- Les traces GPX viennent du dossier Drive du club, sous-dossiers `Vélo` et `Trail` (`outils/sync_traces.py` → `traces.json` et `traces/`).
- `outils/build_pwa.py` regénère `index.html` à partir de `outils/chambery-tri.html`.
