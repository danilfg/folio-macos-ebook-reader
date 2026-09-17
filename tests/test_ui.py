"""Headless integration: real Qt window, continuous reader, engine process, and PDF print output."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

if sys.platform != 'darwin' and not os.environ.get('DISPLAY'):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QDialog
import pymupdf as fitz
from folio.app import Application, PrintPreviewDialog, Window
from make_samples import make as make_samples


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / 'samples' / 'Welcome.pdf').exists():
            make_samples()
        cls.app = Application.instance() or Application([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_dir = os.environ.get('FOLIO_DATA_DIR')
        os.environ['FOLIO_DATA_DIR'] = self.temp.name
        self.window = Window()
        self.errors = []
        self.window.error = self.errors.append
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.working = False
        self.window.close()
        self.app.processEvents()
        self.temp.cleanup()
        if self.old_dir is None:
            os.environ.pop('FOLIO_DATA_DIR', None)
        else:
            os.environ['FOLIO_DATA_DIR'] = self.old_dir

    def wait_for(self, predicate, timeout=10):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                self.assertFalse(self.errors, self.errors)
                return
            QTest.qWait(10)
        self.fail('Timed out; errors: ' + str(self.errors))

    def open_pdf(self):
        self.window.open_path(str(ROOT / 'samples/Welcome.pdf'))
        self.wait_for(lambda: self.window.meta is not None and len(self.window.page_labels) == 2)
        self.wait_for(lambda: self.window.page_labels[0].pixmap() is not None)

    def test_continuous_reader_navigation_bookmark_search_zoom(self):
        self.open_pdf()
        self.assertEqual(len(self.window.page_labels), 2)
        self.assertGreater(self.window.pages_container.height(), self.window.page_labels[0].height())

        self.window.go(1)
        self.wait_for(lambda: self.window.page == 1 and self.window.page_labels[1].pixmap() is not None)
        self.assertEqual(self.window.page_spin.value(), 2)

        self.window.bookmark()
        self.assertEqual(self.window.marks.count(), 1)

        self.window.focus_search()
        self.window.search.setText('Контрольная фраза')
        self.window.find()
        self.wait_for(lambda: not self.window.working and self.window.page == 1)
        self.wait_for(lambda: bool(self.window.page_labels[1].matches))

        self.window.toggle_theme()
        self.window.zoom.setCurrentText('Fit Page')
        self.wait_for(lambda: self.window.page_labels[1].pixmap() is not None)
        self.assertLessEqual(self.window.page_labels[1].height(), self.window.scroll.viewport().height())

    def test_selected_page_prints_to_real_pdf_after_preview(self):
        self.open_pdf()
        output = Path(self.temp.name) / 'printed.pdf'

        def accept_dialog(dialog):
            printer = dialog.printer()
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(str(output))
            return QPrintDialog.DialogCode.Accepted

        with patch.object(PrintPreviewDialog, 'exec', return_value=QDialog.DialogCode.Accepted), \
             patch.object(PrintPreviewDialog, 'selected_pages', return_value=[1]), \
             patch.object(QPrintDialog, 'exec', accept_dialog):
            self.window.print_book()
            self.wait_for(lambda: not self.window.working)

        self.assertTrue(output.exists())
        with fitz.open(output) as pdf:
            self.assertEqual(pdf.page_count, 1)
            self.assertGreater(len(pdf[0].get_images()), 0)
            pix = pdf[0].get_pixmap()
            self.assertGreater(pix.width, 100)


if __name__ == '__main__':
    unittest.main()
