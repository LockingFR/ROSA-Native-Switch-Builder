# R9 qualification - October 27, 2026

Historical candidate report. Superseded by [the final beta qualification](QUALIFICATION-R9-BETA.md)
after the complete frozen-EXE build and the owner's publication instruction.

**GO for controlled Windows testing of this candidate. No new public binary
release was created. Wine/macOS and new Switch execution remain unvalidated.**

## Executed results

- 42 automated source tests pass, including compatibility classes, encrypted
  method-zero rejection, strict SDK hashes/architecture, parent-folder resolution,
  managed-cache recovery with preservation, and diagnostic-export exclusions.
- A complete source-CLI build of the owner's enrolled input compiled all 133
  ARM64 units and linked/packaged the Horizon NRO. It used automatic Mesa and
  detected/hash-verified installed devkitPro. The output path contains spaces.
- ELF/NRO headers, native archive and game-copy digests pass; no save is present
  in the generated SD output. The original input and SDK were not modified.
- Compared with the previous R8.2 full build: zero changed C units, zero changed
  object units, and byte-identical ELF and NRO. NRO SHA-256 remains
  `47c7215f90ca9d4a3954875038e8701c2cf300c64ec1e640a63a6a6574773fd3`.
- This full build took 4314.602 seconds with two compiler jobs while development
  tests/builds also ran. It is not an isolated timing comparison with R8.2, a
  general build-time promise, or a Switch performance measurement.
- The final frozen Windows EXE starts, constructs the guided GUI, and passes
  ROM/SDK preflight with the selected *parent* SDK path. ROM diagnosis matches
  all four reference identities. A modified but still AArch64 EGL archive is
  rejected with explicit actual/expected hashes.
- A real `core.build` preflight with a manual parent SDK path resolves the
  correct SDK and completes checks before deliberately stopping at codegen.
  The default automatic path is covered by the complete 133-unit build above.
- Mesa was installed into an isolated path with spaces and reused with network
  calls forbidden; 39 SDK files verify. Existing original EGL remains SHA-256
  `a662e39dc959e7d17b8b5255f693d6bd6f6bcddc74e5ecc46d52e250ad81adab`.
- Recursive EXE/DATA/SDK/source/PYZ/ZIP inspection passes with zero issues and
  zero review findings. Source-history/credential scans also pass. The final
  archive is an explicit allowlist and contains no private game build output.

## Candidate fingerprints

`ROSA-Builder.exe`:
`88d1a8bdd843ea559ed1c311a9ff9f9e7414c024766799f8bb15995b07ac2ac0`

Unchanged qualified `ROSA-Builder.data`:
`55f225cfd9e03ca4b39997749dfa0610a9c8c67a837b77dcefcb9c1a44fd088d`

Local `ROSA-Builder-R9-20261027.zip`:
`9fd568e35207555d293603622202073e4993dde6f45290de0112970131d922c4`

Fingerprints identify the local candidate; they are not a download announcement.
The DATA retains its game-free runtime, SDK sources, patches and third-party
notices. The candidate does not contain the owner's ROM, font, saves, private
textures/shaders, generated game C/archives or playable NRO.

## Limits and the tester's report

The old Mesa message merged missing files and byte mismatches. The tester's
reported EGL prefix differs from the enrolled archive; that explains a digest
rejection if it is the file selected by the Builder. It does not prove a driver
ABI failure. Their exact binary was not available for inspection. R9's normal
solution is the authenticated bundled SDK, not accepting an unknown rebuild.

The reported ROM revision error was not reproduced with the owner's exact input.
The old encryption guard had a real method-zero gap; this is fixed and tested,
but it is not asserted to be the tester's proven cause. Their new diagnostic
can distinguish input hashes, encryption, EXE/DATA version and compatibility
without sharing game data. Different executable revisions remain blocked.

The full build above used the source CLI, not a complete run of the final frozen
EXE. The final EXE has separate GUI/ROM/SDK preflight checks. There is no fresh
clean-machine full build, usable Wine test environment, Mac host or new Switch
execution in this qualification. Byte identity with prior PC artifacts does not
substitute for those tests or prove every configuration playable.

`distribution_approved=false` is retained. Technical checks and owner publication
decisions are separate. R8/R8.1/R8.2, B20, original saves/SDK, the private archive,
the main repository's visibility and MKW are preserved.
