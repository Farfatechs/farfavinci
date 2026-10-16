"""Génère icon.ico : mi sous-titres, mi masque magique (noir / bleu).

Silhouette coupée en deux : moitié gauche normale, moitié droite détourée
(contour de sélection bleu sur damier de transparence), bandes de sous-titres
en bas et une étincelle. Dessiné en 1024 px puis réduit (anticrénelage).
"""
import os

from PIL import Image, ImageChops, ImageDraw, ImageFilter

S = 1024
FOND = (10, 14, 24, 255)
BLEU = (47, 124, 255, 255)
BLEU_CLAIR = (77, 144, 255, 255)
BLANC = (236, 241, 250, 255)
GRIS = (150, 162, 186, 255)


def forme_carte():
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).rounded_rectangle((32, 32, S - 32, S - 32), radius=220, fill=255)
    return m


def silhouette():
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    d.ellipse((392, 170, 632, 410), fill=255)            # tête
    d.ellipse((250, 450, 774, 900), fill=255)             # épaules
    d.rectangle((0, 690, S, S), fill=0)                   # coupe sous les épaules
    return m


def dessiner():
    carte = forme_carte()
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(FOND, (0, 0), carte)

    # moitié droite : damier de transparence (le "fond retiré")
    damier = Image.new("RGBA", (S, S), FOND)
    dd = ImageDraw.Draw(damier)
    pas = 64
    for y in range(0, S, pas):
        for x in range(0, S, pas):
            if (x // pas + y // pas) % 2 == 0:
                dd.rectangle((x, y, x + pas - 1, y + pas - 1), fill=(22, 31, 50, 255))
    droite = Image.new("L", (S, S), 0)
    ImageDraw.Draw(droite).rectangle((S // 2, 0, S, S), fill=255)
    img.paste(damier, (0, 0), ImageChops.multiply(droite, carte))

    sil = silhouette()
    gauche = ImageChops.subtract(sil, droite)
    sil_droite = ImageChops.multiply(sil, droite)
    img.paste(GRIS, (0, 0), gauche)                       # sujet normal
    # contour de sélection bleu autour de la moitié détourée
    contour = ImageChops.subtract(sil_droite.filter(ImageFilter.MaxFilter(29)), sil_droite)
    contour = ImageChops.multiply(contour, droite)
    img.paste(BLEU, (0, 0), contour)
    img.paste(BLANC, (0, 0), sil_droite)                  # sujet détouré

    # ligne de coupe
    d = ImageDraw.Draw(img)
    d.rectangle((S // 2 - 4, 120, S // 2 + 4, 700), fill=BLEU_CLAIR)

    # bandes de sous-titres
    d.rounded_rectangle((180, 750, S - 180, 815), radius=33, fill=BLANC)
    d.rounded_rectangle((290, 850, S - 290, 915), radius=33, fill=BLEU)

    # étincelle (étoile à 4 branches)
    cx, cy, r, e = 815, 215, 95, 22
    d.polygon([(cx, cy - r), (cx + e, cy - e), (cx + r, cy), (cx + e, cy + e),
               (cx, cy + r), (cx - e, cy + e), (cx - r, cy), (cx - e, cy - e)], fill=BLEU_CLAIR)

    # liseré bleu
    d.rounded_rectangle((32, 32, S - 32, S - 32), radius=220, outline=BLEU, width=26)
    return img


if __name__ == "__main__":
    dossier = os.path.dirname(os.path.abspath(__file__))
    grand = dessiner()
    grand.resize((256, 256), Image.LANCZOS).save(
        os.path.join(dossier, "icon.ico"),
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(os.path.join(dossier, "icon.ico"))
