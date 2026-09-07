# Dist — delivery formats for the Press Kit Reassembler

Everything here packages the **original** HTML5 + WASM press-kit reassembler
(`presskit-reassembler.html`, the DOS-`.COM` generator). No studio promotional
copy; default content is original placeholder text.

| Path | Format | What it is |
|---|---|---|
| `webxdc/presskit-reassembler.webxdc` / `.xdc` | webxdc offline-app (ZIP) | index.html + `manifest.{json,xml,toml}` + icon. Drag into **Delta Chat** or open the zip in any webxdc host. |
| `war/presskit-reassembler.war` | WAR (static web app) | index.html + `WEB-INF/web.xml`. Drop into **Tomcat / Jetty / GlassFish**. |
| `java/PressKitServer.java` + `build.sh` | Java source → runnable **.jar** | JDK-only embedded HTTP server (no Maven/Gradle). Compiles to `presskit-reassembler.jar`. A JDK is required and isn't installed in this sandbox, so no prebuilt `.jar` is shipped here — run `build.sh` where a JDK exists. |
| `qbasic/PRESSKIT.BAS` | QBasic source | Scene-style intro + access gate that echoes the .COM's behaviour. Run under QBasic in DOSBox: `QB PRESSKIT.BAS`. Access code: `opensaysme`. |
| `gfx/intro.gif`, `gfx/boot.gif`, `gfx/icon.png`, `gfx/intro.txt` | animated ASCII-art | The animated-intro + "button" GIFs and the ASCII frameset (renderable with `python3 gfx/gen_gfx.py`). |

## Rebuild everything
```bash
# animated gfx
python3 gfx/gen_gfx.py
# webxdc + war
bash make_packages.sh
# jar (needs a JDK)
bash java/build.sh
```

## Verify
- webxdc/xdc & war are ordinary ZIPs (`unzip -l`).
- All packages embed the self-contained app, so they work offline.
- The WASM engine and DOS runtime inside the app were independently verified
  (cipher round-trips, Capstone disassembly, DOS-semantics execution).

## Scope note
This is a legitimate retrocomputing / scene-aesthetic homage on an *original*
tool. It is **not** affiliated with any cracking group, is not derived from warez
releases or crack archives, and reproduces no studio's promotional material.
