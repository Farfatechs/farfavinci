"""Client du pont DaVinci : envoie des demandes au script Lua résident et lit les réponses."""
import base64
import glob
import os
import re
import threading
import time

DOSSIER = os.path.join(os.environ.get("LOCALAPPDATA", ""), "farfavinci")
MAILBOX = os.path.join(DOSSIER, "bridge")
REQUETE = os.path.join(MAILBOX, "request.lua")
PREFS_GLOB = os.path.join(os.environ.get("APPDATA", ""), "Blackmagic Design", "DaVinci Resolve",
                          "Support", "Fusion", "Profiles", "*", "Fusion.prefs")


class PontErreur(Exception):
    pass


def _prefs():
    fichiers = glob.glob(PREFS_GLOB)
    if not fichiers:
        raise PontErreur("Fusion.prefs introuvable : DaVinci a-t-il déjà été lancé ?")
    return max(fichiers, key=os.path.getmtime)


def _valeur(texte, cle):
    trouve = re.findall(r'\b' + cle + r' = "([^"]*)"', texte)
    return trouve[-1] if trouve else None


def _decoder(b64):
    brut = base64.b64decode(b64)
    try:
        texte = brut.decode("utf-8")
    except UnicodeDecodeError:
        texte = brut.decode("cp1252", errors="replace")
    res = {}
    for ligne in texte.split("\n"):
        if "=" in ligne:
            k, v = ligne.split("=", 1)
            res[k] = v
    return res


_verrou = threading.Lock()


class _VerrouFichier:
    """Verrou partagé entre processus (les fenêtres Sous-titres et Masque IA
    peuvent tourner en même temps, mais un seul request.lua doit exister)."""

    def __enter__(self):
        import msvcrt
        os.makedirs(MAILBOX, exist_ok=True)
        self.f = open(os.path.join(MAILBOX, "verrou"), "a+")
        while True:
            try:
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                return self
            except OSError:
                time.sleep(0.1)

    def __exit__(self, *_):
        import msvcrt
        self.f.seek(0)
        msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
        self.f.close()


def envoyer(cmd, timeout=30, **args):
    """Envoie une commande au pont et renvoie le dictionnaire de réponse."""
    with _verrou, _VerrouFichier():  # une seule demande à la fois (un seul request.lua)
        return _envoyer(cmd, timeout, **args)


def _envoyer(cmd, timeout, **args):
    os.makedirs(MAILBOX, exist_ok=True)
    id_ = str(int(time.time() * 1000))
    corps = [f'id = "{id_}"', f'cmd = "{cmd}"']
    corps += [f"{k} = [==[{v}]==]" for k, v in args.items()]
    tmp = REQUETE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("return { " + ", ".join(corps) + " }")
    os.replace(tmp, REQUETE)

    prefs = _prefs()
    debut = time.time()
    ack = False
    try:
        while True:
            try:
                with open(prefs, "rb") as f:
                    texte = f.read().decode("latin-1")
            except OSError:
                texte = ""
            rep = _valeur(texte, "ATReply")
            if rep and rep.startswith(id_ + ":"):
                res = _decoder(rep[len(id_) + 1:])
                if "erreur" in res:
                    raise PontErreur(res["erreur"])
                return res
            if not ack and _valeur(texte, "ATAck") == id_:
                ack = True
            if not ack and time.time() - debut > 4:
                raise PontErreur(
                    "DaVinci ne répond pas. Lance d'abord le pont : "
                    "Espace de travail > Scripts > farfascript (ou farfamask)")
            if time.time() - debut > timeout:
                raise PontErreur("Délai dépassé en attendant DaVinci.")
            time.sleep(0.2)
    finally:
        try:
            os.remove(REQUETE)
        except OSError:
            pass
