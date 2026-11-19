#!/usr/bin/env python3
"""Build the DTAK Word / Google Docs document template: dtak.dotx and dtak.docx.

The Word twin of ../../latex/dtakdoc.cls (article): A4, two-sided (mirrored margins), UPC mark + DTAK logo in the
header on page 1, then the UPC mark on even pages and the DTAK logo on odd pages, a thin navy rule under the
header, the page number at the outer edge. Titles and Heading 1 in Montserrat Bold, navy; the body in Georgia.
Everything lives in styles, theme, numbering and the header/footer parts, so typed text gets the DTAK look.
The OOXML package is written directly (like ../../../slides/pptx/tools/make_pptx.py), so the output is
byte-identical on every run.

    .venv/bin/python -I documents/docx/tools/make_docx.py [outdir]     # default: documents/docx/

Outputs:
  dtak.dotx  Word template (File > New from it): the title block and one empty section.
  dtak.docx  the same template with the example article of ../../latex/article.tex; also the file to upload to
             Google Docs.

Montserrat Bold is embedded (obfuscated TTF, as Word does), so Word shows the headings without installing anything.
Georgia ships with Windows, macOS, Office and Google Docs, and is not embedded. Google Docs has Montserrat natively.
"""
import io
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg

ROOT = Path(__file__).resolve().parents[3]          # dtak-image/
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'documents' / 'docx'

# ---------------------------------------------------------------- identity (= ../../latex/dtakdoc.cls)
ACCENT = '0076CF'     # dtakaccent: UPC blue, Pantone 2195 (subtitle, links, table header rule)
NAVY = '0A2A4F'       # dtaknavy: titles, headings, header rule, table top/bottom rules
MUTED = '6B7785'      # dtakmuted: page numbers, author/date line
LINE = 'DDE3EA'       # dtakline
SOFT = '66ADE2'
EDGE = '8494A7'

TITLE_FONT, BODY_FONT = 'Montserrat', 'Georgia'
TITLE_TTF = ROOT / 'fonts' / 'Montserrat-Bold.ttf'   # embedded as the bold face of Montserrat
FONT_KEY = '{6A8C2D3E-1B4F-4A7C-9E2D-5F0B3C8A1D74}'   # fixed obfuscation key (any GUID works)

# Page geometry in mm (= the geometry options of dtakdoc.cls)
INNER = OUTER = 25
TOP, BOTTOM = 38, 28
HEADER_DIST = 16      # page top -> header top: the logos sit 13 mm high in the 13 mm header box, 9 mm above the text
FOOTER_DIST = 14      # page bottom -> footer bottom
TEXT_W = 210 - INNER - OUTER
LOGO_H = 10           # both marks 10 mm tall: equal footing; dtak_long's minimum print size
STAMP = (2026, 11, 19, 0, 0, 0)       # fixed zip/core dates

LOGOS = {  # key -> svg; the PNG fallback is rendered from it (Google Docs, LibreOffice and old Word use it)
    'upc': ROOT / 'slides/revealjs/theme/logos/upc-barcelonatech.svg',
    'dtak': ROOT / 'logo/dtak_long.svg',
}
LOGO_NAMES = {'upc': 'UPC BarcelonaTech', 'dtak': 'DTAK. Data to knowledge, Data for knowledge'}


def tw(mm):  # mm -> twentieths of a point
    return int(round(mm * 1440 / 25.4))


def emu(mm):
    return int(round(mm * 36000))


XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
      'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"')


def rels(items):
    """items: [(rid, type, target[, external])]"""
    out = [f'<Relationship Id="{i[0]}" Type="{REL if "/" not in i[1] else ""}{i[1]}" Target="{escape(i[2])}"'
           + (' TargetMode="External"' if len(i) > 3 else '') + '/>' for i in items]
    return (XML + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + ''.join(out) + '</Relationships>')


# ---------------------------------------------------------------- run / paragraph helpers
def t(text):
    sp = ' xml:space="preserve"' if text != text.strip() else ''
    return f'<w:t{sp}>{escape(text)}</w:t>'


def r(text, rpr=''):
    return f'<w:r>{f"<w:rPr>{rpr}</w:rPr>" if rpr else ""}{t(text)}</w:r>'


