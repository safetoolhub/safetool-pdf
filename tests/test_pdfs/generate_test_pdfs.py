# This file is part of SafeTool PDF, licensed under GPLv3 with
# additional terms. See LICENSE or https://safetoolhub.org for details.

"""Generate 31 regression-test PDFs for SafeTool PDF.

Uses fpdf2, reportlab, pikepdf, and Pillow to produce a variety of PDF
structures that exercise different optimisation paths.

Run standalone:
    python generate_test_pdfs.py          # writes to ./generated/
"""

from __future__ import annotations

import io
import logging
import struct
import sys
import textwrap
import warnings
import zlib
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — each helper catches ImportError so missing libs skip gracefully
# ---------------------------------------------------------------------------

def _import_fpdf():
    from fpdf import FPDF
    return FPDF

def _import_reportlab():
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    return rl_canvas, A4

def _import_pikepdf():
    import pikepdf
    return pikepdf

def _import_pillow():
    from PIL import Image
    return Image

# ---------------------------------------------------------------------------
# 1. simple_text
# ---------------------------------------------------------------------------

def gen_simple_text(out: Path) -> Path:
    """Only text, no images."""
    FPDF = _import_fpdf()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    for i in range(1, 41):
        pdf.cell(0, 10, f"This is line {i} of a simple text-only PDF.", new_x="LMARGIN", new_y="NEXT")
    path = out / "simple_text.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 2. large_images  (~10 MB target, 5 JPEG images across pages)
# ---------------------------------------------------------------------------

def gen_large_images(out: Path) -> Path:
    """5 large JPEG images, multi-page."""
    FPDF = _import_fpdf()
    Image = _import_pillow()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    for idx in range(5):
        # Create a 2000x2000 synthetic JPEG (~varied colour per image)
        r = (50 * idx) % 256
        g = (100 + 40 * idx) % 256
        b = (200 - 30 * idx) % 256
        img = Image.new("RGB", (2000, 2000), (r, g, b))
        # Add some variation so JPEG doesn't compress to near-zero
        pixels = img.load()
        for y in range(0, 2000, 4):
            for x in range(0, 2000, 4):
                pixels[x, y] = ((r + x) % 256, (g + y) % 256, (b + x + y) % 256)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95)
        buf.seek(0)

        pdf.add_page()
        pdf.image(buf, x=10, y=10, w=190)

    path = out / "large_images.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 3. mixed_content  (text + images + rectangles)
# ---------------------------------------------------------------------------

