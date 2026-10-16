# farfascript — sous-titres automatiques

Sous-titres automatiques pour **DaVinci Resolve gratuit**, avec Whisper large-v3 sur ta carte
graphique. Fait partie de [farfavinci](../), mais s'installe et fonctionne **seul**.

## Configuration requise

| | Minimum | Testé |
|---|---|---|
| Système | Windows 10 / 11 (64 bits) | Windows 11 Pro |
| Carte graphique | NVIDIA conseillée (sans NVIDIA : processeur, beaucoup plus lent) | RTX 4060 Ti 8 Go |
| Mémoire graphique | 4 Go conseillés | 8 Go |
| DaVinci Resolve | 21.x gratuit | 21.1.1 |
| Python | 3.12 exactement | 3.12.10 |
| Espace disque | environ 6 Go | |

## Fonctionnalités

- Transcription de **toute la timeline** ou de la **sélection I / O**
- Découpage : **bloc complet**, **phrase par phrase**, **mot par mot**
- **Sous-titres simples** (piste de sous-titres) ou **titres animés** (piste vidéo 2 « Sous-titres »)
- **Styles en un clic** : Rebond karaoké, Rebond mot à mot, Bulle, Néon, Glissement, Élégant
- Réglages : police (affichée dans sa propre police), taille, contour, animation (fondu, pop,
  rebond, glissement), entrée / sortie, karaoké avec couleur au choix
- **23 langues**, dont japonais, chinois, coréen (police adaptée automatiquement)
- Création d'un simple fichier `.srt` depuis n'importe quelle vidéo

## Installation

1. Installe [Python 3.12](https://www.python.org/downloads/) (coche « py launcher »).
2. Double-clique sur **`Installer.bat`** dans ce dossier (environ 2 Go à télécharger).
3. Redémarre DaVinci Resolve s'il était ouvert.

Tout est installé dans `%LOCALAPPDATA%\farfascript` ; ce dossier peut ensuite être supprimé.

## Utilisation

1. Dans DaVinci : **Espace de travail > Scripts > farfascript**.
   Rien ne s'affiche dans DaVinci (le pont tourne en arrière-plan) : l'application farfascript
   s'ouvre toute seule. À relancer une fois par session de DaVinci.
2. Choisis le découpage, la langue, le type (simples ou animés) et un style.
3. Clique sur le gros bouton bleu. Le 1er lancement télécharge le modèle Whisper (environ 3 Go).

## Bon à savoir

- Titres animés et sous-titres simples ne vont pas sur la même piste (règle de DaVinci : les
  titres animés sont des titres Fusion, donc sur une piste vidéo).
- « Remplacer les anciens sous-titres » n'efface que les titres créés par farfascript.
- Un petit programme invisible se lance avec Windows pour ouvrir l'application quand tu lances
  le script dans DaVinci. Il est retiré par la désinstallation.

## Dépannage

| Problème | Solution |
|---|---|
| « Pont DaVinci non lancé » | Espace de travail > Scripts > farfascript |
| farfascript absent du menu Scripts | Redémarre DaVinci après l'installation |
| Texte en carrés vides | Choisis une police qui contient les caractères de la langue |
| Karaoké en arabe / hébreu | Affichage de droite à gauche non garanti |

## Désinstallation

Double-clique sur **`Desinstaller.bat`** (ne touche pas à farfamask).

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.pyw` | Application |
| `farfascript.lua` | Script du menu DaVinci = pont résident (échange par fichiers avec l'application) |
| `bridge.py` | Client du pont côté application |
| `transcribe.py` | Transcription Whisper (faster-whisper) |
| `watcher.pyw` | Ouvre l'application quand le script démarre |
| `caption-bin.drb` | Modèle de titres animés d'AutoSubs (MIT) |
