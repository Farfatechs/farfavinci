"""farfamask - masque IA pour DaVinci Resolve gratuit (SAM 2 sur GPU)."""
import os
import sys
import threading
import time
from tkinter import messagebox

import customtkinter as ctk

DOSSIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOSSIER)
PYTHON = os.path.join(DOSSIER, "venv", "Scripts", "python.exe")

# Palette noir / bleu (identique à farfascript)
FOND = "#07090f"
CARTE = "#0e131d"
BORD = "#1c2536"
CHAMP = "#141b28"
TEXTE = "#e6ecf7"
DOUX = "#7d8aa5"
ACCENT = "#2f7cff"
ACCENT_SURVOL = "#4d90ff"
OK = "#3ddc84"
ERREUR = "#ff5470"


def police(taille, gras=False):
    return ctk.CTkFont(family="Segoe UI", size=taille, weight="bold" if gras else "normal")


class Carte(ctk.CTkFrame):
    def __init__(self, parent, titre=None, **kw):
        super().__init__(parent, fg_color=CARTE, corner_radius=14, border_width=1,
                         border_color=BORD, **kw)
        if titre:
            ctk.CTkLabel(self, text=titre.upper(), font=police(11, True),
                         text_color=DOUX).pack(anchor="w", padx=18, pady=(14, 6))


def interrupteur(parent, texte, variable):
    sw = ctk.CTkSwitch(parent, text=texte, variable=variable, onvalue=True, offvalue=False,
                       font=police(13), text_color=TEXTE, progress_color=ACCENT,
                       button_color=TEXTE, button_hover_color="#ffffff", fg_color=BORD)
    sw.select() if variable.get() else sw.deselect()
    return sw


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=FOND)
        ctk.set_appearance_mode("dark")
        self.title("farfamask")
        icone = os.path.join(DOSSIER, "icon.ico")
        if os.path.exists(icone):
            # CustomTkinter remet son icône après le démarrage : on repasse derrière
            self.after(250, lambda: self.iconbitmap(icone))
        # hauteur adaptée à l'écran (barre des tâches comprise)
        self.geometry(f"600x{min(820, self.winfo_screenheight() - 120)}")
        self.minsize(580, 480)
        self.occupe_flag = False

        # --- En-tête -----------------------------------------------------------
        tete = ctk.CTkFrame(self, fg_color="transparent")
        tete.pack(fill="x", padx=20, pady=(16, 0))
        gauche = ctk.CTkFrame(tete, fg_color="transparent")
        gauche.pack(side="left")
        ctk.CTkLabel(gauche, text="farfamask", font=police(26, True),
                     text_color=TEXTE).pack(anchor="w")
        ctk.CTkLabel(gauche, text="Masque IA  ·  local  ·  GPU", font=police(12),
                     text_color=DOUX).pack(anchor="w")
        pastille = ctk.CTkFrame(tete, fg_color=CHAMP, corner_radius=20)
        pastille.pack(side="right", pady=6)
        self.point = ctk.CTkLabel(pastille, text="●", font=police(13), text_color=DOUX)
        self.point.pack(side="left", padx=(12, 4), pady=5)
        self.etat_pont = ctk.CTkLabel(pastille, text="Recherche de DaVinci…",
                                      font=police(12), text_color=DOUX)
        self.etat_pont.pack(side="left", padx=(0, 14))

        # --- Action + progression : collé en bas, emballé avant le contenu pour
        # rester visible même si la fenêtre est plus petite que le contenu -------
        bas = ctk.CTkFrame(self, fg_color=FOND)
        bas.pack(side="bottom", fill="x", padx=20, pady=(8, 16))
        self.bouton = ctk.CTkButton(
            bas, text="Suivre le sujet et créer le masque", height=50, corner_radius=12,
            font=police(16, True), fg_color=ACCENT, hover_color=ACCENT_SURVOL,
            text_color="#ffffff", command=self.lancer)
        self.bouton.pack(fill="x", pady=(0, 12))
        self.barre = ctk.CTkProgressBar(bas, height=6, corner_radius=3,
                                        fg_color=CHAMP, progress_color=ACCENT)
        self.barre.set(0)
        self.barre.pack(fill="x")
        self.statut = ctk.CTkLabel(bas, text="Prêt.", font=police(12), text_color=DOUX,
                                   wraplength=540, justify="left", anchor="w")
        self.statut.pack(fill="x", pady=(8, 0))

        # --- Contenu : la page du masque (défilante) --------------------------------
        import masque_ui
        self.page_masque = masque_ui.PageMasque(self, self, globals())
        self.page_masque.pack(fill="both", expand=True, padx=12, pady=(10, 0))

        threading.Thread(target=self.surveiller_pont, daemon=True).start()

    # -- utilitaires utilisés par la page du masque -----------------------------------
    def msg(self, texte, pct=None, couleur=DOUX):
        def f():
            self.statut.configure(text=texte, text_color=couleur)
            if pct is not None:
                self.barre.set(pct / 100)
        self.after(0, f)

    def occupe(self, oui):
        self.occupe_flag = oui
        self.after(0, lambda: self.bouton.configure(
            state="disabled" if oui else "normal",
            fg_color=BORD if oui else ACCENT))

    def pont(self, connecte, texte):
        self.after(0, lambda: (self.point.configure(text_color=OK if connecte else DOUX),
                               self.etat_pont.configure(text=texte,
                                                        text_color=TEXTE if connecte else DOUX)))

    def surveiller_pont(self):
        import bridge
        while True:
            if not self.occupe_flag:
                try:
                    info = bridge.envoyer("ping", timeout=6)
                    self.pont(True, f"{info.get('timeline')}  ·  {info.get('fps')} i/s")
                except Exception:
                    self.pont(False, "Pont DaVinci non lancé")
            time.sleep(5)

    def lancer(self):
        self.page_masque.lancer()


def deja_ouverte(port):
    """Une seule fenêtre : si le port est pris, l'application tourne déjà."""
    import socket
    global _verrou
    _verrou = socket.socket()
    try:
        _verrou.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True


if __name__ == "__main__":
    if deja_ouverte(47824):
        sys.exit(0)
    if not os.path.exists(PYTHON):
        messagebox.showerror("farfamask", "Installation manquante : lance Installer.bat")
        sys.exit(1)
    try:  # icône propre dans la barre des tâches (au lieu de celle de Python)
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Farfatechs.farfamask")
    except Exception:
        pass
    App().mainloop()
