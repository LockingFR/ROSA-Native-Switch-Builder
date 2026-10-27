# ROSA Builder R9 - guided development preview

This branch contains the new guided Windows Builder source and qualification
candidate. **No new R9 public release has been published.** Existing downloads
on [Releases](https://github.com/LockingFR/ROSA-Native-Switch-Builder/releases)
remain unchanged and do not necessarily include these features.

Select your own compatible unencrypted `.3ds` or `.cci` dump, choose a local
output parent, then build. Compatible installed devkitPro is detected and
hash-verified; otherwise the official pinned toolchain is installed into the
new build. **Mesa setup is automatic from the authenticated matching DATA**;
testers do not need to compile Mesa or configure many paths.

- **Diagnose ROM:** format/encryption/remaster metadata and complete file,
  game-partition, executable and exheader hashes, through the same classifier
  as the build. Different executables remain blocked.
- **Diagnose SDK:** exact file/hash/size/architecture details; common parent
  selections resolve without accepting unknown binaries.
- **Export diagnostic:** reviewed JSON without game bytes, personal paths,
  ROM filenames, raw logs, keys or saves. No automatic upload.
- Advanced retains manual SDK/import and explicit experimental code-equivalent
  options. A damaged managed Mesa cache is preserved and recovered separately.

Read [the R9 guide](docs/INSTALL-R9.md),
[the Mesa/ROM explanation](docs/MESA-AND-ROM-DIAGNOSTICS.md), and
[the changelog](docs/CHANGELOG-R9.md). Source/tests are under [builder](builder).
The runtime DATA remains the qualified game-free B20 payload; HD/HUD research
is a separate private-runtime branch, not an advertised R9 runtime feature.

Forty-two automated source tests pass. Frozen Windows GUI construction, ROM
identity diagnosis, exact SDK parent resolution and rejection of a modified
AArch64 library pass. Mesa installation/reuse from DATA was exercised with
network calls forbidden. These checks do not establish macOS/Wine or Switch
validation. Final full-build qualification is recorded separately before any
release decision. Wine was not installed in the available environment.

No dump, keys, firmware, save, private texture/shader payload, generated game
source, native game archive or playable game NRO is included in this source
branch. Other players use their own inputs and create their own saves.
The Builder never installs on the console or modifies NAND. Public source
updates do not constitute approval of a new binary release.

## Existing published reference

# ROSA Native Switch Builder ðŸŽ®

**ROSA Builder v0.1.0-beta (R8) â€” experimental community test.**

A Windows desktop application to build an experimental **PokÃ©mon Omega Ruby** native homebrew port for a modified Nintendo Switch, using **your own compatible game dump**. This is **not** a ROM download, an emulator, or an official Nintendo product.

The application uses static recompilation of the game's 3DS ARM11 code into locally generated native ARM64 code, a B20-reference runtime adapted from Pocket Native / Zakuro, and a graphics stack based on Mesa Switch / OpenGL ES.

## Download & installation

Get the **matching** `ROSA-Builder.exe` and `ROSA-Builder.data` from the [Releases](https://github.com/LockingFR/ROSA-Native-Switch-Builder/releases) page, save them **next to each other**, and check the published hashes. Read **[INSTALL.md](docs/INSTALL.md)** before building.

The Builder only prepares **local files**; it does not transfer anything to your Switch, modify NAND, install a HOME forwarder or upload your game data.

## Requirements

- 64-bit Windows PC, sufficient free storage (at least **8 GiB** in the build output directory).
- **Your own unencrypted, exact supported PokÃ©mon Omega Ruby `.3ds` cartridge dump**. Other regions, revisions, `.cia` and encrypted files are not currently supported. The Builder checks the complete file hash.
- A modified Switch capable of running homebrew in application mode.
- An **exact compatible Mesa Switch 26.2.4 SDK**, **not provided by the Builder**.
- Either a compatible existing devkitPro SDK, or R8's **experimental optional automatic download** of six version-pinned official devkitPro packages (internet needed in this mode).
- Optional compatible personal shared font (not distributed).

## Status / test evidence

- **R7:** the owner reports that a Builder-generated NRO ran on a real Nintendo Switch.
- **R8:** the frozen EXE starts and shows the managed-SDK option on Windows; the EXE and DATA were built and paired. **The complete R8 managed-SDK installation and an R8-generated NRO on Switch are not yet independently validated.**
- Report failures through [GitHub Issues](https://github.com/LockingFR/ROSA-Native-Switch-Builder/issues) with **redacted** error details only. A successful PC build is not a guarantee that every Switch configuration works.

## Safety and limitations

Do not post ROMs, generated game C code, keys, saved games, NRO/ELF files, console identities, full build workspaces, or private shader caches. Even a diagnostic log may contain sensitive information; review it before sharing.

There is no official game data, no decrypted ROM, no key distribution, no proprietary recompiled game code, no Nintendo artwork and no prebuilt playable game executable included in the Builder downloads. Local outputs remain your own responsibility.

See [known limitations](docs/LIMITATIONS.md), [licenses and notices](docs/LICENSES.md), and [security guidance](SECURITY.md).

**Unofficial fan-made research project. Not affiliated with, sponsored by, or endorsed by Nintendo, Game Freak or The PokÃ©mon Company.**
