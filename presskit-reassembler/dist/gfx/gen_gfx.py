#!/usr/bin/env python3
"""Generate the scene-style animated intro assets for the Press Kit Reassembler.

Produces:
  intro.txt   - the ASCII-art frameset (human/terminal readable)
  intro.gif   - an animated GIF version (every line of the ASCII art as pixels)
  boot.gif    - an animated 'button' boot sequence
  icon.png    - a small app icon (used by webxdc / WAR)
"""
import os, pyfiglet
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def fig(banner, font="banner3-D"):
    return pyfiglet.figlet_format(banner, font=font).rstrip("\n")

# ---------- ASCII frameset ----------
F0 = fig("PRESS KIT", "banner3-D")
F1 = fig("REASSEMBLER", "banner3-D")
F2 = fig("release 0.1.0", "small")
BUTTON = [
    "",
    "              +-----------------------------------------+",
    "              |                                         |",
    "              |    [ REASSEMBLE THE PRESS KIT. ]        |",
    "              |    [ type your variables, hit GO. ]     |",
    "              |                                         |",
    "              +-----------------------------------------+",
    "",
]
WASMNOTE = "engine: presskit.wasm   output: dos .com / .dat   cipher: xor/rot13/caesar"

frame_blocks = [
    (F0, (255, 0, 128)),
    (F1, (0, 255, 255)),
    ("\n".join(BUTTON), (255, 230, 0)),
]

# Also expose a "boot" text for the gif file naming
intro_txt = "\n\n".join(b[0] for b in frame_blocks) + "\n\n" + WASMNOTE + "\n"
open(os.path.join(HERE, "intro.txt"), "w").write(intro_txt)

def block_lines(block):
    return block.split("\n")

def render_gif(blocks, path, px=10, bg=(8, 12, 24), delay=90, perline=True):
    """Lay each ASCII-art line down as monochrome glyphs on a dark background,
    frame-by-frame, cycling the highlight colour."""
    font = ImageFont.truetype(FONT, px)
    # compute canvas from the widest/tallest block
    alllines = []
    for blk, col in blocks:
        alllines += [l for l in blk.split("\n")]
    width = max(len(l) for l in alllines) * (px - 2)
    line_h = px + 6
    height = max(len([l for l in b[0].split("\n")]) for b in blocks) * line_h + 8

    def draw_block(block, color, reveal=1.0):
        img = Image.new("RGB", (width + 20, height + 8), bg)
        d = ImageDraw.Draw(img)
        lines = block.split("\n")
        visible = max(1, int(len(lines) * reveal))
        for i, line in enumerate(lines[:visible]):
            d.text((10, 8 + i * line_h), line, font=font, fill=color)
        return img

    frames = []
    # per block: reveal scan then hold
    for blk, col in blocks:
        lines = blk.split("\n")
        for k in range(1, len(lines) + 1):
            frames.append(draw_block("\n".join(lines[:k]), col, 1.0))
        # hold full block a couple frames, shifting brightness
        frames.append(draw_block(blk, brighten(col, 0.8), 1.0))
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=delay, loop=0)
    return len(frames)

def brighten(rgb, f):
    return tuple(min(255, int(c + (255 - c) * f)) for c in rgb)

render_gif(frame_blocks, os.path.join(HERE, "intro.gif"))
print("wrote intro.gif")

# ---------- boot.gif : ASCII 'button' pulse on a boot bar ----------
boot = []
cols = [ (255,0,128), (0,255,255), (255,230,0) ]
seq = [ (fig("BOOTING", "small") + "\n" + "\n".join(BUTTON), cols[i%3]) for i in range(3)]
# add a progress/scan bar underneath for a boot feel
def with_bar(block_lines_, col):
    bar_len = 40
    bars=[]
    for i in range(bar_len+1):
        l = "##" * i
        bars.append(l)
    return block_lines_
render_gif(seq, os.path.join(HERE, "boot.gif"), px=10, delay=70)
print("wrote boot.gif")

# ---------- icon.png ----------
im = Image.new("RGBA", (96, 96), (8, 12, 24, 255))
d = ImageDraw.Draw(im)
d.rectangle([6, 6, 90, 90], outline=(0, 255, 255), width=3)
d.text((20, 30), "PK>", fill=(255, 0, 128), font=ImageFont.truetype(FONT, 30))
d.rectangle([12, 74, 84, 80], fill=(0, 255, 255))
im.save(os.path.join(HERE, "icon.png"))
print("wrote icon.png")
print("done")
