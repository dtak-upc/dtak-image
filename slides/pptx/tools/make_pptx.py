#!/usr/bin/env python3
"""Build the DTAK PowerPoint / Google Slides template: dtak.potx and dtak.pptx.

The PowerPoint twin of ../revealjs/ and ../latex/: same 1280x720 canvas, colors, fonts, footer and slide types.
Everything lives in the theme, slide master and layouts, so new slides and typed text get the DTAK look without
touching any formatting. The OOXML package is written directly (python-pptx cannot author masters or layouts).

    .venv/bin/python -I slides/pptx/tools/make_pptx.py [outdir]     # default: slides/pptx/

Outputs:
  dtak.potx  PowerPoint template (File > New from it): one empty title slide.
  dtak.pptx  the same template with the example slides of ../revealjs/index.html; also the file to upload to
             Google Slides.

Geometry is in CSS px of the reveal.js theme (1 px = 9525 EMU = 0.75 pt), sizes are copied from
../revealjs/theme/dtak.css. Fonts (Montserrat Bold, Roboto, Roboto Mono) are embedded as uncompressed EOT
(.fntdata), as PowerPoint does, so PowerPoint shows them without installing anything. Google Slides has them natively.
"""
import io
import re
import struct
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[3]          # dtak-image/
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'slides' / 'pptx'

# ---------------------------------------------------------------- identity (= ../revealjs/theme/dtak.css)
ACCENT = '0076CF'     # UPC blue, Pantone 2195
NAVY = '0A2A4F'       # titles; section slide background
SOFT = '66ADE2'       # UPC blue at 60 % over white: the accent on dark backgrounds
TEXT = '1C2430'
MUTED = '6B7785'
LINE = 'DDE3EA'
EDGE = '8494A7'       # navy at 50 % over white = white at 50 % over navy: footer rule on dark slides
NUM_DARK = 'C2CAD3'   # white at 75 % over navy: slide number on dark slides
BOX_BG = 'EBF4FB'     # accent at 8 % over white (.box)
CODE_BG = 'F0F7FC'    # accent at 6 % over white (pre code)

TITLE_FONT, BODY_FONT, MONO_FONT = 'Montserrat', 'Roboto', 'Roboto Mono'
FONTS = {  # family -> {style: file in dtak-image/fonts/}; embedded in the package
    TITLE_FONT: {'bold': 'Montserrat-Bold.ttf'},
    BODY_FONT: {'regular': 'Roboto-Regular.ttf', 'bold': 'Roboto-Bold.ttf',
                'italic': 'Roboto-Italic.ttf', 'boldItalic': 'Roboto-BoldItalic.ttf'},
    MONO_FONT: {'regular': 'RobotoMono-Regular.ttf', 'bold': 'RobotoMono-Bold.ttf'},
}

W, H = 1280, 720
PAD_T, PAD_X, FOOT = 56, 64, 110      # section padding: 56px 64px 110px
CW = W - 2 * PAD_X                    # content width 1152
BAR = 12                              # top accent bar
LOGO_H, FOOT_L, FOOT_R, FOOT_B, FOOT_GAP = 46, 24, 72, 18, 28
TABLE_STYLE = '{3C0E7D5B-6F0A-4C1E-9D2B-DA7A0C0D7A4B}'
STAMP = (2026, 11, 19, 0, 0, 0)       # fixed zip/core dates: the output is byte-identical on every run


def emu(px):
    return int(round(px * 9525))


def pt(px):  # CSS px -> hundredths of a point
    return int(round(px * 75))


NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'


def rels(items):
    """items: [(rid, type, target[, external])]"""
    out = [f'<Relationship Id="{i[0]}" Type="{REL if "/" not in i[1] else ""}{i[1]}" Target="{escape(i[2])}"'
           + (' TargetMode="External"' if len(i) > 3 else '') + '/>' for i in items]
    return (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(out) + '</Relationships>')


# ---------------------------------------------------------------- DrawingML helpers
def xfrm(x, y, w, h, tag='a:xfrm'):
    return f'<{tag}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></{tag}>'


def color(c):  # 'RRGGBB' or a theme color name (tx1, tx2, bg2, accent1, ...)
    return f'<a:srgbClr val="{c}"/>' if re.fullmatch('[0-9A-F]{6}', c) else f'<a:schemeClr val="{c}"/>'


def fill(c):
    return f'<a:solidFill>{color(c)}</a:solidFill>' if c else ''


def font(face):  # '+mj' / '+mn' theme fonts, or an explicit face
    if face.startswith('+'):
        return f'<a:latin typeface="{face}-lt"/><a:ea typeface="{face}-ea"/><a:cs typeface="{face}-cs"/>'
    return f'<a:latin typeface="{face}"/><a:cs typeface="{face}"/>'