def gen_mixed_content(out: Path) -> Path:
    """Text, an image, and drawn rectangles."""
    FPDF = _import_fpdf()
    Image = _import_pillow()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, "Mixed Content PDF", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=10)
    for i in range(1, 11):
        pdf.cell(0, 8, f"Paragraph line {i} with some descriptive text for testing.", new_x="LMARGIN", new_y="NEXT")

    # Small embedded image
    img = Image.new("RGB", (200, 200), (0, 128, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    buf.seek(0)
    pdf.image(buf, x=30, y=120, w=60)

    # Rectangles
    pdf.set_draw_color(200, 0, 0)
    pdf.set_line_width(1)
    pdf.rect(110, 120, 60, 40)
    pdf.set_fill_color(255, 255, 0)
    pdf.rect(110, 170, 60, 40, style="DF")

    path = out / "mixed_content.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 4. multiple_fonts
# ---------------------------------------------------------------------------

def gen_multiple_fonts(out: Path) -> Path:
    """Uses 4+ built-in fonts."""
    FPDF = _import_fpdf()
    pdf = FPDF()
    pdf.add_page()

    fonts = [
        ("Helvetica", "", 14),
        ("Courier", "", 12),
        ("Times", "", 12),
        ("Symbol", "", 14),
        ("Helvetica", "B", 16),
        ("Courier", "I", 12),
    ]
    y = 20
    for name, style, size in fonts:
        pdf.set_font(name, style=style, size=size)
        label = f"{name} {style or 'Regular'} {size}pt"
        pdf.set_xy(10, y)
        pdf.cell(0, 10, label, new_x="LMARGIN", new_y="NEXT")
        y += 14

    path = out / "multiple_fonts.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 5. already_optimized  (minimal compact PDF)
# ---------------------------------------------------------------------------

def gen_already_optimized(out: Path) -> Path:
    """Tiny, already-compact PDF."""
    FPDF = _import_fpdf()
    pdf = FPDF()
    pdf.compress = True
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 10, "Already optimized.", new_x="LMARGIN", new_y="NEXT")
    path = out / "already_optimized.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 6. uncompressed  (reportlab, no stream compression)
# ---------------------------------------------------------------------------

def gen_uncompressed(out: Path) -> Path:
    """Uncompressed streams via reportlab."""
    rl_canvas, A4 = _import_reportlab()
    path = out / "uncompressed.pdf"
    c = rl_canvas.Canvas(str(path), pagesize=A4, pageCompression=0)
    c.setFont("Helvetica", 12)
    for i in range(1, 31):
        c.drawString(72, 800 - i * 20, f"Uncompressed line {i}: " + "x" * 60)
    c.showPage()
    c.save()
    return path

# ---------------------------------------------------------------------------
# 7. with_forms  (reportlab AcroForm)
# ---------------------------------------------------------------------------

def gen_with_forms(out: Path) -> Path:
    """Interactive form fields using reportlab AcroForm."""
    rl_canvas, A4 = _import_reportlab()
    path = out / "with_forms.pdf"
    c = rl_canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(72, 750, "Form Fields Test")

    form = c.acroForm
    c.drawString(72, 700, "Name:")
    form.textfield(name="name", x=150, y=690, width=200, height=20,
                   borderColor=None, fillColor=None, textColor=None,
                   forceBorder=True)

    c.drawString(72, 660, "Email:")
    form.textfield(name="email", x=150, y=650, width=200, height=20,
                   borderColor=None, fillColor=None, textColor=None,
                   forceBorder=True)

    c.drawString(72, 620, "Accept:")
    form.checkbox(name="accept", x=150, y=612, size=16,
                  borderColor=None, fillColor=None,
                  buttonStyle="check", checked=False)

    c.drawString(72, 580, "Choice:")
    form.radio(name="radio_choice", value="opt1", x=150, y=580, size=16,
               borderColor=None, fillColor=None, selected=True)
    c.drawString(170, 580, "Option 1")
    form.radio(name="radio_choice", value="opt2", x=150, y=560, size=16,
               borderColor=None, fillColor=None, selected=False)
    c.drawString(170, 560, "Option 2")

    c.showPage()
    c.save()
    return path

# ---------------------------------------------------------------------------
# 8. with_bookmarks  (10+ bookmarks via fpdf2 set_section)
# ---------------------------------------------------------------------------

def gen_with_bookmarks(out: Path) -> Path:
    """PDF with 10+ bookmarks."""
    FPDF = _import_fpdf()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=12)

    for chapter in range(1, 12):
        pdf.add_page()
        pdf.start_section(f"Chapter {chapter}")
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 12, f"Chapter {chapter}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        for line in range(1, 16):
            pdf.cell(0, 8, f"Content line {line} of chapter {chapter}.", new_x="LMARGIN", new_y="NEXT")

    path = out / "with_bookmarks.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 9. with_links  (internal + external hyperlinks)
# ---------------------------------------------------------------------------

def gen_with_links(out: Path) -> Path:
    """Internal and external hyperlinks."""
    FPDF = _import_fpdf()
    pdf = FPDF()

    # Page 1
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Page 1 - Links Test", new_x="LMARGIN", new_y="NEXT")
    link_to_p2 = pdf.add_link()
    pdf.set_text_color(0, 0, 200)
    pdf.cell(0, 10, "Go to Page 2 (internal link)", new_x="LMARGIN", new_y="NEXT", link=link_to_p2)
    pdf.cell(0, 10, "Visit example.com (external link)", new_x="LMARGIN", new_y="NEXT",
             link="https://example.com")
    pdf.cell(0, 10, "Visit python.org", new_x="LMARGIN", new_y="NEXT",
             link="https://www.python.org")

    # Page 2
    pdf.add_page()
    pdf.set_link(link_to_p2)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Page 2 - Target of internal link", new_x="LMARGIN", new_y="NEXT")
    link_back = pdf.add_link()
    pdf.set_link(link_back, page=1)
    pdf.set_text_color(0, 0, 200)
    pdf.cell(0, 10, "Back to Page 1", new_x="LMARGIN", new_y="NEXT", link=link_back)

    path = out / "with_links.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 10. with_js  (JavaScript injected via pikepdf)
