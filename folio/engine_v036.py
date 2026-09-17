from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import urllib.parse
import xml.etree.ElementTree as ET
import zipfile

from .engine_v035 import Book as V035Book


def _local_name(tag):
    return tag.rsplit('}', 1)[-1]


def _normalise_member(base_file: str, href: str):
    href = urllib.parse.unquote((href or '').split('#', 1)[0]).strip()
    if not href:
        return None
    return (Path(base_file).parent / href).as_posix()


def _image_kind(member: str, media_type: str = ''):
    media = (media_type or '').casefold()
    if media == 'image/jpeg':
        return 'jpeg'
    if media.startswith('image/'):
        return media.split('/', 1)[1]
    ext = Path(member).suffix.lower().lstrip('.')
    if ext == 'jpg':
        return 'jpeg'
    return ext or None


def _read_image_member(z: zipfile.ZipFile, member: str, media_type: str = ''):
    if not member or member not in z.namelist():
        return None
    kind = _image_kind(member, media_type)
    if kind not in {'jpeg', 'png', 'gif', 'bmp', 'webp', 'tif', 'tiff'}:
        return None
    try:
        data = z.read(member)
    except KeyError:
        return None
    return (data, kind) if data else None


def _image_from_cover_document(z: zipfile.ZipFile, opf_path: str, href: str):
    member = _normalise_member(opf_path, href)
    if not member or member not in z.namelist():
        return None
    direct = _read_image_member(z, member)
    if direct:
        return direct
    try:
        root = ET.fromstring(z.read(member))
    except Exception:
        return None
    for node in root.iter():
        if _local_name(node.tag) not in {'img', 'image'}:
            continue
        image_href = (
            node.attrib.get('src')
            or node.attrib.get('href')
            or node.attrib.get('{http://www.w3.org/1999/xlink}href')
        )
        if not image_href:
            continue
        image_member = _normalise_member(member, image_href)
        result = _read_image_member(z, image_member)
        if result:
            return result
    return None


def epub_cover_bytes(path):
    """Return the real EPUB cover image, preferring image metadata over cover XHTML.

    EPUB 2 books commonly contain both `<meta name="cover" ...>` pointing at an
    image and a guide `type="cover"` pointing at an XHTML title page. The image
    must win; otherwise a valid cover can be mistaken for HTML and the thumbnail
    becomes blank.
    """
    try:
        with zipfile.ZipFile(path) as z:
            container = ET.fromstring(z.read('META-INF/container.xml'))
            opf_path = None
            for node in container.iter():
                if _local_name(node.tag) == 'rootfile':
                    opf_path = node.attrib.get('full-path')
                    if opf_path:
                        break
            if not opf_path:
                return None

            opf = ET.fromstring(z.read(opf_path))
            manifest = {}
            epub3_cover = None
            epub2_cover_id = None
            guide_cover = None

            for node in opf.iter():
                name = _local_name(node.tag)
                if name == 'item':
                    item_id = node.attrib.get('id')
                    if item_id:
                        manifest[item_id] = dict(node.attrib)
                    if 'cover-image' in node.attrib.get('properties', '').split():
                        epub3_cover = dict(node.attrib)
                elif name == 'meta' and node.attrib.get('name', '').casefold() == 'cover':
                    epub2_cover_id = node.attrib.get('content')
                elif name == 'reference' and node.attrib.get('type', '').casefold() == 'cover':
                    guide_cover = node.attrib.get('href')

            # EPUB 3: manifest item with properties="cover-image".
            if epub3_cover:
                member = _normalise_member(opf_path, epub3_cover.get('href'))
                result = _read_image_member(z, member, epub3_cover.get('media-type', ''))
                if result:
                    return result

            # EPUB 2: <meta name="cover" content="manifest-id">. This must take
            # priority over the guide cover page, which is often XHTML.
            if epub2_cover_id and epub2_cover_id in manifest:
                item = manifest[epub2_cover_id]
                member = _normalise_member(opf_path, item.get('href'))
                result = _read_image_member(z, member, item.get('media-type', ''))
                if result:
                    return result

            # Guide cover can be either an image or an XHTML/SVG wrapper around it.
            if guide_cover:
                result = _image_from_cover_document(z, opf_path, guide_cover)
                if result:
                    return result

            # Last embedded-image heuristic for malformed EPUBs.
            for item in manifest.values():
                media = item.get('media-type', '')
                item_id = item.get('id', '').casefold()
                href = item.get('href', '')
                if media.startswith('image/') and ('cover' in item_id or 'cover' in href.casefold()):
                    member = _normalise_member(opf_path, href)
                    result = _read_image_member(z, member, media)
                    if result:
                        return result
    except Exception:
        return None
    return None


class Book(V035Book):
    def cover(self, width=120):
        # Fix EPUB cover discovery; V035 retains MOBI/CBR handling and the final
        # first-page fallback for books with no usable embedded cover.
        if self.path.suffix.lower() == '.epub':
            from .engine_v035 import _image_preview

            result = epub_cover_bytes(self.path)
            if result:
                raw, filetype = result
                preview = _image_preview(raw, width, filetype)
                if preview:
                    return dict(
                        image=base64.b64encode(preview).decode('ascii'),
                        source='embedded-cover',
                    )
            fallback = self.render(0, width)
            return dict(image=fallback['image'], source='first-page')
        return super().cover(width)


def worker():
    import pymupdf as fitz

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