def rpr(tag='a:rPr', sz=None, b=None, i=None, color=None, face=None, extra=''):
    a = (f' sz="{sz}"' if sz else '') + (f' b="{b}"' if b is not None else '') + \
        (f' i="{i}"' if i is not None else '')
    return f'<{tag}{a}>{fill(color)}{font(face) if face else ""}{extra}</{tag}>'


def ppr(lvl, marL=0, indent=0, algn=None, ln=None, bef=None, bu=None, bucolor=None, defrpr='', busz=None):
    """bu: None = no bullet, else the bullet character. busz: bullet size in % of the text."""
    a = f' marL="{emu(marL)}" indent="{emu(indent)}"' + (f' algn="{algn}"' if algn else '')
    body = (f'<a:lnSpc><a:spcPct val="{ln * 1000}"/></a:lnSpc>' if ln else '') + \
           (f'<a:spcBef><a:spcPts val="{bef}"/></a:spcBef>' if bef is not None else '')
    if bu:
        body += f'<a:buClr>{color(bucolor)}</a:buClr>' if bucolor else ''
        body += f'<a:buSzPct val="{busz * 1000}"/>' if busz else ''
        body += f'<a:buFont typeface="Arial"/><a:buChar char="{bu}"/>'
    else:
        body += '<a:buNone/>'
    return f'<a:lvl{lvl}pPr{a}>{body}{defrpr}</a:lvl{lvl}pPr>'


def body_pr(anchor='t', autofit=True, ins=(0, 0, 0, 0), wrap=True):
    l, t, r, b = (emu(v) for v in ins)
    return (f'<a:bodyPr vert="horz" wrap="{"square" if wrap else "none"}" lIns="{l}" tIns="{t}" rIns="{r}" '
            f'bIns="{b}" rtlCol="0" anchor="{anchor}">' + ('<a:normAutofit/>' if autofit else '<a:noAutofit/>')
            + '</a:bodyPr>')


def run(text, **kw):
    link = kw.pop('link', None)
    extra = f'<a:hlinkClick r:id="{link}"/>' if link else ''
    return f'<a:r>{rpr(extra=extra, **kw)}<a:t>{escape(text)}</a:t></a:r>'


def para(*runs, lvl=0, ppr_xml=''):
    lv = f'<a:pPr lvl="{lvl}"/>' if lvl and not ppr_xml else ppr_xml
    return f'<a:p>{lv}{"".join(r if r.startswith("<") else run(r) for r in runs)}</a:p>'


class Shapes:
    """Collects the shapes of one spTree, numbering their ids."""

    def __init__(self):
        self.items, self.n = [], 1

    def _id(self):
        self.n += 1
        return self.n

    def ph(self, name, ph, box=None, lst='', paras=None, bodypr='<a:bodyPr/>'):
        """A placeholder. ph: the <p:ph> attributes. box: (x, y, w, h) in px, or None to inherit."""
        geom = (xfrm(*box) + '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>') if box else ''
        txt = ''.join(paras) if paras else '<a:p><a:endParaRPr/></a:p>'
        self.items.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{escape(name)}"/><p:cNvSpPr><a:spLocks noGrp="1"/>'
            f'</p:cNvSpPr><p:nvPr><p:ph {ph}/></p:nvPr></p:nvSpPr><p:spPr>{geom}</p:spPr>'
            f'<p:txBody>{bodypr}<a:lstStyle>{lst}</a:lstStyle>{txt}</p:txBody></p:sp>')

    def rect(self, name, box, color, paras=None, bodypr=None, line=None):
        ln = (f'<a:ln w="{emu(line[1])}">{fill(line[0])}</a:ln>' if line else '<a:ln><a:noFill/></a:ln>')
        tx = ''
        if paras:
            tx = f'<p:txBody>{bodypr or body_pr(autofit=False)}<a:lstStyle/>{"".join(paras)}</p:txBody>'
        self.items.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{self._id()}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{xfrm(*box)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'{fill(color) if color else "<a:noFill/>"}{ln}</p:spPr>{tx}</p:sp>')

    def pic(self, name, box, png_rid, svg_rid, descr):
        svg = ('<a:extLst><a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}"><asvg:svgBlip '
               'xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" '
               f'r:embed="{svg_rid}"/></a:ext></a:extLst>')
        self.items.append(
            f'<p:pic><p:nvPicPr><p:cNvPr id="{self._id()}" name="{escape(name)}" descr="{escape(descr)}"/>'
            f'<p:cNvPicPr><a:picLocks noGrp="1" noChangeAspect="1"/></p:cNvPicPr><p:nvPr userDrawn="1"/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{png_rid}">{svg}</a:blip><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr>{xfrm(*box)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')

    def table(self, name, box, rows, col_w, row_h, sz):
        grid = ''.join(f'<a:gridCol w="{emu(w)}"/>' for w in col_w)
        trs = ''
        for row in rows:
            tcs = ''.join(
                f'<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr sz="{sz}"/><a:t>{escape(c)}</a:t>'
                f'</a:r></a:p></a:txBody><a:tcPr marL="{emu(14)}" marR="{emu(14)}" marT="{emu(6)}" '
                f'marB="{emu(6)}" anchor="ctr"/></a:tc>' for c in row)
            trs += f'<a:tr h="{emu(row_h)}">{tcs}</a:tr>'
        self.items.append(
            f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{self._id()}" name="{escape(name)}"/>'
            f'<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/>'
            f'</p:nvGraphicFramePr>{xfrm(*box, tag="p:xfrm")}<a:graphic><a:graphicData '
            f'uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="0">'
            f'<a:tableStyleId>{TABLE_STYLE}</a:tableStyleId></a:tblPr><a:tblGrid>{grid}</a:tblGrid>{trs}</a:tbl>'
            f'</a:graphicData></a:graphic></p:graphicFrame>')

    def tree(self):
        return ('<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
                '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>' + ''.join(self.items) + '</p:spTree>')