def p(content='', style=None, ppr=''):
    s = f'<w:pStyle w:val="{style}"/>' if style else ''
    pp = f'<w:pPr>{s}{ppr}</w:pPr>' if s or ppr else ''
    if isinstance(content, str) and content and not content.startswith('<'):
        content = r(content)
    return f'<w:p>{pp}{content}</w:p>'


def fld(instr, cached, rpr=''):
    """A complex field with a cached result (Google Docs keeps the cached text)."""
    rp = f'<w:rPr>{rpr}</w:rPr>' if rpr else ''
    return (f'<w:r>{rp}<w:fldChar w:fldCharType="begin"/></w:r>'
            f'<w:r>{rp}<w:instrText xml:space="preserve"> {instr} </w:instrText></w:r>'
            f'<w:r>{rp}<w:fldChar w:fldCharType="separate"/></w:r>{r(cached, rpr)}'
            f'<w:r>{rp}<w:fldChar w:fldCharType="end"/></w:r>')


# ---------------------------------------------------------------- logos
def svg_size(path):
    s = path.read_text()
    w, h = (float(re.search(fr'<svg[^>]*\s{k}="([\d.]+)', s).group(1)) for k in ('width', 'height'))
    return w / h


def logo_media():
    media = {}
    for k, svg in LOGOS.items():
        media[f'{k}.svg'] = svg.read_bytes()
        media[f'{k}.png'] = cairosvg.svg2png(url=str(svg), output_height=512)
    return media


LOGO_RELS = [(f'rId{k}{ext}', 'image', f'media/{k}.{ext}') for k in LOGOS for ext in ('png', 'svg')]


