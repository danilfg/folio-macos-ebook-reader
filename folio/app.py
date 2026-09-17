from __future__ import annotations

from .ui_shared import *
from .window_ui import WindowUiMixin
from .window_library import WindowLibraryMixin
from .window_reader import WindowReaderMixin
from .window_commands import WindowCommandsMixin


class Window(WindowUiMixin, WindowLibraryMixin, WindowReaderMixin, WindowCommandsMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Folio — ebook & document reader')
        self.resize(1280, 880)
        self.setMinimumSize(900, 620)
        self.setAcceptDrops(True)

        self.library = Library()
        self.meta = None
        self.page = 0
        self.generation = 0
        self.render_generation = 0
        self.render_busy = False
        self.pending_pages = set()
        self.rendered_signature = {}
        self.opening = False
        self.working = False
        self.dark = False
        self.last_query = ''
        self.printer = self.painter = None
        self.page_labels = []
        self.page_label = None
        self.zoom_value = 'Fit Width'
        self.zoom_numeric_values = ['50%', '67%', '75%', '90%', '100%', '110%', '125%', '150%', '175%', '200%', '250%', '300%']
        self.book_previews = {}
        self.preview_queue = []
        self.preview_active = None
        self.preview_engine = None

        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.refresh_page_geometry)
        self.scroll_timer = QTimer(self)
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self.render_visible_pages)
        self.render_debounce_timer = QTimer(self)
        self.render_debounce_timer.setSingleShot(True)
        self.render_debounce_timer.timeout.connect(self.render_visible_pages)

        self.build_ui()
        self.engine = EngineClient(self)
        self.engine.failed.connect(self.error)
        self.refresh_library()
        self.apply_style()


class Application(QApplication):
    window = None
    queued = []

    def event(self, event):
        if event.type() == QEvent.Type.FileOpen:
            if self.window:
                self.window.add_paths([event.file()])
            else:
                self.queued.append(event.file())
            return True
        return super().event(event)


def main():
    app = Application(sys.argv)
    app.setApplicationName('Folio')
    app.setOrganizationName('FolioReader')
    app.setFont(QFont('Helvetica Neue', 13))
    window = Window()
    app.window = window
    window.show()
    files = app.queued + [s for s in sys.argv[1:] if not s.startswith('-') and Path(s).is_file()]
    if files:
        QTimer.singleShot(50, lambda: window.add_paths(files))
    sys.exit(app.exec())