# ---------------------------------------------------------------------------

def gen_with_js(out: Path) -> Path:
    """PDF with JavaScript in /Names."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    # Base PDF
    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with JavaScript", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "with_js.pdf"
    with pikepdf.open(buf) as pdf:
        js_code = "app.alert('Hello from SafeTool PDF test!');"
        js_action = pikepdf.Dictionary(
            S=pikepdf.Name.JavaScript,
            JS=pikepdf.String(js_code),
        )
        js_name_tree = pikepdf.Array([
            pikepdf.String("AutoOpen"),
            pdf.make_indirect(js_action),
        ])
        js_dict = pikepdf.Dictionary(Names=js_name_tree)

        if "/Names" not in pdf.Root:
            pdf.Root.Names = pikepdf.Dictionary()
        pdf.Root.Names.JavaScript = pdf.make_indirect(js_dict)

        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 11. with_attachments  (2 embedded files via pikepdf)
# ---------------------------------------------------------------------------

def gen_with_attachments(out: Path) -> Path:
    """PDF with 2 embedded file attachments."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with Attachments", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "with_attachments.pdf"
    with pikepdf.open(buf) as pdf:
        files_array = pikepdf.Array()
        for fname, content in [("readme.txt", b"Hello from attachment 1."),
                               ("data.csv", b"col1,col2\n1,2\n3,4\n")]:
            stream = pikepdf.Stream(pdf, content)
            stream["/Type"] = pikepdf.Name.EmbeddedFile
            filespec = pikepdf.Dictionary(
                Type=pikepdf.Name.Filespec,
                F=pikepdf.String(fname),
                UF=pikepdf.String(fname),
                EF=pikepdf.Dictionary(F=pdf.make_indirect(stream)),
            )
            files_array.append(pikepdf.String(fname))
            files_array.append(pdf.make_indirect(filespec))

        ef_dict = pikepdf.Dictionary(Names=files_array)
        if "/Names" not in pdf.Root:
            pdf.Root.Names = pikepdf.Dictionary()
        pdf.Root.Names.EmbeddedFiles = pdf.make_indirect(ef_dict)

        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 12. with_metadata  (extensive XMP metadata via pikepdf)
# ---------------------------------------------------------------------------

