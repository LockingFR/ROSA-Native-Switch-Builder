# Mesa and ROM compatibility: what the checks mean

## Mesa: version strings do not identify a binary

The R8.1/R8.2 check `sdk.verify_mesa_files` compares file bytes with the enrolled
SDK hashes. Its older message merged missing files and different hashes into
`Missing or incompatible Mesa SDK file: lib/libEGL.a`.

The known working EGL archive SHA-256 is:

`a662e39dc959e7d17b8b5255f693d6bd6f6bcddc74e5ecc46d52e250ad81adab`

A library with a different SHA is rejected even if its reported Mesa version
is 26.2.4 and its source commit starts with `0ff5207`. This is an intentional
validation boundary, not proof that the other library is inherently unusable.
It has not been enrolled or tested as an interchangeable SDK.

R9 reports the relative filename, expected/actual SHA-256 and size, missing-file
status and static AArch64 object validation. It distinguishes unrecognized bytes
from an invalid archive. Manual parent-folder selection resolves only a matching
known SDK. The system installation is never repaired or overwritten implicitly.

The default solution is **Automatic Mesa setup** using the authenticated bundled
SDK. The EXE pins DATA, DATA pins the SDK ZIP, and the SDK inventory pins each
file. Cache reuse is verified again. Local imports require the same approved ZIP;
there is no arbitrary Mesa download or unverified fallback.

## Reproducing the supported installation and maintaining the SDK

The reused R8.2 SDK comes from `danfromtico/mesa-switch` commit
`0ff52079ca9e9e837ed27eb95a8d239f439a1864`. Its source snapshot, local patch and
license/notices remain inside the unchanged DATA package. The final qualified
SDK inventory includes 39 files, including `sources/SOURCE-EXCLUSIONS.json`;
the preliminary 38-file inventory predates that qualification fix.

ROSA's `tools/configure_mesa.py` records the actual maintained profile: static
release, optimization 2, Nouveau, Switch EGL/GLES2, shader cache enabled, GLES1
disabled, LLVM/Vulkan/LTO/zstd disabled. It also uses local Windows cross-build
fixes and driver-cache instrumentation. Upstream `build-opengl.sh` defaults
include GLES1 enabled and xmlconfig/expat auto; same source commit alone cannot
promise identical archives. Actual tester build options were not supplied.

Testers reproduce the supported *installation* by using the matching EXE/DATA
pair and Automatic setup; no Meson, Zig or Rust installation is needed. A
maintainer rebuilding Mesa must use isolated source/build/install directories,
the pinned source and packaged changes, and the recorded profile. A new archive
requires new byte/architecture checks, a real Horizon link and console testing
before its hashes can be enrolled. A fresh bit-identical Mesa source build was
not performed during R9 qualification; do not claim otherwise.

## ROM: separate file identity, partition identity and code identity

R8 originally accepted one full-file hash. R8.1 introduced partition/code/exheader
classification; R8.2 retained it. R9 keeps those controls and uses one shared
classifier for the GUI, diagnostic and build, adding `.cci` NCSD support.

The enrolled reference file SHA-256 is:
`bd5b432f304edaf04f92fa853f5e52bd0345474e13983306c26c88cfc53f4136`.
The game partition SHA-256 is:
`7d2eb6ec0a241e055b295101d310328db58289ee53d84a78737d0ee452ea8d41`.
The stored `.code` SHA-256 is:
`7046fdd23c28858856cea14b359b69caca68742fb21acaa49f737ca610fa9bd5`.
The exheader SHA-256 is:
`63c5eeddc891be395bf24b1882448f2bc4b50ee7e4deb8e6be75b70cc2eb67a3`.

R9 exports all four actual hashes and their reference comparisons, including
when an otherwise parseable input is rejected. It also checks that size/mtime
did not change during diagnosis. No game bytes are exported.

An old encryption guard required both the NoCrypto flag to be absent and the
crypto-method byte to be nonzero. Method-zero encrypted containers could reach
revision checking and receive a misleading revision error. R9 requires the
NoCrypto flag; it does not decrypt inputs or handle keys.

The owner's actual local reference passes all four comparisons. A truly identical
full-file SHA cannot be classified as a different executable by the same build.
The tester's precise cause remains unproven without a report from that exact
EXE/DATA/input combination. Do not infer a region difference or a Wine bug from
the old message alone. Wine was not installed in the available test environment;
no macOS/Wine compatibility claim is made.