# ---------------------------------------------------------------- logos
def svg_size(path):
    s = path.read_text()
    w, h = (float(re.search(fr'<svg[^>]*\s{k}="([\d.]+)', s).group(1)) for k in ('width', 'height'))
    return w / h


LOGOS = {  # key -> svg; the PNG fallback is rendered from it (Google Slides, LibreOffice and old Office use it)
    'upc': ROOT / 'slides/revealjs/theme/logos/upc-barcelonatech.svg',
    'upc-neg': ROOT / 'slides/revealjs/theme/logos/upc-barcelonatech-neg.svg',
    'dtak': ROOT / 'logo/dtak_short.svg',
    'dtak-neg': ROOT / 'logo/dtak_short_dark.svg',
}


def logo_media():
    media = {}
    for k, svg in LOGOS.items():
        media[f'{k}.svg'] = svg.read_bytes()
        media[f'{k}.png'] = cairosvg.svg2png(url=str(svg), output_height=512)
    return media


def chrome(sh, dark, rid):
    """Footer: UPC mark left, rule, DTAK short right, both LOGO_H tall (equal footing). rid: key -> (png, svg)."""
    y = H - FOOT_B - LOGO_H
    wu, wd = LOGO_H * svg_size(LOGOS['upc']), LOGO_H * svg_size(LOGOS['dtak'])
    sfx = '-neg' if dark else ''
    if not dark:
        sh.rect('Accent bar', (0, 0, W, BAR), 'accent1')
    sh.pic('UPC mark', (FOOT_L, y, wu, LOGO_H), *rid['upc' + sfx], 'UPC BarcelonaTech')
    x0, x1 = FOOT_L + wu + FOOT_GAP, W - FOOT_R - wd - FOOT_GAP
    sh.rect('Footer rule', (x0, y + LOGO_H / 2 - 1, x1 - x0, 2), EDGE if dark else 'accent1')
    sh.pic('DTAK logo', (W - FOOT_R - wd, y, wd, LOGO_H), *rid['dtak' + sfx], 'DTAK')


NUM_BOX = (W - 22 - 80, H - 32 - 22, 80, 22)  # .num: right 22px, bottom 32px, 16px


def slide_num(sh, color=None, box=None):
    lst = ppr(1, algn='r', defrpr=rpr('a:defRPr', sz=pt(16), color=color or 'accent3', face='+mn')) if color or box \
        else ''
    sh.ph('Slide Number', 'type="sldNum" sz="quarter" idx="12"', box, lst,
          ['<a:p><a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr/><a:t>‹#›</a:t>'
           '</a:fld></a:p>'], body_pr('b', False) if box else '<a:bodyPr/>')