def gen_with_metadata(out: Path) -> Path:
    """PDF with extensive XMP metadata."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with Metadata", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "with_metadata.pdf"
    with pikepdf.open(buf) as pdf:
        with pdf.open_metadata() as meta:
            meta["dc:title"] = "SafeTool PDF Test — Metadata"
            meta["dc:creator"] = ["Test Author", "Second Author"]
            meta["dc:description"] = "A PDF generated for regression testing of SafeTool PDF."
            meta["dc:subject"] = ["testing", "pdf", "optimization"]
            meta["pdf:Producer"] = "SafeTool PDF Test Suite"
            meta["xmp:CreatorTool"] = "generate_test_pdfs.py"
            meta["xmp:CreateDate"] = "2026-01-01T00:00:00Z"
            meta["xmp:ModifyDate"] = "2026-03-01T00:00:00Z"
        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 13. with_thumbnails  (page thumbnails via pikepdf)
# ---------------------------------------------------------------------------

def gen_with_thumbnails(out: Path) -> Path:
    """PDF with page thumbnail objects."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()
    Image = _import_pillow()

    base = FPDF()
    for p in range(1, 4):
        base.add_page()
        base.set_font("Helvetica", size=12)
        base.cell(0, 10, f"Page {p} with thumbnail", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "with_thumbnails.pdf"
    with pikepdf.open(buf) as pdf:
        for i, page in enumerate(pdf.pages):
            # Create a small RGB thumbnail image (76x100)
            thumb_img = Image.new("RGB", (76, 100), ((80 * i) % 256, 120, 200))
            raw = thumb_img.tobytes()
            thumb_stream = pikepdf.Stream(pdf, raw)
            thumb_stream["/Type"] = pikepdf.Name.XObject
            thumb_stream["/Subtype"] = pikepdf.Name.Image
            thumb_stream["/Width"] = 76
            thumb_stream["/Height"] = 100
            thumb_stream["/ColorSpace"] = pikepdf.Name.DeviceRGB
            thumb_stream["/BitsPerComponent"] = 8
            page["/Thumb"] = pdf.make_indirect(thumb_stream)
        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 14. with_layers  (2+ OCG layers via pikepdf)
# ---------------------------------------------------------------------------

def gen_with_layers(out: Path) -> Path:
    """PDF with Optional Content Groups (layers)."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with Layers (OCG)", new_x="LMARGIN", new_y="NEXT")
    base.cell(0, 10, "Some content on the base layer.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "with_layers.pdf"
    with pikepdf.open(buf) as pdf:
        # Create OCG dictionaries
        ocg1 = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.OCG,
            Name=pikepdf.String("Layer 1 - Annotations"),
        ))
        ocg2 = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.OCG,
            Name=pikepdf.String("Layer 2 - Watermark"),
        ))
        ocg3 = pdf.make_indirect(pikepdf.Dictionary(
            Type=pikepdf.Name.OCG,
            Name=pikepdf.String("Layer 3 - Background"),
        ))

        ocgs_array = pikepdf.Array([ocg1, ocg2, ocg3])
        default_config = pikepdf.Dictionary(
            BaseState=pikepdf.Name.ON,
            Order=ocgs_array,
            Name=pikepdf.String("Default"),
        )
        pdf.Root.OCProperties = pikepdf.Dictionary(
            OCGs=ocgs_array,
            D=default_config,
        )

        # Tag some content with an OCG on the first page
        page = pdf.pages[0]
        if "/Resources" not in page:
            page["/Resources"] = pikepdf.Dictionary()
        resources = page["/Resources"]
        if "/Properties" not in resources:
            resources["/Properties"] = pikepdf.Dictionary()
        resources["/Properties"]["/OC1"] = ocg1
        resources["/Properties"]["/OC2"] = ocg2

        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 15. encrypted_user  (user password via pikepdf)  — password: 1234
# ---------------------------------------------------------------------------

def gen_encrypted_user(out: Path) -> Path:
    """PDF encrypted with user password '1234'."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "Encrypted PDF (user password).", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "encrypted_user.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="1234",
            owner="",
            R=4,
        ))
    return path

# ---------------------------------------------------------------------------
# 16. encrypted_owner  (owner password via pikepdf)  — password: 1234
# ---------------------------------------------------------------------------

def gen_encrypted_owner(out: Path) -> Path:
    """PDF encrypted with owner password '1234'."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "Encrypted PDF (owner password).", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "encrypted_owner.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="",
            owner="1234",
            R=4,
        ))
    return path

# ---------------------------------------------------------------------------
# 19. encrypted_both  (user + owner password)  — password: 1234
# ---------------------------------------------------------------------------

def gen_encrypted_both(out: Path) -> Path:
    """PDF encrypted with both user and owner password '1234'."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "Encrypted PDF (both passwords).", new_x="LMARGIN", new_y="NEXT")
    base.cell(0, 10, "This file has user + owner password protection.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234 (both user and owner)
    path = out / "encrypted_both.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="1234",
            owner="1234",
            R=4,
        ))
    return path

# ---------------------------------------------------------------------------
# 20. encrypted_aes256  (AES-256 encryption)  — password: 1234
# ---------------------------------------------------------------------------

def gen_encrypted_aes256(out: Path) -> Path:
    """PDF encrypted with AES-256 (R=6), password '1234'."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "Encrypted PDF (AES-256).", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234, AES-256
    path = out / "encrypted_aes256.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="1234",
            owner="1234",
            R=6,
        ))
    return path

# ---------------------------------------------------------------------------
# 21. permissions_no_print  — owner-restricted, no printing allowed
#     password: 1234 (owner)
# ---------------------------------------------------------------------------

def gen_permissions_no_print(out: Path) -> Path:
    """PDF that denies printing (owner password '1234')."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with print permission denied.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "permissions_no_print.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="",
            owner="1234",
            R=4,
            allow=pikepdf.Permissions(
                print_lowres=False,
                print_highres=False,
                modify_other=True,
                extract=True,
                modify_annotation=True,
                modify_form=True,
                accessibility=True,
                modify_assembly=True,
            ),
        ))
    return path

