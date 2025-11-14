import fitz  # PyMuPDF
import pdfplumber
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter

from .layout_detector import detect_layout

def extract(file_path: str) -> list:
    """
    Primary extraction function.
    Uses pdfminer.six for detailed layout analysis (text boxes, coords)
    as this provides the most robust data for column detection.
    """
    # You've chosen the "excellent" path. This is how you do it.
    return extract_layout_with_pdfminer(file_path)

def extract_layout_with_pdfminer(file_path: str) -> list:
    """
    Extracts layout elements (LTTextBox) with full coordinate info
    using pdfminer.six. This gives you the granular control you asked for.
    """
    blocks = []
    
    # --- This is the standard, complex setup for pdfminer.six ---
    rsrcmgr = PDFResourceManager()
    laparams = LAParams(
        line_margin=0.5, # Tweak these parameters for your specific resumes
        word_margin=0.1,
        boxes_flow=0.5
    )
    # Use PDFPageAggregator to get layout objects (LTTextBox, etc.)
    device = PDFPageAggregator(rsrcmgr, laparams=laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    with open(file_path, 'rb') as fp:
        for page in PDFPage.get_pages(fp):
            try:
                interpreter.process_page(page)
            except Exception as e:
                print(f"Warning: pdfminer.six failed to process a page: {e}")
                continue # Skip bad pages
                
            layout = device.get_result()
            
            page_num = layout.pageid
            
            for element in layout:
                # We only care about text boxes, as they represent paragraphs/blocks
                if isinstance(element, LTTextBox):
                    blocks.append({
                        "text": element.get_text().strip(),
                        "x0": element.x0,
                        "y0": element.y0,
                        "x1": element.x1,
                        "y1": element.y1,
                        "page": page_num,
                        "type": "textbox"
                        # pdfminer doesn't easily expose font info here
                        # PyMuPDF is better for that.
                    })
            
    layout_info = detect_layout(blocks)
    labels = layout_info.get("labels")
    if labels:
        # Map cluster index to column order using centers
        centers = layout_info.get("column_centers", [])
        ordering = sorted(enumerate(centers), key=lambda item: item[1])
        column_rank = {cluster_idx: rank for rank, (cluster_idx, _) in enumerate(ordering)}

        for block, label in zip(blocks, labels):
            block["column"] = column_rank.get(label, 0)

        # Sort blocks by column (left-to-right) then top-to-bottom (y1 higher means higher on page)
        blocks.sort(key=lambda b: (b.get("column", 0), -b.get("y1", 0), b.get("x0", 0)))

    return blocks

def extract_with_pymupdf(file_path: str) -> list:
    """
    Alternative/Supplementary: Extracts spans with PyMuPDF.
    Use this if you need fast font/color metadata, or if pdfminer fails.
    """
    blocks = []
    with fitz.open(file_path) as doc:
        for page_num, page in enumerate(doc, 1):
            page_blocks = page.get_text("dict")["blocks"]
            for b in page_blocks:
                if b['type'] == 0:  # text block
                    for l in b['lines']:
                        for s in l['spans']:
                            blocks.append({
                                "text": s['text'],
                                "x0": s['bbox'][0], "y0": s['bbox'][1],
                                "x1": s['bbox'][2], "y1": s['bbox'][3],
                                "font": s['font'], "size": s['size'],
                                "color": s['color'],
                                "page": page_num,
                                "type": "span"
                            })
    return blocks

def extract_tables_with_pdfplumber(file_path: str) -> list:
    """
    Supplementary: Use pdfplumber *specifically* for table extraction,
    as it's the best tool for that job.
    """
    tables = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            tables.extend(page.extract_tables())
    return tables