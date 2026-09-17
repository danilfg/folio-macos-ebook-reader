import os
import tempfile
import unittest

if not os.environ.get('DISPLAY'):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from folio.app import Application, Window
from folio.v034 import CompactBookRow


class V034SmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Application.instance() or Application([])

    def test_ui_overrides_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get('FOLIO_DATA_DIR')
            os.environ['FOLIO_DATA_DIR'] = tmp
            window = Window()
            window.show()
            self.app.processEvents()
            self.assertEqual(window.tabs.tabText(0), 'Books')
            self.assertEqual(window.tabs.tabText(1), 'Contents')
            self.assertEqual(window.tabs.tabText(2), 'Marks')
            self.assertIn('menu-indicator', window.zoom_menu_button.styleSheet())
            row = CompactBookRow('Example', 'PDF · Page 1 / 2', 'PDF')
            row.set_selected(True)
            self.assertTrue(row.selected)
            window.close()
            self.app.processEvents()
            if old is None:
                os.environ.pop('FOLIO_DATA_DIR', None)
            else:
                os.environ['FOLIO_DATA_DIR'] = old


if __name__ == '__main__':
    unittest.main()
