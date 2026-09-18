from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import sys

from PySide6.QtCore import QByteArray, QEvent, QPoint, QRectF, QSize, Qt, QProcess, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QImage, QKeySequence, QPainter, QPixmap
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QAbstractSpinBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenu, QMessageBox, QProgressDialog,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
    QStackedWidget, QTabWidget, QToolBar, QToolButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget
)

from .engine import EXTENSIONS, supported
from .storage import Library

BOOK_FILTER = 'Books (' + ' '.join('*' + x for x in sorted(EXTENSIONS)) + ' *.fb2.zip);;All files (*)'

ICON_PATHS = {
    'open': '<path d="M3 6h6l2 2h10v10H3z"/><path d="M3 10h18l-3 8H5z"/>',
    'print': '<path d="M6 8V3h12v5"/><rect x="5" y="14" width="14" height="7" rx="1"/><path d="M4 9h16a2 2 0 0 1 2 2v5h-3M5 16H2v-5a2 2 0 0 1 2-2z"/>',
    'prev': '<path d="M15 5l-7 7 7 7"/>',
    'next': '<path d="M9 5l7 7-7 7"/>',
    'bookmark': '<path d="M7 3h10v18l-5-3-5 3z"/>',
    'export': '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M4 18v3h16v-3"/>',
    'theme': '<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
    'zoom_in': '<circle cx="10" cy="10" r="6"/><path d="M14.5 14.5L21 21M10 7v6M7 10h6"/>',
    'zoom_out': '<circle cx="10" cy="10" r="6"/><path d="M14.5 14.5L21 21M7 10h6"/>',
    'search': '<circle cx="10" cy="10" r="6"/><path d="M14.5 14.5L21 21"/>',
    'close': '<path d="M6 6l12 12M18 6L6 18"/>',
    'fit_width': '<rect x="4" y="5" width="16" height="14" rx="2"/><path d="M8 12h8"/><path d="M6 12l2-2M6 12l2 2M18 12l-2-2M18 12l-2 2"/>',
    'fit_page': '<rect x="5" y="4" width="14" height="16" rx="2"/><path d="M12 8v8"/><path d="M12 6l-2 2M12 6l2 2M12 18l-2-2M12 18l2-2"/>',
}


