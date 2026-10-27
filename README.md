# ROSA Builder R9 - guided development preview

This branch contains the new guided Windows Builder source and a locally
qualified Windows candidate. **No new R9 public binary release is published.**
Existing [Releases](https://github.com/LockingFR/ROSA-Native-Switch-Builder/releases)
remain unchanged; older downloads do not necessarily include these features.

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
[the qualification and exact limits](docs/QUALIFICATION-R9.md).
Source and tests are under [builder](builder).

42 source tests pass. The complete PC source-CLI build compiled 133 native units;
its C, object, ELF and NRO outputs match the earlier R8.2 reference exactly.
The final frozen EXE passes GUI construction and ROM/SDK checks, including a
parent SDK selection and rejection of a modified AArch64 library. SDK installation
and reuse were also exercised with network calls forbidden.

The complete build above used the source CLI; a complete run of the final frozen
EXE, a new clean-machine full build, macOS/Wine and Switch execution have not been
validated. These results are not universal playability or performance guarantees.
No usable Wine test environment was available.

The runtime DATA remains the qualified game-free B20 payload. HD/HUD research
belongs to a separate runtime branch and is not advertised as an R9 feature.
No game dump, key, firmware, save, private texture/shader payload, generated game
code, native game archive or playable NRO is distributed in this source branch.
Other players must use their own inputs and create their own saves.
The Builder never installs on the console or modifies NAND.

For existing published versions, read their original release-specific guide.
A source update does not change old releases or approve a new binary release.

Unofficial fan research; not affiliated with Nintendo, Game Freak or The Pokemon
Company. See [license notes](docs/LICENSES.md) and [security guidance](SECURITY.md).
