"""Page « Masque IA » de farfamask : sélection d'un sujet au clic, suivi SAM 2, retour dans DaVinci."""
import json
import os
import queue
import subprocess
import threading
import time
import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

DOSSIER = os.path.dirname(os.path.abspath(__file__))
PYTHON_MASQUE = os.path.join(DOSSIER, "venv", "Scripts", "python.exe")
SCRIPT_MASQUE = os.path.join(DOSSIER, "mask.py")
TRAVAIL = os.path.join(DOSSIER, "work")
TOILE_L, TOILE_H = 556, 313


class MoteurMasque:
    """Processus SAM 2 permanent (garde le modèle en mémoire graphique)."""

    def __init__(self, sur_progres):
        os.makedirs(TRAVAIL, exist_ok=True)
        self.sur_progres = sur_progres
        self.reponses = queue.Queue()
        self.journal = open(os.path.join(TRAVAIL, "masque_journal.txt"), "w", encoding="utf-8")
        env = dict(os.environ, HF_HUB_DISABLE_SYMLINKS_WARNING="1", PYTHONIOENCODING="utf-8")
        self.p = subprocess.Popen(
            [PYTHON_MASQUE, SCRIPT_MASQUE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.journal, text=True, encoding="utf-8", errors="replace", env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.pret = threading.Event()
        threading.Thread(target=self._lire, daemon=True).start()

    def _lire(self):
        for ligne in self.p.stdout:
            if not ligne.startswith("@"):
                continue
            d = json.loads(ligne[1:])
            if d.get("etat") == "pret":
                self.pret.set()
            elif "progres" in d or "etat" in d:
                self.sur_progres(d)
            else:
                self.reponses.put(d)
        self.reponses.put({"ok": False, "erreur": "Le moteur de masque s'est arrêté "
                                                  "(voir work/masque_journal.txt)"})
        self.pret.set()

    def vivant(self):
        return self.p.poll() is None

    def requete(self, cmd, **kw):
        self.pret.wait()
        if not self.vivant():
            raise RuntimeError("Le moteur de masque ne tourne pas (voir work/masque_journal.txt)")
        self.p.stdin.write(json.dumps({"cmd": cmd, **kw}) + "\n")
        self.p.stdin.flush()
        d = self.reponses.get()
        if not d.get("ok"):
            raise RuntimeError(d.get("erreur", "erreur inconnue"))
        return d


class PageMasque(ctk.CTkScrollableFrame):
    def __init__(self, parent, app, ui):
        super().__init__(parent, fg_color="transparent", scrollbar_button_color=ui["BORD"],
                         scrollbar_button_hover_color=ui["ACCENT"])
        self.app, self.ui = app, ui
        self.moteur = None
        self.clip = None          # infos du clip DaVinci + dimensions
        self.points = []          # [x, y, 1 garder / 0 exclure] en pixels d'origine
        self.boite = None         # cadre [x0, y0, x1, y1] en pixels d'origine
        self.depart = None        # début du cliquer-glisser (pixels de la toile)
        self.image_k = 0
        self.photo = None
        self.apercu_en_cours = False
        self.poser = ctk.BooleanVar(value=True)
        self.selection = ctk.BooleanVar(value=False)
        U = ui

        c1 = U["Carte"](self, "Clip")
        c1.pack(fill="x", padx=8, pady=(8, 12))
        l = ctk.CTkFrame(c1, fg_color="transparent")
        l.pack(fill="x", padx=18, pady=(0, 6))
        self.b_clip = ctk.CTkButton(
            l, text="Récupérer les clips sélectionnés", height=36,
            font=U["police"](13, True), fg_color=U["BORD"], hover_color="#26324a",
            command=self.recuperer)
        self.b_clip.pack(side="left")
        self.info = ctk.CTkLabel(c1, text="Sélectionne un ou plusieurs clips sur la timeline : "
                                          "ils formeront un seul masque.",
                                 font=U["police"](12), text_color=U["DOUX"], anchor="w",
                                 justify="left", wraplength=520)
        self.info.pack(fill="x", padx=18)
        U["interrupteur"](c1, "Seulement la sélection (points I / O)",
                          self.selection).pack(anchor="w", padx=18, pady=(8, 2))
        U["interrupteur"](c1, "Poser le sujet détouré sur la timeline (piste vidéo 2 « Détourage »)",
                          self.poser).pack(anchor="w", padx=18, pady=(2, 14))

        c2 = U["Carte"](self, "Sélection du sujet")
        c2.pack(fill="x", padx=8)
        self.toile = tk.Canvas(c2, width=TOILE_L, height=TOILE_H, bg=U["CHAMP"],
                               highlightthickness=0, cursor="crosshair")
        self.toile.pack(padx=18)
        self.toile.create_text(TOILE_L // 2, TOILE_H // 2, fill=U["DOUX"],
                               text="L'image du clip s'affichera ici", font=("Segoe UI", 12))
        # clic gauche : point (clic simple) ou cadre (cliquer-glisser) ; clic droit : exclure
        self.toile.bind("<ButtonPress-1>", self.appui)
        self.toile.bind("<B1-Motion>", self.glisser)
        self.toile.bind("<ButtonRelease-1>", self.relache)
        self.toile.bind("<Button-3>", lambda e: self.clic(e, 0))

        l2 = ctk.CTkFrame(c2, fg_color="transparent")
        l2.pack(fill="x", padx=18, pady=(10, 0))
        self.curseur = ctk.CTkSlider(l2, from_=0, to=1, number_of_steps=1,
                                     progress_color=U["ACCENT"], button_color=U["TEXTE"],
                                     fg_color=U["BORD"], command=self.deplacer, state="disabled")
        self.curseur.pack(side="left", fill="x", expand=True)
        self.l_image = ctk.CTkLabel(l2, text="", width=110, font=U["police"](12),
                                    text_color=U["DOUX"])
        self.l_image.pack(side="right")

        l3 = ctk.CTkFrame(c2, fg_color="transparent")
        l3.pack(fill="x", padx=18, pady=(6, 14))
        ctk.CTkLabel(l3, text="Clic : garder  ·  Glisser : encadrer  ·  Clic droit : exclure",
                     font=U["police"](12), text_color=U["DOUX"]).pack(side="left")
        ctk.CTkButton(l3, text="Effacer les points", width=130, height=30,
                      font=U["police"](12), fg_color=U["BORD"], hover_color="#26324a",
                      command=self.effacer).pack(side="right")

    # -- moteur ---------------------------------------------------------------------
    def progres(self, d):
        if "progres" in d:
            etape = {"chargement": "Préparation des images", "suivi": "Suivi du sujet",
                     "écriture": "Écriture des masques"}.get(d.get("etape"), d.get("etape", ""))
            self.app.msg(f"{etape}  ·  {d['progres']} %", d["progres"])
        elif "etat" in d:
            self.app.msg("IA de masque : " + d["etat"] + "… (le 1er lancement télécharge le modèle)")

    def moteur_pret(self):
        if not os.path.exists(PYTHON_MASQUE):
            raise RuntimeError("Le module de masque n'est pas installé (relance Installer.bat)")
        if self.moteur is None or not self.moteur.vivant():
            self.app.msg("Démarrage de l'IA de masque…")
            self.moteur = MoteurMasque(self.progres)
        return self.moteur

    # -- clip -------------------------------------------------------------------------
    def recuperer(self):
        self.app.occupe(True)
        self.b_clip.configure(state="disabled")
        threading.Thread(target=self._recuperer, daemon=True).start()

    def _recuperer(self):
        import bridge
        try:
            info = bridge.envoyer("clip_courant",
                                  range="inout" if self.selection.get() else "all")
            moteur = self.moteur_pret()
            dossier = os.path.join(TRAVAIL, f"masque_{int(time.time())}")
            os.makedirs(dossier, exist_ok=True)
            self.app.msg("Préparation des images du clip…", 0)
            # clips sélectionnés mis bout à bout (sans fichier = trou entre deux clips)
            segments = []
            for i in range(1, int(info["nb_segments"]) + 1):
                k = f"seg{i}_"
                seg = {"nb": int(info[k + "duree"])}
                if info.get(k + "fichier"):
                    seg.update(video=info[k + "fichier"], debut=int(info[k + "source_debut"]))
                segments.append(seg)
            res = moteur.requete("charger", segments=segments, dossier=dossier)
            info.update(n=res["n"], w=res["w"], h=res["h"], proxy=res["proxy"], dossier=dossier)
            self.clip = info
            k = min(max(0, int(float(info.get("tete", 0)))), res["n"] - 1)
            self.after(0, lambda: self._clip_pret(k))
            self.app.msg("Clique sur le sujet à sélectionner.", 0)
        except Exception as e:
            self.app.msg("Erreur : " + str(e), couleur=self.ui["ERREUR"])
        self.app.occupe(False)
        self.after(0, lambda: self.b_clip.configure(state="normal"))

    def _clip_pret(self, k):
        c = self.clip
        nb = int(c.get("nb_clips", 1))
        nom = c["nom"] if nb == 1 else f"{nb} clips réunis"
        if c.get("origine") == "tête de lecture":
            nom += " (aucune sélection : clip sous la tête de lecture)"
        plage = "   ·   points I / O" if self.selection.get() else ""
        self.info.configure(text=f"{nom}   ·   {c['w']}×{c['h']}   ·   {c['n']} images{plage}",
                            text_color=self.ui["TEXTE"])
        self.curseur.configure(state="normal", from_=0, to=max(1, c["n"] - 1),
                               number_of_steps=max(1, c["n"] - 1))
        self.curseur.set(k)
        self.points = []
        self.boite = None
        self.afficher(k)

    # -- affichage -------------------------------------------------------------------------
    def echelle(self):
        c = self.clip
        s = min(TOILE_L / c["w"], TOILE_H / c["h"])
        return s, (TOILE_L - c["w"] * s) / 2, (TOILE_H - c["h"] * s) / 2

    def afficher(self, k, chemin=None):
        self.image_k = k
        c = self.clip
        chemin = chemin or os.path.join(c["proxy"], f"{k:05d}.jpg")
        s, ox, oy = self.echelle()
        img = Image.open(chemin).resize((round(c["w"] * s), round(c["h"] * s)), Image.BILINEAR)
        self.photo = ImageTk.PhotoImage(img)
        t = self.toile
        t.delete("all")
        t.create_image(ox, oy, image=self.photo, anchor="nw")
        for x, y, lab in self.points:
            px, py = ox + x * s, oy + y * s
            couleur = "#3ddc84" if lab else "#ff5470"
            t.create_oval(px - 6, py - 6, px + 6, py + 6, fill=couleur, outline="white", width=2)
        if self.boite:
            x0, y0, x1, y1 = self.boite
            t.create_rectangle(ox + x0 * s, oy + y0 * s, ox + x1 * s, oy + y1 * s,
                               outline=self.ui["ACCENT_SURVOL"], width=2, dash=(6, 3))
        self.l_image.configure(text=f"Image {k + 1} / {c['n']}")

    def deplacer(self, v):
        if not self.clip:
            return
        k = int(round(v))
        if k != self.image_k:
            self.points = []  # points et cadre valent pour une image précise
            self.boite = None
            self.afficher(k)

    def effacer(self):
        if self.clip:
            self.points = []
            self.boite = None
            self.afficher(self.image_k)

    def vers_image(self, cx, cy):
        """Pixels de la toile -> pixels de l'image d'origine (bornés)."""
        s, ox, oy = self.echelle()
        x = min(max((cx - ox) / s, 0), self.clip["w"] - 1)
        y = min(max((cy - oy) / s, 0), self.clip["h"] - 1)
        return round(x, 1), round(y, 1)

    def appui(self, e):
        if self.clip and not self.app.occupe_flag:
            self.depart = (e.x, e.y)

    def glisser(self, e):
        if not self.depart:
            return
        self.toile.delete("cadre")
        self.toile.create_rectangle(*self.depart, e.x, e.y, outline=self.ui["ACCENT_SURVOL"],
                                    width=2, dash=(6, 3), tags="cadre")

    def relache(self, e):
        if not self.depart:
            return
        x0, y0 = self.depart
        self.depart = None
        if abs(e.x - x0) < 8 and abs(e.y - y0) < 8:
            self.clic(e, 1)  # mouvement minuscule : c'est un clic
            return
        a, b = self.vers_image(min(x0, e.x), min(y0, e.y))
        c, d = self.vers_image(max(x0, e.x), max(y0, e.y))
        self.boite = [a, b, c, d]
        self.mettre_a_jour()

    def clic(self, e, label):
        if not self.clip or self.app.occupe_flag:
            return
        s, ox, oy = self.echelle()
        x, y = (e.x - ox) / s, (e.y - oy) / s
        if not (0 <= x < self.clip["w"] and 0 <= y < self.clip["h"]):
            return
        self.points.append([round(x, 1), round(y, 1), label])
        self.mettre_a_jour()

    def mettre_a_jour(self):
        self.afficher(self.image_k)
        if not self.apercu_en_cours:
            self.apercu_en_cours = True
            threading.Thread(target=self._apercu, daemon=True).start()

    def _apercu(self):
        try:
            while True:
                pts, boite = list(self.points), self.boite
                k = self.image_k
                if not pts and not boite:
                    break
                res = self.moteur.requete("apercu", frame=k, points=pts, boite=boite)
                if pts == self.points and boite == self.boite and k == self.image_k:
                    self.after(0, lambda: self.afficher(k, res["image"]))
                    break
                if not self.points and not self.boite:
                    break  # sélection effacée entre-temps
        except Exception as e:
            self.app.msg("Erreur aperçu : " + str(e), couleur=self.ui["ERREUR"])
        self.apercu_en_cours = False

    # -- suivi + retour dans DaVinci ------------------------------------------------------
    def lancer(self):
        if not self.clip:
            self.app.msg("Récupère d'abord un clip.", couleur=self.ui["ERREUR"])
            return
        if not self.boite and not any(p[2] == 1 for p in self.points):
            self.app.msg("Clique sur le sujet ou encadre-le (cliquer-glisser).",
                         couleur=self.ui["ERREUR"])
            return
        self.app.occupe(True)
        threading.Thread(target=self._suivre, daemon=True).start()

    def _suivre(self):
        import bridge
        c = self.clip
        try:
            self.app.msg("Suivi du sujet…", 0)
            res = self.moteur.requete("propager", frame=self.image_k, points=self.points,
                                      boite=self.boite,
                                      sortie=os.path.join(c["dossier"], "sortie"))
            self.app.msg("Import dans DaVinci…", 99)
            r = bridge.envoyer("add_mask", timeout=300, detourage=res["detourage"],
                               cache=res["cache"], n=str(res["n"]), debut=c["debut"],
                               poser="1" if self.poser.get() else "0")
            texte = "Terminé  ·  détourage + cache dans le bin « Masques IA »"
            if r.get("pose") == "true":
                texte += f", sujet posé sur la piste vidéo {r.get('piste')} « Détourage »"
            self.app.msg(texte, 100, self.ui["OK"])
        except Exception as e:
            self.app.msg("Erreur : " + str(e), couleur=self.ui["ERREUR"])
        self.app.occupe(False)
