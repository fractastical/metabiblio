import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import os
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

def pdf_to_image(pdf_path, image_path):
    pdf_document = fitz.open(pdf_path)
    page = pdf_document.load_page(0)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img.save(image_path)
    pdf_document.close()

def extract_pdf_title(pdf_path):
    pdf_document = fitz.open(pdf_path)
    page = pdf_document.load_page(0)
    text = page.get_text("text").split("\n")
    title = text[0].strip() if text else None
    pdf_document.close()
    return title

def clean_text(text):
    return ''.join(c for c in text if ord(c) < 128)

def epub_to_image(epub_path, image_path, font_path):
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

def extract_epub_title(epub_path):
    book = epub.read_epub(epub_path)
    titles = book.get_metadata('DC', 'title')
    title = titles[0][0] if titles else None
    return clean_text(title) if title else None

def create_toc(titles, font_path, toc_image_paths):
    # Create images for the TOC
    lines_per_page = 50
    pages = (len(titles) + lines_per_page - 1) // lines_per_page

    for page in range(pages):
        img = Image.new('RGB', (800, 1000), color='white')
        d = ImageDraw.Draw(img)
        font = ImageFont.truetype(font_path, size=15)
        y_text = 10
        start = page * lines_per_page
        end = start + lines_per_page
        for i, title in enumerate(titles[start:end], start=start + 1):
            d.text((10, y_text), f"{i}. {title}", fill='black', font=font)
            y_text += 20
        toc_image_path = f"toc_page_{page + 1}.png"
        img.save(toc_image_path)
        toc_image_paths.append(toc_image_path)

def compile_images_to_pdf(image_paths, output_pdf_path):
    first_image = Image.open(image_paths[0])
    first_image.save(output_pdf_path, save_all=True, append_images=[Image.open(img) for img in image_paths[1:]])

def main(folder_path, output_pdf_path, font_path):
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    image_paths = []
    titles = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            pdf_path = os.path.join(folder_path, filename)
            image_path = os.path.join(folder_path, f"{os.path.splitext(filename)[0]}.png")
            pdf_to_image(pdf_path, image_path)
            title = extract_pdf_title(pdf_path) or os.path.splitext(filename)[0]
            image_paths.append(image_path)
            titles.append(title)
        elif filename.endswith(".epub"):
            epub_path = os.path.join(folder_path, filename)
            image_path = os.path.join(folder_path, f"{os.path.splitext(filename)[0]}.png")
            epub_to_image(epub_path, image_path, font_path)
            title = extract_epub_title(epub_path) or os.path.splitext(filename)[0]
            image_paths.append(image_path)
            titles.append(title)
    
    toc_image_paths = []
    create_toc(titles, font_path, toc_image_paths)
    image_paths = toc_image_paths + image_paths
    
    compile_images_to_pdf(image_paths, output_pdf_path)
    
    for image_path in image_paths:
        if os.path.exists(image_path):
            os.remove(image_path)


if __name__ == "__main__":
    folder_path = "/Users/jd/Documents/books-research/uva/References"
    output_pdf_path = "/Users/jd/Documents/books-research/uva/compiled-references.pdf"
    font_path = "kenpixel.ttf"  # Path to your TrueType font file
    main(folder_path, output_pdf_path, font_path)
