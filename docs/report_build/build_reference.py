"""Reference PDF = RESEARCH_NOTE.md (rendered) + the project report PDF. Usage: .venv/bin/python docs/report_build/build_reference.py"""
import os, re, sys
from pathlib import Path
import matplotlib
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPO = Path(__file__).resolve().parents[2]
fd = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for n, f in (("S", "DejaVuSans.ttf"), ("S-B", "DejaVuSans-Bold.ttf"), ("S-I", "DejaVuSans-Oblique.ttf"), ("S-BI", "DejaVuSans-BoldOblique.ttf"), ("M", "DejaVuSansMono.ttf")):
    pdfmetrics.registerFont(TTFont(n, os.path.join(fd, f)))
pdfmetrics.registerFontFamily("S", normal="S", bold="S-B", italic="S-I", boldItalic="S-BI")
INK, MUTED, SHADE, RULE = (colors.HexColor(c) for c in ("#1f2328", "#57606a", "#f3f6fa", "#d0d7de"))
st = {"h1": ParagraphStyle("h1", fontName="S-B", fontSize=17, leading=22, spaceAfter=8, textColor=INK),
      "h2": ParagraphStyle("h2", fontName="S-B", fontSize=12, leading=16, spaceBefore=10, spaceAfter=5, textColor=INK, keepWithNext=1),
      "p": ParagraphStyle("p", fontName="S", fontSize=8.8, leading=12.6, spaceAfter=5, textColor=INK),
      "c": ParagraphStyle("c", fontName="S", fontSize=7.8, leading=10.2, textColor=INK)}


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font name="M" size="7.8">\1</font>', t)
    return re.sub(r"(?<![\w*])\*([^*]+)\*(?!\w)", r"<i>\1</i>", t)


story, W = [], letter[0] - 1.7 * inch
lines = (REPO / "RESEARCH_NOTE.md").read_text().splitlines()
i = 0
while i < len(lines):
    ln = lines[i]
    if ln.startswith("# "):
        story.append(Paragraph(inline(ln[2:]), st["h1"]))
    elif ln.startswith("## "):
        story.append(Paragraph(inline(ln[3:]), st["h2"]))
    elif ln.startswith("|"):
        rows = []
        while i < len(lines) and lines[i].startswith("|"):
            if not re.match(r"^\|[-| ]+\|$", lines[i]):
                rows.append([Paragraph(inline(c.strip()), st["c"]) for c in lines[i].strip("|").split("|")])
            i += 1
        t = Table(rows, colWidths=[W * 0.28, W * 0.72][:len(rows[0])] if len(rows[0]) == 2 else None)
        t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BACKGROUND", (0, 0), (-1, 0), SHADE),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]))
        story += [t, Spacer(1, 6)]
        continue
    elif re.match(r"^(\d+\.|-) ", ln):
        items = []
        while i < len(lines) and re.match(r"^(\d+\.|-) ", lines[i]):
            items.append(ListItem(Paragraph(inline(re.sub(r"^(\d+\.|-) ", "", lines[i])), st["p"]), leftIndent=12))
            i += 1
        story.append(ListFlowable(items, bulletType="1" if re.match(r"^\d", lines[i - 1]) else "bullet", leftIndent=14, bulletFontName="S", bulletFontSize=8))
        continue
    elif ln.strip():
        story.append(Paragraph(inline(ln), st["p"]))
    i += 1
note = REPO / "docs/report_build/_note.pdf"
SimpleDocTemplate(str(note), pagesize=letter, leftMargin=0.85 * inch, rightMargin=0.85 * inch, topMargin=0.75 * inch,
                  bottomMargin=0.75 * inch, title="Who Rises in the Colony? Reference").build(story)
w = PdfWriter()
for f in (note, REPO / "docs/who_rises_in_the_colony_report.pdf"):
    for pg in PdfReader(str(f)).pages:
        w.add_page(pg)
w.add_metadata({"/Title": "Who Rises in the Colony? Reference (research note + project report)", "/Author": "Soham Padia and team"})
out = REPO / "docs/who_rises_in_the_colony_reference.pdf"
with open(out, "wb") as fh:
    w.write(fh)
note.unlink()
print("wrote", out, len(PdfReader(str(out)).pages), "pages")
