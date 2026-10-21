# Known limitations — Preview 0.1 R8

- **Unverified R8 end-to-end:** GUI launch and R8 EXE+DATA packaging confirmed by the maintainer; live auto-provisioned devkitPro installation, a full R8 cold build on a clean Windows system, and an R8-generated NRO running on Switch are **not yet confirmed**.
- **R7 history is not an R8 test:** earlier candidate R4 passed an isolated PC build; the maintainer separately confirmed an R7-generated NRO launch on Switch.
- Exactly one unencrypted validated Omega Ruby `.3ds` revision accepted. Other ROM revisions/regions, `.cia`, encrypted inputs and game updates are not supported.
- Mesa Switch 26.2.4 SDK is a separately sourced, specially validated prerequisite, even when managed devkitPro mode is enabled. There is **no one-click universal install**.
- R8 downloads pinned devkitPro packages only if explicitly opted in. It is not a system package manager and does not download game data.
- Homebrew / modified Switch is required. No automatic SD transfer, forwarder, NAND operation or administrator privilege.
- B20 reference behavior; B21 improvements, unvalidated renderer experiments and soft reset changes are excluded. Avoid the known B20 L+R+Plus soft-reset path during testing.
- No verified online or local multiplayer support.
- A personal shared font is not provided; fallback typography may vary.
- GUI build cancellation/resume has not been validated. Forced termination may leave an incomplete private workspace, without altering original game data.
- Cache helps when the same compatible shader program has already been compiled. It does not fix all performance problems.
- This is an **experimental community beta** and is provided without any compatibility warranty.
