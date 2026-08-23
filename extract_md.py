import pymupdf4llm
from pathlib import Path
import os


def extract_text_from_pdf(pdf_path, output_dir):
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"The PDF file {pdf_path} does not exist.")

    md_text = pymupdf4llm.to_markdown(
        pdf_path,
        header=False,
        footer=False
    )

    Path(output_dir).write_bytes(md_text.encode("utf-8"))