# ---------------------------------------------------------------------------
# 22. permissions_no_extract  — owner-restricted, no text/image extraction
#     password: 1234 (owner)
# ---------------------------------------------------------------------------

def gen_permissions_no_extract(out: Path) -> Path:
    """PDF that denies extraction (owner password '1234')."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with extraction denied.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "permissions_no_extract.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="",
            owner="1234",
            R=4,
            allow=pikepdf.Permissions(
                print_lowres=True,
                print_highres=True,
                modify_other=True,
                extract=False,
                modify_annotation=True,
                modify_form=True,
                accessibility=True,
                modify_assembly=True,
            ),
        ))
    return path

# ---------------------------------------------------------------------------
# 23. permissions_no_modify  — owner-restricted, no modification
#     password: 1234 (owner)
# ---------------------------------------------------------------------------

def gen_permissions_no_modify(out: Path) -> Path:
    """PDF that denies modification (owner password '1234')."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with modification denied.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "permissions_no_modify.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="",
            owner="1234",
            R=4,
            allow=pikepdf.Permissions(
                print_lowres=True,
                print_highres=True,
                modify_other=False,
                extract=True,
                modify_annotation=False,
                modify_form=False,
                accessibility=True,
                modify_assembly=False,
            ),
        ))
    return path

# ---------------------------------------------------------------------------
# 24. permissions_readonly  — maximum restrictions (nothing allowed)
#     password: 1234 (owner)
# ---------------------------------------------------------------------------

def gen_permissions_readonly(out: Path) -> Path:
    """PDF with all permissions denied (owner password '1234')."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with all permissions denied.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "permissions_readonly.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="",
            owner="1234",
            R=4,
            allow=pikepdf.Permissions(
                print_lowres=False,
                print_highres=False,
                modify_other=False,
                extract=False,
                modify_annotation=False,
                modify_form=False,
                accessibility=False,
                modify_assembly=False,
            ),
        ))
    return path

# ---------------------------------------------------------------------------
# 25. permissions_print_only  — only printing allowed
#     password: 1234 (owner)
# ---------------------------------------------------------------------------

def gen_permissions_print_only(out: Path) -> Path:
    """PDF that allows only printing (owner password '1234')."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF that only allows printing.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234
    path = out / "permissions_print_only.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="",
            owner="1234",
            R=4,
            allow=pikepdf.Permissions(
                print_lowres=True,
                print_highres=True,
                modify_other=False,
                extract=False,
                modify_annotation=False,
                modify_form=False,
                accessibility=False,
                modify_assembly=False,
            ),
        ))
    return path

# ---------------------------------------------------------------------------
# 26. permissions_with_user_pw  — restricted + user password required
#     password: 1234 (user + owner)
# ---------------------------------------------------------------------------

def gen_permissions_with_user_pw(out: Path) -> Path:
    """PDF with restrictions AND user password '1234'."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with restrictions and user password.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    # Password: 1234 (both user and owner)
    path = out / "permissions_with_user_pw.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.save(str(path), encryption=pikepdf.Encryption(
            user="1234",
            owner="1234",
            R=4,
            allow=pikepdf.Permissions(
                print_lowres=False,
                print_highres=False,
                modify_other=False,
                extract=True,
                modify_annotation=False,
                modify_form=False,
                accessibility=True,
                modify_assembly=False,
            ),
        ))
    return path

# ---------------------------------------------------------------------------
# 27. metadata_author_only  — DocInfo with author only
# ---------------------------------------------------------------------------

def gen_metadata_author_only(out: Path) -> Path:
    """PDF with only Author in DocInfo."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with author metadata.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "metadata_author_only.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.docinfo["/Author"] = pikepdf.String("María García López")
        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 28. metadata_full_docinfo  — DocInfo with all standard fields
# ---------------------------------------------------------------------------

