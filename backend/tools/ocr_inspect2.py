"""Run Vision API OCR WITHOUT the (buggy) auto-orient step, to see true rows."""
import io
import sys
from PIL import Image, ImageOps
from google.cloud import vision


def main():
    path = sys.argv[1]
    with open(path, 'rb') as f:
        raw = f.read()

    # Only apply EXIF orientation; do NOT force portrait
    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=95)
    oriented = out.getvalue()

    print(f"Using image size: {img.size}")

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=oriented)
    response = client.document_text_detection(image=image)

    if response.error.message:
        print(f"Vision error: {response.error.message}")
        sys.exit(1)

    ann = response.full_text_annotation
    page = ann.pages[0]

    words = []
    for block in page.blocks:
        for paragraph in block.paragraphs:
            for word in paragraph.words:
                text = ''.join(s.text for s in word.symbols)
                verts = word.bounding_box.vertices
                cx = sum(v.x for v in verts) / 4
                cy = sum(v.y for v in verts) / 4
                words.append({'text': text, 'x': cx, 'y': cy, 'conf': round(word.confidence, 2)})

    words.sort(key=lambda w: w['y'])

    page_h = page.height or 0
    row_thresh = max(10, min(50, page_h * 0.015)) if page_h else 20

    rows = []
    cur = [words[0]]
    for w in words[1:]:
        if abs(w['y'] - cur[-1]['y']) < row_thresh:
            cur.append(w)
        else:
            rows.append(sorted(cur, key=lambda x: x['x']))
            cur = [w]
    rows.append(sorted(cur, key=lambda x: x['x']))

    print(f"Image size: {page.width}x{page.height}")
    print(f"Row threshold: {row_thresh:.1f}")
    print(f"Total rows: {len(rows)}\n")

    for i, row in enumerate(rows):
        y = int(sum(w['y'] for w in row) / len(row))
        texts = [w['text'] for w in row]
        print(f"Row {i:2d} y={y:4d}: {texts}")


if __name__ == '__main__':
    main()
