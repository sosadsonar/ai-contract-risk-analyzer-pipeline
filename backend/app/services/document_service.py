import fitz


def extract_pdf_text(file_bytes: bytes) -> str:
    document = fitz.open(
        stream=file_bytes,
        filetype="pdf"
    )

    text = "\n".join(
        page.get_text()
        for page in document
    )

    document.close()

    return text