def logo(key, n):
    """Inline picture, LOGO_H tall: PNG blip with the SVG as the Office 2016+ extension."""
    cx, cy = emu(LOGO_H * svg_size(LOGOS[key])), emu(LOGO_H)
    name = LOGO_NAMES[key]
    return ('<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            f'<wp:docPr id="{n}" name="{key}" descr="{escape(name)}"/>'
            '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{n}" name="{key}"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rId{key}png"><a:extLst><a:ext uri="{{96DAC541-7B7A-43D3-8B79-37D633B846F1}}">'
            '<asvg:svgBlip xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" '
            f'r:embed="rId{key}svg"/></a:ext></a:extLst></a:blip><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            '</wp:inline></w:drawing></w:r>')


# ---------------------------------------------------------------- headers and footers
def hdr(body, root='hdr'):
    return XML + f'<w:{root} {NS}>{body}</w:{root}>'


def headers():
    tab = '<w:r><w:tab/></w:r>'
    return {
        'header1.xml': hdr(p(logo('upc', 101) + tab + logo('dtak', 102), 'Header')),   # page 1: both marks
        'header2.xml': hdr(p(logo('upc', 103), 'Header')),                               # even pages: UPC left
        'header3.xml': hdr(p(logo('dtak', 104), 'Header', '<w:jc w:val="right"/>')),     # odd pages: DTAK right
        'footer1.xml': hdr(p(fld('PAGE', '1'), 'Footer', '<w:jc w:val="right"/>'), 'ftr'),
        'footer2.xml': hdr(p(fld('PAGE', '2'), 'Footer', '<w:jc w:val="left"/>'), 'ftr'),
        'footer3.xml': hdr(p(fld('PAGE', '3'), 'Footer', '<w:jc w:val="right"/>'), 'ftr'),
    }


def sect_pr():
    return ('<w:sectPr>'
            '<w:headerReference w:type="first" r:id="rIdH1"/><w:headerReference w:type="even" r:id="rIdH2"/>'
            '<w:headerReference w:type="default" r:id="rIdH3"/>'
            '<w:footerReference w:type="first" r:id="rIdF1"/><w:footerReference w:type="even" r:id="rIdF2"/>'
            '<w:footerReference w:type="default" r:id="rIdF3"/>'
            f'<w:pgSz w:w="{tw(210)}" w:h="{tw(297)}"/>'
            f'<w:pgMar w:top="{tw(TOP)}" w:right="{tw(OUTER)}" w:bottom="{tw(BOTTOM)}" w:left="{tw(INNER)}" '
            f'w:header="{tw(HEADER_DIST)}" w:footer="{tw(FOOTER_DIST)}" w:gutter="0"/>'
            '<w:cols w:space="708"/><w:titlePg/><w:docGrid w:linePitch="360"/></w:sectPr>')


# ---------------------------------------------------------------- styles
def rpr(font=None, sz=None, color=None, b=False, i=False):
    out = ''
    if font:
        out += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    if b:
        out += '<w:b/><w:bCs/>'
    if i:
        out += '<w:i/><w:iCs/>'
    if color:
        out += f'<w:color w:val="{color}"/>'
    if sz:
        out += f'<w:sz w:val="{int(sz * 2)}"/><w:szCs w:val="{int(sz * 2)}"/>'
    return out


def style(sid, name, ppr='', rp='', kind='paragraph', based='Normal', nxt=None, extra='', default=False, prio=None):
    d = ' w:default="1"' if default else ''
    b = f'<w:basedOn w:val="{based}"/>' if based else ''
    n = f'<w:next w:val="{nxt}"/>' if nxt else ''
    pr = f'<w:uiPriority w:val="{prio}"/>' if prio is not None else ''
    return (f'<w:style w:type="{kind}"{d} w:styleId="{sid}"><w:name w:val="{name}"/>{b}{n}{pr}<w:qFormat/>'
            f'{f"<w:pPr>{ppr}</w:pPr>" if ppr else ""}{extra}{f"<w:rPr>{rp}</w:rPr>" if rp else ""}</w:style>')


def spacing(before=0, after=0, line=None):
    ln = f' w:line="{line}" w:lineRule="auto"' if line else ''
    return f'<w:spacing w:before="{before}" w:after="{after}"{ln}/>'


def heading(level, rp, before, after):
    return style(f'Heading{level}', f'heading {level}', nxt='Normal', prio=9,
                 ppr=(f'<w:keepNext/><w:keepLines/><w:numPr><w:ilvl w:val="{level - 1}"/><w:numId w:val="1"/>'
                      f'</w:numPr>{spacing(before, after)}<w:jc w:val="left"/>'
                      f'<w:outlineLvl w:val="{level - 1}"/>'),
                 rp=rp)


def tbl_border(edge, sz, color):
    return f'<w:{edge} w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'


def styles():
    nil = ''.join(f'<w:{e} w:val="nil"/>' for e in ('left', 'right', 'insideV'))
    defaults = ('<w:docDefaults><w:rPrDefault><w:rPr>'
                '<w:rFonts w:asciiTheme="minorHAnsi" w:hAnsiTheme="minorHAnsi" w:eastAsiaTheme="minorHAnsi" '
                'w:cstheme="minorBidi"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-GB" w:eastAsia="en-US" w:bidi="ar-SA"/>'
                '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr>'
                f'{spacing(0, 120, 264)}</w:pPr></w:pPrDefault></w:docDefaults>')
    s = [
        style('Normal', 'Normal', based=None, default=True, ppr='<w:jc w:val="both"/>'),
        # Title block (= \maketitle): Title, Subtitle, Author line.
        style('Title', 'Title', nxt='Subtitle', prio=10, ppr=f'{spacing(0, 120, 240)}<w:jc w:val="left"/>',
              rp=rpr(TITLE_FONT, 22, NAVY, b=True) + '<w:kern w:val="28"/>'),
        style('Subtitle', 'Subtitle', nxt='AuthorLine', prio=11, ppr=f'{spacing(0, 120)}<w:jc w:val="left"/>',
              rp=rpr(None, 13, ACCENT)),
        style('AuthorLine', 'Author line', nxt='Normal', ppr=f'{spacing(0, 480)}<w:jc w:val="left"/>',
              rp=rpr(color=MUTED)),
        style('AbstractHeading', 'Abstract heading', nxt='Abstract',
              ppr=f'<w:keepNext/>{spacing(0, 80)}<w:jc w:val="center"/>', rp=rpr(sz=9.5, b=True)),
        style('Abstract', 'Abstract', ppr=f'{spacing(0, 120)}<w:ind w:left="{tw(10)}" w:right="{tw(10)}"/>',
              rp=rpr(sz=9.5)),
        # Headings (= \section, \subsection, \subsubsection), numbered 1, 1.1, 1.1.1
        heading(1, rpr(TITLE_FONT, 14.5, NAVY, b=True), 360, 160),
        heading(2, rpr(None, 12, NAVY, b=True), 280, 120),
        heading(3, rpr(None, 11, NAVY, b=True), 240, 100),
        style('Caption', 'caption', nxt='Normal', prio=35,
              ppr=f'<w:keepNext/>{spacing(120, 120)}<w:jc w:val="center"/>', rp=rpr(sz=10)),
        style('Equation', 'Equation', nxt='Normal',
              ppr=(f'<w:tabs><w:tab w:val="center" w:pos="{tw(TEXT_W / 2)}"/>'
                   f'<w:tab w:val="right" w:pos="{tw(TEXT_W)}"/></w:tabs>{spacing(120, 240)}<w:jc w:val="left"/>')),
        # Header: the logos, with a thin navy rule 2.5 mm under them (= \dtak@head)
        style('Header', 'header', prio=99,
              ppr=(f'<w:pBdr><w:bottom w:val="single" w:sz="3" w:space="7" w:color="{NAVY}"/></w:pBdr>'
                   f'<w:tabs><w:tab w:val="clear" w:pos="4513"/><w:tab w:val="clear" w:pos="9026"/>'
                   f'<w:tab w:val="right" w:pos="{tw(TEXT_W)}"/></w:tabs>{spacing(0, 0, 240)}<w:jc w:val="left"/>')),
        style('Footer', 'footer', prio=99, ppr=f'{spacing(0, 0, 240)}', rp=rpr(sz=9, color=MUTED)),
        style('Hyperlink', 'Hyperlink', kind='character', based=None, prio=99, rp=rpr(color=ACCENT)),
        style('ListParagraph', 'List Paragraph', prio=34, ppr=f'<w:ind w:left="{tw(10)}"/>{spacing(0, 60)}'),
        # Tables (= booktabs): navy top/bottom rules, a UPC-blue rule under the header row, no vertical lines.
        '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/>'
        '<w:uiPriority w:val="99"/><w:semiHidden/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar>'
        '<w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/>'
        '<w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>',
        '<w:style w:type="table" w:styleId="DTAKTable"><w:name w:val="DTAK Table"/><w:basedOn w:val="TableNormal"/>'
        '<w:uiPriority w:val="1"/><w:qFormat/><w:pPr><w:spacing w:before="40" w:after="40" w:line="240" '
        'w:lineRule="auto"/><w:jc w:val="left"/></w:pPr>'
        f'<w:tblPr><w:jc w:val="center"/><w:tblBorders>{tbl_border("top", 6, NAVY)}{nil}'
        f'{tbl_border("bottom", 6, NAVY)}<w:insideH w:val="nil"/></w:tblBorders><w:tblCellMar>'
        '<w:top w:w="40" w:type="dxa"/><w:left w:w="113" w:type="dxa"/><w:bottom w:w="40" w:type="dxa"/>'
        '<w:right w:w="113" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        '<w:tblStylePr w:type="firstRow"><w:tblPr/><w:trPr><w:tblHeader/></w:trPr><w:tcPr><w:tcBorders>'
        f'{tbl_border("bottom", 4, ACCENT)}</w:tcBorders></w:tcPr></w:tblStylePr></w:style>',
    ]
    return (XML + f'<w:styles {NS}>{defaults}'
            '<w:latentStyles w:defLockedState="0" w:defUIPriority="99" w:defSemiHidden="0" w:defUnhideWhenUsed="0" '
            'w:defQFormat="0" w:count="376"/>' + ''.join(s) + '</w:styles>')


def numbering():
    lvls = ''
    for i, txt in enumerate(('%1', '%1.%2', '%1.%2.%3')):
        lvls += (f'<w:lvl w:ilvl="{i}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                 f'<w:pStyle w:val="Heading{i + 1}"/><w:lvlText w:val="{txt}"/><w:lvlJc w:val="left"/>'
                 f'<w:pPr><w:tabs><w:tab w:val="num" w:pos="{tw(10)}"/></w:tabs>'
                 f'<w:ind w:left="{tw(10)}" w:hanging="{tw(10)}"/></w:pPr></w:lvl>')
    return (XML + f'<w:numbering {NS}><w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="multilevel"/>'
            f'{lvls}</w:abstractNum>'
            '<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>'
            '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
            f'<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="{tw(7)}" w:hanging="{tw(5)}"/></w:pPr>'
            f'<w:rPr><w:color w:val="{ACCENT}"/></w:rPr></w:lvl></w:abstractNum>'
            '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
            '<w:num w:numId="2"><w:abstractNumId w:val="1"/></w:num></w:numbering>')


def theme():
    clr = (f'<a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1>'
           f'<a:dk2><a:srgbClr val="{NAVY}"/></a:dk2><a:lt2><a:srgbClr val="{LINE}"/></a:lt2>'
           f'<a:accent1><a:srgbClr val="{ACCENT}"/></a:accent1><a:accent2><a:srgbClr val="{SOFT}"/></a:accent2>'
           f'<a:accent3><a:srgbClr val="{MUTED}"/></a:accent3><a:accent4><a:srgbClr val="{EDGE}"/></a:accent4>'
           f'<a:accent5><a:srgbClr val="{NAVY}"/></a:accent5><a:accent6><a:srgbClr val="{LINE}"/></a:accent6>'
           f'<a:hlink><a:srgbClr val="{ACCENT}"/></a:hlink><a:folHlink><a:srgbClr val="{ACCENT}"/></a:folHlink>')
    fonts = (f'<a:majorFont><a:latin typeface="{TITLE_FONT}"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>'
             f'<a:minorFont><a:latin typeface="{BODY_FONT}"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>')
    ph = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    lines = ''.join(f'<a:ln w="{w}" cap="flat" cmpd="sng" algn="ctr">{ph}<a:prstDash val="solid"/>'
                    '<a:miter lim="800000"/></a:ln>' for w in (6350, 12700, 19050))
    fmt = (f'<a:fillStyleLst>{ph * 3}</a:fillStyleLst><a:lnStyleLst>{lines}</a:lnStyleLst>'
           '<a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 + '</a:effectStyleLst>'
           f'<a:bgFillStyleLst>{ph * 3}</a:bgFillStyleLst>')
    return (XML + '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="DTAK">'
            f'<a:themeElements><a:clrScheme name="DTAK">{clr}</a:clrScheme><a:fontScheme name="DTAK">{fonts}'
            f'</a:fontScheme><a:fmtScheme name="DTAK">{fmt}</a:fmtScheme></a:themeElements>'
            '<a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')


def settings():
    return (XML + f'<w:settings {NS}><w:embedTrueTypeFonts/><w:mirrorMargins/>'
            '<w:defaultTabStop w:val="709"/><w:autoHyphenation/><w:evenAndOddHeaders/>'
            '<w:characterSpacingControl w:val="doNotCompress"/>'
            '<m:mathPr><m:mathFont m:val="Cambria Math"/><m:dispDef/></m:mathPr>'
            '<w:defaultTableStyle w:val="DTAKTable"/>'
            '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" '
            'w:val="15"/></w:compat></w:settings>')


# ---------------------------------------------------------------- embedded font (.odttf, ECMA-376 Part 1 §17.8.1)
def odttf(path, guid):
    key = bytes.fromhex(re.sub(r'[^0-9A-Fa-f]', '', guid))[::-1]
    data = bytearray(path.read_bytes())
    for i in range(32):
        data[i] ^= key[i % 16]
    return bytes(data)


def font_table():
    return (XML + f'<w:fonts {NS}>'
            f'<w:font w:name="{BODY_FONT}"><w:panose1 w:val="02040502050405020303"/><w:charset w:val="00"/>'
            '<w:family w:val="roman"/><w:pitch w:val="variable"/></w:font>'
            f'<w:font w:name="{TITLE_FONT}"><w:charset w:val="00"/><w:family w:val="swiss"/>'
            f'<w:pitch w:val="variable"/><w:embedBold r:id="rIdFont1" w:fontKey="{FONT_KEY}"/></w:font>'
            '<w:font w:name="Cambria Math"><w:panose1 w:val="02040503050406030204"/><w:charset w:val="00"/>'
            '<w:family w:val="roman"/><w:pitch w:val="variable"/></w:font></w:fonts>')


# ---------------------------------------------------------------- content
LOREM_ABSTRACT = ('Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore '
                  'et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut '
                  'aliquip ex ea commodo consequat.')
FILLER = ('Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor. '
          'Maecenas mattis. Sed convallis tristique sem. Proin ut ligula vel nunc egestas porttitor. Morbi lectus '
          'risus, iaculis vel, suscipit quis, luctus non, massa. Fusce ac turpis quis ligula lacinia aliquet. Mauris '
          'ipsum. Nulla metus metus, ullamcorper vel, tincidunt sed, euismod in, nibh. Quisque volutpat condimentum '
          'velit.')


def title_block(title, subtitle, author_line):
    return p(title, 'Title') + p(subtitle, 'Subtitle') + p(author_line, 'AuthorLine')


def bookmarked(content, name, bid):
    return f'<w:bookmarkStart w:id="{bid}" w:name="{name}"/>{content}<w:bookmarkEnd w:id="{bid}"/>'


def link(text, rid):
    return f'<w:hyperlink r:id="{rid}" w:history="1">{r(text, "<w:rStyle w:val=\"Hyperlink\"/>")}</w:hyperlink>'


def equation():
    """E[X] = sum_i x_i p(x_i), centred, numbered (1) at the right margin."""
    def mr(s, sty=None):
        st = f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else ''
        return f'<m:r>{st}<m:t xml:space="preserve">{escape(s)}</m:t></m:r>'

    def sub(base, s):
        return f'<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>'
    nary = (f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/><m:supHide m:val="1"/></m:naryPr>'
            f'<m:sub>{mr("i")}</m:sub><m:sup/><m:e>{sub(mr("x"), mr("i"))}{mr(" ")}{mr("p")}'
            f'<m:d><m:e>{sub(mr("x"), mr("i"))}</m:e></m:d></m:e></m:nary>')
    expr = f'{mr("𝔼", "p")}<m:d><m:dPr><m:begChr m:val="["/><m:endChr m:val="]"/></m:dPr><m:e>{mr("X")}</m:e></m:d>'
    math = f'<m:oMath>{expr}{mr("=")}{nary}{mr(".", "p")}</m:oMath>'
    return p(f'<w:r><w:tab/></w:r>{math}<w:r><w:tab/></w:r>{r("(1)")}', 'Equation')


def table(rows):
    widths = (tw(40), tw(25))
    grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in widths)
    out = ''
    for n, row in enumerate(rows):
        cells = ''
        for j, txt in enumerate(row):
            jc = '<w:jc w:val="right"/>' if j else ''
            cells += f'<w:tc><w:tcPr><w:tcW w:w="{widths[j]}" w:type="dxa"/></w:tcPr>{p(txt, ppr=jc)}</w:tc>'
        trpr = '<w:trPr><w:tblHeader/></w:trPr>' if n == 0 else ''
        out += f'<w:tr>{trpr}{cells}</w:tr>'
    return (f'<w:tbl><w:tblPr><w:tblStyle w:val="DTAKTable"/><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/>'
            '<w:tblLook w:val="0020" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
            f'w:noHBand="1" w:noVBand="1"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{out}</w:tbl>')


