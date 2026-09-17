import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from folio.engine import Book, executable
from folio.storage import Library
from make_samples import make as make_samples


class ReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT/'samples'/'Welcome.pdf').exists():
            make_samples()

    def test_text_formats_preserve_cyrillic_and_export(self):
        for name in ['Welcome.pdf','Welcome.epub','Welcome.fb2','Welcome.fb2.zip','Welcome.txt']:
            with self.subTest(name=name),tempfile.TemporaryDirectory() as folder:
                book = Book(ROOT/'samples'/name)
                self.assertGreater(book.count,0)
                text = '\n'.join(book.text(i) for i in range(book.count))
                self.assertIn('закладка',text.lower())
                self.assertIsNotNone(book.find('закладка',0))
                result = book.render(0,500)
                self.assertTrue(base64.b64decode(result['image']).startswith(b'\x89PNG'))
                output = Path(folder)/'export.pdf'
                book.export_pdf(output)
                with fitz.open(output) as pdf:
                    self.assertEqual(pdf.page_count,book.count)
                book.close()

    def test_page_search_wrap_and_highlights(self):
        book = Book(ROOT/'samples/Welcome.pdf')
        self.assertEqual(book.find('Контрольная фраза',0),1)
        self.assertEqual(book.find('Контрольная фраза',2),1)
        self.assertIsNone(book.find('NOT_FOUND_928731',0))
        self.assertTrue(book.render(1,500,'закладка')['matches'])
        with self.assertRaises(IndexError):
            book.render(99)
        with self.assertRaises(ValueError):
            book.export_pdf(book.path)
        book.close()

    def test_comic_and_image(self):
        for name,total in [('Welcome.cbz',2),('page-1.png',1)]:
            book = Book(ROOT/'samples'/name)
            self.assertEqual(book.count,total)
            self.assertTrue(book.render(total-1,400)['image'])
            book.close()

    def test_password_and_permissions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'locked.pdf'
            with fitz.open(ROOT/'samples/Welcome.pdf') as doc:
                doc.save(path,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='reader',permissions=0)
            with self.assertRaises(PermissionError):
                Book(path)
            with self.assertRaises(PermissionError):
                Book(path,'wrong')
            book = Book(path,'reader')
            self.assertFalse(book.can_print)
            self.assertFalse(book.can_copy)
            self.assertTrue(book.render(0,400)['image'])
            with self.assertRaises(PermissionError):
                book.export_pdf(Path(folder)/'copy.pdf')
            book.close()

    def test_txt_encodings(self):
        with tempfile.TemporaryDirectory() as folder:
            for encoding in ('utf-8-sig','utf-16','cp1251'):
                path = Path(folder)/(encoding+'.txt')
                path.write_bytes('Русский текст, закладка'.encode(encoding))
                book = Book(path)
                self.assertIn('Русский текст',book.text(0))
                book.close()

    def test_zip_ambiguity_and_corruption(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'ambiguous.fb2.zip'
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('a.fb2','a'); z.writestr('b.fb2','b')
            with self.assertRaises(ValueError):
                Book(path)
            path = Path(folder)/'broken.pdf'
            path.write_bytes(b'not a PDF')
            with self.assertRaises(Exception):
                Book(path)

    def test_library_persists_position_and_does_not_delete_original(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'books.sqlite'
            original = Path(folder)/'book.txt'
            original.write_text('hi')
            path = str(original.resolve())
            lib = Library(db)
            lib.add(path,'Книга',20)
            lib.opened(path,7)
            lib.toggle_bookmark(path,7)
            lib.close()
            lib = Library(db)
            self.assertEqual(lib.get(path)['page'],7)
            self.assertEqual(lib.bookmarks(path)[0]['page'],7)
            self.assertEqual(len(lib.all('книГА')),1)
            lib.remove(path)
            self.assertTrue(original.exists())
            self.assertEqual(lib.bookmarks(path),[])
            lib.close()

    def test_worker_recovers_after_bad_open(self):
        requests = [dict(id=1,op='open',args={'path':str(ROOT/'samples/Welcome.pdf')}),
                    dict(id=2,op='open',args={'path':'/does-not-exist.pdf'}),
                    dict(id=3,op='text',args={'page':1}),dict(id=4,op='quit')]
        result = subprocess.run([sys.executable,str(ROOT/'main.py'),'--worker'],
            input=''.join(json.dumps(x)+'\n' for x in requests),text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        responses = [json.loads(s) for s in result.stdout.splitlines()]
        self.assertIn('error',responses[1])
        self.assertIn('Контрольная фраза',responses[2]['result'])

    def test_djvu(self):
        path = ROOT/'samples/Welcome.djvu'
        try:
            executable('ddjvu')
        except RuntimeError:
            self.skipTest('DjVuLibre not installed')
        if not path.exists():
            self.skipTest('DjVu fixture not generated')
        book = Book(path)
        self.assertEqual(book.count,2)
        self.assertTrue(book.render(1,600)['image'])
        self.assertIn('Folio',book.text(0))
        self.assertEqual(book.find('SECOND',0),1)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder)/'djvu-export.pdf'
            book.export_pdf(output)
            with fitz.open(output) as doc:
                self.assertEqual(doc.page_count,2)
        book.close()


if __name__ == '__main__':
    unittest.main()
