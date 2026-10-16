# farfavinci

Plugin DaVinci Resolve (**version gratuite**) : sous-titres automatiques + masque IA, le tout en local sur la carte graphique.

## Fonctionnalités

**Sous-titres automatiques** (Whisper large-v3, GPU)
- Transcription de la timeline entière ou de la sélection I / O
- Découpage : bloc complet, phrase par phrase, mot par mot
- Sous-titres simples (piste de sous-titres) ou **titres animés** (piste vidéo 2)
- Styles en un clic : rebond karaoké, bulle, néon, glissement, élégant…
- Police (aperçu dans sa propre police), taille, contour, animation d'entrée / sortie, couleur karaoké
- 23 langues, dont japonais, chinois, coréen (police adaptée automatiquement)

**Masque IA** (SAM 2, GPU)
- Sélection du sujet au clic (garder / exclure) ou en l'encadrant
- Suivi sur tout le clip ou sur la sélection I / O
- Sortie : sujet détouré (ProRes 4444 avec transparence) + cache noir et blanc pour la page Color

## Fonctionnement

DaVinci gratuit bloque les scripts externes. Un petit script Lua résident (`AutoTexte Pont.lua`,
menu *Espace de travail > Scripts*) échange avec l'application par fichiers : demandes via
`request.lua`, réponses via `Fusion.prefs`.

| Fichier | Rôle |
|---|---|
| `app.pyw` | Application (CustomTkinter) |
| `AutoTexte Pont.lua` | Pont résident dans DaVinci |
| `bridge.py` | Client du pont côté application |
| `transcribe.py` | Transcription Whisper (faster-whisper) |
| `mask.py` / `masque_ui.py` | Moteur SAM 2 / onglet Masque IA |
| `watcher.pyw` | Ouvre l'application quand le pont démarre |
| `installer.ps1` | Installation complète |

## Installation

Windows, Python 3.12, carte NVIDIA (testé sur RTX 4060 Ti 8 Go) :

```powershell
powershell -ExecutionPolicy Bypass -File installer.ps1
```

Puis dans DaVinci : *Espace de travail > Scripts > AutoTexte Pont*.

## Crédits

Le modèle de titres animés (`caption-bin.drb`) et le principe du pont viennent de
[AutoSubs](https://github.com/tmoroney/auto-subs) (licence MIT, voir `NOTICE-AutoSubs.txt`).
Transcription : [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
Masque : [SAM 2](https://github.com/facebookresearch/sam2) (Meta, Apache 2.0).
