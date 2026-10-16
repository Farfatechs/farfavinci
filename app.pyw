"""farfavinci - application autonome (fonctionne avec DaVinci Resolve gratuit)."""
import json
import os
import subprocess
import sys
import threading
import time
from tkinter import colorchooser, filedialog, font as tkfont, messagebox

import customtkinter as ctk

DOSSIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOSSIER)
PYTHON = os.path.join(DOSSIER, "venv", "Scripts", "python.exe")
TRANSCRIBE = os.path.join(DOSSIER, "transcribe.py")
TRAVAIL = os.path.join(DOSSIER, "work")
LANGUES = {"Français": "fr", "English": "en", "Español": "es", "Deutsch": "de",
           "Italiano": "it", "Português": "pt", "Nederlands": "nl", "Polski": "pl",
           "Svenska": "sv", "Ελληνικά": "el", "Русский": "ru", "Українська": "uk",
           "Türkçe": "tr", "العربية": "ar", "עברית": "he", "हिन्दी": "hi",
           "日本語": "ja", "中文": "zh", "한국어": "ko", "ไทย": "th",
           "Tiếng Việt": "vi", "Bahasa Indonesia": "id", "Détection auto": "auto"}
# Polices Windows qui contiennent les caractères de ces langues
POLICE_LANGUE = {"ja": "Yu Gothic", "zh": "Microsoft YaHei", "ko": "Malgun Gothic",
                 "th": "Leelawadee UI", "hi": "Nirmala UI"}
MODES = {"Bloc complet": "bloc", "Phrase par phrase": "phrase", "Mot par mot": "mot"}
ANIMATIONS = ["Aucune", "Fondu", "Pop", "Rebond", "Glissement"]
SENS = {"Entrée": 0, "Sortie": 1, "Les deux": 2}
KARAOKE = {"Couleur du texte": 0, "Contour": 1, "Lueur": 2, "Bulle": 3}

# Styles prêts à l'emploi : un clic remplit tous les réglages
STYLES = {
    "Rebond karaoké": dict(police="Arial Black", anim="Rebond", sens="Entrée", karaoke=True,
                           kstyle="Couleur du texte", couleur="#2f7cff", affichage="Phrase par phrase",
                           contour=False, par_mot=True),
    "Rebond mot à mot": dict(police="Impact", anim="Rebond", sens="Entrée", karaoke=False,
                             kstyle="Couleur du texte", couleur="#2f7cff", affichage="Mot par mot",
                             contour=False, par_mot=False),
    "Bulle": dict(police="Segoe UI", anim="Pop", sens="Les deux", karaoke=True,
                  kstyle="Bulle", couleur="#2f7cff", affichage="Phrase par phrase",
                  contour=False, par_mot=False),
    "Néon": dict(police="Arial Black", anim="Fondu", sens="Les deux", karaoke=True,
                 kstyle="Lueur", couleur="#00d4ff", affichage="Phrase par phrase",
                 contour=False, par_mot=False),
    "Glissement": dict(police="Bahnschrift", anim="Glissement", sens="Les deux", karaoke=True,
                       kstyle="Couleur du texte", couleur="#ffd23f", affichage="Phrase par phrase",
                       contour=True, par_mot=False),
    "Élégant": dict(police="Georgia", anim="Fondu", sens="Les deux", karaoke=False,
                    kstyle="Couleur du texte", couleur="#2f7cff", affichage="Bloc complet",
                    contour=False, par_mot=False),
}

# Palette noir / bleu
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


def lua_chaine(s):
    """Chaîne longue Lua [==[...]==] avec un niveau qui n'apparaît pas dans s."""
    n = 1
    while ("]" + "=" * n + "]") in s:
        n += 1
    eq = "=" * n
    return f"[{eq}[{s}]{eq}]"