# ---------------------------------------------------------------- theme
def theme():
    clr = (f'<a:dk1><a:srgbClr val="{TEXT}"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
           f'<a:dk2><a:srgbClr val="{NAVY}"/></a:dk2><a:lt2><a:srgbClr val="{LINE}"/></a:lt2>'
           f'<a:accent1><a:srgbClr val="{ACCENT}"/></a:accent1><a:accent2><a:srgbClr val="{SOFT}"/></a:accent2>'
           f'<a:accent3><a:srgbClr val="{MUTED}"/></a:accent3><a:accent4><a:srgbClr val="{EDGE}"/></a:accent4>'
           f'<a:accent5><a:srgbClr val="{NAVY}"/></a:accent5><a:accent6><a:srgbClr val="{BOX_BG}"/></a:accent6>'
           f'<a:hlink><a:srgbClr val="{ACCENT}"/></a:hlink><a:folHlink><a:srgbClr val="{ACCENT}"/></a:folHlink>')
    fonts = (f'<a:majorFont><a:latin typeface="{TITLE_FONT}"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
             f'<a:minorFont><a:latin typeface="{BODY_FONT}"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>')
    ph = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    lines = ''.join(f'<a:ln w="{w}" cap="flat" cmpd="sng" algn="ctr">{ph}<a:prstDash val="solid"/><a:miter lim="800000"/>'
                    f'</a:ln>' for w in (12700, 19050, 25400))
    fmt = (f'<a:fillStyleLst>{ph * 3}</a:fillStyleLst><a:lnStyleLst>{lines}</a:lnStyleLst>'
           '<a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 + '</a:effectStyleLst>'
           f'<a:bgFillStyleLst>{ph * 3}</a:bgFillStyleLst>')
    # New shapes: accent fill, no outline, white Roboto. New text boxes: Roboto in the text color.
    sp_def = ('<a:spDef><a:spPr><a:solidFill><a:schemeClr val="accent1"/></a:solidFill><a:ln><a:noFill/></a:ln>'
              '</a:spPr><a:bodyPr rtlCol="0" anchor="ctr"/><a:lstStyle/><a:style><a:lnRef idx="0"><a:schemeClr '
              'val="accent1"/></a:lnRef><a:fillRef idx="1"><a:schemeClr val="accent1"/></a:fillRef><a:effectRef '
              'idx="0"><a:schemeClr val="accent1"/></a:effectRef><a:fontRef idx="minor"><a:schemeClr val="lt1"/>'
              '</a:fontRef></a:style></a:spDef>')
    ln_def = ('<a:lnDef><a:spPr><a:ln w="19050"><a:solidFill><a:schemeClr val="accent1"/></a:solidFill></a:ln>'
              '</a:spPr><a:bodyPr/><a:lstStyle/><a:style><a:lnRef idx="0"><a:schemeClr val="accent1"/></a:lnRef>'
              '<a:fillRef idx="0"><a:schemeClr val="accent1"/></a:fillRef><a:effectRef idx="0"><a:schemeClr '
              'val="accent1"/></a:effectRef><a:fontRef idx="minor"><a:schemeClr val="tx1"/></a:fontRef></a:style>'
              '</a:lnDef>')
    tx_def = ('<a:txDef><a:spPr><a:noFill/></a:spPr><a:bodyPr wrap="square" rtlCol="0"><a:spAutoFit/></a:bodyPr>'
              f'<a:lstStyle><a:defPPr><a:defRPr sz="{pt(30)}"/></a:defPPr></a:lstStyle></a:txDef>')
    return (XML + f'<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="DTAK">'
            f'<a:themeElements><a:clrScheme name="DTAK">{clr}</a:clrScheme><a:fontScheme name="DTAK">{fonts}'
            f'</a:fontScheme><a:fmtScheme name="DTAK">{fmt}</a:fmtScheme></a:themeElements>'
            f'<a:objectDefaults>{sp_def}{ln_def}{tx_def}</a:objectDefaults><a:extraClrSchemeLst/></a:theme>')


def table_styles():
    def bdr(edge, w, c):
        return f'<a:{edge}><a:ln w="{emu(w)}">{fill(c)}</a:ln></a:{edge}>'
    def nob(edge):
        return f'<a:{edge}><a:ln><a:noFill/></a:ln></a:{edge}>'
    return (XML + f'<a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            f'def="{TABLE_STYLE}"><a:tblStyle styleId="{TABLE_STYLE}" styleName="DTAK">'
            '<a:wholeTbl><a:tcTxStyle><a:fontRef idx="minor"/><a:schemeClr val="tx1"/></a:tcTxStyle><a:tcStyle>'
            f'<a:tcBdr>{nob("left")}{nob("right")}{nob("top")}{bdr("bottom", 1, "bg2")}{bdr("insideH", 1, "bg2")}'
            f'{nob("insideV")}</a:tcBdr><a:fill><a:noFill/></a:fill></a:tcStyle>'
            '</a:wholeTbl><a:firstRow><a:tcTxStyle b="on"><a:fontRef idx="minor"/><a:schemeClr val="tx2"/>'
            f'</a:tcTxStyle><a:tcStyle><a:tcBdr>{bdr("bottom", 2, "accent1")}</a:tcBdr><a:fill><a:noFill/></a:fill>'
            '</a:tcStyle></a:firstRow></a:tblStyle></a:tblStyleLst>')


# ---------------------------------------------------------------- master and layouts
def body_levels(color='tx1', bucolor='accent1'):
    """Bullet levels of ul/li: accent bullets as in the browser (disc, circle, square), 30/25.5/21 px text,
    line-height 1.35 (~115 % in PowerPoint)."""
    sizes, chars, busz, mar = (30, 25.5, 21), ('•', '◦', '▪'), (100, 106, 100), (34, 74, 110)
    # Bullets sit on the text baseline. '◦' (U+25E6) is drawn at the height of '•'; the bigger '○' (U+25CB)
    # at 80 % sat below the middle of the text. 106 % puts its centre at the height of level 1 (~0.33 em).
    out = ''
    for lvl in range(1, 10):
        k = min(lvl, 3) - 1
        out += ppr(lvl, marL=mar[k] + 36 * max(0, lvl - 3), indent=-30, ln=115, bef=pt(6), bu=chars[k],
                   bucolor=bucolor, busz=busz[k], defrpr=rpr('a:defRPr', sz=pt(sizes[k]), color=color, face='+mn'))
    return out


