"""Génère icon.ico (noir / bleu, bandes de sous-titres)."""
import os
from PIL import Image, ImageDraw

S = 512


def dessiner():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # fond : carré arrondi noir bleuté, liseré bleu
    d.rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=(10, 14, 24), outline=(47, 124, 255),
                        width=14)
    # écran (zone image)
    d.rounded_rectangle((92, 110, S - 92, 300), radius=34, fill=(20, 29, 46))
    # onde audio dans l'écran
    xs = range(130, S - 130, 28)
    hauteurs = [30, 60, 95, 55, 120, 80, 40, 100, 65, 35, 75, 45]
    for x, h in zip(xs, hauteurs):
        d.rounded_rectangle((x, 205 - h // 2, x + 14, 205 + h // 2), radius=7, fill=(47, 124, 255))
    # bandes de sous-titres
    d.rounded_rectangle((110, 336, S - 110, 370), radius=17, fill=(230, 236, 247))
    d.rounded_rectangle((160, 394, S - 160, 428), radius=17, fill=(77, 144, 255))
    return img


if __name__ == "__main__":
    sortie = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    dessiner().save(sortie, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(sortie)
