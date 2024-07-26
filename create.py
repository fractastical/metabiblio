import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import os
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from collections import defaultdict
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import json
import warnings

def pdf_to_image(pdf_path, image_path):
    pdf_document = fitz.open(pdf_path)
    page = pdf_document.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.save(image_path)
    pdf_document.close()

def extract_pdf_title(pdf_path, filename):
    pdf_document = fitz.open(pdf_path)
    page = pdf_document.load_page(0)
    text = page.get_text("text").split("\n")
    title = text[0].strip() if text else None
    pdf_document.close()
    
    if not title or len(title.split()) < 3:
        title = filename.replace("_", " ").replace("-", " ")
    
    return title

def clean_text(text):
    return ''.join(c for c in text if ord(c) < 128)

def epub_to_image(epub_path, image_path, font_path):
    # Suppress specific warnings from ebooklib
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, message="In the future version we will turn default option ignore_ncx to True.")
        warnings.filterwarnings("ignore", category=FutureWarning, message="This search incorrectly ignores the root element, and will be fixed in a future version.")
        
        book = epub.read_epub(epub_path)
    
    text = ""
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_body_content(), 'html.parser')
        text = soup.get_text()
        if text.strip():
            break

    text = clean_text(text)

    # Create an image from the text of the first chapter
    img = Image.new('RGB', (800, 1000), color='white')
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size=15)
    d.text((10, 10), text[:1000], fill='black', font=font)  # Only take the first 1000 characters for the screenshot
    img.save(image_path)

def extract_epub_title(epub_path, filename):
    # Suppress specific warnings from ebooklib
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, message="In the future version we will turn default option ignore_ncx to True.")
        warnings.filterwarnings("ignore", category=FutureWarning, message="This search incorrectly ignores the root element, and will be fixed in a future version.")
        
        book = epub.read_epub(epub_path)
    
    titles = book.get_metadata('DC', 'title')
    title = titles[0][0] if titles else None
    
    if not title or len(title.split()) < 3:
        title = filename.replace("_", " ").replace("-", " ")
    else:
        title = clean_text(title)
    
    return title

def is_colorful(image_path, threshold=20):
    img = Image.open(image_path)
    img = img.convert('RGB')
    pixels = list(img.getdata())
    diff = sum([max(p) - min(p) for p in pixels]) / len(pixels)
    return diff > threshold

def wrap_text(text, font, max_width):
    lines = []
    words = text.split()
    while words:
        line = ''
        while words and font.getbbox(line + words[0])[2] <= max_width:
            line = line + (words.pop(0) + ' ')
        lines.append(line)
    return lines

def create_meta_toc(grouped_titles, font_path, toc_image_paths, meta_toc_data):
    img = Image.new('RGB', (800, 1000), color='white')
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_path, size=15)
    y_text = 10
    d.text((10, y_text), "Meta Table of Contents", fill='black', font=font)
    y_text += 30

    for category, titles in grouped_titles.items():
        d.text((10, y_text), f"{category}: {len(titles)} books", fill='black', font=font)
        y_text += 20
        meta_toc_data.append((category, len(titles)))

    toc_image_path = "meta_toc.png"
    img.save(toc_image_path)
    toc_image_paths.append(toc_image_path)

def create_toc(grouped_titles, font_path, toc_image_paths, toc_data, start_page):
    lines_per_page = 50
    page_num = 1
    current_page = start_page

    for category, titles in grouped_titles.items():
        pages = (len(titles) + lines_per_page - 1) // lines_per_page
        for page in range(pages):
            img = Image.new('RGB', (800, 1000), color='white')
            d = ImageDraw.Draw(img)
            font = ImageFont.truetype(font_path, size=15)
            y_text = 10
            if page == 0:
                d.text((10, y_text), category, fill='black', font=font)
                y_text += 30
            start = page * lines_per_page
            end = start + lines_per_page
            for i, title in enumerate(titles[start:end], start=start + 1):
                entry_text = f"{i}. {title} ......... {current_page + 1}"
                wrapped_lines = wrap_text(entry_text, font, 750)
                for line in wrapped_lines:
                    d.text((10, y_text), line, fill='black', font=font)
                    y_text += 20
                toc_data.append((title, current_page + 1))
                current_page += 1
            toc_image_path = f"toc_page_{page_num}.png"
            img.save(toc_image_path)
            toc_image_paths.append(toc_image_path)
            page_num += 1

