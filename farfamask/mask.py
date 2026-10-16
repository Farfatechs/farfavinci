"""Moteur de masque IA (SAM 2) - processus permanent piloté par l'application.

Protocole : une commande JSON par ligne sur stdin, réponses sur stdout en
lignes préfixées par "@" (JSON). Commandes :
  charger   {video, debut, nb, dossier}  -> décode le clip en images allégées
  apercu    {frame, points}              -> masque instantané sur une image
  propager  {frame, points, sortie}      -> suit le sujet sur tout le clip et
                                            écrit détourage (alpha) + cache N&B
Points : [[x, y, 1 = garder / 0 = exclure], ...] et boite [x0, y0, x1, y1] (optionnelle),
en pixels de l'image d'origine.
"""
import json
import os
import shutil
import sys
from fractions import Fraction

import av
import numpy as np
import torch
from PIL import Image, ImageFilter

MODELE = "facebook/sam2.1-hiera-base-plus"
LARGEUR_PROXY = 960   # images envoyées à SAM 2 (il travaille en 1024 de toute façon)
PAQUET = 120          # images par paquet de propagation (limite la mémoire)
# bfloat16 : RTX 30 et plus récentes ; float16 sur les cartes plus anciennes
TYPE = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16


def dire(**kw):
    print("@" + json.dumps(kw, ensure_ascii=False), flush=True)


