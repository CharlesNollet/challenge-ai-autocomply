import fitz
import base64
import io
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

_FONT_CACHE = {}

def _load_font(size: int = 70) -> Optional[ImageFont.FreeTypeFont]:
    """Load and cache font at specified size.
    
    Args:
        size: Font size in points
    
    Returns:
        Font object or None if unavailable
    """
    if size not in _FONT_CACHE:
        font_paths = ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]
        for font_path in font_paths:
            try:
                _FONT_CACHE[size] = ImageFont.truetype(font_path, size)
                break
            except (IOError, OSError):
                continue
        else:
            _FONT_CACHE[size] = None
    
    return _FONT_CACHE[size]

def create_page_grid_b64(doc, page_indices):
    """Generate base64-encoded grid image from PDF pages.
    
    Creates a 2-column grid layout with page numbers overlaid.
    Optimized for speed and quality balance.
    
    Args:
        doc: PyMuPDF document object
        page_indices: List of page indices to include
    
    Returns:
        Base64-encoded JPEG string or None
    """
    grid_columns = 2
    thumbnail_dimensions = (600, 800)
    render_scale = 0.85
    
    page_thumbnails = []
    
    for page_idx in page_indices:
        try:
            pdf_page = doc.load_page(page_idx)
            render_matrix = fitz.Matrix(render_scale, render_scale)
            pixmap = pdf_page.get_pixmap(matrix=render_matrix)
            
            page_img = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples
            )
            
            page_img.thumbnail(thumbnail_dimensions, Image.Resampling.LANCZOS)
            
            canvas = Image.new('RGB', thumbnail_dimensions, (255, 255, 255))
            paste_x = (thumbnail_dimensions[0] - page_img.width) // 2
            paste_y = (thumbnail_dimensions[1] - page_img.height) // 2
            canvas.paste(page_img, (paste_x, paste_y))
            
            page_thumbnails.append(canvas)
            
        except Exception as e:
            blank = Image.new('RGB', thumbnail_dimensions, (255, 255, 255))
            page_thumbnails.append(blank)

    if not page_thumbnails:
        return None

    grid_rows = (len(page_thumbnails) + grid_columns - 1) // grid_columns
    grid_width = thumbnail_dimensions[0] * grid_columns
    grid_height = thumbnail_dimensions[1] * grid_rows
    
    composite = Image.new('RGB', (grid_width, grid_height), (255, 255, 255))
    drawer = ImageDraw.Draw(composite)
    label_font = _load_font(70)

    for idx, thumbnail in enumerate(page_thumbnails):
        col = idx % grid_columns
        row = idx // grid_columns
        pos_x = col * thumbnail_dimensions[0]
        pos_y = row * thumbnail_dimensions[1]
        
        composite.paste(thumbnail, (pos_x, pos_y))
        
        page_label = str(idx + 1)
        label_size = 85
        label_margin = 10
        label_x = pos_x + thumbnail_dimensions[0] - label_size - label_margin
        label_y = pos_y + thumbnail_dimensions[1] - label_size - label_margin
        
        drawer.rectangle(
            [label_x, label_y, label_x + label_size, label_y + label_size],
            fill=(255, 255, 255)
        )
        
        text_x = label_x + label_margin
        text_y = label_y + label_margin
        drawer.text((text_x, text_y), page_label, fill=(255, 0, 0), font=label_font)
        
        drawer.rectangle(
            [pos_x, pos_y, pos_x + thumbnail_dimensions[0], pos_y + thumbnail_dimensions[1]],
            outline=(0, 0, 0),
            width=2
        )

    output_buffer = io.BytesIO()
    composite.save(output_buffer, format="JPEG", quality=85, optimize=False)
    encoded_bytes = output_buffer.getvalue()
    
    return base64.b64encode(encoded_bytes).decode('utf-8')
