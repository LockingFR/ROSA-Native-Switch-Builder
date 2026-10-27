# R9 beta (v0.2.0-beta)

- Replace the long mandatory SDK form with dump/output selection and automatic,
  hash-verified dependency selection. Keep manual options in Advanced.
- Use the existing authenticated bundled Mesa SDK and verified cache; testers
  no longer need to compile a Mesa driver.
- Add **Diagnose ROM**, **Diagnose SDK**, and a shareable diagnostic JSON export.
- Report exact SDK file/size/hash/architecture failures and resolve common SDK
  parent folders without accepting unknown binaries.
- Compare full cartridge, NCCH partition, executable and exheader identities
  through one classifier. Retain strict and explicit experimental classes.
- Detect method-zero encrypted NCCH inputs before executable revision checking.
- Support `.cci` NCSD names, retain CIA/CXI rejection, and check input stability.
- Fix detected-installed-devkitPro plus automatic-Mesa build orchestration.
- Preserve B20 runtime DATA, original SDKs, existing releases and all user saves.

The final frozen Windows EXE completed all 133 compilation units and generated
the same NRO as the R8.2 reference. 42 source tests, real EXE ROM/SDK diagnostics,
offline Mesa install/reuse and container checks pass. This beta is Windows
qualified; Wine/macOS, a new clean-machine R9 build and new Switch execution
remain unvalidated. No HD/HUD runtime change is included in this Builder release.
