"""Single-process document engine. The UI communicates with this module over JSON lines."""
from __future__ import annotations

import base64
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import pymupdf as fitz

EXTENSIONS = {
    '.pdf', '.djvu', '.djv', '.epub', '.fb2', '.mobi', '.prc', '.xps', '.oxps',
    '.cbz', '.txt', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.gif', '.svg'
}
MAX_TEXT = 32 * 1024 * 1024
MAX_FB2 = 128 * 1024 * 1024
DJVU_EXPORT_DPI = 160
DJVU_EXPORT_QUALITY = 80


def supported(path):
    p = Path(path)
    return p.suffix.lower() in EXTENSIONS or p.name.lower().endswith('.fb2.zip')


def executable(name):
    bundled = Path(getattr(sys, '_MEIPASS', '')) / 'djvu' / 'bin' / name if getattr(sys, '_MEIPASS', None) else None
    if bundled and bundled.is_file():
        return str(bundled)
    for root in (os.environ.get('LEXUMI_DJVU_BIN', ''), '/opt/homebrew/bin', '/usr/local/bin'):
        if root and (Path(root) / name).is_file():
            return str(Path(root) / name)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError('DjVuLibre was not found. Install DjVuLibre or use the official Lexumi DMG, which bundles the required DjVu tools.')


def run_djvu(name, *args, timeout=90):
    try:
        result = subprocess.run([executable(name), *map(str, args)], capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'{name} did not finish within {timeout} seconds. The file may be damaged.') from None
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[:1600] or f'{name} failed.')
    return result.stdout


def decode_text(data):
    if data.startswith((b'\xff\xfe', b'\xfe\xff')):
        return data.decode('utf-16')
    try:
        return data.decode('utf-8-sig')
    except UnicodeDecodeError:
        return data.decode('cp1251')


