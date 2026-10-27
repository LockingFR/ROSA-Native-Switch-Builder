# R9 beta qualification - October 27, 2026

**GO for owner-authorized Windows beta v0.2.0-beta.** Wine/macOS, a new
clean-machine R9 full build and new Switch execution remain unvalidated.

## Actual final frozen EXE build

The exact release EXE completed the pipeline through its CLI: input validation,
automatic verified Mesa setup/reuse, detected and hash-verified installed
devkitPro, generation, all 133 ARM64 units, Horizon link, NRO packaging and
verified private game copying. The output path contains spaces.

- Wall time: 1877.521 seconds (31 minutes 18 seconds), four compiler jobs while
  HD development/tests also ran. This is not a controlled speed comparison.
- NRO: 198,840,376 bytes; SHA-256
  `47c7215f90ca9d4a3954875038e8701c2cf300c64ec1e640a63a6a6574773fd3`.
- NRO is byte-identical to R8.2. AArch64 ELF, NRO segments, native archive hash
  against the build record and personal game-copy hash verify.
- No save is in the generated SD output; originals were not modified.
- This was the frozen EXE, not source CLI. Clicking Build was not automated;
  GUI construction has its separate smoke test.

## Other executed evidence

- 42 source tests pass. The earlier complete source-CLI build also matched all
  133 C/object units and the ELF/NRO reference.
- Actual final EXE ROM diagnostics match all four reference identities.
- Actual final EXE automatic SDK diagnostics pass all 39 enrolled files.
  Modified AArch64 EGL bytes are rejected with precise actual/expected hashes.
  Manual parent folders resolve only to the known SDK.
- Actual EXE diagnostic JSONL reports were generated and checked for private
  paths. The source export allowlist was replayed with those frozen results and
  passes privacy checks. The GUI export button was not driven automatically:
  desktop automation could not initialize in this environment.
- Fresh Mesa install/reuse in a path with spaces passed with network forbidden.
  The final pair uses that authenticated payload. Original EGL is unchanged.
- The unchanged EXE/DATA passed recursive EXE/PYZ/ZIP/SDK/source-tar inspection
  with zero issues/findings. Exact hashes bind the audited pair. The final beta
  ZIP's eight-file allowlist, CRC and member hashes pass.
- SDK sources, local patch, notices and license texts remain included. No ROM,
  font, save, private pack/cache, generated game source/archive or playable NRO
  is in the distributable ZIP. Source credential scans pass.

## Release identities

EXE: `88d1a8bdd843ea559ed1c311a9ff9f9e7414c024766799f8bb15995b07ac2ac0`

DATA: `55f225cfd9e03ca4b39997749dfa0610a9c8c67a837b77dcefcb9c1a44fd088d`

`ROSA-Builder-R9-beta.zip`:
`bcbe2f5ee535fb51c34401d45daf474def7394858e183b115acf0c034346d60b`

The EXE identifies internally as `0.2.0-preview-r9`; this tested pair is released
as the R9 beta without a cosmetic rebuild.

## Boundaries and authorization

The tester's different EGL digest explains rejection if it is the selected file,
but does not prove an ABI failure. Automatic setup supplies the verified SDK.
The tester's precise ROM rejection is unproven; the owner's input passes. The
real method-zero encryption guard defect is fixed without asserting that it was
that tester's cause. Different game code stays blocked.

The owner explicitly instructed beta publication after essential Windows checks.
The automated auditor retains `distribution_approved=false` because it never
grants human authorization. Its field was not forced to true. Technical checks,
license/source inventory and the owner's decision remain separate.
Older releases, R8.2 work, B20, original SDK/saves, the private archive, the main
ROSA repository's privacy and MKW remain preserved.
