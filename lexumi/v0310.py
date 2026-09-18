from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPageLayout, QPainter, QPen, QPixmap
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QDialog, QMenu, QMessageBox, QProgressDialog, QPushButton

from .v039 import (
    PrintPreviewDialog as PrintPreviewDialogV039,
    PrintSheetWidget as PrintSheetWidgetV039,
    WindowV039Mixin,
    chunk_pages,
)


def parse_page_range(value: str, total: int) -> list[int]:
    total = max(0, int(total))
    if total == 0:
        return []
    value = value.strip()
    if not value:
        return list(range(total))
    pages: list[int] = []
    for raw in value.split(','):
        part = raw.strip()
        if not part:
            continue
        if '-' in part:
            if part.count('-') != 1:
                raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11- or -6.')
            start_raw, end_raw = [x.strip() for x in part.split('-', 1)]
            if not start_raw and not end_raw:
                raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11- or -6.')
            if start_raw and not start_raw.isdigit():
                raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11- or -6.')
            if end_raw and not end_raw.isdigit():
                raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11- or -6.')
            start = int(start_raw) if start_raw else 1
            end = int(end_raw) if end_raw else total
            if start < 1 or end < 1:
                raise ValueError('Page numbers start at 1.')
            if start > end:
                start, end = end, start
            start = min(start, total)
            end = min(end, total)
            pages.extend(range(start - 1, end))
        elif part.isdigit():
            page = int(part)
            if page < 1:
                raise ValueError('Page numbers start at 1.')
            if page <= total:
                pages.append(page - 1)
        else:
            raise ValueError('Use page numbers and ranges, for example: 1-5, 8, 11- or -6.')
    result = sorted(set(pages))
    if not result:
        raise ValueError('The selected range does not contain any valid pages.')
    return result


def landscape_for_pages_per_sheet(pages_per_sheet: int) -> bool:
    return int(pages_per_sheet) in (2, 6)


def select_chevron_icon(color: str) -> QIcon:
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(color), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(4, 7, 9, 12)
    painter.drawLine(9, 12, 14, 7)
    painter.end()
    return QIcon(pixmap)


class LexumiSelect(QPushButton):
    currentIndexChanged = Signal(int)

    def __init__(self, items: list[tuple[str, object]], dark: bool = False, parent=None):
        super().__init__(parent)
        self._items = list(items)
        self._index = 0
        self._dark = bool(dark)
        self.setObjectName('printSelect')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setIconSize(QSize(18, 18))
        self.setMinimumHeight(44)
        self.clicked.connect(self.show_select_menu)
        self._sync()

    def _sync(self):
        text = self._items[self._index][0] if self._items else ''
        self.setText(text)
        self.setIcon(select_chevron_icon('#dfe9e3' if self._dark else '#24332d'))

    def currentIndex(self) -> int:
        return self._index

    def currentData(self):
        return None if not self._items else self._items[self._index][1]

    def currentText(self) -> str:
        return '' if not self._items else self._items[self._index][0]

    def setCurrentIndex(self, index: int):
        if not self._items:
            return
        index = max(0, min(int(index), len(self._items) - 1))
        changed = index != self._index
        self._index = index
        self._sync()
        if changed:
            self.currentIndexChanged.emit(index)

    def show_select_menu(self):
        menu = QMenu(self)
        menu.setObjectName('printSelectMenu')
        menu.setMinimumWidth(self.width())
        for index, (label, _) in enumerate(self._items):
            action = menu.addAction(label)
            action.triggered.connect(lambda _checked=False, i=index: self.setCurrentIndex(i))
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))


class PrintSheetWidget(PrintSheetWidgetV039):
    def __init__(self, pages: list[int], pages_per_sheet: int, parent=None):
        super().__init__(pages, pages_per_sheet, parent)
        if landscape_for_pages_per_sheet(pages_per_sheet):
            self.setFixedSize(920, 650)
        else:
            self.setFixedSize(650, 920)


