"""Transcription audio -> SRT avec faster-whisper (GPU). Appelé par le script DaVinci."""
import os
import sys
import site
import argparse
import json


def _ajouter_dll_cuda():
    # Les DLL cuBLAS/cuDNN sont installées via pip (nvidia-*-cu12) dans site-packages/nvidia/*/bin
    for base in site.getsitepackages():
        nv = os.path.join(base, "nvidia")
        if os.path.isdir(nv):
            for sub in os.listdir(nv):
                b = os.path.join(nv, sub, "bin")
                if os.path.isdir(b):
                    os.add_dll_directory(b)
                    os.environ["PATH"] = b + os.pathsep + os.environ["PATH"]


_ajouter_dll_cuda()
from faster_whisper import WhisperModel  # noqa: E402


def tc(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"


# fins de phrase, y compris la ponctuation chinoise / japonaise
FIN_PHRASE = (".", "?", "!", "…", "。", "？", "！")
# langues écrites sans espaces entre les mots
SANS_ESPACES = {"ja", "zh", "yue", "th", "lo", "my", "km", "bo"}


def decouper(mots, max_car, max_lignes, max_duree):
    """Regroupe les mots en sous-titres lisibles (coupe sur ponctuation / longueur / pause)."""
    blocs, cur = [], []

    def longueur(ws):
        return len("".join(w.word for w in ws).strip())

    for w in mots:
        if cur:
            pause = w.start - cur[-1].end
            trop_long = longueur(cur + [w]) > max_car * max_lignes
            trop_duree = w.end - cur[0].start > max_duree
            if pause > 0.8 or trop_long or trop_duree:
                blocs.append(cur)
                cur = []
        cur.append(w)
        if w.word.strip().endswith(FIN_PHRASE) and longueur(cur) > max_car * 0.5:
            blocs.append(cur)
            cur = []
    if cur:
        blocs.append(cur)
    return blocs


def decouper_phrases(mots, pause_max=0.8, duree_max=10.0):
    """Une phrase par sous-titre : coupe après . ? ! … ou sur une vraie pause.
    duree_max évite un bloc interminable quand la ponctuation manque."""
    blocs, cur = [], []
    for w in mots:
        if cur and (w.start - cur[-1].end > pause_max or w.end - cur[0].start > duree_max):
            blocs.append(cur)
            cur = []
        cur.append(w)
        if w.word.strip().endswith(FIN_PHRASE):
            blocs.append(cur)
            cur = []
    if cur:
        blocs.append(cur)
    return blocs


def mettre_en_lignes(texte, max_car, max_lignes):
    if len(texte) <= max_car or max_lignes < 2:
        return texte
    milieu = len(texte) // 2
    # coupe à l'espace le plus proche du milieu
    g = texte.rfind(" ", 0, milieu + 1)
    d = texte.find(" ", milieu)
    candidats = [i for i in (g, d) if i > 0]
    if not candidats:
        return texte
    i = min(candidats, key=lambda x: abs(x - milieu))
    return texte[:i] + "\n" + texte[i + 1:]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio")
    p.add_argument("srt")
    p.add_argument("--langue", default="fr")
    p.add_argument("--modele", default="large-v3")
    p.add_argument("--max-car", type=int, default=42)
    p.add_argument("--max-lignes", type=int, default=2)
    p.add_argument("--max-duree", type=float, default=6.0)
    p.add_argument("--decalage", type=float, default=0.0)
    p.add_argument("--mode", choices=["bloc", "ligne", "phrase", "mot"], default="bloc")
    a = p.parse_args()

    langue = None if a.langue == "auto" else a.langue
    try:
        modele = WhisperModel(a.modele, device="cuda", compute_type="int8_float16")
    except Exception as e:  # repli CPU si le GPU échoue
        print(f"GPU indisponible ({e}), passage sur CPU", flush=True)
        modele = WhisperModel(a.modele, device="cpu", compute_type="int8")

    segments, info = modele.transcribe(
        a.audio, language=langue, word_timestamps=True,
        vad_filter=True, beam_size=5,
    )
    total = info.duration or 1
    mots = []
    print(f"LANGUE {info.language}", flush=True)
    # sans espaces (japonais, chinois...), chaque morceau est un mot à part entière
    recoller = info.language not in SANS_ESPACES
    for seg in segments:
        for w in seg.words or []:
            # Whisper coupe parfois un mot ("j" + "'ai") : un morceau sans espace
            # devant appartient au mot précédent
            if recoller and mots and w.word and not w.word[0].isspace():
                mots[-1].word += w.word
                mots[-1].end = w.end
            else:
                mots.append(w)
        print(f"PROGRES {min(100, int(seg.end / total * 100))}", flush=True)

    if a.mode == "mot":
        blocs = [[w] for w in mots]
        # prolonge chaque mot jusqu'au suivant si la pause est courte (évite le clignotement)
        for i in range(len(blocs) - 1):
            w, suivant = blocs[i][0], blocs[i + 1][0]
            if 0 < suivant.start - w.end < 0.4:
                w.end = suivant.start
    elif a.mode == "phrase":
        blocs = decouper_phrases(mots)
    elif a.mode == "ligne":
        blocs = decouper(mots, a.max_car, 1, 3.5)
    else:
        blocs = decouper(mots, a.max_car, a.max_lignes, a.max_duree)
    with open(a.srt, "w", encoding="utf-8") as f:
        for n, b in enumerate(blocs, 1):
            texte = "".join(w.word for w in b).strip()
            texte = mettre_en_lignes(texte, a.max_car, a.max_lignes)
            f.write(f"{n}\n{tc(b[0].start + a.decalage)} --> {tc(b[-1].end + a.decalage)}\n{texte}\n\n")
    # Données pour les titres animés : texte + minutage de chaque mot.
    # Le texte doit être exactement la concaténation des mots (le karaoké
    # compte les caractères mot par mot), d'où le lstrip du seul premier mot.
    captions = []
    for b in blocs:
        mots_c = []
        for i, w in enumerate(b):
            txt = w.word.lstrip() if i == 0 else w.word
            mots_c.append({"s": round(w.start + a.decalage, 3), "e": round(w.end + a.decalage, 3), "w": txt})
        captions.append({"s": mots_c[0]["s"], "e": mots_c[-1]["e"],
                         "t": "".join(m["w"] for m in mots_c), "w": mots_c})
    with open(os.path.splitext(a.srt)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(captions, f, ensure_ascii=False)
    print(f"OK {len(blocs)} sous-titres", flush=True)


if __name__ == "__main__":
    sys.exit(main())
