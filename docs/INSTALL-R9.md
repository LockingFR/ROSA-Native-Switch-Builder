# R9 beta - three steps on Windows

Download `ROSA-Builder-R9-beta.zip` from the official v0.2.0-beta release and
extract it into a local folder. Keep all files together and compare SHA-256
values with `SHA256SUMS-R9.txt` on the release page. Older packages are preserved.

1. Keep `ROSA-Builder.exe` beside `ROSA-Builder.data` on a local Windows disk.
2. Select your own unencrypted Omega Ruby cartridge dump (`.3ds` or `.cci`).
3. Choose an output parent. Click **Build my port**. A fresh subfolder is made;
   existing outputs, console files and saves are never replaced.

Compatible installed devkitPro is discovered and checked against the DATA's
pinned hashes. Otherwise the existing official-package installer prepares an
isolated toolchain. Internet is needed for those official downloads. Mesa is
prepared automatically from the authenticated SDK ZIP inside DATA, or reused
from its verified local cache. **Testers do not need to compile Mesa.**

Use **Diagnose ROM** to inspect format, encryption flags, remaster metadata and
the four identity hashes. It uses the same classification as the build:

- Exact reference file: accepted.
- Identical game partition with different surrounding bytes: accepted.
- Identical executable and exheader with different resources: blocked by default;
  Advanced exposes the existing explicit experimental opt-in.
- Different executable/exheader: blocked. No filename trick or regional guess
  bypasses this check. CIA and standalone CXI packages remain unsupported.

Use **Diagnose SDK** for per-file SHA-256, size and AArch64 checks. Automatic is
the normal choice. If using Advanced/manual mode, select a root containing
`lib/` and `include/`; common parent folders are also resolved, but only an
exactly verified SDK is accepted. An unrecognized library is not silently used.

**Export diagnostic** creates a new JSON with hashes, compatibility results and
stage counters. It excludes game bytes, ROM filenames, personal paths, raw logs,
keys and saves. Review it before sharing. Reports never upload automatically.

The optional personal shared font and manual SDK/import modes are in Advanced.
Keep code-equivalent resources experimental. Build and relaunch behavior on
Switch remains separate from a PC build. Wine/macOS have not been validated in
this development environment; use Windows or a suitable Windows VM for now.

The SD output contains the owner's game-derived files and must remain private.
Other players must build from their own input and create their own saves.
HOME-forwarder installation and NAND changes remain separate operations.

The final Windows EXE completed a 133-unit build with automatic Mesa; its NRO
matches the R8.2 reference byte for byte. ROM/SDK diagnostic reports and the
source-level export allowlist were tested. A new R9 clean-machine full build,
Wine/macOS and new Switch execution have not been validated. The GUI export
button was not driven by desktop automation in this qualification.
