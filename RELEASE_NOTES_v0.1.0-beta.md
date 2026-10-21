# ROSA Builder v0.1.0-beta (R8) — Experimental Community Preview 🎮

The first **community testing beta** of ROSA Builder is now available for Windows.

The Builder generates a Nintendo Switch homebrew version of Pokémon Omega Ruby **locally from your own exact supported game dump**. It uses native ARM64 recompilation instead of traditional 3DS CPU emulation.

### What's in this beta

- Windows desktop GUI with progress feedback and input validation.
- Local ARM11-to-C generation, ARM64 compilation and B20 reference runtime linking.
- New **experimental automatic devkitPro package download** (opt-in, official pinned packages).
- Existing manually installed devkitPro option remains supported.
- Output prepared for compatible modified Nintendo Switch homebrew environments.

### Very important limitations

- **R8 auto-SDK flow has not been fully tested end-to-end on a fresh Windows installation.** R8 GUI starts; R8 pair is produced. Prior R7 game build reportedly launched on a real Switch, but that is **not a confirmation for R8**.
- You **still must separately provide a compatible Mesa Switch 26.2.4 SDK**. This is not a universal one-click installer.
- Only one exact unencrypted Pokémon Omega Ruby `.3ds` revision is recognized; CIA, encrypted dumps and different revisions are unsupported.
- No game ROM, key, firmware, original game assets, generated Nintendo code, ready-to-play NRO, private save or warm shader cache is included.
- First visits can stutter when the game compiles shaders. Online/multiplayer features are not implemented.

### Downloads

Download **both** `ROSA-Builder.exe` **and** `ROSA-Builder.data` from this same release. They must remain side-by-side and must match the published checksums. See `SHA256SUMS.txt` and the [setup guide](https://github.com/LockingFR/ROSA-Native-Switch-Builder/blob/main/docs/INSTALL.md).

### Bug reports

Please help us test. Report build failures and compatibility results via [GitHub Issues](https://github.com/LockingFR/ROSA-Native-Switch-Builder/issues). Include your Windows version, stage and **redacted** error only. **Do not attach ROMs, generated C files, archives, NROs, saves, keys or raw logs.**

*Unofficial fan project. Not affiliated with Nintendo, Game Freak, or The Pokémon Company.*
