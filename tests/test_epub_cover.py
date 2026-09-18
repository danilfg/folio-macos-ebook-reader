from pathlib import Path
import tempfile
import unittest
import zipfile

from lexumi.engine_v036 import epub_cover_bytes


class EpubCoverTests(unittest.TestCase):
    def test_epub2_metadata_image_beats_guide_xhtml(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'book.epub'
            container = '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
            opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0">
  <metadata><meta name="cover" content="cover"/></metadata>
  <manifest>
    <item id="cover" href="cover.jpeg" media-type="image/jpeg"/>
    <item id="titlepage" href="titlepage.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <guide><reference type="cover" href="titlepage.xhtml" title="Cover"/></guide>
</package>'''
            titlepage = '''<html xmlns="http://www.w3.org/1999/xhtml"><body>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<image xlink:href="cover.jpeg"/></svg></body></html>'''
            jpeg = b'\xff\xd8\xff' + b'cover-bytes'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('META-INF/container.xml', container)
                z.writestr('content.opf', opf)
                z.writestr('titlepage.xhtml', titlepage)
                z.writestr('cover.jpeg', jpeg)

            result = epub_cover_bytes(path)
            self.assertIsNotNone(result)
            data, kind = result
            self.assertEqual(data, jpeg)
            self.assertEqual(kind, 'jpeg')

    def test_missing_embedded_cover_returns_none_for_first_page_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'book.epub'
            container = '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''
            opf = '''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0"><metadata/><manifest/></package>'''
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('META-INF/container.xml', container)
                z.writestr('content.opf', opf)
            self.assertIsNone(epub_cover_bytes(path))


if __name__ == '__main__':
    unittest.main()
