#!/usr/bin/env bash
# Build Ubuntu/Debian gutenprint packages with the card-tray patch, install and pin them.
# Tested: Ubuntu 26.04, gutenprint 5.3.4.20220624T01008808d602-4ubuntu2, Canon PIXMA MX922.
#
#   ./build.sh            # source → patch → build → install → hold → regenerate PPDs
#   ./build.sh --no-install
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); BUILD=${BUILD:-$HERE/build}; INSTALL=1
[ "${1:-}" = "--no-install" ] && INSTALL=0
mkdir -p "$BUILD"; cd "$BUILD"

# deb-src must be enabled for apt-get source (deb822: "Types: deb deb-src" in /etc/apt/sources.list.d/*.sources)
if ! apt-cache showsrc printer-driver-gutenprint >/dev/null 2>&1; then
  echo "!! no source index for printer-driver-gutenprint — add deb-src to your apt sources and apt-get update" >&2; exit 1
fi
sudo apt-get build-dep -y gutenprint
[ -d gutenprint-*/ ] || apt-get source printer-driver-gutenprint
SRC=$(ls -d gutenprint-*/ | head -1); cd "$SRC"

if grep -q CDNoMask src/main/print-canon.c; then echo "== already patched"
else patch -p1 < "$HERE/patches/gutenprint-5.3.4-cardtray.patch" || { echo "!! patch failed — try tools/apply-patch.py src/main/print-canon.c" >&2; exit 1; }
fi
# Give the build a HIGHER version than the archive (…+cardtray3). Without this the packages
# carry the stock version string: `dpkg -i` then silently clears any apt hold, and
# unattended-upgrades will "upgrade" same-version → same-version from the archive and wipe
# the patch (this happened 2026-09-15). A local suffix makes the archive never a candidate.
if ! head -1 debian/changelog | grep -q '+cardtray'; then
  python3 - <<'PY'
import re,email.utils
p="debian/changelog"; s=open(p).read()
pkg,ver,dist,_=re.match(r'(\S+) \(([^)]+)\) (\S+); urgency=(\S+)', s).groups()
s=(f"{pkg} ({ver}+cardtray3) {dist}; urgency=medium\n\n  * Local build: Canon CD-tray patch for PVC card trays "
   f"(StpCDNoMask, CD X/Y adjustment ±120pt). https://github.com/jphein/gutenprint-cardtray\n\n"
   f" -- gutenprint-cardtray build.sh <noreply@localhost>  {email.utils.formatdate(localtime=True)}\n\n")+s
open(p,"w").write(s)
PY
fi
dpkg-buildpackage -us -uc -b -nc -j"$(nproc)"
cd ..
echo "== built:"; ls -1 *.deb
dpkg --fsys-tarfile libgutenprint9_*.deb | tar -xO --wildcards '*/modules/print-canon.so' | grep -a -q CDNoMask && echo "== print-canon module carries the patch"

[ $INSTALL = 1 ] || exit 0
sudo dpkg -i libgutenprint-common_*+cardtray*.deb libgutenprint9_*+cardtray*.deb printer-driver-gutenprint_*+cardtray*.deb
# hold AFTER dpkg -i: dpkg -i resets the selection state and drops an existing hold
sudo apt-mark hold libgutenprint-common libgutenprint9 printer-driver-gutenprint
sudo cups-genppdupdate || true
sudo systemctl restart cups
echo "== done. Existing gutenprint queues were regenerated; check:  lpoptions -p <queue> -l | grep StpCDNoMask"
