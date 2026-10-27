# ROSA Builder R9 beta - guided Windows setup

Download [R9 beta (v0.2.0-beta)](https://github.com/LockingFR/ROSA-Native-Switch-Builder/releases/tag/v0.2.0-beta),
extract the ZIP, and keep `ROSA-Builder.exe` beside `ROSA-Builder.data`.
Compare the files with the release's `SHA256SUMS-R9.txt`. R8/R8.1 assets are
preserved; the separate R8.2 work is not replaced.

Select your own compatible unencrypted `.3ds` or `.cci` dump, choose a local
output parent, then build. Compatible installed devkitPro is detected and
hash-verified; otherwise pinned official packages are installed into the new
build. **Mesa is prepared automatically from the authenticated matching DATA.**
Testers do not need to compile Mesa or configure a collection of SDK paths.

- **Diagnose ROM:** format, encryption and remaster metadata; complete file,
  game-partition, executable and exheader hashes through the build's classifier.
- **Diagnose SDK:** explicit file/hash/size/architecture checks and verified
  resolution of common parent folders. Unknown binaries remain blocked.
- **Export diagnostic:** JSON excluding game bytes, personal paths, ROM filenames,
  raw logs, keys and saves. No automatic uploads.
- Advanced retains manual SDK/import and explicit experimental code-equivalent
  options. Damaged managed Mesa caches are preserved and recovered separately.

Read [the R9 guide](docs/INSTALL-R9.md),
[the Mesa/ROM explanation](docs/MESA-AND-ROM-DIAGNOSTICS.md),
[the changelog](docs/CHANGELOG-R9.md), and
[the qualification and exact limits](docs/QUALIFICATION-R9-BETA.md).
Source and tests are under [builder](builder).

42 source tests pass. **The final Windows EXE completed the full 133-unit build**
with automatic Mesa; its NRO is byte-identical to the R8.2 reference. Separate
source-CLI compilation also matches the C/object/ELF/NRO reference. The EXE
passes GUI construction and ROM/SDK diagnostics, including parent SDK selection
and rejection of a modified AArch64 library. SDK installation and reuse were
also exercised with network calls forbidden.

A new R9 clean-machine full build, macOS/Wine and new Switch execution have not
been validated. GUI export uses the tested allowlist but its button was not
driven by desktop automation. These results are not universal playability or
performance guarantees. No usable Wine test environment was available.

The runtime DATA remains the qualified game-free B20 payload. HD/HUD research
belongs to a separate runtime branch and is not advertised as an R9 feature.
No game dump, key, firmware, save, private texture/shader payload, generated game
code, native game archive or playable NRO is distributed in this source branch.
Other players must use their own inputs and create their own saves.
The Builder never installs on the console or modifies NAND.

For older published versions, read their original release-specific guide.
Release v0.2.0-beta is explicitly authorized by the owner after Windows checks.
The automated content auditor still never grants human publication approval.

Unofficial fan research; not affiliated with Nintendo, Game Freak or The Pokemon
Company. See [license notes](docs/LICENSES.md) and [security guidance](SECURITY.md).
