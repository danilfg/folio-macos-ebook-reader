from __future__ import annotations

import base64

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def parse_page_range(value: str, total: int) -> list[int]:
    value = value.strip()
    if not value:
        raise ValueError('Enter a page range, for example: 1-5, 8, 11-13.')
    pages: list[int] = []
    for raw in value.split(','):
        part = raw.strip()
        if not part:
            continue
        if '-' in part:
            start_raw, end_raw = [x.strip() for x in part.split('-', 1)]
            if not start_raw.isdigit() or not end_raw.isdigit():
                raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11-13.')
            start, end = int(start_raw), int(end_raw)
            if start > end:
                start, end = end, start
            pages.extend(range(start - 1, end))
        elif part.isdigit():
            pages.append(int(part) - 1)
        else:
            raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11-13.')
    result = sorted(set(page for page in pages if 0 <= page < total))
    if not result:
        raise ValueError('The selected range does not contain any valid pages.')
    return result


def chunk_pages(pages: list[int], pages_per_sheet: int) -> list[list[int]]:
    size = max(1, int(pages_per_sheet))
    return [pages[index:index + size] for index in range(0, len(pages), size)]


def grid_for_pages(pages_per_sheet: int) -> tuple[int, int]:
    value = int(pages_per_sheet)
    if value <= 1:
        return 1, 1
    if value == 2:
        return 2, 1
    if value == 4:
        return 2, 2
    return 3, 2


def cell_rects(bounds: QRectF, pages_per_sheet: int) -> list[QRectF]:
    columns, rows = grid_for_pages(pages_per_sheet)
    margin = max(8.0, min(bounds.width(), bounds.height()) * 0.025)
    gap = max(8.0, min(bounds.width(), bounds.height()) * 0.018)
    inner = bounds.adjusted(margin, margin, -margin, -margin)
    cell_w = (inner.width() - gap * (columns - 1)) / columns
    cell_h = (inner.height() - gap * (rows - 1)) / rows
    result = []
    for row in range(rows):
        for column in range(columns):
            result.append(QRectF(
                inner.x() + column * (cell_w + gap),
                inner.y() + row * (cell_h + gap),
                cell_w,
                cell_h,
            ))
    return result


class PrintSheetWidget(QLabel):
    def __init__(self, pages: list[int], pages_per_sheet: int, parent=None):
        super().__init__(parent)
        self.pages = list(pages)
        self.pages_per_sheet = int(pages_per_sheet)
        self.pending = False
        self.rendered = False
        self.generation = 0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(650, 920)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.reset_placeholder()

    def reset_placeholder(self):
        self.pending = False
        self.rendered = False
        self.generation += 1
        self.setPixmap(QPixmap())
        if not self.pages:
            self.setText('Empty sheet')
        elif len(self.pages) == 1:
            self.setText(f'Page {self.pages[0] + 1}')
        else:
            self.setText(f'Pages {self.pages[0] + 1}–{self.pages[-1] + 1}')


