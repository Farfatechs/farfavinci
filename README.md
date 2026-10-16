# farfavinci

**Sous-titres automatiques et masque IA pour DaVinci Resolve — version gratuite.**

Les fonctions « Transcription automatique » et « Magic Mask » de DaVinci sont réservées à la
version Studio (payante). farfavinci les apporte à la version gratuite, en tournant
**entièrement sur ton PC** grâce à ta carte graphique NVIDIA.

---

## ⚠️ Configuration requise

| | Minimum | Testé |
|---|---|---|
| **Système** | Windows 10 ou 11 (64 bits) | Windows 11 Pro |
| **Carte graphique** | **NVIDIA uniquement** (CUDA), RTX série 20 ou plus récente conseillée | RTX 4060 Ti 8 Go |
| **Mémoire graphique (VRAM)** | 6 Go conseillés | 8 Go |
| **Pilote NVIDIA** | récent (2024 ou plus) | 617.42 |
| **DaVinci Resolve** | 21.x gratuit | 21.1.1 |
| **Python** | 3.12 exactement | 3.12.10 |
| **Espace disque** | environ 12 Go | 11 Go |
| **Internet** | pour l'installation et le 1er lancement (téléchargement des modèles) | |

**Pas de carte NVIDIA (AMD, Intel, Mac) ?**
- Les **sous-titres** fonctionnent quand même, sur le processeur, mais beaucoup plus lentement.
- Le **masque IA ne fonctionne pas** : il n'est pas installé.

Mac et Linux ne sont pas pris en charge.

---

## Fonctionnalités

### Sous-titres automatiques (Whisper large-v3)
- Transcription de **toute la timeline** ou seulement de la **sélection I / O**
- Découpage : **bloc complet**, **phrase par phrase**, **mot par mot**
- **Sous-titres simples** (piste de sous-titres) ou **titres animés** (piste vidéo 2)
- **Styles en un clic** : Rebond karaoké, Rebond mot à mot, Bulle, Néon, Glissement, Élégant
- Réglages : police (affichée dans sa propre police), taille, contour, animation
  (fondu, pop, rebond, glissement), entrée / sortie, karaoké avec couleur au choix
- **23 langues** : français, anglais, espagnol, allemand, italien, portugais, japonais, chinois,
  coréen, arabe, russe… (police adaptée automatiquement pour le japonais, le chinois, le coréen)
- Export d'un simple fichier `.srt` depuis n'importe quelle vidéo

### Masque IA (SAM 2 de Meta)
- Sélection du sujet **au clic** (garder / exclure) ou **en l'encadrant** (cliquer-glisser)
- Aperçu instantané, suivi sur **tout le clip** ou la **sélection I / O**
- Résultat importé dans DaVinci (bin « Masques IA ») :
  - **sujet détouré** avec transparence (ProRes 4444), posé sur une piste « Détourage »
  - **cache noir et blanc** (ProRes 422) à utiliser dans la page **Color**

---

## Installation

1. **Installe Python 3.12** depuis [python.org](https://www.python.org/downloads/)
   (pendant l'installation, laisse cochée l'option **« py launcher »**).
2. **Télécharge farfavinci** : bouton vert **Code > Download ZIP** en haut de cette page,
   puis extrais le ZIP où tu veux.
3. **Double-clique sur `Installer.bat`**.
   L'installation vérifie ta configuration, puis télécharge environ 5 Go (10 à 30 minutes
   selon ta connexion).
4. **Redémarre DaVinci Resolve** s'il était ouvert.

Le dossier extrait peut être supprimé après l'installation : tout est copié dans
`%LOCALAPPDATA%\farfavinci`.

---

## Utilisation

1. Dans DaVinci, ouvre ton projet et ta timeline.
2. Menu **Espace de travail > Scripts > farfavinci**.
   Rien ne s'affiche dans DaVinci : c'est normal, le pont tourne en arrière-plan.
   L'application **farfavinci** s'ouvre toute seule.
3. Le voyant vert en haut à droite indique que DaVinci est connecté.

À relancer **une fois par session** de DaVinci.

### Sous-titres
Onglet **Sous-titres** : choisis le découpage, la langue, le type (simples ou animés) et un style,
puis clique sur le gros bouton bleu. Le 1er lancement télécharge le modèle Whisper (environ 3 Go).

