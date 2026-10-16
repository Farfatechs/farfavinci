"""Surveillant discret : ouvre l'application quand le pont DaVinci démarre."""
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
        return None, None
    f = max(fichiers, key=os.path.getmtime)
    try:
        mtime = os.path.getmtime(f)
        with open(f, "rb") as h:
            m = re.findall(rb'ATStart = "([^"]*)"', h.read())
        return mtime, (m[-1] if m else None)
    except OSError:
        return None, None


def main():
    # Mutex simple : une seule instance du surveillant
    import socket
    verrou = socket.socket()
    try:
        verrou.bind(("127.0.0.1", 47814))
    except OSError:
        return
    _, dernier = signal()
    while True:
        time.sleep(2)
        _, valeur = signal()
        if valeur and valeur != dernier:
            dernier = valeur
            subprocess.Popen([PYTHONW, APP], cwd=DOSSIER)


main()