class PrintPreviewDialog(PrintPreviewDialogV039):
    def __init__(self, window):
        super().__init__(window)
        dark = bool(getattr(window, 'dark', False))
        self.pages_mode = self._replace_select(
            self.pages_mode,
            LexumiSelect([('All pages', 'all'), ('Current page', 'current'), ('Custom range', 'custom')], dark, self),
            self.mode_changed,
        )
        self.pages_per_sheet_combo = self._replace_select(
            self.pages_per_sheet_combo,
            LexumiSelect([('1', 1), ('2', 2), ('4', 4), ('6', 6)], dark, self),
            self.rebuild_preview,
        )
        self.scale_mode = self._replace_select(
            self.scale_mode,
            LexumiSelect([('Fit to paper', 'fit'), ('Actual size', 'actual'), ('Custom', 'custom')], dark, self),
            self.scale_changed,
        )
        self.apply_lexumi_style()
        self.rebuild_preview()

    def _replace_select(self, old_widget, new_widget, slot):
        layout = old_widget.parentWidget().layout()
        layout.replaceWidget(old_widget, new_widget)
        old_widget.hide()
        old_widget.deleteLater()
        new_widget.currentIndexChanged.connect(slot)
        return new_widget

    def apply_lexumi_style(self):
        super().apply_lexumi_style()
        dark = bool(getattr(self.window, 'dark', False))
        if dark:
            panel, ink, border, input_bg, accent = '#1d232b', '#eef2f7', '#3b4654', '#252d37', '#3aa675'
        else:
            panel, ink, border, input_bg, accent = '#f8f6f1', '#24332d', '#d6ddd4', '#ffffff', '#11875d'
        self.setStyleSheet(self.styleSheet() + f'''
            QPushButton#printSelect {{
                background:{input_bg}; color:{ink}; border:1px solid {border}; border-radius:11px;
                padding:8px 12px 8px 14px; min-height:26px; text-align:left; font-size:14px; font-weight:400;
            }}
            QPushButton#printSelect:hover {{ border-color:{accent}; background:{input_bg}; }}
            QPushButton#printSelect:pressed {{ border-color:{accent}; background:{panel}; }}
            QMenu#printSelectMenu {{
                background:{input_bg}; color:{ink}; border:1px solid {border}; border-radius:10px;
                padding:6px; font-size:14px;
            }}
            QMenu#printSelectMenu::item {{ min-height:26px; padding:7px 14px; border-radius:7px; margin:1px 0; }}
            QMenu#printSelectMenu::item:selected {{ background:{accent}; color:white; }}
        ''')

    def selected_pages(self) -> list[int]:
        mode = self.pages_mode.currentIndex()
        if mode == 1:
            return [self.window.page]
        if mode == 2:
            return parse_page_range(self.range_edit.text(), self.window.meta['count'])
        return list(range(self.window.meta['count']))

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


class WindowV0310Mixin(WindowV039Mixin):
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
        orientation = QPageLayout.Orientation.Landscape if landscape_for_pages_per_sheet(self.print_pages_per_sheet) else QPageLayout.Orientation.Portrait
        self.printer.setPageOrientation(orientation)
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            self.printer = None
            return
        if self.printer.pageOrder() == QPrinter.PageOrder.LastPageFirst:
            self.print_groups.reverse()
        if not self.printer.supportsMultipleCopies():
            copies = max(1, self.printer.copyCount())
            self.print_groups = self.print_groups * copies if self.printer.collateCopies() else [group for group in self.print_groups for _ in range(copies)]
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

    def about(self):
        QMessageBox.about(
            self, 'About Lexumi',
            'Lexumi 0.3.10\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ / CBR · images\n\n'
            'Continuous scrolling, embedded ebook covers, two-page spreads, text search, bookmarks, '
            'multi-sheet print preview, N-up printing, open-ended print ranges, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre, libarchive.\nAGPL-3.0-or-later.'
        )