def create_tiled_cover(image_paths, cover_image_path, tile_size=(100, 150), grid_size=(5, 5), font_path=None, max_images=25):
    cover_width = tile_size[0] * grid_size[0]
    cover_height = tile_size[1] * grid_size[1]
    cover_image = Image.new('RGB', (cover_width, cover_height), color='white')
    
    colorful_images = [img_path for img_path in image_paths if is_colorful(img_path)]
    
    for i, img_path in enumerate(colorful_images[:min(len(colorful_images), max_images)]):
        img = Image.open(img_path)
        img.thumbnail(tile_size, Image.LANCZOS)
        x = (i % grid_size[0]) * tile_size[0]
        y = (i // grid_size[0]) * tile_size[1]
        cover_image.paste(img, (x, y))
    
    if font_path:
        d = ImageDraw.Draw(cover_image)
        font = ImageFont.truetype(font_path, size=42)
        title_lines = ["Arcane", "Worlds", "Bibliography"]
        y_text = (cover_height - 3 * 40) // 2
        for line in title_lines:
            bbox = d.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            d.text(((cover_width - text_width) // 2, y_text), line, fill='purple', font=font)
            y_text += 40
    
    cover_image.save(cover_image_path)

def create_final_pdf(image_paths, output_pdf_path, toc_data, font_path):
    c = canvas.Canvas(output_pdf_path, pagesize=letter)
    width, height = letter
    font = "Helvetica"
    c.setFont(font, 12)

    # Add the cover image
    cover_image = ImageReader(image_paths[0])
    c.drawImage(cover_image, 0, 0, width=width, height=height)
    c.showPage()

    # Add the Meta TOC image
    meta_toc_image = ImageReader(image_paths[1])
    c.drawImage(meta_toc_image, 0, 0, width=width, height=height)
    c.showPage()

    # Add the TOC images
    toc_page_count = (len(toc_data) + 49) // 50  # Number of TOC pages
    for toc_image in image_paths[2:2 + toc_page_count]:
        toc_image = ImageReader(toc_image)
        c.drawImage(toc_image, 0, 0, width=width, height=height)
        c.showPage()

    # Add the content images with headers
    content_start_page = toc_page_count + 3  # Adjusted for cover, meta TOC, and TOC pages
    print(f"Content start page: {content_start_page}")
    print(f"Total images: {len(image_paths)}")
    print(f"Total TOC entries: {len(toc_data)}")
    
    for i, (title, page_num) in enumerate(toc_data, start=1):
        content_image_index = content_start_page + i - 1
        if content_image_index < len(image_paths):
            img_path = image_paths[content_image_index]
            img = ImageReader(img_path)
            c.drawImage(img, 0, 0, width=width, height=height)
            # c.drawString(30, height - 30, f"Page {content_start_page + i} - {title}")
            print(f"Adding {title} as page {content_start_page + i} with image {img_path}")
            c.showPage()
        else:
            print(f"Warning: Missing image for {title} on page {page_num}")

    c.save()

def main(folder_path, output_pdf_path, font_path, json_path):
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    all_cover_images_folder = os.path.join(folder_path, "all_cover_images")
    os.makedirs(all_cover_images_folder, exist_ok=True)
    
    image_paths = []
    grouped_titles = defaultdict(list)
    toc_data = []
    meta_toc_data = []

    # Load JSON data
    with open(json_path, 'r') as f:
        json_data = json.load(f)

    image_counter = 1
    last_folder = None
    for subdir, _, files in os.walk(folder_path):
        category = os.path.basename(subdir)
        if category != last_folder:
            print(f"Processing folder: {category}")
            last_folder = category
        
        for filename in files:
            if filename.endswith(".pdf"):
                pdf_path = os.path.join(subdir, filename)
                image_path = os.path.join(all_cover_images_folder, f"{image_counter}_{os.path.splitext(filename)[0].replace(' ', '_')}.png")
                pdf_to_image(pdf_path, image_path)
                title = extract_pdf_title(pdf_path, os.path.splitext(filename)[0])
                if category == "Alchemy":
                    for text in json_data["texts"]:
                        if text["title"] == title:
                            title += f' ({text.get("type", "Book")}, PH: {text.get("PH", "")}, BPH: {text.get("BPH", "")})'
                image_paths.append(image_path)
                grouped_titles[category].append(title)
                print(f"Processed PDF: {filename} as {image_path}")
                image_counter += 1
            elif filename.endswith(".epub"):
                epub_path = os.path.join(subdir, filename)
                image_path = os.path.join(all_cover_images_folder, f"{image_counter}_{os.path.splitext(filename)[0].replace(' ', '_')}.png")
                epub_to_image(epub_path, image_path, font_path)
                title = extract_epub_title(epub_path, os.path.splitext(filename)[0])
                if category == "Alchemy":
                    for text in json_data["texts"]:
                        if text["title"] == title:
                            title += f' ({text.get("type", "Book")}, PH: {text.get("PH", "")}, BPH: {text.get("BPH", "")})'
                image_paths.append(image_path)
                grouped_titles[category].append(title)
                print(f"Processed EPUB: {filename} as {image_path}")
                image_counter += 1

    print("\nAll files processed. Creating table of contents...")

    # Add JSON data to the "Alchemy" category
    for text in json_data["texts"]:
        title = text["title"]
        if "type" in text or "PH" in text or "BPH" in text:
            title += f' ({text.get("type", "Book")}, PH: {text.get("PH", "")}, BPH: {text.get("BPH", "")})'
        grouped_titles["Alchemy"].append(title)
        print(f"Added JSON title: {title} to Alchemy")

    toc_image_paths = []
    create_meta_toc(grouped_titles, font_path, toc_image_paths, meta_toc_data)
    create_toc(grouped_titles, font_path, toc_image_paths, toc_data, start_page=len(toc_image_paths) + 1)

    print("Table of contents created. Creating cover image...")

    cover_image_path = os.path.join(folder_path, "cover.png")
    create_tiled_cover(image_paths.copy(), cover_image_path, font_path=font_path)  # Use a copy of image_paths to prevent removal

    # Combine all images for final PDF
    final_image_paths = [cover_image_path] + toc_image_paths + image_paths

    print("Cover image created. Compiling final PDF...")

    create_final_pdf(final_image_paths, output_pdf_path, toc_data, font_path)
    
    print("Final PDF compiled. Cleaning up temporary files...")

    # Note: Do not delete images for verification

    print("Process completed successfully.")

if __name__ == "__main__":
    json_path = "/Users/jd/Documents/books-research/uva/References/alchemy.json"
    folder_path = "/Users/jd/Documents/books-research/uva/References"
    output_pdf_path = "/Users/jd/Documents/books-research/uva/arcane-worlds-biblio.pdf"
    font_path = "kenpixel.ttf"  # Path to your TrueType font file
    main(folder_path, output_pdf_path, font_path, json_path)
