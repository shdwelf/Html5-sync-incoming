# Dist — delivery formats for the Press Kit Reassembler

Everything here packages the **original** HTML5 + WASM press-kit reassembler
(`presskit-reassembler.html`, the DOS-`.COM` generator). No studio promotional
copy; default content is original placeholder text.

| Path | Format | What it is |
|---|---|---|
| `webxdc/presskit-reassembler.xdc` | webxdc offline-app (ZIP) | `index.html` + `manifest.toml` + `icon.png` — exactly the three entries the container spec knows. No `manifest.json`, no `manifest.xml`, no `webxdc.js` and no `.webxdc` twin: all four were shipped at some point and all four are wrong (REVIEW.md XDC-2/-3/-5). index.html plays an animated ASCII **boot splash** on open, then reveals the form. Drag into **Delta Chat** or any webxdc host; this app is single-player and never calls the webxdc API, so it needs no shim. |
| `war/presskit-reassembler.war` | WAR (static web app) | index.html + `WEB-INF/web.xml`. Drop into **Tomcat / Jetty / GlassFish**. |
| `java/PressKitServer.java` + `build.sh` | Java source → runnable **.jar** | JDK-only embedded HTTP server (no Maven/Gradle). Compiles to `presskit-reassembler.jar`. A JDK is required; the sandbox's network egress blocks every JDK-binary host (Adoptium's GitHub assets, Oracle, Azul, BellSoft, Debian mirrors all time out), so no prebuilt `.jar` ships here. Run `bash java/build.sh` wherever a JDK exists (any OpenJDK 17+). |
| `qbasic/PRESSKIT.BAS` | QBasic source | Scene-style intro + access gate that echoes the .COM's behaviour. Run under QBasic in DOSBox: `QB PRESSKIT.BAS`. Access code: `opensaysme`. |
| `gfx/intro.gif`, `gfx/boot.gif`, `gfx/icon.png`, `gfx/intro.txt` | animated ASCII-art | The animated-intro + "button" GIFs and the ASCII frameset, all produced by `python3 gfx/gen_gfx.py` (needs `pyfiglet` + `Pillow`). Regenerated 2026-09-19: `intro.gif`, `boot.gif` and `intro.txt` came back **byte-identical** to what was committed, which is what proves the icon is the only thing that changed when it went 96×96 → 256×256. |

## Rebuild everything
```bash
# animated gfx (intro.gif, boot.gif, intro.txt, icon.png)
pip install pyfiglet pillow   # add --break-system-packages on PEP 668 distros
python3 gfx/gen_gfx.py
# webxdc + war, then verified: manifest parsed, package run through webxdc_tool.py validate
bash make_packages.sh
# jar (needs a JDK)
bash java/build.sh
```

## Verify
- webxdc/xdc & war are ordinary ZIPs (`unzip -l`).
- All packages embed the self-contained app, so they work offline.
- The WASM engine and DOS runtime inside the app were independently verified
  (cipher round-trips, Capstone disassembly, DOS-semantics execution).

## Open-source Java options (to build the .jar)
The JDK is the open-source **Eclipse Temurin** distribution of OpenJDK
(Adoptium project, GPLv2 + Classpath Exception) — `github.com/adoptium`.
The `.java` here only needs a plain `javac`/`jar`, so no IDE is required;
if you want one, the open-source choices are **Eclipse IDE** (EPL) or
**VS Code + the "Extension Pack for Java"** — note **JCreator is proprietary
shareware**, not open source.

## Scope note
This is a legitimate retrocomputing / scene-aesthetic homage on an *original*
tool. It is **not** affiliated with any cracking group, is not derived from warez
releases or crack archives, and reproduces no studio's promotional material.
