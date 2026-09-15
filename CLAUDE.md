# gutenprint-cardtray

Patch + build script for gutenprint's Canon driver: adds `StpCDNoMask` (print the full square CD page, no disc mask)
and widens `StpCDX/YAdjustment` to ±120 pt, so PVC ID-card trays (Brainstorm ID "Canon J" tray) work on Linux.
Born in `~/Projects/printing` (MX922 notes) with the card artwork in `~/Projects/labels/label-kit/make-cards.py`.

- `patches/*.patch` is the source of truth; `tools/apply-patch.py` is the same change as string edits (fails loudly).
- Rebuild = `./build.sh`; it pins the three packages with `apt-mark hold`. Unpin to take a distro update, then rebuild.
- Never commit `build/` or `.deb`s — attach them to a GitHub release instead.
- Upstreaming: gutenprint lives on SourceForge (gimp-print) with a GitHub mirror; a cleaner upstream shape would be a
  `CDMask` string option (Disc / None) rather than a boolean.
