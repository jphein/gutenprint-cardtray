#!/usr/bin/env python3
"""Patch gutenprint's Canon driver for PVC card trays (Brainstorm ID "Canon J" tray).

Adds a boolean option  StpCDNoMask  ("CD tray: no disc mask") that disables the
circular disc/hub mask in CD-tray mode so a rectangular block (two CR80 cards)
prints on the full 120x120 mm CD page, and widens the CD X/Y fine adjustment
from ±15 pt to ±120 pt (±42 mm) so the block can be moved onto the card slots.

  ./patch-gutenprint-cardtray.py <gutenprint-src>/src/main/print-canon.c
"""
import re, sys
p = sys.argv[1]; s = open(p).read(); n0 = s

# 1. parameter declaration (after FullBleed)
s = s.replace('''    "FullBleed", N_("Borderless"), "Color=No,Category=Basic Printer Setup",
    N_("Print without borders"),
    STP_PARAMETER_TYPE_BOOLEAN, STP_PARAMETER_CLASS_FEATURE,
    STP_PARAMETER_LEVEL_BASIC, 1, 1, STP_CHANNEL_NONE, 1, 0
  },
''', '''    "FullBleed", N_("Borderless"), "Color=No,Category=Basic Printer Setup",
    N_("Print without borders"),
    STP_PARAMETER_TYPE_BOOLEAN, STP_PARAMETER_CLASS_FEATURE,
    STP_PARAMETER_LEVEL_BASIC, 1, 1, STP_CHANNEL_NONE, 1, 0
  },
  {
    "CDNoMask", N_("CD tray: no disc mask"), "Color=No,Category=Basic Printer Setup",
    N_("Print the whole square CD page without masking the disc shape (PVC card trays)"),
    STP_PARAMETER_TYPE_BOOLEAN, STP_PARAMETER_CLASS_FEATURE,
    STP_PARAMETER_LEVEL_BASIC, 1, 1, STP_CHANNEL_NONE, 1, 0
  },
''', 1)

# 2. parameter description (before Duplex)
s = s.replace('''  else if (strcmp(name, "Duplex") == 0)
  {
    int offer_duplex=0;
''', '''  else if (strcmp(name, "CDNoMask") == 0)
    {
      const char* input_slot = stp_get_string_parameter(v, "InputSlot");
      description->deflt.boolean = 0;
      description->is_active = (!input_slot || !strcmp(input_slot,"CD")) ? 1 : 0;
    }
  else if (strcmp(name, "Duplex") == 0)
  {
    int offer_duplex=0;
''', 1)

# 3. wider fine adjustment
old = '''      description->bounds.dimension.lower = -15;
      description->bounds.dimension.upper = 15;
      description->deflt.dimension = 0;'''
assert s.count(old) == 1, "adjustment-bounds anchor not found exactly once"
s = s.replace(old, '''      description->bounds.dimension.lower = -120;
      description->bounds.dimension.upper = 120;
      description->deflt.dimension = 0;''', 1)

# 4. mask bypass in the row loop
s = s.replace('''  privdata.emptylines = 0;
  if (print_cd) {
    cd_mask = stp_malloc''', '''  privdata.emptylines = 0;
  no_cd_mask = stp_get_boolean_parameter(v, "CDNoMask");
  if (print_cd) {
    cd_mask = stp_malloc''', 1)
s, k = re.subn(r'    if \(print_cd\) *\n      \{\n\tint x_center', '    if (print_cd && !no_cd_mask)\n      {\n\tint x_center', s, count=1)
assert k == 1, "mask-loop anchor not found"
s = s.replace('''    stp_dither(v, y, duplicate_line, zero_mask, cd_mask);''',
              '''    stp_dither(v, y, duplicate_line, zero_mask, no_cd_mask ? NULL : cd_mask);''', 1)
s = s.replace('''  unsigned char *cd_mask = NULL;''', '''  unsigned char *cd_mask = NULL;
  int no_cd_mask = 0;''', 1)

changes = sum(1 for a, b in zip(n0.splitlines(), s.splitlines()) if a != b) + abs(len(s.splitlines()) - len(n0.splitlines()))
for anchor in ('"CDNoMask", N_', 'strcmp(name, "CDNoMask")', 'dimension.upper = 120;', 'no_cd_mask = stp_get_boolean', '!no_cd_mask)', 'no_cd_mask ? NULL', 'int no_cd_mask = 0'):
    assert anchor in s, f"missing: {anchor}"
open(p, "w").write(s); print(f"patched {p} (~{changes} lines changed)")