def gen_metadata_full_docinfo(out: Path) -> Path:
    """PDF with complete DocInfo metadata (no XMP)."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with full DocInfo metadata.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "metadata_full_docinfo.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.docinfo["/Author"] = pikepdf.String("Carlos Rodríguez Fernández")
        pdf.docinfo["/Title"] = pikepdf.String("Informe Confidencial Q4 2025")
        pdf.docinfo["/Subject"] = pikepdf.String("Resultados financieros internos")
        pdf.docinfo["/Keywords"] = pikepdf.String("confidencial, finanzas, Q4, 2025")
        pdf.docinfo["/Creator"] = pikepdf.String("Microsoft Word 2025")
        pdf.docinfo["/Producer"] = pikepdf.String("Adobe PDF Library 15.0")
        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 29. metadata_xmp_rich  — XMP with many fields + DocInfo
# ---------------------------------------------------------------------------

def gen_metadata_xmp_rich(out: Path) -> Path:
    """PDF with rich XMP metadata and DocInfo."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with rich XMP and DocInfo metadata.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "metadata_xmp_rich.pdf"
    with pikepdf.open(buf) as pdf:
        # DocInfo
        pdf.docinfo["/Author"] = pikepdf.String("Elena Martínez Ruiz")
        pdf.docinfo["/Title"] = pikepdf.String("Propuesta Técnica — Proyecto Aurora")
        pdf.docinfo["/Creator"] = pikepdf.String("LibreOffice 7.6")
        pdf.docinfo["/Producer"] = pikepdf.String("SafeTool PDF Test Generator")
        # XMP
        with pdf.open_metadata() as meta:
            meta["dc:title"] = "Propuesta Técnica — Proyecto Aurora"
            meta["dc:creator"] = ["Elena Martínez Ruiz", "Pedro Sánchez Gil"]
            meta["dc:description"] = "Propuesta técnica para el desarrollo del proyecto Aurora."
            meta["dc:subject"] = ["propuesta", "técnica", "aurora", "desarrollo"]
            meta["dc:publisher"] = ["Empresa Ficticia S.L."]
            meta["dc:rights"] = "© 2026 Empresa Ficticia S.L. Todos los derechos reservados."
            meta["pdf:Producer"] = "SafeTool PDF Test Generator"
            meta["xmp:CreatorTool"] = "generate_test_pdfs.py"
            meta["xmp:CreateDate"] = "2025-11-15T10:30:00Z"
            meta["xmp:ModifyDate"] = "2026-02-20T14:45:00Z"
        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 30. metadata_gps_location  — DocInfo with GPS-like custom metadata
# ---------------------------------------------------------------------------

def gen_metadata_gps_location(out: Path) -> Path:
    """PDF with custom metadata fields simulating GPS/location info."""
    FPDF = _import_fpdf()
    pikepdf = _import_pikepdf()

    base = FPDF()
    base.add_page()
    base.set_font("Helvetica", size=12)
    base.cell(0, 10, "PDF with location metadata.", new_x="LMARGIN", new_y="NEXT")
    buf = io.BytesIO()
    base.output(buf)
    buf.seek(0)

    path = out / "metadata_gps_location.pdf"
    with pikepdf.open(buf) as pdf:
        pdf.docinfo["/Author"] = pikepdf.String("Ana Belén Torres")
        pdf.docinfo["/Title"] = pikepdf.String("Informe de Campo — Parcela 47")
        pdf.docinfo["/Creator"] = pikepdf.String("iPad Pro — GoodNotes 6")
        pdf.docinfo["/Subject"] = pikepdf.String("GPS: 40.4168, -3.7038 — Madrid")
        pdf.docinfo["/Keywords"] = pikepdf.String(
            "campo, inspección, parcela47, lat:40.4168, lon:-3.7038"
        )
        pdf.save(str(path))
    return path

# ---------------------------------------------------------------------------
# 31. multipage_images  — 10 pages with images (medium-size, for merge tests)
# ---------------------------------------------------------------------------

def gen_multipage_images(out: Path) -> Path:
    """10-page PDF with a small image per page, suitable for merge tests."""
    FPDF = _import_fpdf()
    Image = _import_pillow()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    for idx in range(10):
        img = Image.new("RGB", (400, 300), ((30 * idx) % 256, 100, 180))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        buf.seek(0)
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, f"Page {idx + 1} of multipage images PDF", new_x="LMARGIN", new_y="NEXT")
        pdf.image(buf, x=10, y=30, w=100)

    path = out / "multipage_images.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 17. large_100pages  (100 pages of text)
# ---------------------------------------------------------------------------

