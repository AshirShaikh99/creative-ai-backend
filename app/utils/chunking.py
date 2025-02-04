import fitz
import pandas as pd
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class DocumentChunker:
    def process_document(self, file_path: str) -> List[Dict]:
        logger.info(f"Processing document: {file_path}")
        file_extension = file_path.split('.')[-1].lower()
        
        processors = {
            'pdf': self._process_pdf,
            'xlsx': self._process_excel,
            'xls': self._process_excel,
            'txt': self._process_text
        }
        
        processor = processors.get(file_extension)
        if processor:
            return processor(file_path)
        else:
            logger.warning(f"Unsupported file type: {file_extension}")
            return []

    def _process_pdf(self, file_path: str) -> List[Dict]:
        logger.info(f"Processing PDF file: {file_path}")
        chunks = []
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc, 1):
                blocks = page.get_text("blocks")
                for block in blocks:
                    if block[4].strip():
                        chunks.append({
                            "content": block[4],
                            "page": page_num,
                            "source": file_path,
                            "type": "pdf",
                            "coordinates": {
                                "x0": block[0],
                                "y0": block[1],
                                "x1": block[2],
                                "y1": block[3]
                            }
                        })
            logger.info(f"Processed {len(chunks)} chunks from PDF file: {file_path}")
        except Exception as e:
            logger.error(f"Error processing PDF file {file_path}: {e}")
        return chunks

    def _process_excel(self, file_path: str) -> List[Dict]:
        logger.info(f"Processing Excel file: {file_path}")
        chunks = []
        try:
            df = pd.read_excel(file_path, sheet_name=None)  # Read all sheets
            for sheet_name, sheet_df in df.items():
                for idx, row in sheet_df.iterrows():
                    content = " ".join(str(cell) for cell in row if pd.notna(cell))
                    if content.strip():
                        chunks.append({
                            "content": content,
                            "source": file_path,
                            "type": "excel",
                            "metadata": {
                                "sheet": sheet_name,
                                "row": idx
                            }
                        })
            logger.info(f"Processed {len(chunks)} chunks from Excel file: {file_path}")
        except Exception as e:
            logger.error(f"Error processing Excel file {file_path}: {e}")
        return chunks

    def _process_text(self, file_path: str) -> List[Dict]:
        logger.info(f"Processing text file: {file_path}")
        chunks = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
                for idx, paragraph in enumerate(paragraphs):
                    chunks.append({
                        "content": paragraph,
                        "source": file_path,
                        "type": "text",
                        "metadata": {
                            "paragraph": idx
                        }
                    })
            logger.info(f"Processed {len(chunks)} chunks from text file: {file_path}")
        except Exception as e:
            logger.error(f"Error processing text file {file_path}: {e}")
        return chunks