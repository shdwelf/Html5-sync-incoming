# Deep dive: NationalSecurityAgency on GitHub as a conversion source

*Investigation date: 2026-09-21. Method: full org API enumeration (89 repositories, 20 archived),
clone + execution of the shortlisted sources (CPython 3.11), cross-check against published
reference vectors, then conversion of the best candidate. Triggered by the request to convert
"this suite of utilities" at github.com/NationalSecurityAgency into this repo's single-file
HTML5 app format — "deep dive, no filter".*

---

## 1. Executive summary

1. **There is no HTML5 suite in the NSA org.** Of 89 repositories, exactly one is written in
   HTML — the org's own project-listing website (`nationalsecurityagency.github.io`, code.nsa.gov).
   The famous single-file HTML5 crypto suite people usually mean when they say this — **CyberChef —
   is GCHQ, not NSA**, and it is already in this repo (`webxdc/cyberchef/`). Nothing was skipped:
   the premise fails, and the *convertible* content is elsewhere in the org.
2. The org's actual center of mass is invisible from a browser: **40 Java repos** (half of them the
   ~30-repo DataWave Accumulo microservices family), 17 Python, plus C/C++/Rust systems code
   (Ghidra, eBPF, TPM, attestation). Licensing: 55× Apache-2.0, 13× GPL-2.0, rest MIT/custom/none.