def plain(px, color, face='+mn', b=None, algn=None, ln=115, i=None):
    """lstStyle level 1 without bullets (subtitles, author, column headings)."""
    return ppr(1, algn=algn, ln=ln, bef=0, defrpr=rpr('a:defRPr', sz=pt(px), b=b, i=i, color=color, face=face))


def master(rid):
    sh = Shapes()
    chrome(sh, False, rid)
    sh.ph('Title Placeholder', 'type="title"', (PAD_X, PAD_T, CW, 60),
          paras=[para('Slide title')], bodypr=body_pr('t'))
    sh.ph('Text Placeholder', 'type="body" idx="1"', (PAD_X, 190, CW, H - FOOT - 190),
          paras=[para('First level'), para('Second level', lvl=1), para('Third level', lvl=2)],
          bodypr=body_pr('t'))
    slide_num(sh, 'accent3', NUM_BOX)
    ids = ''.join(f'<p:sldLayoutId id="{2147483649 + i}" r:id="rIdL{i + 1}"/>' for i in range(len(LAYOUTS)))
    title_style = ppr(1, algn='l', ln=90, bef=0, defrpr=rpr('a:defRPr', sz=pt(50), b=1, color='tx2', face='+mj'))
    other = '<a:defPPr><a:defRPr/></a:defPPr>' + ppr(1, defrpr=rpr('a:defRPr', sz=pt(24), color='tx1', face='+mn'))
    return (XML + f'<p:sldMaster {NS}><p:cSld><p:bg><p:bgPr><a:solidFill><a:schemeClr val="bg1"/></a:solidFill>'
            f'<a:effectLst/></p:bgPr></p:bg>{sh.tree()}</p:cSld>'
            '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" '
            'accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
            f'<p:sldLayoutIdLst>{ids}</p:sldLayoutIdLst><p:hf hdr="0" ftr="0" dt="0"/>'
            f'<p:txStyles><p:titleStyle>{title_style}</p:titleStyle><p:bodyStyle>{body_levels()}</p:bodyStyle>'
            f'<p:otherStyle>{other}</p:otherStyle></p:txStyles></p:sldMaster>')


SUB = (PAD_X, 126, CW, 36)              # h2 small: 10px under a 56px title, 26px Roboto in the accent


def lay_title(sh, rid):
    sh.ph('Title', 'type="ctrTitle"', (PAD_X, 220, CW, 84), ppr(1, algn='ctr', ln=90, defrpr=rpr(
        'a:defRPr', sz=pt(72))), [para('Presentation title')], body_pr('b'))
    sh.ph('Subtitle', 'type="subTitle" idx="1"', (PAD_X, 321, CW, 44), plain(32, 'accent1', algn='ctr'),
          [para('Subtitle')], body_pr('t'))
    sh.ph('Author', 'type="body" sz="quarter" idx="13"', (PAD_X, 400, CW, 34), plain(24, 'accent3', algn='ctr'),
          [para('Name Surname · Event · Date')], body_pr('t'))
    slide_num(sh)


def lay_section(sh, rid):
    chrome(sh, True, rid)
    sh.ph('Title', 'type="title"', (PAD_X, 240, CW, 82), ppr(1, defrpr=rpr('a:defRPr', sz=pt(70), color='FFFFFF')),
          [para('Section title')], body_pr('b'))
    sh.ph('Subtitle', 'type="body" idx="1"', (PAD_X, 332, CW, 46), plain(34, SOFT), [para('Optional subtitle')],
          body_pr('t'))
    slide_num(sh, NUM_DARK, NUM_BOX)


def _title_sub(sh):
    sh.ph('Title', 'type="title"', None, paras=[para('Slide title')])
    sh.ph('Subtitle', 'type="body" sz="quarter" idx="13"', SUB, plain(26, 'accent1'), [para('Optional subtitle')],
          body_pr('t'))


def lay_content(sh, rid):
    _title_sub(sh)
    sh.ph('Content', 'idx="1"', None, paras=[para('One idea per slide, at most ~6 bullets'),
                                             para('Second level', lvl=1)])
    slide_num(sh)


COL_W = (CW - 40) / 2


COL_Y = 144                             # .cols right under the title (h2 56px + 32px margin); no subtitle here


def lay_two(sh, rid):
    sh.ph('Title', 'type="title"', None, paras=[para('Slide title')])
    for k, x in enumerate((PAD_X, PAD_X + COL_W + 40)):
        sh.ph(f'Column heading {k + 1}', f'type="body" sz="quarter" idx="{14 + k}"', (x, COL_Y, COL_W, 44),
              plain(32, 'tx2', b=1), [para(('Left', 'Right')[k])], body_pr('t'))
        sh.ph(f'Column {k + 1}', f'sz="half" idx="{1 + k}"', (x, COL_Y + 56, COL_W, H - FOOT - COL_Y - 56),
              paras=[para('Text, a list, a picture or a table')])
    slide_num(sh)


