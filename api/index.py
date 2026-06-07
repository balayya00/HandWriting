import os
import io
import base64
import json
import math
import random
import textwrap
import tempfile
import zipfile
from pathlib import Path
from typing import Optional

# Flask imports
from flask import (
    Flask, request, jsonify, render_template,
    send_file, Response
)
from flask_cors import CORS

# Image processing
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np

# PDF processing
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

# OCR
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ReportLab for PDF generation
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import mm, inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

# ─────────────────────────────────────────────
# Font Management
# ─────────────────────────────────────────────

FONT_URLS = {
    'style1': {
        'name': 'Caveat',
        'url': 'https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Regular.ttf',
        'bold_url': 'https://github.com/google/fonts/raw/main/ofl/caveat/Caveat-Bold.ttf'
    },
    'style2': {
        'name': 'Homemade Apple',
        'url': 'https://github.com/google/fonts/raw/main/ofl/homemadeapple/HomemadeApple-Regular.ttf',
        'bold_url': None
    },
    'style3': {
        'name': 'Indie Flower',
        'url': 'https://github.com/google/fonts/raw/main/ofl/indieflower/IndieFlower-Regular.ttf',
        'bold_url': None
    },
    'style4': {
        'name': 'Patrick Hand',
        'url': 'https://github.com/google/fonts/raw/main/ofl/patrickhand/PatrickHand-Regular.ttf',
        'bold_url': None
    },
    'style5': {
        'name': 'Shadows Into Light',
        'url': 'https://github.com/google/fonts/raw/main/ofl/shadowsintolight/ShadowsIntoLight.ttf',
        'bold_url': None
    }
}

FONT_CACHE = {}
FONT_DIR = Path(tempfile.gettempdir()) / 'handwriting_fonts'
FONT_DIR.mkdir(exist_ok=True)


def download_font(style: str) -> Optional[Path]:
    """Download font if not cached locally."""
    if style not in FONT_URLS:
        style = 'style1'

    font_path = FONT_DIR / f"{style}.ttf"

    if font_path.exists():
        return font_path

    try:
        import requests
        url = FONT_URLS[style]['url']
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            font_path.write_bytes(response.content)
            return font_path
    except Exception as e:
        print(f"Font download failed: {e}")

    return None


def get_font(style: str, size: int) -> ImageFont.FreeTypeFont:
    """Get font object, using cache."""
    cache_key = f"{style}_{size}"

    if cache_key in FONT_CACHE:
        return FONT_CACHE[cache_key]

    font_path = download_font(style)

    if font_path and font_path.exists():
        try:
            font = ImageFont.truetype(str(font_path), size)
            FONT_CACHE[cache_key] = font
            return font
        except Exception as e:
            print(f"Font load error: {e}")

    # Fallback to default font
    font = ImageFont.load_default()
    return font


# ─────────────────────────────────────────────
# Text Extraction
# ─────────────────────────────────────────────