def example_body():
    b = title_block('Lorem ipsum dolor sit amet', 'Consectetur adipiscing elit', 'Name Surname · November 2026')
    b += p('Abstract', 'AbstractHeading') + p(LOREM_ABSTRACT, 'Abstract')
    b += p('Introduction', 'Heading1')
    b += p(r('Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer nec odio. Praesent libero. Sed cursus '
             'ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent '
             'mauris. See Section ') + fld('REF _RefMethod \\r \\h', '2') + r(' and ')
           + link('the DTAK site', 'rIdLink1') + r('.'))
    b += p('Background', 'Heading2')
    b += p('Fusce nec tellus sed augue semper porta. Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent '
           'taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Curabitur sodales ligula '
           'in libero:')
    b += equation()
    b += p(bookmarked(r('Method'), '_RefMethod', 1), 'Heading1')
    b += p(r('Table ') + fld('SEQ Table \\* ARABIC', '1') + r(': A table with booktabs.'), 'Caption')
    b += table([('Item', 'Value'), ('Lorem', '42'), ('Ipsum', '7')])
    b += p('Lorem', 'Heading2') + p('Ipsum', 'Heading3')
    b += ''.join(p(FILLER) for _ in range(14))
    b += p('Conclusions', 'Heading1')
    b += p('Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Nam nec ante.')
    return b