class Moteur:
    def __init__(self):
        from sam2.sam2_image_predictor import SAM2ImagePredictor
        from sam2.sam2_video_predictor import SAM2VideoPredictor
        self.image = SAM2ImagePredictor.from_pretrained(MODELE)
        self.video = SAM2VideoPredictor.from_pretrained(MODELE)
        self.clip = None

    # -- lecture du clip --------------------------------------------------------
    def images(self, debut, nb):
        """Images [debut, debut + nb) du clip, en pleine résolution (PIL RGB)."""
        c = self.clip
        with av.open(c["video"]) as conteneur:
            flux = conteneur.streams.video[0]
            flux.thread_type = "AUTO"
            t = debut / c["fps"]
            conteneur.seek(int(t / flux.time_base), stream=flux, backward=True)
            rendu = 0
            for image in conteneur.decode(flux):
                idx = round(image.time * c["fps"]) if image.time is not None else None
                if idx is not None and idx < debut:
                    continue
                yield image.to_image()
                rendu += 1
                if rendu >= nb:
                    return

    def charger(self, video, debut, nb, dossier):
        with av.open(video) as conteneur:
            flux = conteneur.streams.video[0]
            fps = flux.average_rate or flux.guessed_rate or Fraction(25)
        self.clip = {"video": video, "debut": int(debut), "nb": int(nb), "fps": float(fps),
                     "fps_frac": fps, "dossier": dossier}
        proxy = os.path.join(dossier, "proxy")
        shutil.rmtree(proxy, ignore_errors=True)
        os.makedirs(proxy)
        n = 0
        for i, img in enumerate(self.images(int(debut), int(nb))):
            if i == 0:
                self.clip["w"], self.clip["h"] = img.size
                self.clip["pw"] = LARGEUR_PROXY
                self.clip["ph"] = round(img.size[1] * LARGEUR_PROXY / img.size[0] / 2) * 2
            img.resize((self.clip["pw"], self.clip["ph"]), Image.BILINEAR).save(
                os.path.join(proxy, f"{i:05d}.jpg"), quality=92)
            n = i + 1
            if i % 20 == 0:
                dire(progres=round(100 * i / max(1, nb)), etape="chargement")
        self.clip["nb"] = n
        return {"n": n, "w": self.clip["w"], "h": self.clip["h"], "proxy": proxy}

    def proxy(self, i):
        return os.path.join(self.clip["dossier"], "proxy", f"{i:05d}.jpg")

    def points_proxy(self, points, boite=None):
        """Points et cadre (pixels d'origine) -> coordonnées des images allégées.
        Renvoie None à la place des points s'il n'y en a pas (cadre seul)."""
        e = self.clip["pw"] / self.clip["w"]
        pts = lab = None
        if points:
            pts = np.array([[p[0] * e, p[1] * e] for p in points], dtype=np.float32)
            lab = np.array([int(p[2]) for p in points], dtype=np.int32)
        b = np.array([v * e for v in boite], dtype=np.float32) if boite else None
        return pts, lab, b

    # -- aperçu sur une image ------------------------------------------------------
    def apercu(self, frame, points, boite=None):
        img = Image.open(self.proxy(frame)).convert("RGB")
        pts, lab, b = self.points_proxy(points, boite)
        with torch.inference_mode(), torch.autocast("cuda", dtype=TYPE):
            self.image.set_image(np.array(img))
            masques, scores, _ = self.image.predict(point_coords=pts, point_labels=lab,
                                                    box=b, multimask_output=False)
        m = masques[0] > 0.5
        # superposition : sujet normal, reste assombri, contour bleu
        base = np.array(img).astype(np.float32)
        base[~m] *= 0.35
        bord = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)) > 0
        base[bord] = [47, 124, 255]
        sortie = os.path.join(self.clip["dossier"], "apercu.png")
        Image.fromarray(base.astype(np.uint8)).save(sortie)
        return {"image": sortie}

    # -- propagation sur tout le clip -------------------------------------------
    def segmenter(self, ordre, pts, lab, b, resultats, total, fait):
        """Propage dans l'ordre donné (avant ou arrière) par paquets.
        Chaque paquet repart du masque de la dernière image du précédent."""
        dossier = os.path.join(self.clip["dossier"], "paquet")
        masque_prec = None
        debut = 0
        while debut < len(ordre):
            morceau = ordre[debut:debut + PAQUET]
            shutil.rmtree(dossier, ignore_errors=True)
            os.makedirs(dossier)
            for j, g in enumerate(morceau):
                cible = os.path.join(dossier, f"{j:05d}.jpg")
                try:
                    os.link(self.proxy(g), cible)
                except OSError:
                    shutil.copy(self.proxy(g), cible)
            with torch.inference_mode(), torch.autocast("cuda", dtype=TYPE):
                etat = self.video.init_state(video_path=dossier, offload_video_to_cpu=True)
                if masque_prec is None:
                    self.video.add_new_points_or_box(etat, frame_idx=0, obj_id=1,
                                                     points=pts, labels=lab, box=b)
                else:
                    self.video.add_new_mask(etat, frame_idx=0, obj_id=1, mask=masque_prec)
                for j, _ids, logits in self.video.propagate_in_video(etat):
                    l = logits[0, 0].float()
                    proba = torch.sigmoid(l).mul(255).byte().cpu().numpy()
                    resultats[morceau[j]] = proba
                    if j == len(morceau) - 1:
                        masque_prec = (l > 0).cpu().numpy()
                    fait[0] += 1
                    if fait[0] % 10 == 0:
                        dire(progres=round(80 * fait[0] / total), etape="suivi")
                self.video.reset_state(etat)
                del etat
            torch.cuda.empty_cache()
            if debut + PAQUET >= len(ordre):
                break
            debut += PAQUET - 1  # la dernière image sert de départ au paquet suivant

    def propager(self, frame, points, sortie, boite=None):
        c = self.clip
        pts, lab, b = self.points_proxy(points, boite)
        resultats = {}
        total = c["nb"] + frame  # avant + arrière (approximatif)
        fait = [0]
        self.segmenter(list(range(frame, c["nb"])), pts, lab, b, resultats, total, fait)
        if frame > 0:
            self.segmenter(list(range(frame, -1, -1)), pts, lab, b, resultats, total, fait)

        # Écriture pleine résolution : détourage ProRes 4444 (alpha) + cache N&B ProRes 422
        os.makedirs(sortie, exist_ok=True)
        nom = os.path.splitext(os.path.basename(c["video"]))[0]
        f_detour = os.path.join(sortie, f"{nom}_detourage.mov")
        f_cache = os.path.join(sortie, f"{nom}_cache.mov")
        w, h = c["w"] - c["w"] % 2, c["h"] - c["h"] % 2
        sorties = []
        for chemin, profil, fmt in ((f_detour, "4", "yuva444p10le"), (f_cache, "2", "yuv422p10le")):
            cont = av.open(chemin, "w")
            flux = cont.add_stream("prores_ks", rate=c["fps_frac"])
            flux.width, flux.height, flux.pix_fmt = w, h, fmt
            flux.options = {"profile": profil, "vendor": "apl0"}
            sorties.append((cont, flux, fmt))
        vide = np.zeros((c["ph"], c["pw"]), np.uint8)
        for i, img in enumerate(self.images(c["debut"], c["nb"])):
            img = img.crop((0, 0, w, h))
            alpha = Image.fromarray(resultats.get(i, vide)).resize((w, h), Image.BILINEAR)
            alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))
            rgba = img.copy()
            rgba.putalpha(alpha)
            cache = Image.merge("RGB", (alpha, alpha, alpha))
            for (cont, flux, fmt), image in zip(sorties, (rgba, cache)):
                # from_ndarray : from_image convertirait le RGBA en RVB (perte de l'alpha)
                vf = av.VideoFrame.from_ndarray(np.asarray(image),
                                                format="rgba" if image.mode == "RGBA" else "rgb24")
                vf = vf.reformat(format=fmt)
                for paquet in flux.encode(vf):
                    cont.mux(paquet)
            if i % 10 == 0:
                dire(progres=80 + round(20 * i / max(1, c["nb"])), etape="écriture")
        for cont, flux, _ in sorties:
            for paquet in flux.encode():
                cont.mux(paquet)
            cont.close()
        return {"detourage": f_detour, "cache": f_cache, "n": c["nb"]}


def main():
    # UTF-8 quel que soit le lanceur (sinon cp1252 sous Windows : accents illisibles)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    dire(etat="chargement du modèle")
    moteur = Moteur()
    dire(etat="pret")
    for ligne in sys.stdin:
        if not ligne.strip():
            continue
        req = json.loads(ligne)
        cmd = req.pop("cmd")
        try:
            dire(ok=True, cmd=cmd, **getattr(moteur, cmd)(**req))
        except Exception as e:  # on renvoie l'erreur sans tuer le moteur
            dire(ok=False, cmd=cmd, erreur=f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