3. **One repository converts beautifully**, and it happens to be a *suite of utilities* in the
   teaching sense: [`enigma-simulator`](https://github.com/NationalSecurityAgency/enigma-simulator)
   (MIT) — Enigma machine simulator (`components.py`, `machine.py`), Rejewski key-recovery attack
   (`rejewski.py`), and two lesson notebooks. It is now converted:
   **`apps/crypto/nsa-enigma.html`** (single-file, fully offline, 16-assertion self-test, CI-gated
   by `apps/crypto/nsa-enigma.test.mjs`).
4. The conversion was not a transcription — executing the NSA code against historical reference
   vectors exposed **two fidelity defects and two integrity defects in the upstream sources**
   (§4). Both machines, the attack, and the notebook golden vectors are reproduced exactly;
   a corrected historical engine is included side-by-side so the divergence is demonstrable.
5. Runner-up conversion target, deliberately deferred: the GPL-2 QGIS coordinate-tool family
   (`qgis-latlontools-plugin` and friends) — the math is portable, the apps are not, and the
   vendored third-party license mix (Boundless GPL, GeographicLib MIT, AGPL geohash, Apache OLC)
   makes a derivative app a licensing decision rather than a transcription exercise (§5).

---

## 2. Method

- `GET /orgs/NationalSecurityAgency/repos?per_page=100` — full enumeration (89 repos), capturing
  language, license, stars, archived flag, last push.
- Convertibility triage of every repo (table in §3): is the artifact's *value* expressible as a
  browser-resident single file? Server backends, desktop IDEs, kernel/eBPF, TPM and Kubernetes
  artifacts are not; pure algorithm/teaching code is.
- Shortlist: `enigma-simulator` (MIT, pure logic, self-contained, thematically adjacent to
  `apps/crypto/`), `qgis-latlontools-plugin` (GPL-2, big surface, QGIS-bound), `MADCert`
  (already JS, ASN.1-heavy), `XORSATFilter`/`fractalrabbit` (portable but niche).
- Verification-driven conversion: golden vectors first, then port, then prove.

## 3. Full org triage (89 repositories)

Verdict key: **YES** = converted here; PARTIAL = portable subset identified; POSSIBLE = portable
in principle, not worth it; no = value is not browser-expressible.

| Repository | Lang | License | ★ | Archived | What it is | HTML5-port verdict |
|---|---|---|---|---|---|---|
| [enigma-simulator](https://github.com/NationalSecurityAgency/enigma-simulator) | Jupyter Notebook | custom/MIT+ | 509 |  | Enigma machine simulator + Rejewski key-recovery lesson (Python + 2 Jupyter notebooks) | YES — pure logic, MIT, self-contained. CONVERTED to apps/crypto/nsa-enigma.html |
| [MADCert](https://github.com/NationalSecurityAgency/MADCert) | JavaScript | custom/MIT+ | 119 | yes | Root/intermediate CA + cert issuance for testing | PARTIAL — already JS; a WebCrypto single-file port is feasible but ASN.1-heavy; low single-file value |
| [qgis-cotraveler-plugin](https://github.com/NationalSecurityAgency/qgis-cotraveler-plugin) | Python | GPL-2.0 | 6 | yes | Co-traveler analysis for QGIS | PARTIAL — analysis math portable; UI bound |
| [qgis-datetimetools-plugin](https://github.com/NationalSecurityAgency/qgis-datetimetools-plugin) | Python | GPL-2.0 | 24 | yes | Date/time conversions for QGIS | PARTIAL — pure datetime math portable |
| [qgis-densityanalysis-plugin](https://github.com/NationalSecurityAgency/qgis-densityanalysis-plugin) | Python | GPL-2.0 | 28 | yes | Density heatmaps (H3/geohash) | PARTIAL — heavy QGIS binding |
| [qgis-earthsunmoon-plugin](https://github.com/NationalSecurityAgency/qgis-earthsunmoon-plugin) | QML | GPL-2.0 | 41 | yes | Sun/moon/planet positions (QML) | PARTIAL — astronomy math portable; QML UI bound to QGIS |
| [qgis-kmltools-plugin](https://github.com/NationalSecurityAgency/qgis-kmltools-plugin) | Python | GPL-2.0 | 72 | yes | KML import/export for QGIS | PARTIAL — KML is XML; converters portable |
| [qgis-latlontools-plugin](https://github.com/NationalSecurityAgency/qgis-latlontools-plugin) | Python | GPL-2.0 | 326 | yes | Coordinate capture/convert tools: DD/DMS/WKT/GeoJSON/MGRS/UPS/GEOREF/ECEF/H3/PlusCodes | PARTIAL — the conversion math is pure Python and portable; capture/zoom/digitize tools are QGIS-bound. GPL-2 + mixed vendored licenses (Boundless, GeographicLib-MIT, AGPL geohash, Apache OLC). Strong candidate #2 |
| [qgis-shapetools-plugin](https://github.com/NationalSecurityAgency/qgis-shapetools-plugin) | Python | GPL-2.0 | 166 | yes | Geodesic shape drawing for QGIS | PARTIAL — geodesic math portable; app is QGIS-bound |
| [skills-client](https://github.com/NationalSecurityAgency/skills-client) | JavaScript | Apache-2.0 | 104 |  | SkillTree client libs | PARTIAL — web JS libs, but framework-integration components |
| [dnf-model-counting](https://github.com/NationalSecurityAgency/dnf-model-counting) | C++ | none | 0 |  | Model counting (C++) | POSSIBLE — algorithmic, heavy math, niche |
| [fractalrabbit](https://github.com/NationalSecurityAgency/fractalrabbit) | Java | Apache-2.0 | 174 |  | Simulate realistic trajectory data w/ sporadic reporting (Java) | POSSIBLE — pure simulation logic could port; niche |
| [XORSATFilter](https://github.com/NationalSecurityAgency/XORSATFilter) | C | custom/MIT+ | 86 |  | XORSAT-based set-membership filters | POSSIBLE — algorithmic C lib; niche but portable; not a "utility suite" |
| [qgis-mgrs-plugin](https://github.com/NationalSecurityAgency/qgis-mgrs-plugin) | Python | GPL-2.0 | 23 | yes | MGRS capture for QGIS | covered by latlontools verdict |
| [nationalsecurityagency.github.io](https://github.com/NationalSecurityAgency/nationalsecurityagency.github.io) | HTML | Apache-2.0 | 345 |  | code.nsa.gov — the org&rsquo;s open-source listing site | already HTML — it IS a website, nothing to convert |
| .github | — | none | 2 |  | Org profile/config | no |
| [accumulo-python3](https://github.com/NationalSecurityAgency/accumulo-python3) | Python | Apache-2.0 | 39 | yes | Python client for Accumulo | no — client lib |
| [call-stack-profiler](https://github.com/NationalSecurityAgency/call-stack-profiler) | Groovy | Apache-2.0 | 32 |  | SkillTree profiler | no |
| [datawave](https://github.com/NationalSecurityAgency/datawave) | Java | Apache-2.0 | 735 |  | Accumulo ingest/query framework | no — server backend |
| [datawave-accumulo-plugins](https://github.com/NationalSecurityAgency/datawave-accumulo-plugins) | Java | none | 3 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-accumulo-service](https://github.com/NationalSecurityAgency/datawave-accumulo-service) | Java | Apache-2.0 | 6 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-accumulo-utils](https://github.com/NationalSecurityAgency/datawave-accumulo-utils) | Java | Apache-2.0 | 9 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-audit-service](https://github.com/NationalSecurityAgency/datawave-audit-service) | Java | Apache-2.0 | 9 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-authorization-service](https://github.com/NationalSecurityAgency/datawave-authorization-service) | Java | Apache-2.0 | 8 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-base-rest-responses](https://github.com/NationalSecurityAgency/datawave-base-rest-responses) | Java | Apache-2.0 | 8 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-common-utils](https://github.com/NationalSecurityAgency/datawave-common-utils) | Java | Apache-2.0 | 7 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-config-service](https://github.com/NationalSecurityAgency/datawave-config-service) | Java | Apache-2.0 | 7 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-dictionary-service](https://github.com/NationalSecurityAgency/datawave-dictionary-service) | Java | Apache-2.0 | 27 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-file-provider-service](https://github.com/NationalSecurityAgency/datawave-file-provider-service) | Java | Apache-2.0 | 3 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-hazelcast-service](https://github.com/NationalSecurityAgency/datawave-hazelcast-service) | Java | Apache-2.0 | 6 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-helm-charts](https://github.com/NationalSecurityAgency/datawave-helm-charts) | Mustache | none | 8 |  | Kubernetes charts | no |
| [datawave-in-memory-accumulo](https://github.com/NationalSecurityAgency/datawave-in-memory-accumulo) | Java | Apache-2.0 | 12 |  | DataWave microservice | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-ingest-services](https://github.com/NationalSecurityAgency/datawave-ingest-services) | Java | Apache-2.0 | 10 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-map-service](https://github.com/NationalSecurityAgency/datawave-map-service) | — | Apache-2.0 | 1 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-mapreduce-query-service](https://github.com/NationalSecurityAgency/datawave-mapreduce-query-service) | Java | Apache-2.0 | 4 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-metadata-utils](https://github.com/NationalSecurityAgency/datawave-metadata-utils) | Java | Apache-2.0 | 19 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-metrics-reporter](https://github.com/NationalSecurityAgency/datawave-metrics-reporter) | Java | Apache-2.0 | 6 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-microservices-root](https://github.com/NationalSecurityAgency/datawave-microservices-root) | Shell | Apache-2.0 | 15 |  | Microservice parent | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-modification-service](https://github.com/NationalSecurityAgency/datawave-modification-service) | Java | Apache-2.0 | 3 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-muchos](https://github.com/NationalSecurityAgency/datawave-muchos) | Shell | Apache-2.0 | 28 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-parent](https://github.com/NationalSecurityAgency/datawave-parent) | — | Apache-2.0 | 7 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-query-executor-service](https://github.com/NationalSecurityAgency/datawave-query-executor-service) | Java | Apache-2.0 | 2 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-query-metric-service](https://github.com/NationalSecurityAgency/datawave-query-metric-service) | Java | Apache-2.0 | 9 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-query-service](https://github.com/NationalSecurityAgency/datawave-query-service) | Java | Apache-2.0 | 3 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-query-storage-service](https://github.com/NationalSecurityAgency/datawave-query-storage-service) | — | Apache-2.0 | 2 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-service-parent](https://github.com/NationalSecurityAgency/datawave-service-parent) | — | Apache-2.0 | 6 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter) | Java | Apache-2.0 | 21 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter-audit](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter-audit) | Java | Apache-2.0 | 8 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter-cache](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter-cache) | Java | Apache-2.0 | 7 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter-cached-results](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter-cached-results) | Java | Apache-2.0 | 2 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter-metadata](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter-metadata) | Java | Apache-2.0 | 3 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter-query](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter-query) | Java | Apache-2.0 | 2 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-spring-boot-starter-query-metric](https://github.com/NationalSecurityAgency/datawave-spring-boot-starter-query-metric) | Java | Apache-2.0 | 2 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-stack-docker-images](https://github.com/NationalSecurityAgency/datawave-stack-docker-images) | Shell | none | 8 |  | Docker stack | no |
| [datawave-tables](https://github.com/NationalSecurityAgency/datawave-tables) | Java | none | 1 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-type-utils](https://github.com/NationalSecurityAgency/datawave-type-utils) | Java | Apache-2.0 | 9 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [datawave-utils](https://github.com/NationalSecurityAgency/datawave-utils) | Java | Apache-2.0 | 5 |  | DataWave microservice/component | no — group: ~30 datawave-* Java microservices/backends |
| [DCP](https://github.com/NationalSecurityAgency/DCP) | C | custom/MIT+ | 343 | yes | digest/stat/copy in one read pass | no — filesystem utility (C) |
| [emissary](https://github.com/NationalSecurityAgency/emissary) | Java | Apache-2.0 | 317 |  | Distributed P2P data-driven workflow framework (Java) | no — server backend |
| [Foundation](https://github.com/NationalSecurityAgency/Foundation) | Rust | Apache-2.0 | 21 |  | Formal cryptographic specifications (Rust) | no — specs/native |
| [ghidra](https://github.com/NationalSecurityAgency/ghidra) | Java | Apache-2.0 | 79224 |  | Reverse-engineering framework | no — Java desktop app |
| [ghidra-data](https://github.com/NationalSecurityAgency/ghidra-data) | — | Apache-2.0 | 218 |  | Ghidra data archives | no — data |
| [ghidra-extensions](https://github.com/NationalSecurityAgency/ghidra-extensions) | Python | none | 39 |  | Ghidra extension sources | no — Java/Python plugins |
| [ghidra-frida](https://github.com/NationalSecurityAgency/ghidra-frida) | Python | none | 16 |  | Ghidra+Frida bridge | no — tooling |
| [ghidra-lisa](https://github.com/NationalSecurityAgency/ghidra-lisa) | Java | none | 15 |  | Ghidra LISA extension | no — tooling |
| [ghidra-volatility](https://github.com/NationalSecurityAgency/ghidra-volatility) | Python | custom/MIT+ | 9 |  | Ghidra+Volatility memory forensics bridge | no — tooling |
| [kmyth](https://github.com/NationalSecurityAgency/kmyth) | C | Apache-2.0 | 114 | yes | TPM-sealed key handling | no — C, TPM hardware |
| [lemongraph](https://github.com/NationalSecurityAgency/lemongraph) | Python | custom/MIT+ | 1210 |  | Log-based transactional graph engine | no — server backend (C+Python) |
| [lemongrenade](https://github.com/NationalSecurityAgency/lemongrenade) | Java | custom/MIT+ | 320 |  | Data-driven automation platform | no — server backend |
| [maat](https://github.com/NationalSecurityAgency/maat) | C | custom/MIT+ | 32 | yes | Software integrity measurement & attestation service | no — OS-level service |
| [openflame](https://github.com/NationalSecurityAgency/openflame) | C | BSD-3-Clause | 5 |  | C systems project | no — native |
| [PACE](https://github.com/NationalSecurityAgency/PACE) | — | Apache-2.0 | 17 |  | Client-side crypto enforcement for Accumulo | no — backend |
| [PACE-python](https://github.com/NationalSecurityAgency/PACE-python) | Python | BSD-2-Clause | 15 |  | PACE Python client | no |
| [pelz](https://github.com/NationalSecurityAgency/pelz) | C | Apache-2.0 | 35 | yes | Key management service (C) | no — service + TPM |
| [qgis-bulk-nominatim](https://github.com/NationalSecurityAgency/qgis-bulk-nominatim) | Python | GPL-2.0 | 38 | yes | Bulk geocoding for QGIS | no — QGIS+network-bound |
| [qgis-d3datavis-plugin](https://github.com/NationalSecurityAgency/qgis-d3datavis-plugin) | Python | GPL-2.0 | 134 | yes | D3 date/time heatmap for QGIS | no — QGIS-bound |
| [qgis-h3library-plugin](https://github.com/NationalSecurityAgency/qgis-h3library-plugin) | C | GPL-2.0 | 4 | yes | H3 lib installer for QGIS | no — packaging |
| [qgis-lockzoom-plugin](https://github.com/NationalSecurityAgency/qgis-lockzoom-plugin) | Python | GPL-2.0 | 21 | yes | QGIS tile-scale lock | no |
| [qgis-searchlayers-plugin](https://github.com/NationalSecurityAgency/qgis-searchlayers-plugin) | Python | GPL-2.0 | 80 | yes | Vector layer search for QGIS | no — QGIS GUI-bound |
| [qonduit](https://github.com/NationalSecurityAgency/qonduit) | Java | Apache-2.0 | 68 |  | WebSocket lib for Accumulo | no — server backend |
| [rank-based-linkage](https://github.com/NationalSecurityAgency/rank-based-linkage) | Java | Apache-2.0 | 6 |  | Entity resolution (Java) | no — backend lib |
| [seabee](https://github.com/NationalSecurityAgency/seabee) | Rust | custom/MIT+ | 66 |  | eBPF policy hardening (Rust) | no — kernel/ebpf |
| [SIMP](https://github.com/NationalSecurityAgency/SIMP) | Ruby | custom/MIT+ | 1336 | yes | Ruby system-automation/config-management stack (SCAP/CIS hardening) | no — server-side infrastructure |
| [skills-client-examples](https://github.com/NationalSecurityAgency/skills-client-examples) | Java | Apache-2.0 | 34 |  | SkillTree examples | no |
| [skills-docs](https://github.com/NationalSecurityAgency/skills-docs) | JavaScript | Apache-2.0 | 66 |  | SkillTree docs site | no — docs |
| [skills-service](https://github.com/NationalSecurityAgency/skills-service) | Groovy | Apache-2.0 | 654 |  | SkillTree gamified micro-learning platform | no — server platform |
| [skills-stress-test](https://github.com/NationalSecurityAgency/skills-stress-test) | Groovy | Apache-2.0 | 30 |  | SkillTree load test | no |
| [timely](https://github.com/NationalSecurityAgency/timely) | Java | Apache-2.0 | 398 |  | Accumulo time-series DB | no — server backend |
| [TraceAnalysis](https://github.com/NationalSecurityAgency/TraceAnalysis) | Rust | Apache-2.0 | 71 |  | Trace analysis (Rust) | no — native tooling |

---

## 4. The converted suite: `enigma-simulator` — findings ("no filter" section)

### 4.1 What the suite is

| File | Lines | Role |
|---|---|---|
| `components.py` | 173 | Rotor I/II/III/V wirings + notches, reflector B, 6-plug-max plugboard |
| `machine.py` | 141 | The 3-rotor machine: Keyboard → Plugboard → L→M→R → Reflector |
| `rejewski.py` | 167 | Rejewski's 1932 attack: AD/BE/CF permutations → cycles → chain index → catalogue |
| `BreakingEnigma.ipynb` / `MasterEnigmaCracker.ipynb` | — | Guided lesson: recover the day key from double-enciphered message keys |

License: MIT (© 2019) with the standard NSA notice that U.S. Government portions are public
domain under 17 U.S.C. Clean for conversion with attribution.

### 4.2 ENG-1 — the NSA "Enigma" is not a historical Enigma (fidelity)

Executed against the canonical published vector (rotors I-II-III left→right, reflector B,
rings AAA, message key AAA, no plugs — the *same* vector family the NSA's own wiring-table
provenance link documents):

- real Enigma I / corrected model: `AAAAA → BDZGO` (and rings BBB → `EWTYX`)
- NSA simulator as published: `AAAAA → FTZMG`

Root cause, from `machine.py.encode_decode_letter`: it calls `self.l_rotor.step()` — the
**left** rotor steps every keypress and cascades rightward; the historical machine drives the
**right** rotor and cascades leftward with the double-stepping anomaly. Additionally the
simulator has **no Ringstellung** (so ring-dependent vectors are inexpressible), **no rotor IV**,
and a hard-wired reflector B. The Rejewski lesson is unaffected — the attack needs a
deterministic involution machine, not history — but ciphertext from the NSA simulator is not
historically valid traffic. The converted app carries **both engines** and asserts the divergence
(`FTZMG` in NSA mode, `BDZGO` + double-step sequence `ADU→ADV→AEW→BFX` in historical mode).

### 4.3 ENG-2 — the lesson notebooks contain stale data (integrity)

`MasterEnigmaCracker.ipynb` cell 22 looks up `chains_dict['AD:6677 BE:11221010 CF:221111']`,
but the index recomputed from the very cycles the same notebook prints (cells 17–19) is
`AD:222299 BE:11221010 CF:6677`. Both strings resolve to the *same* candidate pair
(`YAQ/II-I-III` true secret + `AAC/II-III-I` decoy) in the pickle — so the printed outputs and
the lookup string come from different generations of the intercept data, never reconciled. The
markdown "recall that these are of the form…" cycle strings disagree with the code output in
both notebooks.

### 4.4 ENG-3 — the lesson's data files were never committed (integrity)

`message_key_encrypts.pickle` and `chains.pickle` are `load()`ed by the notebooks and
`rejewski.py` but absent from the repository — the lesson cannot run as shipped. What survives is
printed notebook output: 23 intercepts and the complete AD/BE/CF cycles. From those prints this
conversion reconstructed the full permutations and their true index; the app regenerates an
equivalent scenario deterministically (seeded PRNG, same secret `YAQ` / `II-I-III` /
`JS HY NF`), and its generated traffic provably yields the *same* chain index as the 1932
reconstruction — an end-to-end demonstration of the plugboard-conjugation invariance
(`AD = Q∘T∘Q`, cycle lengths invariant), which is the mathematical heart of the attack.

### 4.5 ENG-4 — code-quality notes (kept faithfully where harmless)

- `rejewski.py`: `if i is 1` / `is 2` — integer identity comparison (works on CPython small-int
  caching only); `alphabet.replace(next_letter, '')` — result discarded, a no-op; the permutation
  maps are filled by encrypting *random* keys until complete (expected hundreds of enciphers;
  this port uses an exact sweep and, for the catalogue, direct permutation composition).
- `components.py`: the "maximum of 6 swaps" cap only rejects a single update listing >6 pairs —
  cumulative smaller updates can exceed 6. The port preserves the cap semantics and the UI
  enforces the real limit.
- Performance: building the full chains dictionary in CPython took ~25 min in this sandbox;
  the JS port's composed-permutation search covers all 105,456 settings in ~4 s, with the fast
  path asserted equal to the literal encipher-based reference path (self-test §14).

### 4.6 What the conversion adds beyond the source

- A corrected **historical Enigma I engine** (right-hand drive, double-stepping, Ringstellung,
  reflectors B/C, rotors I–V) validated on the published `BDZGO`/`EWTYX` vectors.
- Automated **plugboard recovery** with exact constraint matching (`AD(u) = Q(T(Q(u)))`, 78
  constraints) — the step the NSA notebooks leave to manual guessing — plus decoy-candidate
  rejection by English-scoring the decrypted traffic.
- A deterministic scenario generator replacing the lost pickles, and the in-browser catalogue
  (105,456 settings → the notebook's exact candidate pair).
- A 16-assertion self-test suite, run both in-page and in CI via `node --test
  apps/crypto/nsa-enigma.test.mjs`, which extracts the core from the committed HTML so the app
  and its proof can never drift apart.

## 5. Deliberately deferred: the QGIS coordinate-tool family

`qgis-latlontools-plugin` (GPL-2) is a genuine "suite of utilities" — capture/convert/zoom
across DD, DMS, WKT, GeoJSON, MGRS, UTM, UPS, GEOREF, ECEF, H3, Plus Codes. Assessment:

- **Portable core**: the converters are pure-Python (`utm.py`, `georef.py` — adapted from
  GeographicLib MIT, `maidenhead.py`, `geohash.py` — AGPL, `olc.py` — Apache-2.0, `mgrs.py` —
  Boundless-derived GPL, `ups.py`, `ecef.py`). A single-file "coordinate notation toolbox" is
  a viable future conversion.
- **Bound to QGIS**: capture, zoom-to, digitize, extent tools — the majority of the plugin —
  have no browser meaning.
- **License surface**: the app would be a GPL-2 derivative with AGPL- and Apache-licensed
  vendored components. That is a licensing decision this repo's mixed-collection model can
  carry but should be made deliberately, not inherited silently.

## 6. Also considered and rejected

- `MADCert` (JS, MIT-ish): a WebCrypto port is feasible but it is X.509/ASN.1 infrastructure
  tooling; the single-file form adds little.
- `XORSATFilter`, `fractalrabbit`, `dnf-model-counting`: portable algorithm cores, no utility
  narrative, niche audiences.
- `ghidra` ecosystem, `seabee`, `pelz`, `kmyth`, `maat`, `TraceAnalysis`, `openflame`,
  `Foundation`: native/OS-level tools — the opposite of a browser artifact.
- `datawave-*` (~30 repos), `SIMP`, `lemongraph`, `emissary`, `timely`, `qonduit`,
  `skills-*` (SkillTree), `accumulo-python3`, `PACE*`, `rank-based-linkage`: server platforms
  and libraries.
- `qgis-*` remaining plugins: thin wrappers around QGIS APIs (except where covered in §5).

## 7. Conversion provenance record

- Source: `NationalSecurityAgency/enigma-simulator`, commit
  `f234ee68291ccea70446bcbcb1468a2708277ab8` (HEAD, last push 2020-08-13, author Christopher
  Tubbs; suite authored by Emily Willson per file headers).
- Artifact: `apps/crypto/nsa-enigma.html` (single file, 0 network references, ~90 KB).
- Tests: `apps/crypto/nsa-enigma.test.mjs` — 19 node:test cases incl. the offline-file check.
- Golden vectors honored: `this is a test → ZPJJSVSPGBW` (notebooks), the 105-letter Einstein
  ciphertext at TDS with plugs JS/HY/NF (notebook cell 29), `BDZGO`/`EWTYX` (historical
  reference), chain index `AD:222299 BE:11221010 CF:6677`, candidate pair
  `{YAQ/II-I-III, AAC/II-III-I}`, plugboard `{JS, HY, NF}`.
