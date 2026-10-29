# R9.1 diagnostic correction (2026-10-29)

R9's `EXECUTABLE_NOT_ENROLLED` merged a different stored `.code` with a
different exheader. R9.1 distinguishes `CODE_NOT_ENROLLED`,
`EXHEADER_NOT_ENROLLED`, and `RESOURCES_NOT_VALIDATED`. GUI, CLI diagnosis and
build use the same strict classifier. The experimental option still requires
both code and exheader identity. There is no new variant enrollment.

Diagnostic schema 2 adds numeric execution/memory metadata, SHA-256 fingerprints
of every declared exheader block, and separate RomFS, non-code ExeFS, ExeFS
header and NCCH header hashes. A different NCCH hash alone does not prove
different resources. Missing comparisons are `null`, never inferred matches.
Export reconstructs these nested fields from an allowlist. No ROM, service
names, dependency bytes, paths, keys or saves are exported.

The comparison baseline was derived locally with `reference_diagnostics.py`
from the exact full-file SHA-256-verified B20 input. This baseline is diagnostic
only and cannot authorize a build. ExeFS/header overlaps and invalid resource
ranges are rejected. B20's acceptance hashes and runtime DATA are unchanged.

## Independent tester: compatibility remains undemonstrated

The supplied schema-1 report identifies the expected R9 EXE and matching DATA,
an unencrypted NCSD input, title `000400000011C400`, remaster 3 and 3,039,008
stored code bytes. The stored code hash matches B20; the exheader hash is
`34bb6a98bafe13e957ed15d195b263a9447ca351caf771489f3b4c33a846c32c`.
The partition also differs. The report contains no field-level exheader or
resource information. Matching code length and remaster do not close that gap.
R9.1 continues to refuse this variant, including with the experimental option.

### Required non-proprietary diagnostic data

Run R9.1 **Diagnose ROM**, then **Export diagnostic** on the same original local
input. Share only the exported schema-2 JSON. It must include:

- Package EXE/DATA hashes, input stability, full-file/NCCH/stored-code/exheader
  identities and exheader size, tying metadata to the inspected input.
- Text/rodata/data addresses, page counts and byte lengths; stack and BSS sizes;
  SCI flags (especially BLZ compression); remaster and save/jump metadata.
- Program/core IDs, system/CPU/cache flags, scheduling flags/priority and
  resource category; numeric kernel descriptors for memory type, SVC masks,
  mapped ranges and handle limits.
- Block hashes for dependencies, resource limits, storage access, service
  access, kernel capabilities, ARM9 access and reserved bytes. These identify
  differences without distributing their raw contents. If a block differs,
  its semantics must be reviewed locally; a matching subset cannot clear it.
- RomFS length/hash, non-code ExeFS hash, and NCCH/ExeFS header hashes with
  reference comparisons. No resource equality can be inferred from the old
  partition mismatch.

### Why the exheader matters and how enrollment could proceed

The maintained native source was inspected at
`builder/codegen/src/main.rs` and under `third_party/pocket-native/`:
`recompiler/src/rom.rs` uses the compression flag;
`recompiler/src/image.rs` uses segment addresses, page counts and lengths to
discover/recompile code; `engine/fs/src/ncch.rs` parses dependencies, services,
memory/capability descriptors and execution settings; `engine/core/src/loader.rs`
uses memory mode/type, stack, entry, priority and processor to start the process.
Static B20 overrides/runtime do not become compatible with alternate mappings
merely because stored compressed code bytes match. Parsed fields not currently
enforced by HLE are not automatically safe to ignore.

After the new report, review every changed field/block against the exact B20
payload/codegen consumers, including reserved or unknown differences. If the
reports do not resolve a changed block, request only a locally produced semantic
metadata comparison; never request an exheader dump, ROM, key or game code.
Then qualify fresh generation, mapping and runtime behavior in isolation, with
explicit PC versus Switch evidence. Only after sufficient evidence should a
reviewed source change enroll an exact title/code/exheader tuple and, where
validated, exact resource/partition hashes with evidence identifiers. Keep
resource uncertainty opt-in, test adjacent unknown exheaders/code/resources,
and never use a user-supplied diagnostic file as authorization.

This patch intentionally adds no acceptance list while those proofs are absent.
HUD/HD work continues in the separate research checkout; the Builder patch does
not modify or repackage that runtime or the stable B20 installation.