def line_icon(name, size=22):
    body = ICON_PATHS[name]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
        fill="none" stroke="#567064" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{body}</svg>'''
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


class EngineClient(QWidget):
    failed = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.hide()
        self.seq = 0
        self.callbacks = {}
        self.buffer = bytearray()
        self.proc = QProcess(self)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.SeparateChannels)
        self.proc.readyReadStandardOutput.connect(self.receive)
        self.proc.readyReadStandardError.connect(lambda: self.proc.readAllStandardError())
        self.proc.errorOccurred.connect(lambda e: self.failed.emit('Could not start the reading engine: ' + self.proc.errorString()))
        self.proc.finished.connect(self.finished)
        if getattr(sys, 'frozen', False):
            self.proc.start(sys.executable, ['--worker'])
        else:
            self.proc.start(sys.executable, ['-u', str(Path(__file__).resolve().parents[1] / 'main.py'), '--worker'])
        self.proc.waitForStarted(5000)

    def request(self, op, callback, **args):
        if self.proc.state() == QProcess.ProcessState.NotRunning:
            callback({'error': 'The reading engine stopped. Restart Lexumi.', 'kind': 'RuntimeError'})
            return
        self.seq += 1
        self.callbacks[self.seq] = callback
        self.proc.write((json.dumps(dict(id=self.seq, op=op, args=args)) + '\n').encode())

    def receive(self):
        self.buffer.extend(bytes(self.proc.readAllStandardOutput()))
        while b'\n' in self.buffer:
            line, _, rest = self.buffer.partition(b'\n')
            self.buffer = bytearray(rest)
            try:
                response = json.loads(line)
            except ValueError:
                continue
            callback = self.callbacks.pop(response.get('id'), None)
            if callback:
                callback(response)

    def finished(self, code, status):
        callbacks, self.callbacks = self.callbacks, {}
        for callback in callbacks.values():
            callback({'error': 'The reading engine stopped. Restart Lexumi.', 'kind': 'RuntimeError'})

    def stop(self):
        self.callbacks.clear()
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.write(b'{"id":0,"op":"quit"}\n')
            self.proc.closeWriteChannel()
            if not self.proc.waitForFinished(1000):
                self.proc.kill()
                self.proc.waitForFinished(1000)


class PageLabel(QLabel):
    def __init__(self, page_index):
        super().__init__()
        self.page_index = page_index
        self.matches = []
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setScaledContents(True)
        self.setText(f'Page {page_index + 1}')
        self.setObjectName('bookPage')
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def reset_placeholder(self):
        self.clear()
        self.matches = []
        self.setText(f'Page {self.page_index + 1}')

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.matches and self.pixmap() is not None:
            painter = QPainter(self)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 198, 55, 95))
            for x, y, w, h in self.matches:
                painter.drawRect(QRectF(x * self.width(), y * self.height(), w * self.width(), h * self.height()))


class BookListItemWidget(QWidget):
    def __init__(self, title: str, meta: str, ext: str, dark: bool = False):
        super().__init__()
        self.setObjectName('bookListCard')
        self.dark = dark
        self.selected = False

        root = QHBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(12)

        self.thumb = QLabel(ext)
        self.thumb.setObjectName('bookListThumb')
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setWordWrap(True)
        self.thumb.setFixedSize(54, 72)
        root.addWidget(self.thumb, 0, Qt.AlignmentFlag.AlignTop)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 2, 0, 2)
        text_box.setSpacing(4)

        self.title = QLabel(title)
        self.title.setObjectName('bookListTitle')
        self.title.setWordWrap(True)
        text_box.addWidget(self.title)

        self.meta = QLabel(meta)
        self.meta.setObjectName('bookListMeta')
        self.meta.setWordWrap(True)
        text_box.addWidget(self.meta)
        text_box.addStretch(1)

        root.addLayout(text_box, 1)
        self.apply_state()

    def set_preview(self, pixmap: QPixmap | None, fallback: str = ''):
        if pixmap is not None and not pixmap.isNull():
            scaled = pixmap.scaled(50, 68, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.thumb.setText('')
            self.thumb.setPixmap(scaled)
        else:
            self.thumb.setPixmap(QPixmap())
            self.thumb.setText(fallback)

    def set_selected(self, selected: bool, dark: bool | None = None):
        self.selected = selected
        if dark is not None:
            self.dark = dark
        self.apply_state()

    def apply_state(self):
        if self.dark:
            panel = '#20262f'
            thumb_bg = '#11161d'
            border = '#34404f'
            hover = '#243a30'
            accent = '#38b27d'
            title = '#eef2f7'
            meta = '#a5b2c4'
        else:
            panel = '#ffffff'
            thumb_bg = '#eef2ed'
            border = '#d6ddd4'
            hover = '#dff0e6'
            accent = '#11875d'
            title = '#24332d'
            meta = '#6f7872'

        bg = hover if self.selected else panel
        line = accent if self.selected else border
        self.setStyleSheet(
            f"QWidget#bookListCard{{background:{bg};border:1px solid {line};border-radius:16px;}}"
            f"QLabel#bookListThumb{{background:{thumb_bg};border:1px solid {border};border-radius:10px;padding:2px;color:{meta};font-size:10px;font-weight:600;}}"
            f"QLabel#bookListTitle{{color:{title};font-size:14px;font-weight:600;border:0;background:transparent;}}"
            f"QLabel#bookListMeta{{color:{meta};font-size:11px;border:0;background:transparent;}}"
        )


class PrintPreviewDialog(QDialog):
    """A lightweight Chrome-style print preview before the native print dialog."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle('Print preview')
        self.resize(1050, 760)
        self.preview_generation = 0

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        settings = QWidget()
        settings.setObjectName('printSettings')
        settings.setFixedWidth(300)
        left = QVBoxLayout(settings)
        left.setContentsMargins(24, 24, 24, 24)
        title = QLabel('Print')
        title.setObjectName('printTitle')
        left.addWidget(title)

        left.addWidget(QLabel('Pages'))
        self.pages_mode = QComboBox()
        self.pages_mode.addItems(['All pages', 'Current page', 'Custom range'])
        self.pages_mode.currentIndexChanged.connect(self.mode_changed)
        left.addWidget(self.pages_mode)

        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText('Example: 1-3, 7, 10-12')
        self.range_edit.hide()
        left.addWidget(self.range_edit)

        left.addSpacing(14)
        left.addWidget(QLabel('Preview page'))
        nav = QHBoxLayout()
        prev_button = QToolButton()
        prev_button.setIcon(line_icon('prev'))
        prev_button.setToolTip('Previous preview page')
        prev_button.clicked.connect(lambda: self.preview_page.setValue(max(1, self.preview_page.value() - 1)))
        nav.addWidget(prev_button)
        self.preview_page = QSpinBox()
        self.preview_page.setRange(1, window.meta['count'])
        self.preview_page.setValue(window.page + 1)
        self.preview_page.valueChanged.connect(self.render_preview)
        nav.addWidget(self.preview_page)
        next_button = QToolButton()
        next_button.setIcon(line_icon('next'))
        next_button.setToolTip('Next preview page')
        next_button.clicked.connect(lambda: self.preview_page.setValue(min(self.preview_page.maximum(), self.preview_page.value() + 1)))
        nav.addWidget(next_button)
        left.addLayout(nav)

        info = QLabel('A native macOS printer dialog will open after this preview, where you can choose the printer, paper size, copies, and PDF destination.')
        info.setWordWrap(True)
        info.setObjectName('muted')
        left.addWidget(info)
        left.addStretch(1)

        buttons = QDialogButtonBox()
        cancel = buttons.addButton('Cancel', QDialogButtonBox.ButtonRole.RejectRole)
        print_button = buttons.addButton('Print…', QDialogButtonBox.ButtonRole.AcceptRole)
        cancel.clicked.connect(self.reject)
        print_button.clicked.connect(self.accept_if_valid)
        left.addWidget(buttons)
        root.addWidget(settings)

        canvas = QWidget()
        canvas.setObjectName('printCanvas')
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(36, 28, 36, 28)
        self.preview = QLabel('Loading preview…')
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setObjectName('printPage')
        canvas_layout.addWidget(self.preview, 1)
        root.addWidget(canvas, 1)

        self.render_preview()

    def mode_changed(self):
        self.range_edit.setVisible(self.pages_mode.currentIndex() == 2)

    def parse_custom_pages(self):
        value = self.range_edit.text().strip()
        if not value:
            raise ValueError('Enter a page range, for example: 1-3, 7, 10-12.')
        result = []
        total = self.window.meta['count']
        for part in value.split(','):
            part = part.strip()
            if not part:
                continue
            if '-' in part:
                a, b = [x.strip() for x in part.split('-', 1)]
                if not a.isdigit() or not b.isdigit():
                    raise ValueError('Page ranges must use numbers, for example: 1-3, 7.')
                start, end = int(a), int(b)
                if start > end:
                    start, end = end, start
                result.extend(range(start - 1, end))
            elif part.isdigit():
                result.append(int(part) - 1)
            else:
                raise ValueError('Page ranges must use numbers, for example: 1-3, 7.')
        result = sorted(set(p for p in result if 0 <= p < total))
        if not result:
            raise ValueError('The selected range does not contain any valid pages.')
        return result

    def selected_pages(self):
        if self.pages_mode.currentIndex() == 1:
            return [self.window.page]
        if self.pages_mode.currentIndex() == 2:
            return self.parse_custom_pages()
        return list(range(self.window.meta['count']))

    def accept_if_valid(self):
        try:
            self.selected_pages()
        except ValueError as exc:
            QMessageBox.warning(self, 'Print preview', str(exc))
            return
        self.accept()

    def render_preview(self, *_):
        self.preview_generation += 1
        generation = self.preview_generation
        page = self.preview_page.value() - 1
        width = max(700, self.width() - 380)
        self.preview.setText('Loading preview…')

        def done(response):
            if generation != self.preview_generation:
                return
            if 'error' in response:
                self.preview.setText(response['error'])
                return
            image = QImage.fromData(base64.b64decode(response['result']['image']))
            pix = QPixmap.fromImage(image)
            max_w = max(300, self.preview.width() - 30)
            max_h = max(300, self.preview.height() - 30)
            pix = pix.scaled(max_w, max_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.preview.setPixmap(pix)

        self.window.engine.request('render', done, page=page, width=width)
