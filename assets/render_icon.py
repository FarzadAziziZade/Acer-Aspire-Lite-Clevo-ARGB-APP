from pathlib import Path

from PIL import Image, ImageDraw


OUT = Path(__file__).parent
S = 4
im = Image.new("RGBA", (256 * S, 256 * S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
def box(coords, radius, fill, outline=None, width=1):
    coords = tuple(int(v * S) for v in coords)
    d.rounded_rectangle(coords, radius=radius * S, fill=fill, outline=outline, width=width * S)

box((8, 8, 248, 248), 56, "#0b1020")
box((39, 61, 217, 193), 25, "#070b15")
box((42, 55, 214, 185), 23, "#1d2a40", "#40506c", 3)
colors = ["#22d3ee", "#8267ff", "#ec4899", "#fb923c"]
keys = [(58,72,93,103),(101,72,136,103),(144,72,179,103),
        (58,112,93,143),(101,112,136,143),(144,112,179,143),
        (58,152,93,169),(101,152,179,169)]
for i, key in enumerate(keys):
    box(key, 8 if key[3] - key[1] > 20 else 7, "#111a2c", "#53627c", 2)
    if i < 6:
        d.line((int((key[0]+7)*S), int((key[1]+17)*S), int((key[2]-7)*S), int((key[1]+17)*S)),
               fill=colors[i % 4], width=5*S)
# Flowing RGB light trails beneath the keycaps.
for width, pts, color in [
    (12, [(54,205),(78,181),(98,221),(124,197),(146,179),(166,192),(180,207),(201,196),(218,177)], colors),
    (4, [(60,218),(81,202),(101,218),(125,207),(148,194),(168,204),(184,211),(203,202),(216,191)], colors),
]:
    for i in range(len(pts)-1):
        a, b = pts[i], pts[i+1]
        d.line((a[0]*S,a[1]*S,b[0]*S,b[1]*S), fill=colors[min(3, i*4//(len(pts)-1))], width=width*S)
im = im.resize((256, 256), Image.Resampling.LANCZOS)
im.save(OUT / "keyboard-effects-studio.png", optimize=True)
im.save(OUT / "keyboard-effects-studio.ico", format="ICO", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
