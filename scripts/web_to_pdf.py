import os
import pdfkit
import re
from PyPDF2 import PdfReader, PdfMerger

# Configure wkhtmltopdf path
config = pdfkit.configuration(wkhtmltopdf='/usr/local/bin/wkhtmltopdf')

# Ensure wkhtmltopdf is installed and properly configured
PDFKIT_OPTIONS = {
    "quiet": "",
    "no-images": "",  # Remove images if needed
    "disable-javascript": "",  # Remove JS elements (popups, ads)
    "zoom": "1.2",
}

# Define categories (Change based on your needs)
CATEGORIES = {
    "ai": ["https://www.techtarget.com/searchenterpriseai/tip/9-top-AI-and-machine-learning-trends", "https://www.digitalocean.com/resources/articles/ai-trends","https://www.pragmaticcoders.com/blog/ai-predictions-top-ai-trends","https://appinventiv.com/blog/ai-trends/","https://www.ciklum.com/resources/blog/coding-with-ai","https://www.abmcollege.com/blog/top-5-ai-trends-in-software-development-in-2025","https://wpengine.com/blog/web-development-trends/"],
    "development": ["https://www.globalmediainsight.com/blog/web-development-trends/", "https://careerfoundry.com/en/blog/web-development/8-biggest-trends-in-web-development-trends/","https://explodingtopics.com/blog/app-trends"],
    "mobileApps": ["https://www.lambdatest.com/blog/mobile-app-development-trends/", "https://mobidev.biz/blog/mobile-app-development-trends-key-features"],
}

OUTPUT_FOLDER = "pdfs"
MERGED_PDF_FOLDER = "merged_pdfs"

# Ensure output directories exist
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(MERGED_PDF_FOLDER, exist_ok=True)

# 1️⃣ **Convert Webpages to PDFs**
def convert_webpages_to_pdfs(category, urls):
    pdf_files = []
    for i, url in enumerate(urls):
        filename = os.path.join(OUTPUT_FOLDER, f"{category}_{i+1}.pdf")
        pdfkit.from_url(url, filename, options=PDFKIT_OPTIONS, configuration=config)
        pdf_files.append(filename)
    return pdf_files

# 2️⃣ **Sanitize Extracted Text**
def extract_clean_text(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""

    for page in reader.pages:
        raw_text = page.extract_text()
        if raw_text:
            cleaned_text = re.sub(r"\s+", " ", raw_text).strip()  # Remove extra spaces
            text += cleaned_text + "\n\n"
    
    return text

def sanitize_pdfs(pdf_files):
    sanitized_texts = []
    for pdf in pdf_files:
        sanitized_text = extract_clean_text(pdf)
        sanitized_texts.append(sanitized_text)
        with open(pdf.replace(".pdf", "_clean.txt"), "w", encoding="utf-8") as f:
            f.write(sanitized_text)  # Save cleaned text
    return sanitized_texts

# 3️⃣ **Merge PDFs by Category**
def merge_pdfs_by_category(category, pdf_files):
    merged_pdf_path = os.path.join(MERGED_PDF_FOLDER, f"{category}_merged.pdf")
    merger = PdfMerger()

    for pdf in pdf_files:
        merger.append(pdf)
    
    merger.write(merged_pdf_path)
    merger.close()
    return merged_pdf_path

# 🚀 **Run the Full Process**
for category, urls in CATEGORIES.items():
    print(f"\nProcessing category: {category.upper()}")

    # Step 1: Convert webpages to PDFs
    pdf_files = convert_webpages_to_pdfs(category, urls)
    print(f"  ✅ Converted {len(pdf_files)} webpages to PDFs.")

    # Step 2: Sanitize extracted text
    sanitized_texts = sanitize_pdfs(pdf_files)
    print(f"  ✅ Extracted and cleaned text from PDFs.")

    # Step 3: Merge PDFs into a single categorized file
    merged_pdf = merge_pdfs_by_category(category, pdf_files)
    print(f"  ✅ Merged PDFs into: {merged_pdf}")

print("\n🎉 All webpages converted, sanitized, and merged successfully!")
