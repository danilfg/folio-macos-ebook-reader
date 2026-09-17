import tempfile
from pathlib import Path
import unittest
import zipfile

from folio.engine_v035 import epub_cover_bytes, is_rar_archive, natural_key


class V035Tests(unittest.TestCase):
    def test_epub_embedded_cover_is_found(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'cover.epub'
            cover = b'fake-cover-bytes'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr(
                    'META-INF/container.xml',
                    '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                    '<rootfiles><rootfile full-path="OEBPS/content.opf"/></rootfiles></container>',
                )
                z.writestr(
                    'OEBPS/content.opf',
                    '<package xmlns="http://www.idpf.org/2007/opf">'
                    '<manifest><item id="cover" href="images/cover.jpg" media-type="image/jpeg" '
                    'properties="cover-image"/></manifest></package>',
                )
                z.writestr('OEBPS/images/cover.jpg', cover)
            result = epub_cover_bytes(path)
            self.assertEqual(result, (cover, 'jpeg'))

    def test_rar_signature_is_detected_even_with_cbz_extension(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'mislabelled.cbz'
            path.write_bytes(b'Rar!\x1a\x07\x01\x00' + b'payload')
            self.assertTrue(is_rar_archive(path))

    def test_comic_page_names_use_natural_sort(self):
        names = [Path('10.jpg'), Path('2.jpg'), Path('1.jpg')]
        self.assertEqual(
            sorted(names, key=natural_key),
            [Path('1.jpg'), Path('2.jpg'), Path('10.jpg')],
        )


if __name__ == '__main__':
    unittest.main()
