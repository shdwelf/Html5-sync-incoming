# Cryptomonopoly — a WebXDC board game

An **original, crypto-flavoured trading-board game** built from scratch. It runs
two ways from the same code:

- **WebXDC** (`dist/Cryptomonopoly.xdc`) — install/share in **Delta Chat** as an
  app. Each device is one player; actions are broadcast and every peer runs the
  same deterministic reducer, so tables stay in sync peer-to-peer.
- **Plain browser / hot-seat** — open `index.html` (or serve this folder) and
  play 2–6 players on one screen.

## Run it
```bash
# quick local preview
cd cryptomonopoly-webxdc && python3 -m http.server 8231
# -> open http://localhost:8231

# build the Delta Chat app package
./build.sh            # writes dist/Cryptomonopoly.xdc (+ .webxdc copy)
```

## Play
- **Lobby:** add 2–6 seats, give each a name and pick a **piece** (Bitcoin, whale,
  ape, rocket, bot, shark, moon, diamond-hand…).
- Roll two dice and move clockwise around the 24-tile ring. Pass GO → collect 200.
- Land on an unowned **coin / chain / exchange** → buy it. Others landing on it pay you **rent**.
- Own several **exchanges** to raise their fee (25 → 50 → 100 → 200).
- On your turn, **stake a node** on a coin you own (rent rises, max level 4).
- **Gas fees & jail bonds** feed the **Free-Mint pot**; land on that tile to claim it all.
- Doubles give an extra roll; **three doubles** or a **Rug Pull** square sends you to jail.
- Roll doubles to escape jail, otherwise wait it out or pay a 50 bond.
- Bankrupt and you're out — your coins become unowned. **Last chain standing wins.**

## Files
| Path | Purpose |
|------|---------|
| `index.html` | App shell (no webxdc shim needed — transport detects the host) |
| `css/style.css` | Dark neon theme, 7×7 ring board, panels |
| `js/board.js` | 24-tile crypto board + event deck + piece palette (geometry, prices, rents) |
| `js/engine.js` | **Deterministic** game reducer (pure; shared by all peers) |
| `js/transport.js` | Local hot-seat vs real WebXDC adapter |
| `js/app.js` | UI controller (lobby, board render, actions) |
| `test/engine.test.js` | Headless engine checks — `node test/engine.test.js` |
| `build.sh` | Stage & zip the `.xdc` |
| `dist/Cryptomonopoly.xdc` | Built Delta Chat package |

## WebXDC note
The game does **not** install a fake `window.webxdc` — `transport.js` checks for a
real host. Inside Delta Chat `window.webxdc` exists, so a device registers as one
player and shares actions. In a normal browser it falls back to local hot-seat
(with an optional cross-tab BroadcastChannel mirror). No game-server is required;
state converges via the shared reducer.

## Integrity
This is an **original** game. It takes *inspiration* from classic trading-board
titles (Monopoly-style mechanics) and uses public crypto-project names as fun
flavour. It reproduces no copyrighted board-game art, text, or assets. Board-game
mechanics are not copyrightable expression; the specific tiles/names here are our own.
