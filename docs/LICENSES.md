# Licenses and source availability

Original ROSA/Builder development sources remain private. Dependency terms
still apply to each distributed component; packaging does not remove them.

- Pocket Native, its bundled Zakuro/recompiler sources, and ABI identify as
  MIT. Copyright and license notices accompany the payload. Use the exact
  licensed bundled snapshot, not an unidentified upstream executable.
- Symphonia AAC/common/core/metadata are MPL-2.0. The payload includes the
  corresponding unmodified crate sources under `sources/MPL` and their license
  notices. Any future modifications to covered files must be supplied too.
  MPL's file-level obligations do not automatically require all independent
  original ROSA files to become public.
- Other Rust dependency licenses are inventoried in `licenses/rust-components.json`;
  included texts cover their MIT/Apache, BSD, ISC, Zlib and Unicode obligations.
- Rust std/compiler runtime notices accompany the static runtime. Its private
  startup-visibility adjustment does not remove upstream licensing terms.
- The upstream menu font is OFL. It is distinct from a user's external 3DS font.
- Python and Tcl/Tk notices accompany the Windows bundle. PyInstaller's
  bundling exception allows closed applications, subject to dependency terms.
- Microsoft runtime DLL redistribution terms also require review of the actual
  bundled DLLs and their permitted source, not just the Python application license.
- The compiler toolchain and Mesa SDK are not included. If they are bundled
  later, review their exact components, GCC runtime exceptions, and any source
  obligations before distribution. Mesa is not uniformly covered by one license.
- Sphaira is not included. Its separate GPL license applies to its distribution
  and modifications; Builder does not install or conceal a copy of it.

Primary references:

- [MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- [PyInstaller license and bundling exception](https://pyinstaller.org/en/stable/license.html)
- [Python license](https://docs.python.org/3.13/license.html)
- [Mesa component licensing](https://docs.mesa3d.org/license.html)
- [Microsoft redistributable components](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)

This inventory is a technical distribution review, not a claim that every
possible future combination is approved. Distribution permissions must be reviewed for the exact EXE and DATA pair before publication; this inventory is not a legal opinion.

- The R8 SDK downloader uses Python `zstandard` (BSD 3-Clause), and the bundled license notice must be included in the distribution.