def gen_large_100pages(out: Path) -> Path:
    """100 pages of text."""
    FPDF = _import_fpdf()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Helvetica", size=10)

    for page_num in range(1, 101):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Page {page_num} of 100", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 10)
        for line in range(1, 41):
            pdf.cell(0, 6, f"Line {line}: Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                     f"Sed do eiusmod tempor incididunt ut labore.", new_x="LMARGIN", new_y="NEXT")

    path = out / "large_100pages.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# 18. png_images  (PNG / Flate compressed)
# ---------------------------------------------------------------------------

def gen_png_images(out: Path) -> Path:
    """PNG images (Flate compressed) embedded in PDF."""
    FPDF = _import_fpdf()
    Image = _import_pillow()

    pdf = FPDF()
    for idx in range(3):
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, f"PNG image page {idx + 1}", new_x="LMARGIN", new_y="NEXT")

        img = Image.new("RGBA", (800, 600),
                        ((60 * idx) % 256, (120 + 40 * idx) % 256, 180, 255))
        # Add a semi-transparent rectangle via pixels for variety
        pixels = img.load()
        for y in range(100, 300):
            for x in range(100, 400):
                pixels[x, y] = (255, 255, 255, 128)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        pdf.image(buf, x=10, y=30, w=180)

    path = out / "png_images.pdf"
    pdf.output(str(path))
    return path

# ---------------------------------------------------------------------------
# Registry & generate_all
# ---------------------------------------------------------------------------

_GENERATORS: list[tuple[str, Callable[[Path], Path]]] = [
    ("simple_text", gen_simple_text),
    ("large_images", gen_large_images),
    ("mixed_content", gen_mixed_content),
    ("multiple_fonts", gen_multiple_fonts),
    ("already_optimized", gen_already_optimized),
    ("uncompressed", gen_uncompressed),
    ("with_forms", gen_with_forms),
    ("with_bookmarks", gen_with_bookmarks),
    ("with_links", gen_with_links),
    ("with_js", gen_with_js),
    ("with_attachments", gen_with_attachments),
    ("with_metadata", gen_with_metadata),
    ("with_thumbnails", gen_with_thumbnails),
    ("with_layers", gen_with_layers),
    ("encrypted_user", gen_encrypted_user),
    ("encrypted_owner", gen_encrypted_owner),
    ("large_100pages", gen_large_100pages),
    ("png_images", gen_png_images),
    # --- New: additional encrypted & permission PDFs (password: 1234) ---
    ("encrypted_both", gen_encrypted_both),
    ("encrypted_aes256", gen_encrypted_aes256),
    ("permissions_no_print", gen_permissions_no_print),
    ("permissions_no_extract", gen_permissions_no_extract),
    ("permissions_no_modify", gen_permissions_no_modify),
    ("permissions_readonly", gen_permissions_readonly),
    ("permissions_print_only", gen_permissions_print_only),
    ("permissions_with_user_pw", gen_permissions_with_user_pw),
    # --- New: metadata variants ---
    ("metadata_author_only", gen_metadata_author_only),
    ("metadata_full_docinfo", gen_metadata_full_docinfo),
    ("metadata_xmp_rich", gen_metadata_xmp_rich),
    ("metadata_gps_location", gen_metadata_gps_location),
    # --- New: extra merge/tool test asset ---
    ("multipage_images", gen_multipage_images),
]

def generate_all(output_dir: Path) -> dict[str, Path]:
    """Generate all test PDFs in *output_dir*.

    Returns a dict mapping short name → file path for every PDF that was
    successfully created.  PDFs whose generator raises an ImportError (missing
    library) are skipped with a warning.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, Path] = {}

    for name, func in _GENERATORS:
        try:
            path = func(output_dir)
            results[name] = path
            log.info("OK  %-20s  %s", name, path)
        except ImportError as exc:
            warnings.warn(f"Skipping '{name}': missing library — {exc}", stacklevel=2)
        except Exception as exc:
            warnings.warn(f"Skipping '{name}': {exc}", stacklevel=2)
            log.exception("Failed to generate %s", name)

    return results

# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    dest = Path(__file__).parent / "generated"
    print(f"Generating test PDFs in {dest} …")
    created = generate_all(dest)
    print(f"\nDone — {len(created)}/{len(_GENERATORS)} PDFs generated.")
    if len(created) < len(_GENERATORS):
        missing = {n for n, _ in _GENERATORS} - set(created)
        print(f"Skipped: {', '.join(sorted(missing))}")
