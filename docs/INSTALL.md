# Install and build — ROSA Builder R8 experimental beta

1. Download **both files** from the same GitHub release: `ROSA-Builder.exe` and `ROSA-Builder.data`. Keep the original names and place them in the **same folder**. Compare their SHA-256 digests with `SHA256SUMS.txt`.
2. Open `ROSA-Builder.exe` on Windows. Keep Windows security software enabled. This is an unsigned test application, so inspect the publisher and file source carefully.
3. Select your own **supported unencrypted `.3ds`** game dump. The current builder accepts **only one exact tested revision** of Pokémon Omega Ruby, determined by full-file SHA-256, not filename. It does not support `.cia` or decrypt encrypted games.
4. Choose a parent directory on a **local disk** with at least 8 GiB free for a **new** build workspace. The Builder will not overwrite existing output folders.
5. Choose one SDK method: **(a)** an existing compatible official devkitPro installation, or **(b)** the R8 checkbox **Auto-download verified devkitPro**. The new mode is experimental, downloads version-pinned packages from `pkg.devkitpro.org`, checks integrity, and extracts them into the new build workspace without installing system-wide.
6. In **both** modes, select the separately obtained, exactly validated **Mesa Switch 26.2.4 SDK**. It is **not included or downloaded automatically**. An arbitrary Mesa installation is insufficient; the application checks specific SDK content.
7. Optionally select your personally obtained compatible shared-font file. No game fonts are included.
8. Start the build. Full compilation took around **29–30 minutes** in historical *R7/R4* PC tests; R8 may differ. The generated `sd/` tree, `build-result.json`, and local logs will appear in the newly created workspace if successful.
9. Back up existing Switch data before copying anything manually. The expected executable path is `sdmc:/switch/rosa/rosa-b20-mesa26.nro`; the runtime depends on that basename. Launch from **homebrew menu in application mode** on compatible modified hardware. The Builder **does not install** HOME menu forwarders.
10. If the game launches, test intro, inputs, touch, bottom screen, battles, sound, saving, and close/relaunch. Share **redacted** feedback, not game outputs or dumps.

### Important notes

- A complete build produces **copyrighted game-derived executable data locally**. Do not upload generated C, NROs, SD game-data folders, ROM copies, or saves to GitHub or in bug reports.
- New areas, attacks and effects can cause first-time shader compilation and pauses. The cache may help on subsequent launches, but there is no prewarmed private cache bundled here.
- No universal prebuilt Omega Ruby NRO is provided.
- No networking, multiplayer or automatic encryption/key workflows are provided.
- If auto-download fails, report the **step name, error and Windows version** without attaching ROMs or unredacted logs.