### Masque IA
1. Onglet **Masque IA**.
2. Dans DaVinci, place la tête de lecture sur un clip, puis **Récupérer le clip**.
3. Clique sur le sujet (ou encadre-le). Clic droit pour exclure une zone.
4. **Suivre le sujet et créer le masque**.
5. Dans la page **Color**, utilise le clip « …_cache » du bin « Masques IA » comme cache externe.

Conseil : commence par des clips courts (quelques secondes) pour te faire la main.

---

## Bon à savoir

- **100 % local** : aucune image ni aucun son n'est envoyé sur Internet. Seuls les modèles d'IA
  sont téléchargés (depuis Hugging Face) au premier usage.
- Un petit programme invisible se lance avec Windows pour ouvrir l'application quand tu démarres
  le pont dans DaVinci. Il est retiré par la désinstallation.
- **Titres animés et sous-titres simples ne vont pas sur la même piste** : c'est une règle de
  DaVinci (les titres animés sont des titres Fusion, donc sur une piste vidéo).
- Les fichiers ProRes du masque sont volumineux : pense à vider
  `%LOCALAPPDATA%\farfavinci\work` de temps en temps.

## Limites connues

- Le masque est moins précis que le Magic Mask de Studio sur les cheveux fins et le flou de mouvement.
- Karaoké en arabe / hébreu (écriture de droite à gauche) : affichage non garanti.
- Nom d'utilisateur Windows avec accents ou caractères spéciaux : le pont peut ne pas trouver ses
  fichiers (non testé).
- Clips avec changement de vitesse : le masque ne suit pas la vitesse modifiée.

## Dépannage

| Problème | Solution |
|---|---|
| « Pont DaVinci non lancé » | Espace de travail > Scripts > farfavinci, une fois par session |
| « farfavinci » absent du menu Scripts | Redémarre DaVinci après l'installation |
| Texte en carrés vides | Choisis une police qui contient les caractères de la langue |
| Les sous-titres ne changent pas après une 2e génération | Coche « Remplacer les anciens sous-titres » |
| Le masque IA ne démarre pas | Voir `%LOCALAPPDATA%\farfavinci\work\masque_journal.txt` |

## Désinstallation

Double-clique sur **`Desinstaller.bat`** : supprime l'application, le pont, le raccourci, le
démarrage automatique et les modèles d'IA téléchargés.

---

## Comment ça marche

DaVinci gratuit interdit aux programmes extérieurs de piloter la timeline. Un petit script Lua
résident (`farfavinci.lua`) tourne **dans** DaVinci et échange avec l'application par fichiers :
les demandes arrivent via `request.lua`, les réponses repartent via `Fusion.prefs`.

| Fichier | Rôle |
|---|---|
| `app.pyw` | Application (CustomTkinter) |
| `farfavinci.lua` | Pont résident dans DaVinci |
| `bridge.py` | Client du pont côté application |
| `transcribe.py` | Transcription Whisper (faster-whisper, GPU) |
| `mask.py` / `masque_ui.py` | Moteur SAM 2 / onglet Masque IA |
| `watcher.pyw` | Ouvre l'application quand le pont démarre |
| `installer.ps1` / `desinstaller.ps1` | Installation / désinstallation |

## Licence

farfavinci est un logiciel **open source** sous **licence MIT** (voir `LICENSE`).
Tu peux l'utiliser, le modifier, y ajouter des fonctions et partager ta version, même
dans un projet commercial, à une seule condition : **garder le fichier `LICENSE`** (et donc la
mention de l'auteur d'origine) dans ta copie.

Le logiciel est fourni « tel quel », sans garantie.

## Contribuer

Les améliorations sont les bienvenues !
- **Signaler un bug ou proposer une idée** : onglet **Issues** de cette page.
- **Proposer du code** : fais un *fork* du dépôt, modifie-le, puis ouvre une *pull request*.
  Décris ce que tu as changé et comment tu l'as testé.
- Le code et les commentaires sont en français ; garde ce style pour rester cohérent.

## Crédits

- Modèle de titres animés (`caption-bin.drb`) et principe du pont :
  [AutoSubs](https://github.com/tmoroney/auto-subs) de Tom Moroney, licence MIT (voir `NOTICE-AutoSubs.txt`)
- Transcription : [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT),
  modèle [Whisper](https://github.com/openai/whisper) d'OpenAI (MIT)
- Masque : [SAM 2](https://github.com/facebookresearch/sam2) de Meta (Apache 2.0)
- Interface : [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) (MIT)
