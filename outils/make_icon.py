"""Génère les logos des deux outils (noir / bleu) :

- farfascript/icon.ico : écran avec onde audio + bandes de sous-titres
- farfamask/icon.ico   : silhouette coupée en deux (moitié détourée avec contour
  de sélection sur damier de transparence) + étincelle

Dessinés en 1024 px puis réduits (anticrénelage).
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 1024
FOND = (10, 14, 24, 255)
ECRAN = (20, 29, 46, 255)
BLEU = (47, 124, 255, 255)
BLEU_CLAIR = (77, 144, 255, 255)
BLANC = (236, 241, 250, 255)
GRIS = (150, 162, 186, 255)
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def carte():
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle((32, 32, S - 32, S - 32), radius=220, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(FOND, (0, 0), m)
    return img, m


def liseré(img):
    ImageDraw.Draw(img).rounded_rectangle((32, 32, S - 32, S - 32), radius=220,
                                          outline=BLEU, width=26)


def farfascript():
    img, _ = carte()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((170, 200, S - 170, 600), radius=60, fill=ECRAN)   # écran
    hauteurs = [60, 120, 190, 110, 240, 160, 80, 200, 130, 70, 150, 90]    # onde audio
    for i, h in enumerate(hauteurs):
        x = 250 + i * 46
        d.rounded_rectangle((x, 400 - h // 2, x + 26, 400 + h // 2), radius=13, fill=BLEU)
    d.rounded_rectangle((200, 680, S - 200, 745), radius=33, fill=BLANC)   # sous-titres
    d.rounded_rectangle((300, 790, S - 300, 855), radius=33, fill=BLEU)
    liseré(img)
    return img


def farfamask():
    img, m_carte = carte()
    droite = Image.new("L", (S, S), 0)
    ImageDraw.Draw(droite).rectangle((S // 2, 0, S, S), fill=255)
    # moitié droite : damier de transparence (le "fond retiré")
    damier = Image.new("RGBA", (S, S), FOND)
    dd = ImageDraw.Draw(damier)
    pas = 64
    for y in range(0, S, pas):
        for x in range(0, S, pas):
            if (x // pas + y // pas) % 2 == 0:
                dd.rectangle((x, y, x + pas - 1, y + pas - 1), fill=(22, 31, 50, 255))
    img.paste(damier, (0, 0), ImageChops.multiply(droite, m_carte))
    # silhouette (tête + épaules), coupée par le bas de la carte
    sil = Image.new("L", (S, S), 0)
    ds = ImageDraw.Draw(sil)
    ds.ellipse((372, 210, 652, 490), fill=255)
    ds.ellipse((200, 540, 824, 1100), fill=255)
    sil = ImageChops.multiply(sil, m_carte.filter(ImageFilter.MinFilter(61)))
    gauche = ImageChops.subtract(sil, droite)
    sil_droite = ImageChops.multiply(sil, droite)
    img.paste(GRIS, (0, 0), gauche)                                         # sujet normal
    contour = ImageChops.subtract(sil_droite.filter(ImageFilter.MaxFilter(29)), sil_droite)
    img.paste(BLEU, (0, 0), ImageChops.multiply(contour, droite))          # sélection
    img.paste(BLANC, (0, 0), sil_droite)                                    # sujet détouré
    d = ImageDraw.Draw(img)
    d.rectangle((S // 2 - 4, 140, S // 2 + 4, S - 120), fill=BLEU_CLAIR)    # ligne de coupe
    cx, cy, r, e = 815, 215, 95, 22                                          # étincelle
    d.polygon([(cx, cy - r), (cx + e, cy - e), (cx + r, cy), (cx + e, cy + e),
               (cx, cy + r), (cx - e, cy + e), (cx - r, cy), (cx - e, cy - e)], fill=BLEU_CLAIR)
    liseré(img)
    return img


if __name__ == "__main__":
    for nom, dessin in (("farfascript", farfascript), ("farfamask", farfamask)):
        sortie = os.path.join(RACINE, nom, "icon.ico")
        dessin().resize((256, 256), Image.LANCZOS).save(
            sortie, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        print(sortie)
