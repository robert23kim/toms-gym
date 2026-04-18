"""Symbol-level OCR dump — individual digit x-positions to reconstruct columns."""
import io
import sys
from PIL import Image, ImageOps
from google.cloud import vision


def main():
    path = sys.argv[1]
    with open(path, 'rb') as f:
        raw = f.read()

    img = Image.open(io.BytesIO(raw))
    img = ImageOps.exif_transpose(img)
    out = io.BytesIO()
    img.save(out, format='JPEG', quality=95)
    oriented = out.getvalue()

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=oriented)
    response = client.document_text_detection(image=image)

    page = response.full_text_annotation.pages[0]
    print(f"size: {page.width}x{page.height}")

    symbols = []
    for block in page.blocks:
        for paragraph in block.paragraphs:
            for word in paragraph.words:
                for sym in word.symbols:
                    v = sym.bounding_box.vertices
                    cx = sum(pt.x for pt in v) / 4
                    cy = sum(pt.y for pt in v) / 4
                    symbols.append({
                        'text': sym.text,
                        'x': cx,
                        'y': cy,
                        'conf': round(sym.confidence, 2)
                    })

    # Group by y-coordinate into rows
    symbols.sort(key=lambda s: s['y'])
    row_thresh = max(15, page.height * 0.02)
    rows = []
    cur = [symbols[0]]
    for s in symbols[1:]:
        if abs(s['y'] - cur[-1]['y']) < row_thresh:
            cur.append(s)
        else:
            rows.append(sorted(cur, key=lambda x: x['x']))
            cur = [s]
    rows.append(sorted(cur, key=lambda x: x['x']))

    print(f"rows={len(rows)} row_thresh={row_thresh:.0f}\n")
    for i, row in enumerate(rows):
        # Only print rows that have meaningful content
        texts = [(s['text'], int(s['x'])) for s in row]
        y = int(sum(s['y'] for s in row) / len(row))
        # Filter to show just text + x coords compactly
        compact = ' '.join(f"{t}@{x}" for t, x in texts)
        print(f"Row{i:2d} y={y:4d}: {compact[:500]}")


if __name__ == '__main__':
    main()
