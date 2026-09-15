# gutenprint-cardtray

A small patch to [Gutenprint](https://gimp-print.sourceforge.io/)'s Canon driver that lets Linux print
onto **inkjet PVC ID cards** (CR80, 85.6 × 54 mm) using a PVC card tray in the printer's CD/DVD slot —
tested on a **Canon PIXMA MX922** with the [Brainstorm ID "Canon J" card tray](https://brainstormidsupply.com/pvc-card-tray-for-canon-j-tray.html).

## Why

Canon's disc-capable PIXMAs can print on anything that rides in the disc tray, and third-party card trays
exploit that to hold two CR80 cards. On Windows and macOS the Canon driver offers a "Disc Tray J" paper size
and prints the whole tray face. On Linux:

- **Canon's own Linux driver** (`cnijfilter` 3.90) has no tray selector at all — cassette only.
- **Gutenprint** does know these printers and the CD tray (`InputSlot=CD`, disc media types, disc page sizes),
  but it assumes the thing in the tray is a disc: it **masks everything outside a 120 mm circle** (and inside
  the hub) and only allows a **±15 pt (5 mm)** position nudge.

Two CR80 cards side by side form a 115 × 86 mm block whose corners sit 72 mm from the centre — outside the
60 mm disc radius — so the card corners come out blank, and 5 mm isn't enough to move the block onto the slots.
The only Linux driver that handled this was a paid one.

## What the patch does

Seven hunks in `src/main/print-canon.c`:

1. **`StpCDNoMask`** — a new boolean option, *"CD tray: no disc mask"*. When true the driver skips the
   circular disc/hub mask and dithers the whole square CD page (120 × 120 mm for `CD5Inch`).
   It is only offered alongside the CD input slot and defaults to off, so disc printing is unchanged.
2. **`StpCDXAdjustment` / `StpCDYAdjustment`** bounds widened from ±15 pt to **±120 pt (±42 mm)** so the
   printed block can be walked onto the physical card slots.

Everything else — tray selection (`ESC (P … 0x5b` for tray J on the MX920 family), disc media codes,
resolution modes — is stock Gutenprint.

## Install (Ubuntu / Debian)

```bash
# enable deb-src for your Ubuntu archive first (deb822: "Types: deb deb-src"), then:
./build.sh
```

`build.sh` fetches the distro source package, applies the patch, **bumps the version to `…+cardtray1`**,
builds with `dpkg-buildpackage`, installs `libgutenprint-common libgutenprint9 printer-driver-gutenprint`,
pins them with `apt-mark hold`, and regenerates the PPDs of existing Gutenprint queues.
Prebuilt `.deb`s for Ubuntu 26.04 are attached to the GitHub release.

**Why the version bump matters** (learned the hard way, 2026-09-15): a patched build that keeps the stock
version string is one `unattended-upgrades` run away from being replaced by the archive's identical-version
package — and `dpkg -i` silently clears an existing `apt-mark hold`, so "I held it" is not enough. With the
`+cardtray1` suffix the archive is never a candidate, and the hold is belt-and-braces.

The Canon driver is a loadable module; `grep -a -c CDNoMask /usr/lib/*/gutenprint/5.3/modules/print-canon.so`
prints `1` when the patched build is live.

## Use

Add the printer with the Gutenprint PPD (it does not show in `lpinfo -m`; use the driver URI directly):

```bash
sudo apt install cups-backend-bjnp
sudo lpadmin -p canon-mx922 -E -v bjnp://<printer-ip> -m 'gutenprint.5.3://bjc-PIXMA-MX922/expert'
```

Prepare a **120 × 120 mm page** with your card artwork placed where the cards sit relative to the tray's disc
centre (for the Brainstorm J tray: two 2.125 × 3.375 in cards, 0.295 in apart, block centred), then:

```bash
lp -d canon-mx922 -o InputSlot=CD -o PageSize=CD5Inch -o MediaType=DiscOthers \
   -o Resolution=606x600dpi -o StpCDNoMask=True -o fit-to-page=false \
   -o StpCDXAdjustment=0 -o StpCDYAdjustment=0 cards.pdf
```

Print with the tray **out**; the printer stops and asks for it. Calibrate once by taping plain paper over the
empty slots and printing card outlines, then set the X/Y adjustments (points; +X right, +Y down). Cards must be
**inkjet-printable PVC** — plain glossy PVC won't hold ink.

A generator that lays out CR80 label artwork on this page (and on the maker's 5.16 × 10.01 in Windows/macOS
tray page) lives in the author's labels tooling; any PDF of the right size works.

## Compatibility

Built and tested against `gutenprint 5.3.4.20220624T01008808d602-4ubuntu2` (Ubuntu 26.04). The touched code
is unchanged in Gutenprint git master, so the patch should apply to 5.3.x generally. Any Canon model Gutenprint
lists with a CD tray should benefit; only the MX922 has been exercised.

## Upstream

Not upstreamed yet. A cleaner shape for Gutenprint proper is probably a `CDMask` string option
(`Disc` / `None`) instead of a boolean, and a per-model default for the adjustment range.

## Licence

Gutenprint is GPL-2.0-or-later; this patch is a derivative work under the same licence (see `LICENSE`).
