"""Surveillant discret : ouvre farfascript quand le script farfascript démarre le pont dans DaVinci.

Le pont écrit FSStart = "jeton" dans Fusion.prefs ; un nouveau jeton = un nouveau démarrage.
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


def signal():
    fichiers = glob.glob(PREFS_GLOB)
    if not fichiers:
        return None
    f = max(fichiers, key=os.path.getmtime)
    try:
        with open(f, "rb") as h:
            m = re.findall(rb'FSStart = "([^"]*)"', h.read())
        return m[-1] if m else None
    except OSError:
        return None


def main():
    # Mutex simple : une seule instance du surveillant
    import socket
    verrou = socket.socket()
    try:
        verrou.bind(("127.0.0.1", 47821))
    except OSError:
        return
    dernier = signal()
    while True:
        time.sleep(1)
        valeur = signal()
        if valeur and valeur != dernier:
            dernier = valeur
            subprocess.Popen([PYTHONW, APP], cwd=DOSSIER)


main()
