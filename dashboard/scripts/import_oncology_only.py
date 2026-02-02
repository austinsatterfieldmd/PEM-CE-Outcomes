"""
Import ONLY the AllQuestionsOncology file with auto-tagging and LLM fallback.
This is a focused script that skips all other files.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dashboard.scripts.import_data import DataImporter
from dashboard.backend.services.database import DatabaseService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Find the oncology file
    raw_dir = project_root / "data" / "raw"
    oncology_files = list(raw_dir.glob("AllQuestionsOncology*.xlsx"))

    if not oncology_files:
        logger.error("No AllQuestionsOncology file found!")
        return

    file_path = oncology_files[0]
    logger.info(f"Found oncology file: {file_path.name}")

    # Initialize database and importer with auto-tagging and LLM fallback
    db = DatabaseService()
    importer = DataImporter(
        db=db,
        use_auto_tagging=True,
        use_llm_fallback=True
    )

    # Import ONLY the oncology file
    logger.info("Starting import with auto-tagging and LLM fallback...")
    logger.info("This will process 3,808 questions - please be patient...")

    count = importer.import_oncology_questions(file_path)

    logger.info(f"Import complete! Processed {count} questions.")

if __name__ == "__main__":
    main()
