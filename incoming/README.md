# incoming — unprocessed sync payload

Raw archives exactly as they arrived. **Nothing in here is a deliverable**, and
nothing in `apps/`, `webxdc/` or `projects/` depends on it at build time.

It is kept for two reasons: provenance (every classified artifact in the repo can
be traced back to the dump it came out of), and the fact that these archives
contain builds that were never promoted to `apps/` — `internal-storage.7z` alone
holds 302 HTML files.

| Path | Contents |
|------|----------|
| `workspaces/` | 19 Arena workspace snapshots. Filename UUIDs kept verbatim — the UUID is the only stable id the sync source provides. ZIP timestamps are normalised to 1980-01-02 (machine-generated). What is inside each is tabulated in [../INVENTORY.md](../INVENTORY.md#incomingworkspaces--19-arena-workspace-snapshots). |
| `exports/` | 31 named app-export ZIPs, internal timestamps 2015-11-19 → 2026-09-14. |
| `internal-storage.7z` | 6.24 MB, 302 HTML entries. The largest object in the repo and the only 7z. |

## Two things worth knowing

**`exports/radar-scope-webxdc-INVALID.zip` is deliberately broken.** It was
committed as `radar_scope_webxdc.zip` and is an invalid webxdc container on three
counts: `.zip` extension, every entry nested under `webxdc-radar/` so
`index.html` was not at the ZIP root, and a manifest using a non-existent `init`
key. It was rebuilt as `webxdc/radar-scope/dist/radar-scope.xdc`; this copy stays
as evidence. The `-INVALID` suffix keeps it findable and stops anyone shipping it
by accident.

**`internal-storage.7z` is still unclassified** (open item REPO-3). It overlaps
heavily with files that used to sit loose at the repo root — `index (1).html`
through `index (58).html`, twenty `seize_quartiers_quine_<timestamp>.html`
builds, nine `generator.offline.repaired (N).html`, an `index.html.old` — so it
looks like the working directory the root-level exports were downloaded *from*.
Unpacking needs `py7zr`, which is not a declared dependency of anything here.

## The validator skips this directory

`webxdc/webxdc_tool.py` excludes `incoming/` by default (`DEFAULT_EXCLUDE`),
because treating deliberately-preserved mis-packaged artifacts as deliverables
produces false failures. To scan them anyway:

```bash
python3 webxdc/webxdc_tool.py validate --all
```

## Naming

` (N)` collision suffixes were resolved on the way in — see the rename table in
[../INVENTORY.md](../INVENTORY.md#incomingexports--31-app-export-zips). Where a
pair genuinely differed, the newer archive by internal timestamp became the
higher `-rN`; where a name was already a meaningful slug, it was moved unchanged.