def template_body():
    return (title_block('Title', 'Subtitle', 'Name Surname · Date') + p('Introduction', 'Heading1')
            + p('Text.'))


def document(body):
    return XML + f'<w:document {NS}><w:body>{body}{sect_pr()}</w:body></w:document>'


# ---------------------------------------------------------------- package
CT = 'application/vnd.openxmlformats-officedocument.'


def package(path, body, template, title):
    parts = {}
    for k, v in logo_media().items():
        parts[f'word/media/{k}'] = v
    for name, xml in headers().items():
        parts[f'word/{name}'] = xml
        parts[f'word/_rels/{name}.rels'] = rels(LOGO_RELS if name.startswith('header') else [])
    parts['word/fonts/font1.odttf'] = odttf(TITLE_TTF, FONT_KEY)
    parts['word/fontTable.xml'] = font_table()
    parts['word/_rels/fontTable.xml.rels'] = rels([('rIdFont1', 'font', 'fonts/font1.odttf')])
    parts['word/styles.xml'] = styles()
    parts['word/numbering.xml'] = numbering()
    parts['word/settings.xml'] = settings()
    parts['word/theme/theme1.xml'] = theme()
    parts['word/document.xml'] = document(body)
    parts['word/_rels/document.xml.rels'] = rels(
        [('rIdStyles', 'styles', 'styles.xml'), ('rIdNum', 'numbering', 'numbering.xml'),
         ('rIdSettings', 'settings', 'settings.xml'), ('rIdTheme', 'theme', 'theme/theme1.xml'),
         ('rIdFonts', 'fontTable', 'fontTable.xml'),
         ('rIdH1', 'header', 'header1.xml'), ('rIdH2', 'header', 'header2.xml'), ('rIdH3', 'header', 'header3.xml'),
         ('rIdF1', 'footer', 'footer1.xml'), ('rIdF2', 'footer', 'footer2.xml'), ('rIdF3', 'footer', 'footer3.xml'),
         ('rIdLink1', 'hyperlink', 'https://dtak.upc.edu', True)])
    parts['docProps/core.xml'] = (
        XML + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
        f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{escape(title)}</dc:title>'
        '<dcterms:created xsi:type="dcterms:W3CDTF">2026-11-19T00:00:00Z</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">2026-11-19T00:00:00Z</dcterms:modified></cp:coreProperties>')
    parts['docProps/app.xml'] = (XML + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
                                 'extended-properties"><Application>Microsoft Office Word</Application></Properties>')
    parts['_rels/.rels'] = rels([
        ('rId1', 'officeDocument', 'word/document.xml'),
        ('rId2', 'http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties',
         'docProps/core.xml'),
        ('rId3', 'extended-properties', 'docProps/app.xml')])

    main = 'template.main+xml' if template else 'document.main+xml'
    wml = f'{CT}wordprocessingml.'
    ov = {'/word/document.xml': wml + main,
          '/word/styles.xml': wml + 'styles+xml', '/word/numbering.xml': wml + 'numbering+xml',
          '/word/settings.xml': wml + 'settings+xml', '/word/fontTable.xml': wml + 'fontTable+xml',
          '/word/theme/theme1.xml': f'{CT}theme+xml',
          '/docProps/core.xml': 'application/vnd.openxmlformats-package.core-properties+xml',
          '/docProps/app.xml': f'{CT}extended-properties+xml'}
    for name in headers():
        ov[f'/word/{name}'] = wml + ('header+xml' if name.startswith('header') else 'footer+xml')
    parts['[Content_Types].xml'] = (
        XML + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
        '<Default Extension="svg" ContentType="image/svg+xml"/>'
        f'<Default Extension="odttf" ContentType="{CT}obfuscatedFont"/>'
        + ''.join(f'<Override PartName="{k}" ContentType="{v}"/>' for k, v in ov.items()) + '</Types>')

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        first = ['[Content_Types].xml', '_rels/.rels']
        for name in first + sorted(set(parts) - set(first)):
            data = parts[name]
            info = zipfile.ZipInfo(name, STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data.encode() if isinstance(data, str) else data)
    path.write_bytes(buf.getvalue())
    print(f'{path}  ({len(buf.getvalue()) // 1024} KiB)')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    package(OUT / 'dtak.dotx', template_body(), template=True, title='DTAK document template')
    package(OUT / 'dtak.docx', example_body(), template=False, title='Lorem ipsum dolor sit amet')