class Book:
    def __init__(self, path, password=''):
        self.path = Path(path).expanduser().resolve(strict=True)
        if not self.path.is_file() or not supported(self.path):
            raise ValueError('Unsupported format. Open a PDF, DjVu, EPUB, FB2, MOBI, TXT, XPS, CBZ, or image file.')
        self.doc = None
        self.djvu = self.path.suffix.lower() in {'.djvu', '.djv'}
        self.title = self.path.stem
        self.toc = []
        self.can_print = self.can_copy = True

        if self.djvu:
            self.count = int(run_djvu('djvused', self.path, '-e', 'n').strip())
        else:
            if self.path.name.lower().endswith('.fb2.zip'):
                with zipfile.ZipFile(self.path) as z:
                    files = [x for x in z.infolist() if x.filename.lower().endswith('.fb2') and not x.is_dir()]
                    if len(files) != 1:
                        raise ValueError('An FB2.ZIP file must contain exactly one FB2 book.')
                    if files[0].file_size > MAX_FB2:
                        raise ValueError('The uncompressed FB2 file is larger than 128 MB.')
                    self.doc = fitz.open(stream=z.read(files[0]), filetype='fb2')
            elif self.path.suffix.lower() == '.txt':
                if self.path.stat().st_size > MAX_TEXT:
                    raise ValueError('The TXT file is larger than 32 MB. Split it into smaller files first.')
                text = decode_text(self.path.read_bytes())
                source = '<html><head><meta charset="utf-8"></head><body><pre style="white-space:pre-wrap;font-family:serif">' + html.escape(text) + '</pre></body></html>'
                self.doc = fitz.open(stream=source.encode('utf-8'), filetype='html')
            else:
                self.doc = fitz.open(self.path)

            if self.doc.needs_pass and not self.doc.authenticate(password):
                self.doc.close(); self.doc = None
                raise PermissionError('This PDF requires a password, or the password is incorrect.')
            if self.doc.is_reflowable:
                self.doc.layout(width=595, height=842, fontsize=13)
            self.count = self.doc.page_count
            self.title = self.doc.metadata.get('title') or self.title
            self.toc = self.doc.get_toc()
            if self.doc.is_pdf:
                self.can_print = bool(self.doc.permissions & fitz.PDF_PERM_PRINT)
                self.can_copy = bool(self.doc.permissions & fitz.PDF_PERM_COPY)

        if self.count < 1:
            self.close()
            raise ValueError('The document has no pages.')

    def close(self):
        if self.doc is not None:
            self.doc.close(); self.doc = None

    def page_sizes(self):
        if not self.djvu:
            return [[float(self.doc[i].rect.width), float(self.doc[i].rect.height)] for i in range(self.count)]
        try:
            dump = run_djvu('djvudump', self.path, timeout=120)
            found = re.findall(rb'INFO\s+\[(\d+)x(\d+)', dump)
            sizes = [[float(w), float(h)] for w, h in found[:self.count]]
        except Exception:
            sizes = []
        if not sizes:
            sizes = [[595.0, 842.0]]
        while len(sizes) < self.count:
            sizes.append(list(sizes[-1]))
        return sizes[:self.count]

    def metadata(self):
        return dict(path=str(self.path), title=self.title, count=self.count, toc=self.toc, djvu=self.djvu, can_print=self.can_print, can_copy=self.can_copy, page_sizes=self.page_sizes())

    def render(self, page, width=1400, query=''):
        if not 0 <= page < self.count:
            raise IndexError('That page does not exist.')
        width = max(160, min(4096, int(width)))
        if self.djvu:
            raw = run_djvu('ddjvu', '-format=ppm', f'-page={page + 1}', f'-size={width}x{width * 3}', self.path)
            pix = fitz.Pixmap(raw)
        else:
            p = self.doc[page]
            scale = min(width / p.rect.width, 4096 / p.rect.height)
            pix = p.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
        result = dict(image=base64.b64encode(pix.tobytes('png')).decode('ascii'), page=page, width=pix.width, height=pix.height, matches=[])
        if query and not self.djvu:
            rect = self.doc[page].rect
            result['matches'] = [[r.x0 / rect.width, r.y0 / rect.height, r.width / rect.width, r.height / rect.height] for r in self.doc[page].search_for(query)]
        return result

    def text(self, page):
        if not self.can_copy:
            raise PermissionError('The PDF author disabled text copying.')
        if self.djvu:
            return run_djvu('djvutxt', f'--page={page + 1}', self.path).decode('utf-8', errors='replace')
        return self.doc[page].get_text()

    def find(self, query, start):
        if not query.strip():
            return None
        needle = query.casefold()
        for offset in range(self.count):
            page = (start + offset) % self.count
            if needle in self.text(page).casefold():
                return page
        return None

    def _export_djvu_pdf(self, temp):
        cmd = [executable('ddjvu'), '-format=pdf', f'-scale={DJVU_EXPORT_DPI}', f'-quality={DJVU_EXPORT_QUALITY}', str(self.path), str(temp)]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=3600, check=False)
        except subprocess.TimeoutExpired:
            raise RuntimeError('DjVu to PDF export exceeded one hour and was stopped.') from None
        if result.returncode:
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[:2000] or 'DjVuLibre PDF export failed.')

    def export_pdf(self, target):
        if not self.can_print:
            raise PermissionError('The PDF author disabled printing and export.')
        target = Path(target).expanduser().resolve()
        if target == self.path or (target.exists() and os.path.samefile(target, self.path)):
            raise ValueError('Choose a different file name. Lexumi never overwrites the source book.')
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(suffix='.pdf', prefix='.lexumi-', dir=target.parent)
        os.close(fd)
        temp = Path(temp_name); temp.unlink(missing_ok=True)
        try:
            if self.djvu:
                self._export_djvu_pdf(temp)
            elif self.doc.is_pdf:
                self.doc.save(temp, garbage=3, deflate=True)
            else:
                data = self.doc.convert_to_pdf()
                with fitz.open(stream=data, filetype='pdf') as out:
                    valid_toc = [t for t in self.toc if 1 <= t[2] <= out.page_count]
                    if valid_toc: out.set_toc(valid_toc)
                    out.save(temp, garbage=3, deflate=True)
            os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
        return str(target)


def worker():
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    book = None
    for line in sys.stdin:
        req = {}
        try:
            req = json.loads(line); op = req['op']; args = req.get('args', {})
            if op == 'open':
                candidate = Book(**args)
                if book: book.close()
                book = candidate; result = book.metadata()
            elif op == 'quit':
                break
            elif book is None:
                raise ValueError('Open a book first.')
            elif op == 'render': result = book.render(**args)
            elif op == 'text': result = book.text(**args)
            elif op == 'find': result = book.find(**args)
            elif op == 'export': result = book.export_pdf(**args)
            else: raise ValueError('Unknown operation.')
            response = dict(id=req['id'], result=result)
        except Exception as exc:
            response = dict(id=req.get('id'), error=str(exc), kind=type(exc).__name__)
        print(json.dumps(response, ensure_ascii=True), flush=True)
    if book: book.close()


if __name__ == '__main__':
    worker()
