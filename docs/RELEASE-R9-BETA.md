# ROSA Builder R9 beta - guided Mesa and ROM diagnostics

Build your own local port on Windows without compiling Mesa yourself.
This release updates the Builder; its game-free runtime DATA remains B20.
HD/HUD research is separate and is not included in this release.

## Start here

1. Download **ROSA-Builder-R9-beta.zip** and **SHA256SUMS-R9.txt** below.
2. Extract the ZIP into a local Windows folder. Keep EXE and DATA together.
3. Open the EXE, select your own supported unencrypted `.3ds`/`.cci` dump and
   output folder, then select **Build my port**. Leave dependency setup automatic.

Automatic Mesa uses the bundled hash-verified SDK. Compatible installed
devkitPro is detected; otherwise pinned official packages are downloaded into
an isolated workspace. There is no global SDK replacement or console installer.

Use **Diagnose ROM**, **Diagnose SDK** and **Export diagnostic** for support.
Reports contain identities/counters rather than ROM data, keys, saves, filenames
or personal paths. Real executable incompatibilities remain blocked.

## Verified on Windows

- 42 source tests pass.
- The **actual final frozen EXE** completed all 133 compilation units, linked
  Horizon and generated a NRO byte-identical to the R8.2 reference.
- Its actual ROM/SDK diagnostics pass: all four ROM reference identities and
  all 39 enrolled SDK files. JSONL reports were generated and privacy-checked.
- GUI construction, unknown-library rejection, safe export allowlists and
  offline Mesa installation/reuse were checked.
- ZIP CRC/member hashes and the EXE/DATA binding are verified. SDK source
  snapshots, patches, licenses and third-party notices accompany the DATA.

## Beta limits

Wine/macOS, a new clean-machine R9 full build and a new Switch execution of
this release have not been validated. The GUI export button was not driven by
desktop automation; its underlying allowlist has source tests. Full compilation
was performed using the frozen EXE's CLI, not automated clicking of Build.
Windows build success does not certify every scene, controller or performance.

Use your own legally obtained compatible inputs. No ROM, key, font, save,
private texture/cache, generated game code or playable NRO is included.
Each new player creates their own save. The Builder never modifies originals,
existing saves, HOME installations or NAND. Keep your generated SD output private.

New areas/attacks can compile shaders. After saving, closing and relaunching
may reduce repeat compilation with compatible cached shaders; it does not fix
every source of lag. Avoid B20's known L+R+Plus soft-reset failure.

Older releases remain intact. The owner explicitly authorized this beta after
Windows qualification. The automated content auditor's human-approval field
remains false by design and was not forced to true.