def lua_valeur(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return lua_chaine(str(v))


def ecrire_donnees_lua(chemin, captions, reglages, remplacer, anim="Aucune"):
    morceaux = ["return {", f"remplacer = {lua_valeur(remplacer)},",
                f"anim = {lua_valeur(anim)},", "reglages = {"]
    morceaux += [f"{k} = {lua_valeur(v)}," for k, v in reglages.items()]
    morceaux += ["},", "captions = {"]
    for c in captions:
        mots = ", ".join(f"{{{m['s']}, {m['e']}, {lua_chaine(m['w'])}}}" for m in c["w"])
        morceaux.append(f"{{s = {c['s']}, e = {c['e']}, t = {lua_chaine(c['t'])}, w = {{{mots}}}}},")
    morceaux.append("}}")
    with open(chemin, "w", encoding="utf-8") as f:
        f.write("\n".join(morceaux))


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class Carte(ctk.CTkFrame):
    def __init__(self, parent, titre=None, **kw):
        super().__init__(parent, fg_color=CARTE, corner_radius=14, border_width=1,
                         border_color=BORD, **kw)
        if titre:
            ctk.CTkLabel(self, text=titre.upper(), font=police(11, True),
                         text_color=DOUX).pack(anchor="w", padx=18, pady=(14, 6))


def segment(parent, valeurs, variable, command=None, accent=True, hauteur=34):
    return ctk.CTkSegmentedButton(
        parent, values=valeurs, variable=variable, command=command, font=police(13),
        height=hauteur, fg_color=CHAMP, unselected_color=CHAMP, unselected_hover_color=BORD,
        selected_color=ACCENT if accent else BORD,
        selected_hover_color=ACCENT_SURVOL if accent else BORD)


def menu(parent, valeurs, variable, largeur=170):
    return ctk.CTkOptionMenu(
        parent, values=valeurs, variable=variable, width=largeur, height=32, font=police(13),
        fg_color=CHAMP, button_color=BORD, button_hover_color=ACCENT,
        dropdown_fg_color=CARTE, dropdown_hover_color=BORD)


def interrupteur(parent, texte, variable):
    sw = ctk.CTkSwitch(parent, text=texte, variable=variable, onvalue=True, offvalue=False,
                       font=police(13), text_color=TEXTE, progress_color=ACCENT,
                       button_color=TEXTE, button_hover_color="#ffffff", fg_color=BORD)
    sw.select() if variable.get() else sw.deselect()
    return sw


def ligne_reglage(parent, libelle):
    l = ctk.CTkFrame(parent, fg_color="transparent")
    l.pack(fill="x", padx=18, pady=4)
    ctk.CTkLabel(l, text=libelle, font=police(13), text_color=TEXTE).pack(side="left")
    return l


class FenetrePolices(ctk.CTkToplevel):
    """Choix de police : chaque nom est écrit dans sa propre police, avec recherche."""

    def __init__(self, parent, actuelle, choisir):
        super().__init__(parent, fg_color=FOND)
        self.title("Choisir une police")
        self.geometry("420x560")
        self.transient(parent)
        self.choisir = choisir
        self.polices = sorted({f for f in tkfont.families() if not f.startswith("@")},
                              key=str.lower)
        self.recherche = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self.recherche, placeholder_text="Rechercher…",
                     height=36, font=police(13), fg_color=CHAMP, border_color=BORD,
                     text_color=TEXTE).pack(fill="x", padx=14, pady=(14, 8))
        cadre = ctk.CTkFrame(self, fg_color=CARTE, corner_radius=12, border_width=1,
                             border_color=BORD)
        cadre.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        # Un widget Text : une ligne par police, chacune avec sa propre fonte (rapide
        # même avec des centaines de polices, contrairement à un bouton par police)
        import tkinter as tk
        self.liste = tk.Text(cadre, bg=CARTE, fg=TEXTE, bd=0, highlightthickness=0,
                             cursor="hand2", wrap="none", padx=12, pady=8,
                             selectbackground=CARTE, inactiveselectbackground=CARTE)
        barre = ctk.CTkScrollbar(cadre, command=self.liste.yview, button_color=BORD,
                                 button_hover_color=ACCENT)
        self.liste.configure(yscrollcommand=barre.set)
        barre.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self.liste.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        self.liste.tag_configure("survol", background=BORD)
        self.liste.tag_configure("actuelle", foreground=ACCENT_SURVOL)
        self.actuelle = actuelle
        self.recherche.trace_add("write", lambda *_: self.remplir())
        self.remplir()
        self.after(100, self.grab_set)

    def remplir(self):
        filtre = self.recherche.get().lower()
        t = self.liste
        t.configure(state="normal")
        t.delete("1.0", "end")
        for nom in self.polices:
            if filtre and filtre not in nom.lower():
                continue
            tag = "p_" + str(abs(hash(nom)))
            t.tag_configure(tag, font=(nom, 15), spacing1=4, spacing3=4)
            tags = (tag, "actuelle") if nom == self.actuelle else (tag,)
            t.insert("end", nom + "\n", tags)
            t.tag_bind(tag, "<Button-1>", lambda _e, n=nom: self.valider(n))
            t.tag_bind(tag, "<Enter>", lambda _e, g=tag: self.survol(g))
        t.configure(state="disabled")

    def survol(self, tag):
        self.liste.tag_remove("survol", "1.0", "end")
        plage = self.liste.tag_ranges(tag)
        if plage:
            self.liste.tag_add("survol", plage[0], plage[1])

    def valider(self, nom):
        self.choisir(nom)
        self.grab_release()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__(fg_color=FOND)
        ctk.set_appearance_mode("dark")
        self.title("farfavinci")
        icone = os.path.join(DOSSIER, "icon.ico")
        if os.path.exists(icone):
            # CustomTkinter remet son icône après le démarrage : on repasse derrière
            self.after(250, lambda: self.iconbitmap(icone))
        # hauteur adaptée à l'écran (barre des tâches comprise)
        self.geometry(f"600x{min(820, self.winfo_screenheight() - 120)}")
        self.minsize(580, 600)
        self.occupe_flag = False

        self.langue = ctk.StringVar(value="Français")
        self.mode = ctk.StringVar(value="Phrase par phrase")
        self.source = ctk.StringVar(value="Timeline DaVinci")
        self.sortie = ctk.StringVar(value="Titres animés")
        self.selection = ctk.BooleanVar(value=False)
        self.remplacer = ctk.BooleanVar(value=True)
        self.fichier = ctk.StringVar()
        self.decalage = ctk.StringVar(value="0")
        # style des titres animés
        self.style_nom = None
        self.police_var = ctk.StringVar(value="Arial Black")
        self.anim = ctk.StringVar(value="Pop")
        self.sens = ctk.StringVar(value="Les deux")
        self.karaoke = ctk.BooleanVar(value=True)
        self.kstyle = ctk.StringVar(value="Couleur du texte")
        self.couleur = "#2f7cff"
        self.contour = ctk.BooleanVar(value=False)
        self.par_mot = ctk.BooleanVar(value=True)
        self.taille = ctk.DoubleVar(value=0.08)

        racine = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                        scrollbar_button_color=BORD,
                                        scrollbar_button_hover_color=ACCENT)
        self.racine = racine

        # --- En-tête (fixe) ------------------------------------------------------
        tete = ctk.CTkFrame(self, fg_color="transparent")
        tete.pack(fill="x", padx=20, pady=(16, 0))
        gauche = ctk.CTkFrame(tete, fg_color="transparent")
        gauche.pack(side="left")
        ctk.CTkLabel(gauche, text="farfavinci", font=police(26, True),
                     text_color=TEXTE).pack(anchor="w")
        ctk.CTkLabel(gauche, text="Sous-titres & masque IA  ·  local  ·  GPU",
                     font=police(12), text_color=DOUX).pack(anchor="w")
        pastille = ctk.CTkFrame(tete, fg_color=CHAMP, corner_radius=20)
        pastille.pack(side="right", pady=6)
        self.point = ctk.CTkLabel(pastille, text="●", font=police(13), text_color=DOUX)
        self.point.pack(side="left", padx=(12, 4), pady=5)
        self.etat_pont = ctk.CTkLabel(pastille, text="Recherche de DaVinci…",
                                      font=police(12), text_color=DOUX)
        self.etat_pont.pack(side="left", padx=(0, 14))

        # --- Onglets ---------------------------------------------------------------
        self.onglet = ctk.StringVar(value="Sous-titres")
        segment(self, ["Sous-titres", "Masque IA"], self.onglet, command=self.changer_onglet,
                hauteur=38).pack(fill="x", padx=20, pady=(14, 0))
        racine.pack(fill="both", expand=True, padx=12, pady=(10, 0))

        # --- Réglages ----------------------------------------------------------
        reg = Carte(racine, "Transcription")
        reg.pack(fill="x", padx=8, pady=(18, 12))
        ctk.CTkLabel(reg, text="Découpage", font=police(13),
                     text_color=TEXTE).pack(anchor="w", padx=18)
        segment(reg, list(MODES), self.mode, hauteur=36).pack(fill="x", padx=18, pady=(6, 10))
        menu(ligne_reglage(reg, "Langue"), list(LANGUES), self.langue).pack(side="right")
        ctk.CTkFrame(reg, fg_color="transparent", height=10).pack()

        # --- Source ----------------------------------------------------------------
        src = Carte(racine, "Source")
        src.pack(fill="x", padx=8)
        segment(src, ["Timeline DaVinci", "Fichier vidéo / audio"], self.source,
                command=self.changer_source, accent=False).pack(fill="x", padx=18, pady=(0, 12))
        zone = ctk.CTkFrame(src, fg_color="transparent")
        zone.pack(fill="x", padx=18, pady=(0, 16))

        self.p_timeline = ctk.CTkFrame(zone, fg_color="transparent")
        segment(self.p_timeline, ["Sous-titres simples", "Titres animés"], self.sortie,
                command=lambda _v: self.afficher_style(), accent=False
                ).pack(fill="x", pady=(0, 10))
        interrupteur(self.p_timeline, "Seulement la sélection (points I / O)",
                     self.selection).pack(anchor="w", pady=4)
        interrupteur(self.p_timeline, "Remplacer les anciens sous-titres",
                     self.remplacer).pack(anchor="w", pady=4)

        self.p_fichier = ctk.CTkFrame(zone, fg_color="transparent")
        l1 = ctk.CTkFrame(self.p_fichier, fg_color="transparent")
        l1.pack(fill="x")
        ctk.CTkEntry(l1, textvariable=self.fichier, placeholder_text="Choisis un fichier…",
                     height=34, font=police(12), fg_color=CHAMP, border_color=BORD,
                     text_color=TEXTE).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(l1, text="Parcourir", width=96, height=34, font=police(13),
                      fg_color=BORD, hover_color="#26324a", command=self.parcourir
                      ).pack(side="left", padx=(8, 0))
        l2 = ctk.CTkFrame(self.p_fichier, fg_color="transparent")
        l2.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(l2, text="Décalage de départ", font=police(13),
                     text_color=TEXTE).pack(side="left")
        ctk.CTkLabel(l2, text="ex : 1:30 ou 90", font=police(11),
                     text_color=DOUX).pack(side="left", padx=8)
        ctk.CTkEntry(l2, textvariable=self.decalage, width=90, height=32, font=police(13),
                     fg_color=CHAMP, border_color=BORD, text_color=TEXTE,
                     justify="center").pack(side="right")
        self.p_timeline.pack(fill="x")

        # --- Style des titres animés ---------------------------------------------
        self.c_style = Carte(racine, "Style des titres animés")
        grille = ctk.CTkFrame(self.c_style, fg_color="transparent")
        grille.pack(fill="x", padx=14, pady=(0, 10))
        self.cartes_style = {}
        for i, (nom, st) in enumerate(STYLES.items()):
            b = ctk.CTkButton(grille, text=nom, height=54, corner_radius=10, font=police(14, True),
                              fg_color=CHAMP, hover_color=BORD, border_width=2,
                              border_color=CHAMP, text_color=st["couleur"] if st["karaoke"] else TEXTE,
                              command=lambda n=nom: self.appliquer_style(n))
            b.grid(row=i // 3, column=i % 3, padx=4, pady=4, sticky="ew")
            grille.grid_columnconfigure(i % 3, weight=1)
            self.cartes_style[nom] = b

        self.b_police = ctk.CTkButton(
            ligne_reglage(self.c_style, "Police"), text="", width=240, height=36,
            fg_color=CHAMP, hover_color=BORD, border_width=1, border_color=BORD,
            text_color=TEXTE, anchor="w", command=self.ouvrir_polices)
        self.b_police.pack(side="right")
        self.police_var.trace_add("write", lambda *_: self.maj_bouton_police())
        ctk.CTkLabel(self.c_style, text="Animation", font=police(13),
                     text_color=TEXTE).pack(anchor="w", padx=18, pady=(8, 0))
        segment(self.c_style, ANIMATIONS, self.anim).pack(fill="x", padx=18, pady=(6, 8))
        menu(ligne_reglage(self.c_style, "Quand"), list(SENS), self.sens).pack(side="right")
        lt = ligne_reglage(self.c_style, "Taille du texte")
        self.l_taille = ctk.CTkLabel(lt, text="", width=40, font=police(12), text_color=DOUX)
        self.l_taille.pack(side="right")
        ctk.CTkSlider(lt, from_=0.04, to=0.14, variable=self.taille, width=180,
                      progress_color=ACCENT, button_color=TEXTE, button_hover_color="#ffffff",
                      fg_color=BORD, command=lambda _v: self.maj_taille()).pack(side="right", padx=8)
        self.maj_taille()
        lo = ctk.CTkFrame(self.c_style, fg_color="transparent")
        lo.pack(fill="x", padx=18, pady=(8, 0))
        self.sw_par_mot = interrupteur(lo, "Animer chaque mot", self.par_mot)
        self.sw_par_mot.pack(side="left")
        self.sw_contour = interrupteur(lo, "Contour des lettres", self.contour)
        self.sw_contour.pack(side="right")

        lk = ctk.CTkFrame(self.c_style, fg_color="transparent")
        lk.pack(fill="x", padx=18, pady=(12, 4))
        self.sw_karaoke = interrupteur(lk, "Karaoké (la couleur suit la voix)", self.karaoke)
        self.sw_karaoke.pack(side="left")
        self.b_couleur = ctk.CTkButton(lk, text="", width=44, height=28, corner_radius=8,
                                       fg_color=self.couleur, hover_color=self.couleur,
                                       border_width=2, border_color=BORD,
                                       command=self.choisir_couleur)
        self.b_couleur.pack(side="right")
        menu(ligne_reglage(self.c_style, "Effet karaoké"), list(KARAOKE),
             self.kstyle).pack(side="right")
        ctk.CTkFrame(self.c_style, fg_color="transparent", height=12).pack()
        self.ancre_style = ctk.CTkFrame(racine, fg_color="transparent", height=0)
        self.ancre_style.pack(fill="x")

        # --- Action + progression (fixe en bas) ------------------------------------
        bas = ctk.CTkFrame(self, fg_color=FOND)
        # collé en bas et placé avant le contenu : le bouton reste visible même si
        # la fenêtre est plus petite que le contenu (le contenu défile au-dessus)
        bas.pack(side="bottom", fill="x", padx=20, pady=(8, 16))
        racine.pack_forget()  # replacé après la barre du bas dans l'ordre d'emballage
        racine.pack(fill="both", expand=True, padx=12, pady=(10, 0))
        self.bas = bas
        self.bouton = ctk.CTkButton(
            bas, text="Sous-titrer la timeline", height=50, corner_radius=12,
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

        import masque_ui
        self.page_masque = masque_ui.PageMasque(self, self, globals())

        self.appliquer_style("Rebond karaoké")
        self.afficher_style()
        threading.Thread(target=self.surveiller_pont, daemon=True).start()

    # -- interface ----------------------------------------------------------------
    def changer_onglet(self, valeur):
        self.racine.pack_forget()
        self.page_masque.pack_forget()
        if valeur == "Masque IA":
            self.page_masque.pack(fill="both", expand=True, padx=12, pady=(10, 0))
            self.bouton.configure(text="Suivre le sujet et créer le masque")
        else:
            self.racine.pack(fill="both", expand=True, padx=12, pady=(10, 0))
            self.afficher_style()

    def changer_source(self, valeur):
        timeline = valeur == "Timeline DaVinci"
        self.p_timeline.pack_forget()
        self.p_fichier.pack_forget()
        (self.p_timeline if timeline else self.p_fichier).pack(fill="x")
        self.afficher_style()

    def anime(self):
        return self.source.get() == "Timeline DaVinci" and self.sortie.get() == "Titres animés"

    def afficher_style(self):
        self.c_style.pack_forget()
        if self.anime():
            self.c_style.pack(fill="x", padx=8, pady=(12, 4), before=self.ancre_style)
        if self.source.get() != "Timeline DaVinci":
            texte = "Créer le fichier .srt"
        elif self.anime():
            texte = "Créer les titres animés"
        else:
            texte = "Sous-titrer la timeline"
        if self.onglet.get() == "Sous-titres":
            self.bouton.configure(text=texte)

    def appliquer_style(self, nom):
        st = STYLES[nom]
        self.style_nom = nom
        self.police_var.set(st["police"])
        self.anim.set(st["anim"])
        self.sens.set(st["sens"])
        self.karaoke.set(st["karaoke"])
        self.sw_karaoke.select() if st["karaoke"] else self.sw_karaoke.deselect()
        self.kstyle.set(st["kstyle"])
        self.mode.set(st["affichage"])
        self.definir_couleur(st["couleur"])
        for var, sw, val in ((self.contour, self.sw_contour, st["contour"]),
                             (self.par_mot, self.sw_par_mot, st["par_mot"])):
            var.set(val)
            sw.select() if val else sw.deselect()
        for n, b in self.cartes_style.items():
            b.configure(border_color=ACCENT if n == nom else CHAMP)

    def maj_bouton_police(self):
        nom = self.police_var.get()
        self.b_police.configure(text=f"  {nom}", font=ctk.CTkFont(family=nom, size=15))

    def ouvrir_polices(self):
        FenetrePolices(self, self.police_var.get(), self.police_var.set)

    def maj_taille(self):
        self.l_taille.configure(text=f"{round(self.taille.get() / 0.08 * 100)} %")

    def definir_couleur(self, c):
        self.couleur = c
        self.b_couleur.configure(fg_color=c, hover_color=c)

    def choisir_couleur(self):
        c = colorchooser.askcolor(color=self.couleur, title="Couleur du karaoké")[1]
        if c:
            self.definir_couleur(c)

    def reglages_modele(self):
        """Réglages du modèle Fusion (noms des entrées du macro AutoSubs)."""
        p = self.police_var.get().strip() or "Arial Black"
        # japonais, chinois... : police qui contient les caractères (sinon carrés vides)
        lang = getattr(self, "langue_detectee", None) or LANGUES[self.langue.get()]
        if lang in POLICE_LANGUE and p not in POLICE_LANGUE.values():
            p = POLICE_LANGUE[lang]
        epais = any(k in p for k in ("Black", "Impact", "Bold", "Heavy"))
        r, g, b = hex_rgb(self.couleur)
        anim = self.anim.get()
        return {
            "Font": p,
            "Style": "Regular" if epais else "Bold",
            "TextSize": round(self.taille.get(), 3),
            "WrapEnabled": 1,  # retour à la ligne : évite le texte coupé hors écran
            "WrapBoxWidth": 0.85,
            "OutlineEnabled": 1 if self.contour.get() else 0,
            "FadeEnabled": 1 if anim == "Fondu" else 0,
            "PopInEnabled": 1 if anim in ("Pop", "Rebond") else 0,
            "SlideUpEnabled": 1 if anim == "Glissement" else 0,
            "AnimationMode": SENS[self.sens.get()],
            "AnimationLevel": 1 if self.par_mot.get() else 0,
            # durées (s) choisies pour un rendu naturel ; les courbes sont recalculées par le pont
            "AnimationLength": {"Rebond": 0.5, "Pop": 0.25, "Fondu": 0.3,
                                "Glissement": 0.35}.get(anim, 0.2),
            "HighlightEnabled": 1 if self.karaoke.get() else 0,
            "HighlightStyle": KARAOKE[self.kstyle.get()],
            "HighlightColorRed": r,
            "HighlightColorGreen": g,
            "HighlightColorBlue": b,
        }

    def parcourir(self):
        p = filedialog.askopenfilename(filetypes=[
            ("Vidéo / audio", "*.mp4 *.mov *.mkv *.avi *.mxf *.wav *.mp3 *.m4a *.flac *.aac"),
            ("Tous les fichiers", "*.*")])
        if p:
            self.fichier.set(p)

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
        if self.onglet.get() == "Masque IA":
            self.page_masque.lancer()
        elif self.source.get() == "Timeline DaVinci":
            self.lancer_timeline()
        else:
            self.lancer_fichier()

    # -- transcription ----------------------------------------------------------
    def transcrire(self, src, srt, decalage, base=0, plage=100):
        self.langue_detectee = None
        cmd = [PYTHON, TRANSCRIBE, src, srt, "--langue", LANGUES[self.langue.get()],
               "--decalage", str(decalage), "--mode", MODES[self.mode.get()]]
        if self.anime():
            cmd += ["--max-car", "30"]  # lignes plus courtes pour les gros titres animés
        env =dict(os.environ, HF_HUB_DISABLE_SYMLINKS_WARNING="1")
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", env=env,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        fin = ""
        for ligne in p.stdout:
            fin = ligne.strip() or fin
            if ligne.startswith("LANGUE"):
                self.langue_detectee = ligne.split()[1]
            if ligne.startswith("PROGRES"):
                v = int(ligne.split()[1])
                self.msg(f"Transcription  ·  {v} %", base + v * plage / 100)
        p.wait()
        if p.returncode != 0 or not os.path.exists(srt):
            raise RuntimeError(fin or "Transcription échouée")

    # -- mode fichier -------------------------------------------------------------
    def lancer_fichier(self):
        src = self.fichier.get()
        if not os.path.isfile(src):
            messagebox.showwarning("farfavinci", "Choisis d'abord un fichier.")
            return
        sec = 0.0
        try:
            for part in self.decalage.get().replace(",", ".").split(":"):
                sec = sec * 60 + float(part or 0)
        except ValueError:
            sec = 0.0
        self.occupe(True)
        self.msg("Chargement du modèle…", 0)

        def t():
            srt = os.path.splitext(src)[0] + ".srt"
            try:
                self.transcrire(src, srt, sec)
                self.msg("Terminé  ·  " + srt, 100, OK)
                subprocess.Popen(["explorer", "/select,", os.path.normpath(srt)])
            except Exception as e:
                self.msg("Erreur : " + str(e), couleur=ERREUR)
            self.occupe(False)
        threading.Thread(target=t, daemon=True).start()

    # -- mode timeline DaVinci ---------------------------------------------------------
    def lancer_timeline(self):
        self.occupe(True)
        self.msg("Connexion à DaVinci…", 0)
        threading.Thread(target=self.travail_timeline, daemon=True).start()

    def travail_timeline(self):
        import bridge
        try:
            bridge.envoyer("ping")
            self.msg("Rendu de l'audio de la timeline…", 4)
            os.makedirs(TRAVAIL, exist_ok=True)
            rendu = bridge.envoyer("render_audio", timeout=3600, dir=TRAVAIL,
                                   range="inout" if self.selection.get() else "all")
            decalage = float(rendu.get("decalage", 0))
            # nom unique : DaVinci réutilise un SRT déjà importé sous le même chemin
            base = os.path.join(TRAVAIL, f"sous_titres_{MODES[self.mode.get()]}_{int(time.time())}")
            srt = base + ".srt"
            self.msg("Chargement du modèle…", 10)
            self.transcrire(rendu["fichier"], srt, decalage, base=10, plage=80)

            if self.anime():
                self.msg("Création des titres animés dans DaVinci…", 92)
                with open(base + ".json", encoding="utf-8") as f:
                    captions = json.load(f)
                # un titre reste affiché jusqu'au suivant si la pause est courte
                for c, suivant in zip(captions, captions[1:]):
                    if 0 < suivant["s"] - c["e"] < 0.6:
                        c["e"] = suivant["s"]
                donnees = base + "_titres.lua"
                ecrire_donnees_lua(donnees, captions, self.reglages_modele(), self.remplacer.get(),
                                   anim=self.anim.get())
                res = bridge.envoyer("add_captions", timeout=900, data=donnees)
                if res.get("rates", "0") != "0":
                    self.msg(f"{res.get('poses')} titres posés, {res.get('rates')} en échec : "
                             f"{res.get('erreur_titre')}", 100, ERREUR)
                else:
                    self.msg(f"Terminé  ·  {res.get('poses')} titres animés sur la piste vidéo 2 « Sous-titres »",
                             100, OK)
            else:
                self.msg("Ajout des sous-titres dans DaVinci…", 97)
                res = bridge.envoyer("add_srt", timeout=120, srt=srt,
                                     remplacer="1" if self.remplacer.get() else "0")
                n = res.get("clips_sous_titres", "0")
                if n == "0":
                    self.msg("Le fichier est dans le Media Pool : glisse-le sur une piste "
                             "de sous-titres.  (" + srt + ")", 100, ERREUR)
                else:
                    self.msg(f"Terminé  ·  {n} sous-titres ajoutés à la timeline", 100, OK)
        except Exception as e:
            self.msg("Erreur : " + str(e), couleur=ERREUR)
        self.occupe(False)


def deja_ouverte():
    """Une seule fenêtre : si le port est pris, l'application tourne déjà."""
    import socket
    global _verrou
    _verrou = socket.socket()
    try:
        _verrou.bind(("127.0.0.1", 47813))
        return False
    except OSError:
        return True


if __name__ == "__main__":
    if deja_ouverte():
        sys.exit(0)
    if not os.path.exists(PYTHON):
        messagebox.showerror("farfavinci", "Installation manquante : lance installer.ps1")
        sys.exit(1)
    try:  # icône propre dans la barre des tâches (au lieu de celle de Python)
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Farfatechs.farfavinci")
    except Exception:
        pass
    App().mainloop()
