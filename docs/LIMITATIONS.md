# R9 development-preview limitations

- The source-CLI full build passes for the enrolled input, with 133 units and
  byte-identical C/object/ELF/NRO output compared with the R8.2 reference.
  The final frozen EXE has separate GUI and ROM/SDK checks; a complete final
  frozen-EXE build and a new clean-machine full build have not been executed.
- New Switch execution and macOS/Wine validation remain pending. No universal
  compatibility or performance claim is made. See QUALIFICATION-R9.md.
- Only the enrolled Omega Ruby title/executable classes are supported. NCSD
  `.3ds`/`.cci` names are accepted; CIA/CXI and encrypted inputs are blocked.
  Different resources with matching code/exheader require explicit experimental
  opt-in; genuinely different executables remain blocked.
- Automatic Mesa uses the authenticated bundled SDK, not arbitrary rebuilt
  libraries with the same version string. Official devkitPro downloads require
  internet when no compatible installed SDK is detected.
- The runtime is B20. HD/HUD, B21 and soft-reset experiments are separate.
  Avoid the known B20 L+R+Plus soft-reset failure during testing.
- Homebrew application mode is required. No SD transfer, HOME installation,
  NAND operation or global SDK replacement is performed by this Builder.
- Own ROM/font inputs and game-derived outputs stay private. No personal save
  is included; other players create their own saves. Typography without the
  tested personal font setup remains outside the demonstrated configuration.
- No verified multiplayer support or build cancellation/resume. Forced stopping
  can leave an incomplete new workspace. Existing original files are preserved.
- Compatible warm shader caches can reduce repeated compilation, not every lag.
- No new R9 public binary release is announced by this source branch.
