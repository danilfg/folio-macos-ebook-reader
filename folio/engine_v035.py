from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

import pymupdf as fitz

from .engine import Book as BaseBook, supported as base_supported

RAR_MAGIC = b'Rar!\x1a\x07'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.webp'}


def supported(path):
    p = Path(path)
    return base_supported(p) or p.suffix.lower() == '.cbr'


def is_rar_archive(path):
    try:
        with open(path, 'rb') as fh:
            return fh.read(len(RAR_MAGIC)) == RAR_MAGIC
    except OSError:
        return False


def natural_key(path):
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r'(\d+)', str(path))]


def archive_executable():
    candidates = []
    if sys.platform == 'darwin':
        candidates.append(Path('/usr/bin/tar'))
    found = shutil.which('bsdtar')
    if found:
        candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise RuntimeError('RAR/CBR support requires a libarchive bsdtar-compatible extractor.')


def extract_rar(path, target):
    cmd = [archive_executable(), '-xf', str(path), '-C', str(target)]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=600, check=False)
    except subprocess.TimeoutExpired:
        raise RuntimeError('The RAR/CBR archive took too long to extract and was stopped.') from None
    if result.returncode:
        message = result.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(message[:1800] or 'Failed to extract the RAR/CBR archive.')


def _local_name(tag):
    return tag.rsplit('}', 1)[-1]


def _image_preview(data, width=120, filetype=None):
    if not data:
        return None
    try:
        if filetype:
            doc = fitz.open(stream=data, filetype=filetype)
        else:
            doc = fitz.open(stream=data)
        try:
            page = doc[0]
            scale = max(0.05, min(width / max(1, page.rect.width), 2048 / max(1, page.rect.height)))
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
            return pix.tobytes('png')
        finally:
            doc.close()
    except Exception:
        try:
            pix = fitz.Pixmap(data)
            if pix.alpha or pix.n > 3:
                pix = fitz.Pixmap(fitz.csRGB, pix)
            return pix.tobytes('png')
        except Exception:
            return None


def epub_cover_bytes(path):
    try:
        with zipfile.ZipFile(path) as z:
            container = ET.fromstring(z.read('META-INF/container.xml'))
            rootfile = None
            for node in container.iter():
                if _local_name(node.tag) == 'rootfile':
                    rootfile = node.attrib.get('full-path')
                    if rootfile:
                        break
            if not rootfile:
                return None
            opf = ET.fromstring(z.read(rootfile))
            manifest = {}
            cover_id = None
            cover_href = None
            for node in opf.iter():
                name = _local_name(node.tag)
                if name == 'item':
                    item_id = node.attrib.get('id')
                    if item_id:
                        manifest[item_id] = dict(node.attrib)
                    if 'cover-image' in node.attrib.get('properties', '').split():
                        cover_href = node.attrib.get('href')
                elif name == 'meta' and node.attrib.get('name', '').casefold() == 'cover':
                    cover_id = node.attrib.get('content')
                elif name == 'reference' and node.attrib.get('type', '').casefold() == 'cover' and not cover_href:
                    cover_href = node.attrib.get('href')
            if not cover_href and cover_id and cover_id in manifest:
                cover_href = manifest[cover_id].get('href')
            if not cover_href:
                for item in manifest.values():
                    media = item.get('media-type', '')
                    item_id = item.get('id', '').casefold()
                    href = item.get('href', '')
                    if media.startswith('image/') and ('cover' in item_id or 'cover' in href.casefold()):
                        cover_href = href
                        break
            if not cover_href:
                return None
            cover_href = urllib.parse.unquote(cover_href.split('#', 1)[0])
            member = (Path(rootfile).parent / cover_href).as_posix()
            data = z.read(member)
            ext = Path(member).suffix.lower().lstrip('.') or None
            if ext in {'jpg', 'jpeg'}:
                ext = 'jpeg'
            return data, ext
    except Exception:
        return None


def _palm_records(data):
    if len(data) < 78:
        return []
    count = int.from_bytes(data[76:78], 'big')
    if count < 1 or 78 + count * 8 > len(data):
        return []
    offsets = []
    for index in range(count):
        offset = int.from_bytes(data[78 + index * 8:82 + index * 8], 'big')
        if not 0 <= offset < len(data):
            return []
        offsets.append(offset)
    offsets.append(len(data))
    records = []
    for index in range(count):
        start, end = offsets[index], offsets[index + 1]
        if end > start:
            records.append(data[start:end])
    return records


