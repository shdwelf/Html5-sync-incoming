# Secrets of the Screen — an original media-history documentary

A small multi-page documentary web site about things **hidden inside software and
media**. Every animation and note is generated live in the browser (Canvas +
WebAudio); no media files or archive content are reproduced.

## Pages
| Page | Topic |
|---|---|
| `index.html` | Home / hub with animated hero and live chapter-preview cards |
| `chapters/arcade.html` | The coin-op arcade & the Museum of the Game (KLOV) |
| `chapters/scene.html` | Cracktro / demoscene as a historical art form |
| `chapters/eggs.html` | Easter eggs in software (MS-DOS) and film trivia |
| `chapters/presskit.html` | Multimedia CD-ROM press kits — the 1997 DreamWorks "The Peacemaker" kit |
| `chapters/gamewizard.html` | Game Wizard (1994): an educational look at a shareware DOS game enhancer |

## How it's built
- `css/style.css` — shared retro/CRT styling.
- `js/chip.js` — original SID-style WebAudio chiptune engine (loop/pattern model).
- `js/stage.js` — shared animated "attract screen" canvas backdrop.
- `js/nav.js` — injects a shared top navigation + the music toggle on every page.
- Chapters carry their own live canvas interactive(s).

## Research sources cited (original prose, links out)
- Museum of the Game / KLOV — arcade-museum.com
- Easter Egg Archive — eeggs.com (MS-DOS list)
- National Treasure fan easter-egg archive — nationaltreasure.us/easter-eggs
- Internet Archive — The Peacemaker (1997) press kit; C64 cracktros; Game Wizard

## Boundaries
Original educational homage. Distributes **no** cracked software, keygens, or copied
artwork/text; the historical originals live on the archives this site links to.
Run locally with any static server (e.g. `python3 -m http.server`).