class PrintPreviewDialog(QDialog):
    """Lexumi-styled multi-sheet print preview with N-up imposition."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.active = True
        self.preview_generation = 0
        self.sheets: list[PrintSheetWidget] = []
        self.range_timer = QTimer(self)
        self.range_timer.setSingleShot(True)
        self.range_timer.timeout.connect(self.rebuild_preview)

        self.setWindowTitle('Print preview')
        self.resize(1280, 820)
        self.setMinimumSize(1050, 700)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        preview_panel = QWidget()
        preview_panel.setObjectName('printPreviewCanvas')
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(24, 20, 24, 20)
        preview_layout.setSpacing(10)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setObjectName('printPreviewScroll')
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview_scroll.verticalScrollBar().valueChanged.connect(self.render_visible_sheets)
        self.preview_container = QWidget()
        self.preview_container.setObjectName('printPreviewContainer')
        self.preview_stack = QVBoxLayout(self.preview_container)
        self.preview_stack.setContentsMargins(16, 12, 16, 12)
        self.preview_stack.setSpacing(20)
        self.preview_stack.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.preview_scroll.setWidget(self.preview_container)
        preview_layout.addWidget(self.preview_scroll, 1)
        root.addWidget(preview_panel, 1)

        settings = QWidget()
        settings.setObjectName('printSettingsPanel')
        settings.setFixedWidth(390)
        side = QVBoxLayout(settings)
        side.setContentsMargins(28, 24, 28, 24)
        side.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel('Print')
        title.setObjectName('printTitle')
        header.addWidget(title)
        header.addStretch(1)
        self.sheet_count = QLabel('')
        self.sheet_count.setObjectName('printSheetCount')
        header.addWidget(self.sheet_count)
        side.addLayout(header)
        side.addSpacing(6)

        self._add_field_label(side, 'Pages')
        self.pages_mode = QComboBox()
        self.pages_mode.addItems(['All pages', 'Current page', 'Custom range'])
        self.pages_mode.currentIndexChanged.connect(self.mode_changed)
        side.addWidget(self.pages_mode)

        self.range_edit = QLineEdit()
        self.range_edit.setPlaceholderText('e.g. 1-5, 8, 11-13')
        self.range_edit.hide()
        self.range_edit.textChanged.connect(lambda *_: self.range_timer.start(250))
        side.addWidget(self.range_edit)

        self.range_error = QLabel('')
        self.range_error.setObjectName('printRangeError')
        self.range_error.setWordWrap(True)
        self.range_error.hide()
        side.addWidget(self.range_error)

        self._add_field_label(side, 'Pages per sheet')
        self.pages_per_sheet_combo = QComboBox()
        for value in (1, 2, 4, 6):
            self.pages_per_sheet_combo.addItem(str(value), value)
        self.pages_per_sheet_combo.currentIndexChanged.connect(self.rebuild_preview)
        side.addWidget(self.pages_per_sheet_combo)

        self._add_field_label(side, 'Scale')
        self.scale_mode = QComboBox()
        self.scale_mode.addItem('Fit to paper', 'fit')
        self.scale_mode.addItem('Actual size', 'actual')
        self.scale_mode.addItem('Custom', 'custom')
        self.scale_mode.currentIndexChanged.connect(self.scale_changed)
        side.addWidget(self.scale_mode)

        self.scale_percent = QSpinBox()
        self.scale_percent.setRange(10, 400)
        self.scale_percent.setValue(100)
        self.scale_percent.setSuffix('%')
        self.scale_percent.hide()
        self.scale_percent.valueChanged.connect(self.reset_preview_images)
        side.addWidget(self.scale_percent)

        side.addSpacing(10)
        hint = QLabel(
            'Printer, paper size, copies and PDF destination are selected in the native macOS print dialog after this preview.'
        )
        hint.setObjectName('printHint')
        hint.setWordWrap(True)
        side.addWidget(hint)
        side.addStretch(1)

        buttons = QHBoxLayout()
        cancel = QPushButton('Cancel')
        cancel.setObjectName('printSecondaryButton')
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        print_button = QPushButton('Print…')
        print_button.setObjectName('printPrimaryButton')
        print_button.clicked.connect(self.accept_if_valid)
        buttons.addWidget(print_button)
        side.addLayout(buttons)

        root.addWidget(settings)
        self.apply_lexumi_style()
        self.rebuild_preview()

    def _add_field_label(self, layout, text):
        label = QLabel(text)
        label.setObjectName('printFieldLabel')
        layout.addWidget(label)

    def apply_lexumi_style(self):
        dark = bool(getattr(self.window, 'dark', False))
        if dark:
            canvas, panel, ink, muted, border, input_bg, accent, accent_hover = (
                '#14191f', '#1d232b', '#eef2f7', '#9eabb9', '#3b4654', '#252d37', '#3aa675', '#49b985'
            )
        else:
            canvas, panel, ink, muted, border, input_bg, accent, accent_hover = (
                '#e8ebe6', '#f8f6f1', '#24332d', '#6f7872', '#d6ddd4', '#ffffff', '#11875d', '#0e9665'
            )
        self.setStyleSheet(f'''
            QDialog {{ background:{canvas}; color:{ink}; font-family:"Helvetica Neue","Arial"; font-size:14px; }}
            QWidget#printPreviewCanvas {{ background:{canvas}; }}
            QWidget#printSettingsPanel {{ background:{panel}; border-left:1px solid {border}; }}
            QLabel#printTitle {{ font-size:26px; font-weight:700; color:{ink}; }}
            QLabel#printSheetCount {{ color:{muted}; font-size:13px; }}
            QLabel#printFieldLabel {{ color:{ink}; font-size:13px; font-weight:600; margin-top:7px; }}
            QLabel#printHint {{ color:{muted}; font-size:12px; }}
            QLabel#printRangeError {{ color:#c9483d; font-size:11px; }}
            QComboBox, QLineEdit, QSpinBox {{
                background:{input_bg}; color:{ink}; border:1px solid {border}; border-radius:11px;
                padding:9px 12px; min-height:24px; selection-background-color:{accent};
            }}
            QComboBox:hover, QLineEdit:hover, QSpinBox:hover {{ border-color:{accent}; }}
            QComboBox QAbstractItemView {{ background:{input_bg}; color:{ink}; border:1px solid {border}; selection-background-color:{accent}; outline:0; }}
            QSpinBox::up-button, QSpinBox::down-button {{ width:0px; height:0px; border:0; }}
            QPushButton#printSecondaryButton {{ background:{input_bg}; color:{ink}; border:1px solid {border}; border-radius:13px; padding:10px 18px; min-width:92px; }}
            QPushButton#printSecondaryButton:hover {{ border-color:{accent}; }}
            QPushButton#printPrimaryButton {{ background:{accent}; color:white; border:1px solid {accent}; border-radius:13px; padding:10px 20px; min-width:102px; font-weight:600; }}
            QPushButton#printPrimaryButton:hover {{ background:{accent_hover}; border-color:{accent_hover}; }}
            QScrollArea#printPreviewScroll {{ border:0; background:transparent; }}
            QWidget#printPreviewContainer {{ background:transparent; }}
            QLabel#printSheet {{ background:white; color:#87918b; border:1px solid #cfd4cf; border-radius:2px; font-size:13px; }}
            QScrollBar:vertical {{ background:transparent; width:10px; margin:2px; }}
            QScrollBar::handle:vertical {{ background:#aeb8b0; min-height:36px; border-radius:5px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background:transparent; }}
        ''')

    def done(self, result):
        self.active = False
        self.preview_generation += 1
        super().done(result)

    def mode_changed(self, *_):
        custom = self.pages_mode.currentIndex() == 2
        self.range_edit.setVisible(custom)
        self.range_error.setVisible(False)
        self.rebuild_preview()

    def scale_changed(self, *_):
        self.scale_percent.setVisible(self.scale_mode_value() == 'custom')
        self.reset_preview_images()

    def pages_per_sheet_value(self) -> int:
        return int(self.pages_per_sheet_combo.currentData() or 1)

    def scale_mode_value(self) -> str:
        return str(self.scale_mode.currentData() or 'fit')

    def scale_percent_value(self) -> int:
        return int(self.scale_percent.value())

    def selected_pages(self) -> list[int]:
        mode = self.pages_mode.currentIndex()
        if mode == 1:
            return [self.window.page]
        if mode == 2:
            return parse_page_range(self.range_edit.text(), self.window.meta['count'])
        return list(range(self.window.meta['count']))

    def accept_if_valid(self):
        try:
            self.selected_pages()
        except ValueError as exc:
            QMessageBox.warning(self, 'Print preview', str(exc))
            return
        self.accept()

    def clear_sheets(self):
        while self.preview_stack.count():
            item = self.preview_stack.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.sheets = []

    def rebuild_preview(self, *_):
        if not self.active:
            return
        self.preview_generation += 1
        self.clear_sheets()
        self.range_error.hide()
        try:
            pages = self.selected_pages()
        except ValueError as exc:
            self.sheet_count.setText('0 sheets')
            self.range_error.setText(str(exc))
            self.range_error.setVisible(self.pages_mode.currentIndex() == 2)
            return
        groups = chunk_pages(pages, self.pages_per_sheet_value())
        count = len(groups)
        self.sheet_count.setText(f'{count} sheet' if count == 1 else f'{count} sheets')
        for group in groups:
            sheet = PrintSheetWidget(group, self.pages_per_sheet_value(), self.preview_container)
            sheet.setObjectName('printSheet')
            self.sheets.append(sheet)
            self.preview_stack.addWidget(sheet, 0, Qt.AlignmentFlag.AlignHCenter)
        QTimer.singleShot(0, self.render_visible_sheets)

    def reset_preview_images(self, *_):
        if not self.active:
            return
        self.preview_generation += 1
        for sheet in self.sheets:
            sheet.reset_placeholder()
        QTimer.singleShot(0, self.render_visible_sheets)

    def render_visible_sheets(self, *_):
        if not self.active or not self.sheets:
            return
        top = self.preview_scroll.verticalScrollBar().value()
        bottom = top + self.preview_scroll.viewport().height()
        near = []
        for index, sheet in enumerate(self.sheets):
            y = sheet.geometry().top()
            h = sheet.height()
            if y + h >= top - h and y <= bottom + h:
                near.append(index)
        if not near:
            near = [0]
        keep = set(near)
        for index, sheet in enumerate(self.sheets):
            if index not in keep and (sheet.rendered or sheet.pending):
                sheet.reset_placeholder()
        for index in near:
            self.render_sheet(self.sheets[index])

    def render_sheet(self, sheet: PrintSheetWidget):
        if sheet.pending or sheet.rendered or not sheet.pages:
            return
        generation = self.preview_generation
        sheet.pending = True
        sheet_generation = sheet.generation
        canvas = QPixmap(sheet.size())
        canvas.fill(QColor('#ffffff'))
        sheet.setPixmap(canvas)
        sheet.setText('')
        rects = cell_rects(QRectF(0, 0, sheet.width(), sheet.height()), sheet.pages_per_sheet)
        remaining = {'count': len(sheet.pages)}

        def page_done(response, slot, page):
            if not self.active or generation != self.preview_generation or sheet_generation != sheet.generation:
                return
            if 'error' not in response:
                image = QImage.fromData(base64.b64decode(response['result']['image']))
                if not image.isNull():
                    self.draw_page_on_pixmap(sheet, image, rects[slot], page)
            remaining['count'] -= 1
            if remaining['count'] <= 0:
                sheet.pending = False
                sheet.rendered = True

        render_width = 1050 if sheet.pages_per_sheet == 1 else 700 if sheet.pages_per_sheet == 2 else 460
        for slot, page in enumerate(sheet.pages):
            self.window.engine.request(
                'render',
                lambda response, slot=slot, page=page: page_done(response, slot, page),
                page=page,
                width=render_width,
            )

    def draw_page_on_pixmap(self, sheet, image, cell, page):
        pix = sheet.pixmap()
        if pix is None or pix.isNull():
            return
        canvas = pix.copy()
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.fillRect(cell, QColor('#f4f5f2'))
        target = self.preview_target_rect(cell, image, page, sheet.size())
        painter.setClipRect(cell)
        painter.drawImage(target, image)
        painter.setClipping(False)
        painter.setPen(QColor('#c7ccc7'))
        painter.drawRect(target)
        painter.end()
        sheet.setPixmap(canvas)

    def preview_target_rect(self, cell, image, page, sheet_size):
        mode = self.scale_mode_value()
        if mode == 'fit':
            ratio = min(cell.width() / image.width(), cell.height() / image.height())
            width, height = image.width() * ratio, image.height() * ratio
        else:
            sizes = self.window.meta.get('page_sizes') or [[595.0, 842.0]] * self.window.meta['count']
            src_w, src_h = sizes[min(page, len(sizes) - 1)]
            physical_scale = sheet_size.width() / 595.0
            factor = self.scale_percent_value() / 100.0 if mode == 'custom' else 1.0
            width, height = float(src_w) * physical_scale * factor, float(src_h) * physical_scale * factor
        return QRectF(
            cell.x() + (cell.width() - width) / 2,
            cell.y() + (cell.height() - height) / 2,
            width,
            height,
        )


class WindowV039Mixin:
    """v0.3.9: Lexumi-styled multi-sheet print preview and N-up printing."""

    def print_book(self):
        if not self.meta or self.working or self.opening:
            return
        if not self.meta['can_print']:
            self.error('The PDF author disabled printing.')
            return

        preview = PrintPreviewDialog(self)
        if preview.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            selected_pages = preview.selected_pages()
        except ValueError as exc:
            self.error(str(exc))
            return

        self.print_pages_per_sheet = preview.pages_per_sheet_value()
        self.print_scale_mode = preview.scale_mode_value()
        self.print_scale_percent = preview.scale_percent_value()
        preview.active = False
        self.print_pages = list(selected_pages)
        self.print_groups = chunk_pages(self.print_pages, self.print_pages_per_sheet)

        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.printer.setResolution(200)
        self.printer.setDocName(self.meta['title'])
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            self.printer = None
            return

        if self.printer.pageOrder() == QPrinter.PageOrder.LastPageFirst:
            self.print_groups.reverse()
        if not self.printer.supportsMultipleCopies():
            copies = max(1, self.printer.copyCount())
            self.print_groups = (
                self.print_groups * copies
                if self.printer.collateCopies()
                else [group for group in self.print_groups for _ in range(copies)]
            )

        self.painter = QPainter()
        if not self.painter.begin(self.printer):
            self.painter = self.printer = None
            self.error('Could not start printing.')
            return

        self.working = True
        self.print_sheet_index = 0
        self.print_cell_index = 0
        self.print_progress = QProgressDialog('Printing sheets…', 'Cancel', 0, len(self.print_groups), self)
        self.print_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.print_progress.show()
        self.print_next()

    def print_next(self):
        if self.print_progress.wasCanceled() or self.print_sheet_index >= len(self.print_groups):
            self.finish_print(self.print_progress.wasCanceled())
            return

        group = self.print_groups[self.print_sheet_index]
        if self.print_cell_index == 0 and self.print_sheet_index > 0:
            if not self.printer.newPage():
                self.finish_print(True)
                self.error('The printer did not accept the next sheet.')
                return

        page = group[self.print_cell_index]
        columns, _ = grid_for_pages(self.print_pages_per_sheet)
        viewport = self.printer.pageLayout().paintRectPixels(self.printer.resolution())
        render_width = max(700, min(2200, int(viewport.width() / max(1, columns))))

        def done(response):
            if 'error' in response:
                self.finish_print(True)
                self.error(response['error'])
                return
            if self.print_progress.wasCanceled():
                self.finish_print(True)
                return
            image = QImage.fromData(base64.b64decode(response['result']['image']))
            self.draw_print_page(image, page, self.print_cell_index, viewport)
            self.print_cell_index += 1
            if self.print_cell_index >= len(group):
                self.print_sheet_index += 1
                self.print_cell_index = 0
                self.print_progress.setValue(self.print_sheet_index)
            QTimer.singleShot(0, self.print_next)

        self.engine.request('render', done, page=page, width=render_width)

    def draw_print_page(self, image, page, slot, viewport):
        rects = cell_rects(QRectF(viewport), self.print_pages_per_sheet)
        cell = rects[slot]
        mode = getattr(self, 'print_scale_mode', 'fit')
        if mode == 'fit':
            ratio = min(cell.width() / image.width(), cell.height() / image.height())
            width, height = image.width() * ratio, image.height() * ratio
        else:
            sizes = self.meta.get('page_sizes') or [[595.0, 842.0]] * self.meta['count']
            src_w, src_h = sizes[min(page, len(sizes) - 1)]
            factor = getattr(self, 'print_scale_percent', 100) / 100.0 if mode == 'custom' else 1.0
            width = float(src_w) / 72.0 * self.printer.resolution() * factor
            height = float(src_h) / 72.0 * self.printer.resolution() * factor
        target = QRectF(
            cell.x() + (cell.width() - width) / 2,
            cell.y() + (cell.height() - height) / 2,
            width,
            height,
        )
        self.painter.save()
        self.painter.setClipRect(cell)
        self.painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.painter.drawImage(target, image)
        self.painter.restore()

    def finish_print(self, cancelled):
        if cancelled and self.printer is not None:
            self.printer.abort()
        if self.painter is not None:
            self.painter.end()
        self.painter = self.printer = None
        if getattr(self, 'print_progress', None) is not None:
            self.print_progress.close()
        self.working = False
        self.statusBar().showMessage('Printing cancelled' if cancelled else 'Sheets sent to the printer')

    def about(self):
        QMessageBox.about(
            self,
            'About Lexumi',
            'Lexumi 0.3.9\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ / CBR · images\n\n'
            'Continuous scrolling, embedded ebook covers, two-page spreads, text search, bookmarks, '
            'multi-sheet print preview, N-up printing, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre, libarchive.\nAGPL-3.0-or-later.'
        )
