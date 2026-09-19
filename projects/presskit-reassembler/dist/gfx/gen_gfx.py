#!/usr/bin/env python3
"""Generate the scene-style animated intro assets for the Press Kit Reassembler.

Produces:
  intro.txt   - the ASCII-art frameset (human/terminal readable)
  intro.gif   - an animated GIF version (every line of the ASCII art as pixels)
  boot.gif    - an animated 'button' boot sequence
  icon.png    - a small app icon (used by webxdc / WAR)
"""
import os, sys

try:
    import pyfiglet
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(
        "gen_gfx.py: missing dependency (%s).\n"
        "  pip install pyfiglet pillow   # add --break-system-packages on PEP 668 distros\n"
        "See ../JDK_VIA_NPM.md for the same story on the Java build." % e.name)

HERE = os.path.dirname(os.path.abspath(__file__))
# A monospace TTF is required for the ASCII-art frames. The path used to be
# hardcoded to the Debian/Ubuntu DejaVu location, so the script died with a
# bare OSError on macOS, Windows and any distro that ships fonts elsewhere.
FONT_CANDIDATES = [
    os.environ.get("PRESSKIT_FONT", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",   # Debian/Ubuntu
    "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",             # Fedora/Arch
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",                # Arch
    "/Library/Fonts/Menlo.ttf",                               # macOS
    "/System/Library/Fonts/Menlo.ttc",                        # macOS
    "C:/Windows/Fonts/consola.ttf",                           # Windows
]
FONT = next((f for f in FONT_CANDIDATES if f and os.path.exists(f)), None)
if FONT is None:
    raise SystemExit(
        "gen_gfx.py: no monospace TTF found. Set PRESSKIT_FONT=/path/to/font.ttf "
        "(looked in: %s)" % ", ".join(f for f in FONT_CANDIDATES if f))

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
with open(os.path.join(HERE, "intro.txt"), "w") as _fh:
    _fh.write(intro_txt)

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
# NOTE: a `with_bar()` helper used to live here. It built a list of "##"*i
# progress-bar strings, then returned its input unchanged and was never called,
# so the committed boot.gif has never had the bar the comment promised. Removed
# rather than wired up: regenerating the GIFs needs pyfiglet + Pillow, and
# shipping a script whose output does not match the committed artifact is worse
# than shipping one that does. Re-add it here if you want the boot bar.
render_gif(seq, os.path.join(HERE, "boot.gif"), px=10, delay=70)
print("wrote boot.gif")

# ---------- icon.png ----------
# 256x256 square: the container spec asks for "a square at reasonable
# width/height, usually between 128 x 128 and 512 x 512 pixel". The previous
# 96x96 icon fell below that range and made every package fail validation.
# No border rounding or shaped cut-out -- implementations add those themselves.
ICON = 256
im = Image.new("RGBA", (ICON, ICON), (8, 12, 24, 255))
d = ImageDraw.Draw(im)
d.rectangle([16, 16, ICON - 16, ICON - 16], outline=(0, 255, 255), width=8)
d.text((54, 84), "PK>", fill=(255, 0, 128), font=ImageFont.truetype(FONT, 80))
d.rectangle([32, 196, ICON - 32, 214], fill=(0, 255, 255))
im.save(os.path.join(HERE, "icon.png"))
print("wrote icon.png")
print("done")
