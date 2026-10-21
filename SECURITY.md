# Security & private bug reporting

Never attach ROMs, firmware, encryption keys, Nintendo console identities, save files, generated game code, game NRO/ELF archives, private caches, full build folders, private screenshots or raw logs to public issues.

Provide redacted errors, Windows version, Builder candidate (R8), whether managed SDK was selected, build step and reproducible non-sensitive conditions. Review logs for private file paths, account names, secrets and game contents **before** sharing.

Only obtain releases from the official repository. Verify SHA-256 checksums. Keep security software enabled. If a security-sensitive flaw is found, use GitHub private vulnerability reporting if available.

The Builder must not upload personal game data. Optional managed devkitPro installs download official toolchain packages from `pkg.devkitpro.org` and save them locally. Mesa is supplied separately. No installer changes the console.
