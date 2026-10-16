# farfavinci

Deux outils **indépendants** pour **DaVinci Resolve gratuit**, qui tournent entièrement sur ton PC :

| | Outil | Ce qu'il fait | Carte graphique |
|---|---|---|---|
| 📝 | **[farfascript](farfascript/)** | Sous-titres automatiques (Whisper) : simples ou animés, karaoké, 23 langues | NVIDIA conseillée (marche aussi sans, mais lentement) |
| 🎭 | **[farfamask](farfamask/)** | Masque IA (SAM 2) : sélection au clic ou au cadre, détourage + cache pour la page Color | **NVIDIA obligatoire** |

Ces fonctions (« Transcription automatique » et « Magic Mask ») sont réservées à DaVinci Studio,
la version payante. farfavinci les apporte à la version gratuite.

## Faut-il installer les deux ?

**Non.** Les deux outils sont **totalement indépendants** et **aucun n'est obligatoire** :

- Tu veux seulement des sous-titres ? Installe **farfascript**, c'est tout.
- Tu veux seulement le masque IA ? Installe **farfamask**, c'est tout.
- Tu veux les deux ? Installe-les l'un après l'autre, dans n'importe quel ordre.

Chaque outil a son propre dossier, son propre installeur, sa propre application, son propre
script dans DaVinci et sa propre désinstallation. L'un ne dépend jamais de l'autre : en installer
ou en désinstaller un ne change rien au second.

Seule exception pratique : **farfamask exige une carte NVIDIA**. Sans elle, installe seulement
farfascript (qui fonctionne aussi sans NVIDIA, en plus lent).

## Configuration commune

- Windows 10 ou 11 (64 bits) — Mac et Linux non pris en charge
- DaVinci Resolve 21 gratuit (testé : 21.1.1)
- [Python 3.12](https://www.python.org/downloads/) (coche « py launcher » à l'installation)
- Internet pour l'installation et le premier lancement (téléchargement des modèles d'IA)

## Installation

1. Bouton vert **Code > Download ZIP** en haut de cette page, puis extrais le ZIP.
2. Ouvre le dossier de l'outil voulu (**farfascript** ou **farfamask**).
3. Double-clique sur **`Installer.bat`**.

Les détails (configuration, utilisation, dépannage) sont dans le README de chaque dossier.

## 100 % local

Aucune image ni aucun son n'est envoyé sur Internet. Seuls les modèles d'IA sont téléchargés
(depuis Hugging Face) au premier usage.

## Licence

Open source sous **licence MIT** (voir `LICENSE`) : tu peux utiliser, modifier, ajouter des
fonctions et partager ta version, à condition de garder le fichier `LICENSE`.

## Contribuer

- **Bug ou idée** : onglet **Issues** de cette page.
- **Code** : fais un *fork*, modifie, puis ouvre une *pull request* en expliquant ce que tu as
  changé et comment tu l'as testé. Le code et les commentaires sont en français.

## Crédits

- Principe du pont et modèle de titres animés : [AutoSubs](https://github.com/tmoroney/auto-subs)
  de Tom Moroney (MIT, voir `NOTICE-AutoSubs.txt` dans chaque dossier)
- Transcription : [faster-whisper](https://github.com/SYSTRAN/faster-whisper) et
  [Whisper](https://github.com/openai/whisper) d'OpenAI (MIT)
- Masque : [SAM 2](https://github.com/facebookresearch/sam2) de Meta (Apache 2.0)
- Interface : [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (MIT)
