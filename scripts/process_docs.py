import os
import logging
import sys

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.service.document_processor import DocumentProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('document_processing.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        # Get the absolute path to the docs directory
        current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs_dir = os.path.join(current_dir, 'docs')

        # Create docs directory if it doesn't exist
        if not os.path.exists(docs_dir):
            logger.info(f"Creating docs directory at {docs_dir}")
            os.makedirs(docs_dir)

        # Initialize the document processor
        logger.info("Initializing DocumentProcessor")
        processor = DocumentProcessor()

        # Process all documents in the docs directory
        logger.info(f"Starting document processing from: {docs_dir}")
        processor.process_directory(docs_dir)
        
        logger.info("Document processing completed successfully")

    except Exception as e:
        logger.error(f"An error occurred during document processing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()