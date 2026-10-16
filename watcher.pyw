"""Surveillant discret : ouvre la fenêtre farfavinci quand un script du menu DaVinci démarre le pont.

Le pont écrit ATStart = "jeton|mode" dans Fusion.prefs ; mode = soustitres, masque ou tout.
"""
import glob
import os
import re
import subprocess
import time

DOSSIER = os.path.dirname(os.path.abspath(__file__))
PYTHONW = os.path.join(DOSSIER, "venv", "Scripts", "pythonw.exe")
APP = os.path.join(DOSSIER, "app.pyw")
PREFS_GLOB = os.path.join(os.environ.get("APPDATA", ""), "Blackmagic Design", "DaVinci Resolve",
                          "Support", "Fusion", "Profiles", "*", "Fusion.prefs")
MODES = {"soustitres", "masque", "tout"}


def signal():
    fichiers = glob.glob(PREFS_GLOB)
    if not fichiers:
        return None
    f = max(fichiers, key=os.path.getmtime)
    try:
        with open(f, "rb") as h:
            m = re.findall(rb'ATStart = "([^"]*)"', h.read())
        return m[-1].decode("latin-1") if m else None
    except OSError:
        return None


def main():
    # Mutex simple : une seule instance du surveillant
    import socket
    verrou = socket.socket()
    try:
        verrou.bind(("127.0.0.1", 47814))
    except OSError:
        return
    dernier = signal()
    while True:
        time.sleep(1)
        valeur = signal()
        if valeur and valeur != dernier:
            dernier = valeur
            mode = valeur.rsplit("|", 1)[-1] if "|" in valeur else "tout"
            if mode not in MODES:
                mode = "tout"
            subprocess.Popen([PYTHONW, APP, "--mode", mode], cwd=DOSSIER)


main()
