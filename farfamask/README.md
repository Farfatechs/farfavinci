# farfamask — masque IA

Équivalent du Magic Mask pour **DaVinci Resolve gratuit**, avec SAM 2 (Meta) sur ta carte
graphique. Fait partie de [farfavinci](../), mais s'installe et fonctionne **seul**.

## ⚠️ Configuration requise

| | Minimum | Testé |
|---|---|---|
| Système | Windows 10 / 11 (64 bits) | Windows 11 Pro |
| Carte graphique | **NVIDIA obligatoire** (CUDA), RTX série 20 ou plus récente conseillée | RTX 4060 Ti 8 Go |
| Mémoire graphique | 6 Go conseillés | 8 Go |
| Pilote NVIDIA | récent (2024 ou plus) | 617.42 |
| DaVinci Resolve | 21.x gratuit | 21.1.1 |
| Python | 3.12 exactement | 3.12.10 |
| Espace disque | environ 6 Go (+ les vidéos de masque produites) | |

Sans carte NVIDIA, l'installeur s'arrête : farfamask ne peut pas fonctionner.

## Fonctionnalités

- Sélection du sujet **au clic** (garder / exclure) ou **en l'encadrant** (cliquer-glisser)
- Aperçu instantané, choix de l'image de départ
- Suivi sur **tout le clip** ou la **sélection I / O**
- Résultat importé dans DaVinci (bin « Masques IA ») :
  - **sujet détouré** avec transparence (ProRes 4444), posé sur la piste vidéo 2 « Détourage »
  - **cache noir et blanc** (ProRes 422) pour la page **Color**

## Installation

1. Installe [Python 3.12](https://www.python.org/downloads/) (coche « py launcher »).
2. Double-clique sur **`Installer.bat`** dans ce dossier (environ 3 Go à télécharger).
3. Redémarre DaVinci Resolve s'il était ouvert.

Tout est installé dans `%LOCALAPPDATA%\farfamask` ; ce dossier peut ensuite être supprimé.

## Utilisation

1. Dans DaVinci : **Espace de travail > Scripts > farfamask**.
   Rien ne s'affiche dans DaVinci (le pont tourne en arrière-plan) : l'application farfamask
   s'ouvre toute seule. À relancer une fois par session de DaVinci.
2. Place la tête de lecture sur un clip, puis **Récupérer le clip** (option I / O possible).
3. **Clic** sur le sujet pour le garder, **clic droit** pour exclure une zone, ou
   **cliquer-glisser** pour l'encadrer (idéal pour une photo, un écran, un tableau).
4. **Suivre le sujet et créer le masque**.
5. Page **Color** : utilise le clip « …_cache » du bin « Masques IA » comme cache externe.

Conseil : commence par des clips courts (quelques secondes). Le 1er lancement télécharge le
modèle SAM 2 (environ 320 Mo).

## Limites

- Moins précis que le Magic Mask de Studio sur les cheveux fins et le flou de mouvement.
- Clips avec changement de vitesse : le masque ne suit pas la vitesse modifiée.
- Les fichiers ProRes sont volumineux : vide `%LOCALAPPDATA%\farfamask\work` de temps en temps.

## Dépannage

| Problème | Solution |
|---|---|
| « Pont DaVinci non lancé » | Espace de travail > Scripts > farfamask |
| farfamask absent du menu Scripts | Redémarre DaVinci après l'installation |
| Le masque ne démarre pas | Voir `%LOCALAPPDATA%\farfamask\work\masque_journal.txt` |

## Désinstallation

Double-clique sur **`Desinstaller.bat`** (ne touche pas à farfascript).

## Fichiers

| Fichier | Rôle |
|---|---|
| `app.pyw` / `masque_ui.py` | Application et page du masque |
| `farfamask.lua` | Script du menu DaVinci = pont résident (échange par fichiers avec l'application) |
| `bridge.py` | Client du pont côté application |
| `mask.py` | Moteur SAM 2 (processus permanent, garde le modèle en mémoire graphique) |
| `watcher.pyw` | Ouvre l'application quand le script démarre |
