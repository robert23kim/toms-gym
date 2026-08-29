"""Google Vision document OCR helpers shared by the golf and bowling parsers. DB-free."""


def run_document_ocr(image_bytes):
    from google.cloud import vision

    client = vision.ImageAnnotatorClient()
    response = client.document_text_detection(image=vision.Image(content=image_bytes))
    if response.error.message:
        raise RuntimeError(f"Vision API error: {response.error.message}")
    return response.full_text_annotation


def extract_words_and_symbols(annotation):
    """Flatten a full_text_annotation into word and symbol dicts with centroids.

    Returns (words, symbols, page_w, page_h). words: {text,x,y,w,h,conf}; symbols: {text,x,y,conf}.
    """
    if not annotation or not annotation.pages:
        return [], [], 0, 0
    page = annotation.pages[0]
    words, symbols = [], []
    for block in page.blocks:
        for para in block.paragraphs:
            for word in para.words:
                v = word.bounding_box.vertices
                xs = [p.x for p in v]
                ys = [p.y for p in v]
                words.append({
                    'text': ''.join(s.text for s in word.symbols),
                    'x': sum(xs) / 4, 'y': sum(ys) / 4,
                    'w': max(xs) - min(xs), 'h': max(ys) - min(ys),
                    'conf': word.confidence,
                })
                for sym in word.symbols:
                    sv = sym.bounding_box.vertices
                    symbols.append({
                        'text': sym.text,
                        'x': sum(p.x for p in sv) / 4, 'y': sum(p.y for p in sv) / 4,
                        'h': max(p.y for p in sv) - min(p.y for p in sv),
                        'conf': sym.confidence,
                    })
    return words, symbols, (page.width or 0), (page.height or 0)
