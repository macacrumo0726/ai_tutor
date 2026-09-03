from pathlib import Path
def load_pdf_pages(path:Path):
    import fitz
    with fitz.open(path) as doc: return [{"page_num":i+1,"text":page.get_text()} for i,page in enumerate(doc)]