def lay_title_only(sh, rid):
    _title_sub(sh)
    slide_num(sh)


def lay_blank(sh, rid):
    slide_num(sh)


# name, OOXML type, builder, showMasterSp, background
LAYOUTS = [
    ('Title', 'title', lay_title, True, None),
    ('Section (dark)', 'secHead', lay_section, False, NAVY),
    ('Title and content', 'obj', lay_content, True, None),
    ('Two columns', 'twoObj', lay_two, True, None),
    ('Title only', 'titleOnly', lay_title_only, True, None),
    ('Blank, no footer', 'blank', lay_blank, False, None),
]


def layout(i, rid):
    name, typ, build, show, bg = LAYOUTS[i]
    sh = Shapes()
    build(sh, rid)
    bgx = f'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="{bg}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>' \
        if bg else ''
    hide = '' if show else ' showMasterSp="0"'
    return (XML + f'<p:sldLayout {NS} type="{typ}" preserve="1"{hide}>'
            f'<p:cSld name="{escape(name)}">{bgx}{sh.tree()}</p:cSld><p:clrMapOvr><a:masterClrMapping/>'
            '</p:clrMapOvr><p:hf hdr="0" ftr="0" dt="0"/></p:sldLayout>')


# ---------------------------------------------------------------- slides (examples = ../revealjs/index.html)
def num(sh):
    sh.ph('Slide Number', 'type="sldNum" sz="quarter" idx="12"', None, paras=[
        '<a:p><a:fld id="{B6F15528-21DE-4FAA-801E-634DDDAF4B2B}" type="slidenum"><a:rPr/><a:t>‹#›</a:t></a:fld></a:p>'])


def hl(text):   # .hl: accent and bold
    return run(text, b=1, color='accent1')


def s_title(sh, empty=False):
    p = (lambda t: None) if empty else (lambda t: [para(t)])
    sh.ph('Title', 'type="ctrTitle"', paras=p('Lorem ipsum'))
    sh.ph('Subtitle', 'type="subTitle" idx="1"', paras=p('Sit amet, consectetur adipiscing elit'))
    sh.ph('Author', 'type="body" sz="quarter" idx="13"', paras=p('Name Surname · Event · 2026'))
    num(sh)


def s_section(title, sub):
    def build(sh):
        sh.ph('Title', 'type="title"', paras=[para(title)])
        sh.ph('Subtitle', 'type="body" idx="1"', paras=[para(sub)])
        num(sh)
    return build


def s_content(sh):
    sh.ph('Title', 'type="title"', paras=[para('Content slide')])
    sh.ph('Subtitle', 'type="body" sz="quarter" idx="13"', paras=[para('An optional subtitle in the accent')])
    sh.ph('Content', 'idx="1"', (PAD_X, 190, CW, 200), paras=[
        para('Lorem ipsum dolor sit amet, ', hl('consectetur'), ' adipiscing elit'),
        para('Sed do eiusmod tempor incididunt ut labore'),
        para('Ut enim ad minim veniam, quis nostrud', lvl=1),
        para('Duis aute irure dolor in ', run('reprehenderit', link='rIdH1'))])
    # .box: accent callout (left rule + 8 % tint). Copy it from here; there is no callout placeholder.
    sh.rect('Callout background', (PAD_X, 412, CW, 72), BOX_BG, [para(
        'A callout: excepteur sint occaecat cupidatat non proident.', ppr_xml='<a:pPr><a:buNone/></a:pPr>')],
        body_pr('ctr', False, (32, 0, 24, 0)))
    sh.rect('Callout rule', (PAD_X, 412, 8, 72), 'accent1')
    num(sh)


def s_two(sh):
    sh.ph('Title', 'type="title"', paras=[para('Two columns')])
    sh.ph('Column heading 1', 'type="body" sz="quarter" idx="14"', paras=[para('Left')])
    sh.ph('Column heading 2', 'type="body" sz="quarter" idx="15"', paras=[para('Right')])
    nb = '<a:pPr marL="0" indent="0"><a:buNone/></a:pPr>'
    sh.ph('Column 1', 'sz="half" idx="1"', (PAD_X, COL_Y + 56, COL_W, 130), paras=[para(
        'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor.', ppr_xml=nb)])
    # blockquote: italic with a 6px accent rule on the left
    sh.rect('Quote', (PAD_X, COL_Y + 202, COL_W, 44), None, [para(run('Quote: ut enim ad minim veniam.', i=1, sz=pt(30)))],
            body_pr('ctr', False, (24, 0, 0, 0)))
    sh.rect('Quote rule', (PAD_X, COL_Y + 202, 6, 44), 'accent1')
    x = PAD_X + COL_W + 40
    code = ['def hello():', '    return "data to knowledge"']
    sh.rect('Code', (x, COL_Y + 56, COL_W, 92), CODE_BG, [para(run(c, sz=pt(22), color='tx1', face=MONO_FONT),
                                                        ppr_xml='<a:pPr><a:lnSpc><a:spcPct val="115000"/>'
                                                                '</a:lnSpc></a:pPr>') for c in code],
            body_pr('ctr', False, (20, 0, 20, 0), wrap=False), line=('accent1', 1.5))
    sh.table('Table', (x, COL_Y + 172, 300, 120), [('Item', 'Value'), ('Lorem', '42'), ('Ipsum', '7')], (150, 150), 40,
             pt(24))
    num(sh)


