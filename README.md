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

Twenty-four hunks across `src/main/print-canon.c`, `src/main/canon-printers.h` and `src/xml/papers/standard.xml`:

1. **`StpCDNoMask`** — a new boolean option, *"CD tray: no disc mask"*. When true the driver skips the
   circular disc/hub mask and dithers the whole square CD page (120 × 120 mm for `CD5Inch`).
   It is only offered alongside the CD input slot and defaults to off, so disc printing is unchanged.
2. **`StpCDXAdjustment` / `StpCDYAdjustment`** bounds widened from ±15 pt to **±120 pt (±42 mm)** so the
   printed block can be walked onto the physical card slots.

3. **MX920 disc mode** — Gutenprint only sends the disc-mode command `ESC (r 0x68` for a hard-coded list of
   older models. The MX920 entry's own comment says it needs it, but it wasn't on the list and lacked the
   `CANON_CAP_rr` capability that gates the code path, so the printer accepted disc jobs and silently discarded
   them (IPP job "completed, 0 impressions"). The patch adds both.

4. **MX920 tray J page geometry** — Gutenprint routed the MX920's CD jobs to the legacy 8-byte `ESC (p` page
   command; the printer scans the tray and ejects it unprinted. The MX920 now takes the same path as the
   iP7200 (extended 46-byte `ESC (p` with the tray-J border adjustments), which is what Canon's own Windows
   driver sends — verified against a captured Canon job (`ESC (P`, `ESC (l`, `ESC (c`, `ESC (r` byte-identical).

5. **`PageSize=TrayJ`** — a new page: the whole disc-tray face, 5.16 × 10.01 in, fed from the CD slot with
   ordinary margins and no disc mask or disc centring. It is the page Brainstorm ID's templates describe, so their
   PDFs print unchanged:
   `lp -o InputSlot=CD -o PageSize=TrayJ -o MediaType=DiscCompat -o Resolution=606x600dpi template.pdf`.
   Offered for the MX920 and iP7200 (tray J models). On the MX920 every header command in the job is byte-identical
   to Canon's own Windows driver (captured tray-J job): `ESC (p` with page 3071×5311, printable 2911×5122, origin
   80,70 at 600 dpi, and the legacy medium fields 292×513.

   **Where the cards land** (the part that cost a week): Canon's tray-J medium is **8.85 in** long, Brainstorm's
   template page is **10.01 in**. On Windows the PDF viewer centres the page on the medium, so the template's card
   positions assume the page top sits 0.58 in *above* the medium's top edge. Gutenprint anchors the page top *at*
   the medium's top edge and printed every card 14.5 mm too far toward the trailing edge, no matter what the PDF or
   the paper advance said. The patch therefore sends **no initial paper advance** for `TrayJ` on the MX920: with
   the page's 50.8 pt top margin that reproduces the centred placement to within 0.01 in. Horizontally, raster
   column 0 always sits at the `ESC (p` origin, so the page's *left margin* is the lever: `TrayJ` uses 12.84 pt
   (10 pt + a measured 1 mm), and the driver lets that paper margin through its 10 pt minimum-border clamp.
   Verified on 2026-09-16: Brainstorm's unmodified template prints its card outlines on the card edges.

Everything else — disc media codes, resolution modes — is stock Gutenprint.

## Install (Ubuntu / Debian)

```bash
# enable deb-src for your Ubuntu archive first (deb822: "Types: deb deb-src"), then:
./build.sh
```

`build.sh` fetches the distro source package, applies the patch, **bumps the version to `…+cardtray24`**,
builds with `dpkg-buildpackage`, installs `libgutenprint-common libgutenprint9 printer-driver-gutenprint`,
pins them with `apt-mark hold`, and regenerates the PPDs of existing Gutenprint queues.
Prebuilt `.deb`s for Ubuntu 26.04 (`…+cardtray24`) are attached to the GitHub release.

**Why the version bump matters** (learned the hard way, 2026-09-15): a patched build that keeps the stock
version string is one `unattended-upgrades` run away from being replaced by the archive's identical-version
package — and `dpkg -i` silently clears an existing `apt-mark hold`, so "I held it" is not enough. With the
`+cardtrayN` suffix the archive is never a candidate, and the hold is belt-and-braces.

The Canon driver is a loadable module; `grep -a -c CDNoMask /usr/lib/*/gutenprint/5.3/modules/print-canon.so`
prints `1` when the patched build is live.

## Use

Add the printer with the Gutenprint PPD (it does not show in `lpinfo -m`; use the driver URI directly):

```bash
sudo lpadmin -p canon-mx922 -E -v ipp://<printer-ip>/ipp/print -m 'gutenprint.5.3://bjc-PIXMA-MX922/expert'
```

IPP as the transport, not BJNP: on the MX922 the BJNP backend dropped multi-megabyte tray jobs mid-send.

Print a **5.16 × 10.01 in page** laid out like Brainstorm ID's Canon-J template (two 2.125 × 3.375 in cards,
top edges 3.67 in from the page top, left edges at 0.325 in and 2.745 in) — their own template PDFs work as-is:

```bash
lp -d canon-mx922 -o InputSlot=CD -o PageSize=TrayJ -o MediaType=DiscCompat \
   -o Resolution=606x600dpi -o StpCDNoMask=True -o fit-to-page=false cards.pdf
```

Print with the tray **out**; the printer stops and asks for it, and gives up after a few minutes if nobody
inserts it (the job then stays queued and retries when you press OK). Cards must be **inkjet-printable PVC** —
plain glossy PVC won't hold ink. The older `PageSize=CD5Inch` route (120 × 120 mm page, disc mask off,
`StpCDXAdjustment`/`StpCDYAdjustment` to walk the block onto the slots) still works for printers without a
tray-J page.

A generator that lays out CR80 label artwork on this page lives in the author's labels tooling; any PDF of the
right size works.

## Compatibility

Built and tested against `gutenprint 5.3.4.20220624T01008808d602-4ubuntu2` (Ubuntu 26.04). The touched code
is unchanged in Gutenprint git master, so the patch should apply to 5.3.x generally. Any Canon model Gutenprint
lists with a CD tray should benefit; only the MX922 has been exercised.

## Upstream

Not upstreamed yet. A cleaner shape for Gutenprint proper is probably a `CDMask` string option
(`Disc` / `None`) instead of a boolean, and a per-model default for the adjustment range.

## Licence

Gutenprint is GPL-2.0-or-later; this patch is a derivative work under the same licence (see `LICENSE`).
