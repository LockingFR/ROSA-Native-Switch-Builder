# R9.1 targeted qualification - 2026-10-29

Scope: diagnostic correction only. No variant enrolled, no B20 runtime change,
no replacement of the published R9 beta and no console installation.

- Windows source suite: **51 passed** (`unittest discover -s builder -v`).
  Nine new tests cover the tester's exact hash tuple, changed compression,
  segment mappings, stack/BSS, execution/service/capability blocks, independent
  resource mutations, malformed ranges, nested export allowlists, missing
  metadata and reference derivation. Both experimental-option states are tested
  for changed exheaders; matching diagnostic metadata cannot authorize them.
- Final PyInstaller Windows EXE built successfully. Its CLI diagnosed the
  actual SHA-256-verified B20 dump: all four identities, every available numeric
  field/block comparison and all resource comparisons matched. An absent access
  descriptor comparison remains unknown. Source export of that frozen diagnostic
  produced schema 2. A synthetic unknown-code input stayed blocked with the
  experimental option enabled.
- Recursive EXE/PYZ/DATA/Mesa content qualification passed with no findings.
  The auditor's `distribution_approved` field remains false: it is not a human
  authorization mechanism.
- EXE SHA-256:
  `ef978283a669792236a2c60f1b87687bd1ca0955296353530c21dc8f5fcd7c18`.
- Unchanged DATA SHA-256:
  `55f225cfd9e03ca4b39997749dfa0610a9c8c67a837b77dcefcb9c1a44fd088d`.

The tester's ROM/exheader bytes were not available or requested. Its old report
was inspected locally; only identities and non-personal metadata informed the
regression test and analysis. Its compatibility remains **undemonstrated**.
See [the missing diagnostics and review/enrollment gates](CHANGELOG-R9.1.md).

This revision did not repeat a full game compilation, drive the GUI export
button, run on a clean Windows machine, test macOS/Wine or execute on Switch.
R9's earlier full-build evidence does not qualify this new EXE for those claims.
The local candidate is under `build/r9.1-candidate`; binaries/game inputs are
excluded from the source commit. Only source and documentation are pushed.