EXAMPLES = [  # (layout index, builder, extra rels)
    (0, s_title, []),
    (1, s_section('Lorem ipsum', 'Section subtitle'), []),
    (2, s_content, [('rIdH1', 'hyperlink', 'https://www.upc.edu/', True)]),
    (3, s_two, []),
    (1, s_section('Thank you', 'name@upc.edu'), []),
]
TEMPLATE = [(0, lambda sh: s_title(sh, empty=True), [])]


def slide(build):
    sh = Shapes()
    build(sh)
    return (XML + f'<p:sld {NS}><p:cSld>{sh.tree()}</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>'
            '</p:sld>')


# ---------------------------------------------------------------- embedded fonts (.fntdata = uncompressed EOT)
def eot(path):
    data = path.read_bytes()
    f = TTFont(path)
    os2, name = f['OS/2'], f['name']
    p = os2.panose
    panose = bytes([p.bFamilyType, p.bSerifStyle, p.bWeight, p.bProportion, p.bContrast, p.bStrokeVariation,
                    p.bArmStyle, p.bLetterForm, p.bMidline, p.bXHeight])

    def s(nid):
        b = name.getDebugName(nid).encode('utf-16-le')
        return struct.pack('<HH', 0, len(b)) + b   # padding, size, string
    strings = s(1)[2:] + s(2) + s(5) + s(4) + struct.pack('<HH', 0, 0)   # family, style, version, full, root
    head = (panose + struct.pack('<BBIHH', 1, os2.fsSelection & 1, os2.usWeightClass, os2.fsType, 0x504C)
            + struct.pack('<4I', os2.ulUnicodeRange1, os2.ulUnicodeRange2, os2.ulUnicodeRange3, os2.ulUnicodeRange4)
            + struct.pack('<2I', os2.ulCodePageRange1, os2.ulCodePageRange2)
            + struct.pack('<I4IH', f['head'].checkSumAdjustment, 0, 0, 0, 0, 0) + strings)
    size = 16 + len(head) + len(data)
    return struct.pack('<4I', size, len(data), 0x00020001, 0) + head + data, panose.hex().upper()


# ---------------------------------------------------------------- package
CT = 'application/vnd.openxmlformats-officedocument.'