def _image_type(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if data.startswith(b'BM'):
        return 'bmp'
    return None


def mobi_cover_bytes(path):
    try:
        records = _palm_records(Path(path).read_bytes())
    except OSError:
        return None
    best = None
    best_score = -1.0
    image_order = 0
    for record in records[1:]:
        kind = _image_type(record)
        if not kind:
            continue
        image_order += 1
        try:
            pix = fitz.Pixmap(record)
            width, height = pix.width, pix.height
        except Exception:
            continue
        if width < 120 or height < 120:
            continue
        area = width * height
        aspect = width / max(1, height)
        portrait_bonus = 1.75 if 0.45 <= aspect <= 0.9 else 1.0
        early_bonus = 1.0 / (1.0 + max(0, image_order - 1) * 0.08)
        score = area * portrait_bonus * early_bonus
        if score > best_score:
            best_score = score
            best = (record, kind)
        if image_order >= 40:
            break
    return best


class Book(BaseBook):
    def __init__(self, path, password=''):
        self._comic_temp = None
        self.comic_images = []
        path_obj = Path(path).expanduser().resolve(strict=True)
        if is_rar_archive(path_obj):
            self.path = path_obj
            self.doc = None
            self.djvu = False
            self.title = self.path.stem
            self.toc = []
            self.can_print = self.can_copy = True
            self._comic_temp = tempfile.TemporaryDirectory(prefix='folio-cbr-')
            target = Path(self._comic_temp.name)
            try:
                extract_rar(self.path, target)
                self.comic_images = sorted(
                    [p for p in target.rglob('*') if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS],
                    key=natural_key,
                )
                if not self.comic_images:
                    raise ValueError('The RAR/CBR archive does not contain supported image files.')
                self.count = len(self.comic_images)
            except Exception:
                self._comic_temp.cleanup()
                self._comic_temp = None
                raise
            return
        super().__init__(path_obj, password)

    def close(self):
        try:
            super().close()
        finally:
            if self._comic_temp is not None:
                self._comic_temp.cleanup()
                self._comic_temp = None
                self.comic_images = []

    def page_sizes(self):
        if not self.comic_images:
            return super().page_sizes()
        sizes = []
        for path in self.comic_images:
            try:
                with fitz.open(path) as doc:
                    rect = doc[0].rect
                    sizes.append([float(rect.width), float(rect.height)])
            except Exception:
                sizes.append(sizes[-1] if sizes else [595.0, 842.0])
        return sizes

    def metadata(self):
        data = super().metadata()
        if self.comic_images:
            data['comic_rar'] = True
        return data

    def render(self, page, width=1400, query=''):
        if not self.comic_images:
            return super().render(page, width, query)
        if not 0 <= page < self.count:
            raise IndexError('That page does not exist.')
        width = max(160, min(4096, int(width)))
        with fitz.open(self.comic_images[page]) as doc:
            p = doc[0]
            scale = min(width / max(1, p.rect.width), 4096 / max(1, p.rect.height))
            pix = p.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False, colorspace=fitz.csRGB)
        return dict(image=base64.b64encode(pix.tobytes('png')).decode('ascii'), page=page, width=pix.width, height=pix.height, matches=[])

    def text(self, page):
        if self.comic_images:
            if not 0 <= page < self.count:
                raise IndexError('That page does not exist.')
            return ''
        return super().text(page)

    def cover(self, width=120):
        raw = None
        filetype = None
        if self.comic_images:
            path = self.comic_images[0]
            raw = path.read_bytes()
            filetype = path.suffix.lower().lstrip('.') or None
        elif self.path.suffix.lower() == '.epub':
            result = epub_cover_bytes(self.path)
            if result:
                raw, filetype = result
        elif self.path.suffix.lower() in {'.mobi', '.prc'}:
            result = mobi_cover_bytes(self.path)
            if result:
                raw, filetype = result
        if raw:
            preview = _image_preview(raw, width, filetype)
            if preview:
                return dict(image=base64.b64encode(preview).decode('ascii'), source='embedded-cover')
        fallback = self.render(0, width)
        return dict(image=fallback['image'], source='first-page')

    def export_pdf(self, target):
        if not self.comic_images:
            return super().export_pdf(target)
        target = Path(target).expanduser().resolve()
        if target == self.path or (target.exists() and os.path.samefile(target, self.path)):
            raise ValueError('Choose a different file name. Folio never overwrites the source book.')
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(suffix='.pdf', prefix='.folio-', dir=target.parent)
        os.close(fd)
        temp = Path(temp_name)
        temp.unlink(missing_ok=True)
        out = fitz.open()
        try:
            for image_path in self.comic_images:
                with fitz.open(image_path) as image_doc:
                    pdf_bytes = image_doc.convert_to_pdf()
                with fitz.open(stream=pdf_bytes, filetype='pdf') as page_pdf:
                    out.insert_pdf(page_pdf)
            out.save(temp, garbage=3, deflate=True)
            out.close()
            os.replace(temp, target)
        finally:
            if not out.is_closed:
                out.close()
            temp.unlink(missing_ok=True)
        return str(target)


def worker():
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    book = None
    for line in sys.stdin:
        req = {}
        try:
            req = json.loads(line)
            op = req['op']
            args = req.get('args', {})
            if op == 'open':
                candidate = Book(**args)
                if book:
                    book.close()
                book = candidate
                result = book.metadata()
            elif op == 'quit':
                break
            elif book is None:
                raise ValueError('Open a book first.')
            elif op == 'render':
                result = book.render(**args)
            elif op == 'cover':
                result = book.cover(**args)
            elif op == 'text':
                result = book.text(**args)
            elif op == 'find':
                result = book.find(**args)
            elif op == 'export':
                result = book.export_pdf(**args)
            else:
                raise ValueError('Unknown operation.')
            response = dict(id=req['id'], result=result)
        except Exception as exc:
            response = dict(id=req.get('id'), error=str(exc), kind=type(exc).__name__)
        print(json.dumps(response, ensure_ascii=True), flush=True)
    if book:
        book.close()
