#!/usr/bin/env python3
"""Apply patches/gutenprint-5.3.4-cardtray.patch to a gutenprint source tree and verify the markers.

  tools/apply-patch.py <gutenprint-src-dir>

The patch is a plain unified diff against the Ubuntu 26.04 source package
(gutenprint 5.3.4.20220624T01008808d602-4ubuntu2); build.sh calls `patch -p1` itself, this script exists
for applying it by hand and for checking that all hunks landed. Earlier versions of this file were a
string-replacement patcher; it fell behind the patch file, so the patch file is now the single source.
"""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.join(here, "..", "patches", "gutenprint-5.3.4-cardtray.patch")
src = sys.argv[1] if len(sys.argv) > 1 else "."
canon = os.path.join(src, "src", "main", "print-canon.c")
if not os.path.exists(canon):
    sys.exit(f"!! {src} is not a gutenprint source tree (no src/main/print-canon.c)")
if "CDNoMask" in open(canon).read():
    print("== already patched")
else:
    subprocess.run(["patch", "-p1", "-i", patch], cwd=src, check=True)
checks = {
    canon: ["CDNoMask", "TrayJ", "privdata->top = 0;", "printable_length = 513;"],
    os.path.join(src, "src", "main", "canon-printers.h"): ["CANON_CAP_rr"],
    os.path.join(src, "src", "xml", "papers", "standard.xml"): ['name="TrayJ"', '<left value="12.84"/>'],
}
bad = [f"{f}: {m}" for f, ms in checks.items() for m in ms if m not in open(f).read()]
if bad:
    sys.exit("!! markers missing after patch:\n  " + "\n  ".join(bad))
print("== all markers present")
