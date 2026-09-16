#!/usr/bin/env python3
"""Patch gutenprint's Canon driver for PVC card trays (Brainstorm ID "Canon J" tray).

Adds a boolean option  StpCDNoMask  ("CD tray: no disc mask") that disables the
circular disc/hub mask in CD-tray mode so a rectangular block (two CR80 cards)
prints on the full 120x120 mm CD page, and widens the CD X/Y fine adjustment
from ±15 pt to ±120 pt (±42 mm) so the block can be moved onto the card slots.

  ./patch-gutenprint-cardtray.py <gutenprint-src>/src/main/print-canon.c [<gutenprint-src>/src/main/canon-printers.h [<gutenprint-src>/src/xml/papers/standard.xml]]
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

# 5. MX920 family: emit ESC (r 0x68 in CD mode like its siblings (the model also needs CANON_CAP_rr, see below)
old5 = ('!(strcmp(init->caps->name,"PIXMA MG8200")) || !(strcmp(init->caps->name,"PIXMA TS8000")) ) ) {\n'
        '      canon_cmd(v,ESC28,0x72, 1, 0x68); /* same as above case? */')
assert s.count(old5) == 1, "ESC (r CD-mode list anchor not found exactly once"
s = s.replace(old5, old5.replace('"PIXMA TS8000")) ) ) {', '"PIXMA TS8000")) || !(strcmp(init->caps->name,"PIXMA MX920")) ) ) {'), 1)

# 6/7. MX920 tray J page geometry: route CD jobs through the extended ESC (p path with the iP7200's tray-J
#      border adjustments (the printer rejects the legacy 8-byte ESC (p after scanning the tray)
a6 = 'if ( (print_cd) && !(strcmp(init->caps->name,"PIXMA iP7200")) && (test_cd==1) ) {'
assert s.count(a6) == 2, "tray-J blocks (page-dimension + border adjust) anchor not found exactly twice"
s = s.replace(a6, 'if ( (print_cd) && ( !(strcmp(init->caps->name,"PIXMA iP7200")) || !(strcmp(init->caps->name,"PIXMA MX920")) ) && (test_cd==1) ) {')
a7 = '|| !(strcmp(init->caps->name,"PIXMA iP7200")) || !(strcmp(init->caps->name,"PIXMA MP980"))'
assert s.count(a7) == 1, "extended ESC (p exception-list anchor not found exactly once"
s = s.replace(a7, '|| !(strcmp(init->caps->name,"PIXMA iP7200")) || !(strcmp(init->caps->name,"PIXMA MX920")) || !(strcmp(init->caps->name,"PIXMA MP980"))', 1)

# 8-12. "TrayJ" page: the whole disc-tray face (5.16x10.01 in) fed from the CD slot with normal margins —
#       what Brainstorm ID's templates and Canon's "Disc Tray J" paper size describe. No disc geometry/mask.
a8 = '''        stp_string_list_add_string
          (description->bounds.str, "CDCustom", _("CD - Custom"));
'''
assert s.count(a8) == 1, "CD page-list anchor"
s = s.replace(a8, a8 + '''        if (!strcmp(caps->name,"PIXMA MX920") || !strcmp(caps->name,"PIXMA iP7200"))
          stp_string_list_add_string
            (description->bounds.str, "TrayJ", _("Disc Tray J - full face"));
''', 1)
a9 = '''  if(input_slot && !strcmp(input_slot,"CD"))
    cd = 1;

  stp_default_media_size(v, &width, &length);
'''
assert s.count(a9) == 1, "imageable-area anchor"
s = s.replace(a9, '''  if(input_slot && !strcmp(input_slot,"CD") && !(media_size && !strcmp(media_size,"TrayJ")))
    cd = 1;

  stp_default_media_size(v, &width, &length);
''', 1)
tj = '&& !(stp_get_string_parameter(v, "PageSize") && !strcmp(stp_get_string_parameter(v, "PageSize"), "TrayJ"))'
a10 = '''  int print_cd = (media_source && (!strcmp(media_source, "CD")));'''
a11 = '''  int           print_cd = (media_source && (!strcmp(media_source, "CD")));'''
assert s.count(a10) == 1 and s.count(a11) == 1, "canon_setup/do_print print_cd anchors"
s = s.replace(a10, '''  int print_cd = (media_source && (!strcmp(media_source, "CD")) ''' + tj + ");", 1)
s = s.replace(a11, '''  int           print_cd = (media_source && (!strcmp(media_source, "CD")) ''' + tj + ");", 1)
a12 = 'if ( (print_cd) && ( !(strcmp(init->caps->name,"PIXMA iP7200")) || !(strcmp(init->caps->name,"PIXMA MX920")) ) && (test_cd==1) ) {'
assert s.count(a12) == 2, "tray-J adjust anchors (post hunk 6/7)"
s = s.replace(a12, 'if ( (print_cd) && ( !(strcmp(init->caps->name,"PIXMA iP7200")) || !(strcmp(init->caps->name,"PIXMA MX920")) ) && (test_cd==1) && !(stp_get_string_parameter(v, "PageSize") && !strcmp(stp_get_string_parameter(v, "PageSize"), "TrayJ")) ) {')
a13 = '      if (!strcmp(name,"CD5Inch"))     return 0x53; /* CD Tray G --- arbitrary choice here, modify in ESC (P command */'
assert s.count(a13) == 1, "size-type anchor"
s = s.replace(a13, a13 + '\n      if (!strcmp(name,"TrayJ"))       return 0x53; /* full-face disc tray page: same CD workaround path (-> 0x5b for tray J models) */', 1)

# 13-16. TrayJ geometry on the MX920: Canon's own tray-J page (3071x5311 @600 via the size table), Canon's origin
#        (80,70) shifted +24 dots right (measured), Canon's printable area 2911x5122 minus that shift.
a13 = '''  int print_cd = (input_slot && (!strcmp(input_slot, "CD")));

  stp_dprintf(STP_DBG_CANON, v,"setPageMargins2: print_cd = %d\\n",print_cd);'''
assert s.count(a13) == 1, "setPageMargins2 print_cd anchor"
s = s.replace(a13, '''  int print_cd = (input_slot && (!strcmp(input_slot, "CD")));
  int trayj_mx920 = 0; /* MX920 + PageSize=TrayJ: whole-tray-face page, Canon-matching geometry */

  stp_dprintf(STP_DBG_CANON, v,"setPageMargins2: print_cd = %d\\n",print_cd);
  /* MX920: CD pages report 0x53 (tray G placeholder) here; the ESC (P workaround later maps it to 0x5b (tray J).
     Do the same for the paper-size table so fix_papersize() yields Canon's 3071x5311 tray-J page. */
  if ( print_cd && !(strcmp(init->caps->name,"PIXMA MX920")) && arg_ESCP_1 == 0x53 )
    arg_ESCP_1 = 0x5b;''', 1)
a14 = '''	/* this does not seem to need adjustment, so use original borders */
	area_right = border_left * unit / 72;
	area_top = border_top * unit / 72;'''
assert s.count(a14) == 1, "area_right/top anchor"
s = s.replace(a14, a14 + '''
	/* TrayJ (whole tray face) on MX920: Canon's own tray-J origin is (80,70) @600dpi; +24 dots right = the measured 1 mm */
	trayj_mx920 = ( !(strcmp(init->caps->name,"PIXMA MX920")) && stp_get_string_parameter(v, "PageSize") && !strcmp(stp_get_string_parameter(v, "PageSize"), "TrayJ") );
	if ( trayj_mx920 ) {
	  area_right = 104;
	  area_top = 70;
	}''', 1)
a15 = '''	  if ( (print_cd) && (test_cd==1) ) { /* bordered for CD */
	    stp_put32_be(init->page_width * unit / 72,v); /* area_width */
	    stp_put32_be(init->page_height * unit / 72,v); /* area_length */
	  }'''
assert s.count(a15) == 1, "area width/length anchor"
s = s.replace(a15, '''	  if ( trayj_mx920 ) { /* TrayJ: Canon's printable area 2911x5122 minus the 24-dot right shift */
	    stp_put32_be(2887,v); /* area_width */
	    stp_put32_be(5122,v); /* area_length */
	  }
	  else if ( (print_cd) && (test_cd==1) ) { /* bordered for CD */
	    stp_put32_be(init->page_width * unit / 72,v); /* area_width */
	    stp_put32_be(init->page_height * unit / 72,v); /* area_length */
	  }''', 1)

changes = sum(1 for a, b in zip(n0.splitlines(), s.splitlines()) if a != b) + abs(len(s.splitlines()) - len(n0.splitlines()))
for anchor in ('"CDNoMask", N_', 'strcmp(name, "CDNoMask")', 'dimension.upper = 120;', 'no_cd_mask = stp_get_boolean', '!no_cd_mask)', 'no_cd_mask ? NULL', 'int no_cd_mask = 0', '"PIXMA MX920")) ) ) {', '"PIXMA MX920")) ) && (test_cd==1) && !(stp_get_string_parameter(v, "PageSize")', '"PIXMA MX920")) || !(strcmp(init->caps->name,"PIXMA MP980"))', '"TrayJ", _("Disc Tray J - full face")', 'strcmp(media_size,"TrayJ")', 'if (!strcmp(name,"TrayJ"))', 'trayj_mx920', 'stp_put32_be(2887,v)'):
    assert anchor in s, f"missing: {anchor}"
open(p, "w").write(s); print(f"patched {p} (~{changes} lines changed)")

if len(sys.argv) > 2:  # canon-printers.h: MX920 gets CANON_CAP_rr so canon_init_setX72 runs for it
    h = sys.argv[2]; t = open(h).read()
    oldh = "CANON_CAP_STD0|CANON_CAP_DUPLEX|CANON_CAP_r|CANON_CAP_px|CANON_CAP_P|CANON_CAP_I|CANON_CAP_v|CANON_CAP_XML|CANON_CAP_BORDERLESS,0,\n    3,9, /* ESC (l and (P command lengths */\n    1, /* Upper/Lower Cassette option */"
    assert t.count(oldh) == 1, "MX920 model entry anchor not found exactly once"
    t = t.replace(oldh, oldh.replace("CANON_CAP_r|CANON_CAP_px", "CANON_CAP_r|CANON_CAP_rr|CANON_CAP_px"), 1)
    open(h, "w").write(t); print(f"patched {h} (MX920 += CANON_CAP_rr)")

if len(sys.argv) > 3:  # papers XML: define the TrayJ paper (5.16x10.01 in, Canon-matching margins)
    x = sys.argv[3]; t = open(x).read()
    anchor = '    <paper name="CD3Inch">'
    assert t.count(anchor) == 1 and 'name="TrayJ"' not in t, "papers XML anchor"
    t = t.replace(anchor, '''    <paper name="TrayJ">
      <description translate="value" value="Disc Tray J - full face"/>
      <comment value="Canon disc tray J, whole tray face 5.16x10.01in (PVC card trays)"/>
      <width value="371.52"/>
      <height value="720.72"/>
      <left value="9.6"/>
      <right value="15.4"/>
      <top value="50.8"/>
      <bottom value="55.3"/>
      <unit value="english"/>
    </paper>
''' + anchor, 1)
    open(x, "w").write(t); print(f"patched {x} (TrayJ paper)")