def package(path, slides, template):
    parts = {}
    rid = {}
    media = logo_media()
    for k in LOGOS:
        rid[k] = (f'rId{k}png', f'rId{k}svg')
    logo_rels = [(rid[k][j], 'image', f'../media/{k}.{ext}') for k in LOGOS for j, ext in enumerate(('png', 'svg'))]

    parts['ppt/theme/theme1.xml'] = theme()
    parts['ppt/slideMasters/slideMaster1.xml'] = master(rid)
    parts['ppt/slideMasters/_rels/slideMaster1.xml.rels'] = rels(
        [(f'rIdL{i + 1}', 'slideLayout', f'../slideLayouts/slideLayout{i + 1}.xml') for i in range(len(LAYOUTS))]
        + [('rIdT', 'theme', '../theme/theme1.xml')] + logo_rels)
    for i in range(len(LAYOUTS)):
        parts[f'ppt/slideLayouts/slideLayout{i + 1}.xml'] = layout(i, rid)
        parts[f'ppt/slideLayouts/_rels/slideLayout{i + 1}.xml.rels'] = rels(
            [('rIdM', 'slideMaster', '../slideMasters/slideMaster1.xml')] + logo_rels)
    for n, (li, build, extra) in enumerate(slides, 1):
        parts[f'ppt/slides/slide{n}.xml'] = slide(build)
        parts[f'ppt/slides/_rels/slide{n}.xml.rels'] = rels(
            [('rIdL', 'slideLayout', f'../slideLayouts/slideLayout{li + 1}.xml')] + extra)
    for k, v in media.items():
        parts[f'ppt/media/{k}'] = v

    # fonts
    font_rels, font_lst, n = [], '', 0
    for fam, styles in FONTS.items():
        tags, pan = '', ''
        for style in ('regular', 'bold', 'italic', 'boldItalic'):
            if style in styles:
                n += 1
                parts[f'ppt/fonts/font{n}.fntdata'], pan = eot(ROOT / 'fonts' / styles[style])
                font_rels.append((f'rIdF{n}', 'font', f'fonts/font{n}.fntdata'))
                tags += f'<p:{style} r:id="rIdF{n}"/>'
        pitch = 49 if fam == MONO_FONT else 2
        font_lst += (f'<p:embeddedFont><p:font typeface="{fam}" panose="{pan}" pitchFamily="{pitch}" charset="0"/>'
                     f'{tags}</p:embeddedFont>')

    sld_ids = ''.join(f'<p:sldId id="{256 + i}" r:id="rIdS{i + 1}"/>' for i in range(len(slides)))
    default_text = '<a:defPPr><a:defRPr/></a:defPPr>' + ''.join(
        ppr(lv, defrpr=rpr('a:defRPr', sz=pt(30), color='tx1', face='+mn')) for lv in range(1, 10))
    parts['ppt/presentation.xml'] = (
        XML + f'<p:presentation {NS} saveSubsetFonts="0" embedTrueTypeFonts="1">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdM"/></p:sldMasterIdLst>'
        f'<p:sldIdLst>{sld_ids}</p:sldIdLst><p:sldSz cx="{emu(W)}" cy="{emu(H)}"/>'
        f'<p:notesSz cx="6858000" cy="9144000"/><p:embeddedFontLst>{font_lst}</p:embeddedFontLst>'
        f'<p:defaultTextStyle>{default_text}</p:defaultTextStyle></p:presentation>')
    parts['ppt/_rels/presentation.xml.rels'] = rels(
        [('rIdM', 'slideMaster', 'slideMasters/slideMaster1.xml'), ('rIdT', 'theme', 'theme/theme1.xml'),
         ('rIdP', 'presProps', 'presProps.xml'), ('rIdV', 'viewProps', 'viewProps.xml'),
         ('rIdTS', 'tableStyles', 'tableStyles.xml')]
        + [(f'rIdS{i + 1}', 'slide', f'slides/slide{i + 1}.xml') for i in range(len(slides))] + font_rels)
    parts['ppt/presProps.xml'] = XML + f'<p:presentationPr {NS}/>'
    parts['ppt/viewProps.xml'] = (XML + f'<p:viewPr {NS}><p:normalViewPr><p:restoredLeft sz="15620"/>'
                                  '<p:restoredTop sz="94660"/></p:normalViewPr><p:gridSpacing cx="76200" '
                                  'cy="76200"/></p:viewPr>')
    parts['ppt/tableStyles.xml'] = table_styles()
    parts['docProps/core.xml'] = (
        XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>DTAK slide template</dc:title>'
        '<dcterms:created xsi:type="dcterms:W3CDTF">2026-11-19T00:00:00Z</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-11-19T00:00:00Z</dcterms:modified></cp:coreProperties>')
    parts['docProps/app.xml'] = (XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
                                 'extended-properties"><Application>Microsoft Office PowerPoint</Application>'
                                 '<PresentationFormat>Widescreen</PresentationFormat></Properties>')
    parts['_rels/.rels'] = rels([
        ('rId1', 'officeDocument', 'ppt/presentation.xml'),
        ('rId2', 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties',
         'docProps/core.xml'),
        ('rId3', 'extended-properties', 'docProps/app.xml')])

    main = 'template.main+xml' if template else 'presentation.main+xml'
    ov = {'/ppt/presentation.xml': f'{CT}presentationml.{main}',
          '/ppt/theme/theme1.xml': f'{CT}theme+xml',
          '/ppt/slideMasters/slideMaster1.xml': f'{CT}presentationml.slideMaster+xml',
          '/ppt/presProps.xml': f'{CT}presentationml.presProps+xml',
          '/ppt/viewProps.xml': f'{CT}presentationml.viewProps+xml',
          '/ppt/tableStyles.xml': f'{CT}presentationml.tableStyles+xml',
          '/docProps/core.xml': 'application/vnd.openxmlformats-package.core-properties+xml',
          '/docProps/app.xml': f'{CT}extended-properties+xml'}
    for i in range(len(LAYOUTS)):
        ov[f'/ppt/slideLayouts/slideLayout{i + 1}.xml'] = f'{CT}presentationml.slideLayout+xml'
    for i in range(len(slides)):
        ov[f'/ppt/slides/slide{i + 1}.xml'] = f'{CT}presentationml.slide+xml'
    parts['[Content_Types].xml'] = (
        XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
        '<Default Extension="svg" ContentType="image/svg+xml"/>'
        '<Default Extension="fntdata" ContentType="application/x-fontdata"/>'
        + ''.join(f'<Override PartName="{k}" ContentType="{v}"/>' for k, v in ov.items()) + '</Types>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        for name in ['[Content_Types].xml', '_rels/.rels'] + sorted(set(parts) - {'[Content_Types].xml', '_rels/.rels'}):
            data = parts[name]
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data.encode() if isinstance(data, str) else data)
    path.write_bytes(buf.getvalue())
    print(f'{path}  ({len(slides)} slides, {len(buf.getvalue()) // 1024} KiB)')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    package(OUT / 'dtak.potx', TEMPLATE, template=True)
    package(OUT / 'dtak.pptx', EXAMPLES, template=False)