def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pdfplumber."""
    text_parts = []

    try:
        if PDFPLUMBER_AVAILABLE:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text.strip())
        elif PYPDF2_AVAILABLE:
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text.strip())
        else:
            return "PDF extraction libraries not available."
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

    return '\n\n'.join(text_parts) if text_parts else "No text found in PDF."


def extract_text_from_image(file_bytes: bytes) -> str:
    """Extract text from image using Tesseract OCR."""
    if not TESSERACT_AVAILABLE:
        return "OCR library (pytesseract) not available."

    try:
        image = Image.open(io.BytesIO(file_bytes))

        # Preprocess for better OCR
        image = image.convert('RGB')
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Convert to grayscale for OCR
        gray = image.convert('L')

        config = '--oem 3 --psm 6'
        text = pytesseract.image_to_string(gray, config=config)
        return text.strip() if text.strip() else "No text detected in image."

    except Exception as e:
        return f"OCR Error: {str(e)}"


# ─────────────────────────────────────────────
# Paper Generators
# ─────────────────────────────────────────────

def create_plain_paper(width: int, height: int) -> Image.Image:
    """Create plain white paper."""
    paper = Image.new('RGB', (width, height), color=(252, 250, 245))

    # Subtle texture
    draw = ImageDraw.Draw(paper)
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 8, (height, width, 3), dtype=np.uint8)

    paper_array = np.array(paper)
    paper_array = np.clip(paper_array.astype(int) - noise, 0, 255).astype(np.uint8)

    return Image.fromarray(paper_array)


def create_ruled_paper(width: int, height: int, line_spacing: int) -> Image.Image:
    """Create ruled notebook paper."""
    paper = Image.new('RGB', (width, height), color=(250, 248, 240))
    draw = ImageDraw.Draw(paper)

    # Margin line (red)
    margin_x = 80
    draw.line([(margin_x, 0), (margin_x, height)], fill=(220, 100, 100, 180), width=2)

    # Horizontal lines (blue)
    start_y = line_spacing + 30
    y = start_y
    while y < height - 20:
        draw.line([(0, y), (width, y)], fill=(180, 200, 230), width=1)
        y += line_spacing

    # Paper texture
    rng = np.random.default_rng(42)
    paper_array = np.array(paper)
    noise = rng.integers(0, 5, paper_array.shape, dtype=np.uint8)
    paper_array = np.clip(paper_array.astype(int) - noise, 0, 255).astype(np.uint8)

    return Image.fromarray(paper_array)


def create_exam_paper(width: int, height: int, line_spacing: int) -> Image.Image:
    """Create exam sheet paper."""
    paper = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(paper)

    # Header box
    draw.rectangle([(20, 20), (width - 20, 100)], outline=(0, 0, 0), width=2)

    # Name line
    draw.line([(40, 60), (300, 60)], fill=(0, 0, 0), width=1)
    draw.line([(350, 60), (600, 60)], fill=(0, 0, 0), width=1)

    # Roll No box
    for i in range(8):
        x = 40 + i * 30
        draw.rectangle([(x, 70), (x + 28, 95)], outline=(0, 0, 0), width=1)

    # Horizontal lines
    start_y = 120
    y = start_y
    while y < height - 20:
        draw.line([(20, y), (width - 20, y)], fill=(150, 150, 150), width=1)
        y += line_spacing

    # Left margin
    draw.line([(80, 120), (80, height - 20)], fill=(200, 150, 150), width=1)

    # Page number at bottom
    try:
        small_font = ImageFont.load_default()
        draw.text((width // 2 - 20, height - 30), "Page 1", fill=(100, 100, 100), font=small_font)
    except Exception:
        pass

    return paper


# ─────────────────────────────────────────────
# Handwriting Engine
# ─────────────────────────────────────────────

class HandwritingConverter:
    """Main handwriting conversion engine."""

    # A4 at 150 DPI
    PAGE_WIDTH = 1240
    PAGE_HEIGHT = 1754

    INK_COLORS = {
        'blue': (30, 60, 180),
        'black': (20, 20, 20),
        'dark_blue': (10, 30, 120),
        'pencil': (80, 80, 80),
        'red': (180, 20, 20),
    }

    def __init__(
        self,
        style: str = 'style1',
        font_size: int = 32,
        line_spacing: int = 60,
        ink_color: str = 'blue',
        paper_style: str = 'ruled',
        margin: int = 80,
        left_margin: int = 100,
    ):
        self.style = style
        self.font_size = font_size
        self.line_spacing = line_spacing
        self.ink_color_name = ink_color
        self.ink_color = self.INK_COLORS.get(ink_color, (30, 60, 180))
        self.paper_style = paper_style
        self.margin = margin
        self.left_margin = left_margin if paper_style == 'ruled' else margin
        self.right_margin = margin

        # Text area dimensions
        self.text_width = self.PAGE_WIDTH - self.left_margin - self.right_margin
        self.start_y = 130 if paper_style == 'exam' else 50

        # Load font
        self.font = get_font(style, font_size)

    def _get_text_size(self, text: str) -> tuple:
        """Get text width and height."""
        try:
            bbox = self.font.getbbox(text)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            return len(text) * (self.font_size // 2), self.font_size

    def _word_wrap(self, text: str) -> list:
        """Wrap text to fit within page width."""
        lines = []
        paragraphs = text.split('\n')

        for para in paragraphs:
            if not para.strip():
                lines.append('')
                continue

            words = para.split()
            if not words:
                lines.append('')
                continue

            current_line = ''
            for word in words:
                test_line = f"{current_line} {word}".strip()
                w, _ = self._get_text_size(test_line)
                if w <= self.text_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)

        return lines

    def _add_handwriting_variation(self, text: str, x: int, y: int, draw: ImageDraw.Draw):
        """Draw text with subtle handwriting variations."""
        color = self.ink_color

        # Slight angle variation per line
        offset_y = random.randint(-2, 2)

        # Character-by-character with micro variations
        try:
            # Use slightly varied color for realism
            r, g, b = color
            r_var = max(0, min(255, r + random.randint(-15, 10)))
            g_var = max(0, min(255, g + random.randint(-10, 10)))
            b_var = max(0, min(255, b + random.randint(-10, 15)))
            draw_color = (r_var, g_var, b_var)

            draw.text((x, y + offset_y), text, font=self.font, fill=draw_color)
        except Exception:
            draw.text((x, y), text, font=self.font, fill=color)

    def _create_paper(self) -> Image.Image:
        """Create base paper."""
        if self.paper_style == 'ruled':
            return create_ruled_paper(self.PAGE_WIDTH, self.PAGE_HEIGHT, self.line_spacing)
        elif self.paper_style == 'exam':
            return create_exam_paper(self.PAGE_WIDTH, self.PAGE_HEIGHT, self.line_spacing)
        else:
            return create_plain_paper(self.PAGE_WIDTH, self.PAGE_HEIGHT)

    def _render_page(self, lines: list) -> Image.Image:
        """Render a single page of handwritten text."""
        paper = self._create_paper()
        draw = ImageDraw.Draw(paper)

        current_y = self.start_y + self.line_spacing

        for line in lines:
            if line == '':
                # Paragraph spacing
                current_y += self.line_spacing // 2
            else:
                self._add_handwriting_variation(
                    line,
                    self.left_margin + random.randint(0, 3),
                    current_y,
                    draw
                )
            current_y += self.line_spacing

        # Add subtle ink bleed effect
        paper = paper.filter(ImageFilter.SMOOTH_MORE)
        paper = self._add_paper_wear(paper)

        return paper

    def _add_paper_wear(self, image: Image.Image) -> Image.Image:
        """Add subtle realistic paper effects."""
        try:
            # Very slight blur for ink spread effect
            # Only on dark pixels (the text)
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(0.95)
        except Exception:
            pass
        return image

    def convert(self, text: str) -> list:
        """Convert text to list of handwritten page images."""
        # Wrap text
        all_lines = self._word_wrap(text)

        # Calculate lines per page
        usable_height = self.PAGE_HEIGHT - self.start_y - self.margin - self.line_spacing
        lines_per_page = max(1, int(usable_height / self.line_spacing))

        # Split into pages
        pages = []
        for i in range(0, max(1, len(all_lines)), lines_per_page):
            page_lines = all_lines[i:i + lines_per_page]
            page_image = self._render_page(page_lines)
            pages.append(page_image)

        return pages if pages else [self._render_page([])]


# ─────────────────────────────────────────────
# PDF Builder
# ─────────────────────────────────────────────

def images_to_pdf(images: list) -> bytes:
    """Convert list of PIL Images to PDF bytes."""
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=A4)

    a4_width, a4_height = A4  # points

    for img in images:
        # Convert PIL image to bytes
        img_buffer = io.BytesIO()
        img_rgb = img.convert('RGB')
        img_rgb.save(img_buffer, format='JPEG', quality=92)
        img_buffer.seek(0)

        # Draw image on PDF page
        pdf_canvas.setPageSize(A4)
        pdf_canvas.drawImage(
            ImageReader(img_buffer),
            0, 0,
            width=a4_width,
            height=a4_height,
            preserveAspectRatio=False
        )
        pdf_canvas.showPage()

    pdf_canvas.save()
    buffer.seek(0)
    return buffer.read()


def image_to_jpg_bytes(image: Image.Image, quality: int = 92) -> bytes:
    """Convert PIL Image to JPEG bytes."""
    buffer = io.BytesIO()
    image.convert('RGB').save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)
    return buffer.read()


# ─────────────────────────────────────────────
# Flask Routes
# ─────────────────────────────────────────────

@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/extract', methods=['POST'])
def extract_text():
    """Extract text from uploaded file."""
    try:
        if 'file' in request.files:
            file = request.files['file']
            filename = file.filename.lower()
            file_bytes = file.read()

            if not file_bytes:
                return jsonify({'error': 'Empty file uploaded'}), 400

            if filename.endswith('.pdf'):
                text = extract_text_from_pdf(file_bytes)
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')):
                text = extract_text_from_image(file_bytes)
            else:
                return jsonify({'error': 'Unsupported file format. Use PDF, JPG, or PNG.'}), 400

            return jsonify({'text': text, 'success': True})

        elif request.is_json:
            data = request.get_json()
            text = data.get('text', '')
            return jsonify({'text': text, 'success': True})

        else:
            return jsonify({'error': 'No file or text provided'}), 400

    except Exception as e:
        return jsonify({'error': f'Extraction failed: {str(e)}'}), 500


@app.route('/api/convert', methods=['POST'])
def convert_to_handwriting():
    """Convert text to handwritten images."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'No text to convert'}), 400

        # Settings
        settings = {
            'style': data.get('style', 'style1'),
            'font_size': int(data.get('fontSize', 32)),
            'line_spacing': int(data.get('lineSpacing', 60)),
            'ink_color': data.get('inkColor', 'blue'),
            'paper_style': data.get('paperStyle', 'ruled'),
            'margin': int(data.get('margin', 80)),
        }

        # Validate
        settings['font_size'] = max(16, min(72, settings['font_size']))
        settings['line_spacing'] = max(40, min(120, settings['line_spacing']))
        settings['margin'] = max(20, min(200, settings['margin']))

        # Convert
        converter = HandwritingConverter(**settings)
        pages = converter.convert(text)

        # Encode pages as base64
        preview_pages = []
        for i, page in enumerate(pages):
            # Resize for preview (reduce bandwidth)
            preview = page.copy()
            preview.thumbnail((620, 877), Image.LANCZOS)
            jpg_bytes = image_to_jpg_bytes(preview, quality=80)
            b64 = base64.b64encode(jpg_bytes).decode('utf-8')
            preview_pages.append({
                'page': i + 1,
                'data': f"data:image/jpeg;base64,{b64}"
            })

        return jsonify({
            'success': True,
            'pages': preview_pages,
            'total_pages': len(pages),
            'message': f'Generated {len(pages)} page(s) successfully'
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500


@app.route('/api/download', methods=['POST'])
def download_handwriting():
    """Generate and download handwritten document."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'No text to convert'}), 400

        output_format = data.get('format', 'pdf').lower()

        settings = {
            'style': data.get('style', 'style1'),
            'font_size': int(data.get('fontSize', 32)),
            'line_spacing': int(data.get('lineSpacing', 60)),
            'ink_color': data.get('inkColor', 'blue'),
            'paper_style': data.get('paperStyle', 'ruled'),
            'margin': int(data.get('margin', 80)),
        }

        # Validate
        settings['font_size'] = max(16, min(72, settings['font_size']))
        settings['line_spacing'] = max(40, min(120, settings['line_spacing']))
        settings['margin'] = max(20, min(200, settings['margin']))

        # Convert
        converter = HandwritingConverter(**settings)
        pages = converter.convert(text)

        if output_format == 'pdf':
            pdf_bytes = images_to_pdf(pages)
            return Response(
                pdf_bytes,
                mimetype='application/pdf',
                headers={
                    'Content-Disposition': 'attachment; filename="handwritten_notes.pdf"',
                    'Content-Length': str(len(pdf_bytes))
                }
            )

        elif output_format == 'jpg':
            if len(pages) == 1:
                jpg_bytes = image_to_jpg_bytes(pages[0], quality=95)
                return Response(
                    jpg_bytes,
                    mimetype='image/jpeg',
                    headers={
                        'Content-Disposition': 'attachment; filename="handwritten_notes.jpg"',
                        'Content-Length': str(len(jpg_bytes))
                    }
                )
            else:
                # Multiple pages: return ZIP
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for i, page in enumerate(pages):
                        jpg_bytes = image_to_jpg_bytes(page, quality=95)
                        zf.writestr(f'page_{i+1:03d}.jpg', jpg_bytes)

                zip_buffer.seek(0)
                zip_data = zip_buffer.read()

                return Response(
                    zip_data,
                    mimetype='application/zip',
                    headers={
                        'Content-Disposition': 'attachment; filename="handwritten_notes.zip"',
                        'Content-Length': str(len(zip_data))
                    }
                )
        else:
            return jsonify({'error': 'Invalid format. Use pdf or jpg'}), 400

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': f'Download failed: {str(e)}'}), 500


@app.route('/api/fonts', methods=['GET'])
def list_fonts():
    """List available font styles."""
    fonts = [
        {'id': 'style1', 'name': 'Caveat', 'description': 'Natural casual handwriting'},
        {'id': 'style2', 'name': 'Homemade Apple', 'description': 'Flowing cursive style'},
        {'id': 'style3', 'name': 'Indie Flower', 'description': 'Clean print handwriting'},
        {'id': 'style4', 'name': 'Patrick Hand', 'description': 'Comic book style writing'},
        {'id': 'style5', 'name': 'Shadows Into Light', 'description': 'Artistic handwriting'},
    ]
    return jsonify({'fonts': fonts})


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'pdfplumber': PDFPLUMBER_AVAILABLE,
        'tesseract': TESSERACT_AVAILABLE,
        'pypdf2': PYPDF2_AVAILABLE
    })


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)
