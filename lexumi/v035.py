from __future__ import annotations

import base64
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox

from .engine import supported as base_supported
from .engine_v035 import is_rar_archive
from .ui_shared import BOOK_FILTER, EngineClient
from .v034 import CompactBookRow


class DenseBookRow(CompactBookRow):
    def __init__(self, title: str, meta: str, ext: str, dark: bool = False):
        super().__init__(title, meta, ext, dark)
        self.setMinimumHeight(68)
        self.setMaximumHeight(70)
        self.layout().setContentsMargins(5, 4, 5, 4)
        self.layout().setSpacing(8)
        self.thumb.setFixedSize(40, 54)
        self.remove_button.setFixedSize(20, 20)
        self.title.setMaximumHeight(38)
        self.meta.setMaximumHeight(22)

    def set_preview(self, pixmap, fallback: str = ''):
        if pixmap is not None and not pixmap.isNull():
            scaled = pixmap.scaled(
                36,
                50,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb.setPixmap(scaled)
            self.thumb.setText('')
        else:
            self.thumb.setPixmap(QPixmap())
            self.thumb.setText(fallback)


class WindowV035Mixin:
    """v0.3.5: real ebook covers, RAR/CBR comics, and a denser library."""

    def build_ui(self):
        super().build_ui()
        self.books.setSpacing(2)

    def _display_ext(self, path: str):
        p = Path(path)
        if is_rar_archive(p):
            return 'CBR'
        if p.name.lower().endswith('.fb2.zip'):
            return 'FB2.ZIP'
        return p.suffix[1:].upper()

    def refresh_library(self, *_):
        self.books.clear()
        current_path = self.meta['path'] if self.meta else None
        rows = self.library.all(self.filter.text())
        for row in rows:
            ext = self._display_ext(row['path'])
            progress = f'Page {row["page"] + 1} / {row["total"]}' if row['total'] else 'Not opened yet'
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row['path'])
            item.setToolTip(row['path'] + '\nClick to open')
            item.setSizeHint(QSize(0, 72))
            self.books.addItem(item)

            row_widget = DenseBookRow(row['title'], f'{ext}  ·  {progress}', ext, self.dark)
            row_widget.set_preview(self.book_previews.get(row['path']), ext)
            row_widget.set_selected(row['path'] == current_path, self.dark)
            row_widget.openRequested.connect(
                lambda p=row['path'], i=item: self.open_book_from_library(p, i)
            )
            row_widget.removeRequested.connect(lambda p=row['path']: self.remove_book(p))
            self.books.setItemWidget(item, row_widget)
        self._queue_library_previews(rows)

    def choose_open(self):
        book_filter = BOOK_FILTER.replace('*.cbz', '*.cbz *.cbr')
        paths, _ = QFileDialog.getOpenFileNames(self, 'Open books', str(Path.home()), book_filter)
        self.add_paths(paths)

    def add_paths(self, paths):
        valid = []
        for value in paths:
            path = Path(value)
            if not path.is_file():
                continue
            if base_supported(path) or path.suffix.lower() == '.cbr' or is_rar_archive(path):
                valid.append(str(path.resolve()))
        for path in valid:
            self.library.add(path)
        self.refresh_library()
        if valid:
            self.open_path(valid[0])
        elif paths:
            self.error('None of the selected files use a supported book format.')

    def _queue_library_previews(self, rows):
        queued = set(self.preview_queue)
        if self.preview_active:
            queued.add(self.preview_active)
        for row in rows:
            path = row['path']
            if path in self.book_previews or path in queued or not Path(path).is_file():
                continue
            self.preview_queue.append(path)
            queued.add(path)
        self._start_next_preview()

    def update_sidebar_preview(self):
        if not self.meta:
            return
        path = self.meta['path']
        if path in self.book_previews or path == self.preview_active or path in self.preview_queue:
            return
        self.preview_queue.insert(0, path)
        self._start_next_preview()

    def _ensure_preview_engine(self):
        if self.preview_engine is None:
            self.preview_engine = EngineClient(self)
        return self.preview_engine

    def _start_next_preview(self):
        if self.preview_active or not self.preview_queue:
            return
        path = self.preview_queue.pop(0)
        if path in self.book_previews or not Path(path).is_file():
            self._start_next_preview()
            return
        self.preview_active = path
        worker = self._ensure_preview_engine()

        def opened(response, path=path, worker=worker):
            if path != self.preview_active:
                return
            if 'error' in response:
                self._finish_preview(path, None)
                return
            worker.request('cover', lambda r, p=path: self._cover_ready(p, r), width=96)

        worker.request('open', opened, path=path, password='')

    def _cover_ready(self, path, response):
        pixmap = None
        if 'error' not in response:
            try:
                image = base64.b64decode(response['result']['image'])
                pixmap = QPixmap()
                if not pixmap.loadFromData(image):
                    pixmap = None
            except Exception:
                pixmap = None
        self._finish_preview(path, pixmap)

    def _finish_preview(self, path, pixmap):
        if pixmap is not None and not pixmap.isNull():
            self.book_previews[path] = pixmap
            self._apply_preview_to_visible_row(path, pixmap)
        if self.preview_active == path:
            self.preview_active = None
        if self.preview_queue:
            self._start_next_preview()
        elif self.preview_engine is not None:
            self.preview_engine.stop()
            self.preview_engine.deleteLater()
            self.preview_engine = None

    def _apply_preview_to_visible_row(self, path, pixmap):
        for index in range(self.books.count()):
            item = self.books.item(index)
            if item.data(Qt.ItemDataRole.UserRole) != path:
                continue
            widget = self.books.itemWidget(item)
            if isinstance(widget, DenseBookRow):
                widget.set_preview(pixmap, self._display_ext(path))
            break

    def about(self):
        QMessageBox.about(
            self,
            'About Lexumi',
            'Lexumi 0.3.5\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ / CBR · images\n\n'
            'Continuous scrolling, embedded ebook covers, text search, bookmarks, print preview, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre, libarchive.\nAGPL-3.0-or-later.'
        )

    def closeEvent(self, event):
        if self.preview_engine is not None:
            self.preview_engine.stop()
            self.preview_engine = None
        super().closeEvent(event)
