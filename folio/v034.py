from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal, QTimer
from PySide6.QtWidgets import QListWidgetItem, QMessageBox, QToolButton

from .ui_shared import BookListItemWidget, line_icon


class CompactBookRow(BookListItemWidget):
    openRequested = Signal()
    removeRequested = Signal()

    def __init__(self, title: str, meta: str, ext: str, dark: bool = False):
        super().__init__(title, meta, ext, dark)
        self.setObjectName('bookListCard')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(86)
        self.layout().setContentsMargins(8, 7, 7, 7)
        self.layout().setSpacing(10)
        self.thumb.setFixedSize(48, 64)

        self.remove_button = QToolButton()
        self.remove_button.setObjectName('compactBookRemove')
        self.remove_button.setIcon(line_icon('close', 14))
        self.remove_button.setIconSize(QSize(14, 14))
        self.remove_button.setFixedSize(24, 24)
        self.remove_button.setToolTip('Remove from Library')
        self.remove_button.clicked.connect(self.removeRequested.emit)
        self.remove_button.setCursor(Qt.CursorShape.ArrowCursor)
        self.layout().addWidget(self.remove_button, 0, Qt.AlignmentFlag.AlignTop)
        self.apply_state()

    def set_preview(self, pixmap, fallback: str = ''):
        if pixmap is not None and not pixmap.isNull():
            scaled = pixmap.scaled(
                44,
                60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumb.setPixmap(scaled)
            self.thumb.setText('')
        else:
            self.thumb.setPixmap(type(self.thumb.pixmap())()) if self.thumb.pixmap() is not None else self.thumb.clear()
            self.thumb.setText(fallback)

    def apply_state(self):
        if self.dark:
            title = '#eef2f7'
            meta = '#a5b2c4'
            thumb_bg = '#131820'
            thumb_border = '#3a4656'
            selected_bg = '#243b32'
            selected_border = '#55b78a'
            remove_hover = '#3d3035'
        else:
            title = '#24332d'
            meta = '#6f7872'
            thumb_bg = '#eef2ed'
            thumb_border = '#d5ded6'
            selected_bg = '#e2f0e7'
            selected_border = '#18845f'
            remove_hover = '#f3e5e5'

        bg = selected_bg if self.selected else 'transparent'
        border = selected_border if self.selected else 'transparent'
        self.setStyleSheet(
            f"QWidget#bookListCard{{background:{bg};border:1px solid {border};border-radius:14px;}}"
            f"QLabel#bookListThumb{{background:{thumb_bg};border:1px solid {thumb_border};border-radius:9px;padding:2px;color:{meta};font-size:9px;font-weight:600;}}"
            f"QLabel#bookListTitle{{background:transparent;border:0;color:{title};font-size:13px;font-weight:600;}}"
            f"QLabel#bookListMeta{{background:transparent;border:0;color:{meta};font-size:11px;}}"
            f"QToolButton#compactBookRemove{{background:transparent;border:0;border-radius:12px;padding:3px;}}"
            f"QToolButton#compactBookRemove:hover{{background:{remove_hover};border:0;}}"
        )

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.openRequested.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class WindowV034Mixin:
    """Small UX layer for v0.3.4, kept separate from the stable reader core."""

    def build_ui(self):
        super().build_ui()
        self.tabs.setTabText(1, 'Contents')
        self.zoom_menu_button.setStyleSheet(
            'QToolButton::menu-indicator { image: none; width: 0px; height: 0px; }'
        )

    def apply_style(self):
        super().apply_style()
        if self.dark:
            ink = '#e7e9ef'
            muted = '#a2adbd'
            selected_bg = '#294437'
            hover = '#2a313b'
        else:
            ink = '#24332d'
            muted = '#7b837e'
            selected_bg = '#dfeee4'
            hover = '#f2f6f1'
        self.tabs.tabBar().setStyleSheet(
            'QTabBar::tab {'
            f'color:{muted}; background:transparent; border:0; border-radius:13px; '
            'padding:7px 11px; margin-right:5px; min-width:0;'
            '}'
            'QTabBar::tab:hover {'
            f'background:{hover}; color:{ink}; border:0;'
            '}'
            'QTabBar::tab:selected {'
            f'background:{selected_bg}; color:{ink}; border:0; font-weight:600;'
            '}'
        )
        self.zoom_menu_button.setStyleSheet(
            self.zoom_menu_button.styleSheet()
            + 'QToolButton::menu-indicator { image: none; width: 0px; height: 0px; }'
        )
        self.update_book_row_styles()

    def refresh_library(self, *_):
        from pathlib import Path

        self.books.clear()
        current_path = self.meta['path'] if self.meta else None
        for row in self.library.all(self.filter.text()):
            ext = 'FB2.ZIP' if row['path'].lower().endswith('.fb2.zip') else Path(row['path']).suffix[1:].upper()
            progress = f'Page {row["page"] + 1} / {row["total"]}' if row['total'] else 'Not opened yet'
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, row['path'])
            item.setToolTip(row['path'] + '\nClick to open')
            item.setSizeHint(QSize(0, 92))
            self.books.addItem(item)

            row_widget = CompactBookRow(row['title'], f'{ext}  ·  {progress}', ext, self.dark)
            row_widget.set_preview(self.book_previews.get(row['path']), ext)
            row_widget.set_selected(row['path'] == current_path, self.dark)
            row_widget.openRequested.connect(
                lambda p=row['path'], i=item: self.open_book_from_library(p, i)
            )
            row_widget.removeRequested.connect(lambda p=row['path']: self.remove_book(p))
            self.books.setItemWidget(item, row_widget)

    def open_book_from_library(self, path: str, item: QListWidgetItem):
        self.books.setCurrentItem(item)
        self.update_book_row_styles()
        if not self.meta or self.meta['path'] != path:
            self.open_path(path)

    def update_book_row_styles(self):
        current_path = self.meta['path'] if self.meta else None
        selected_item = self.books.currentItem()
        for index in range(self.books.count()):
            item = self.books.item(index)
            widget = self.books.itemWidget(item)
            if not isinstance(widget, CompactBookRow):
                continue
            path = item.data(Qt.ItemDataRole.UserRole)
            selected = path == current_path or (selected_item is item and current_path is None)
            widget.set_selected(selected, self.dark)

    def set_zoom(self, value):
        anchor_page = self.page
        if self.meta and self.page_labels:
            self.update_current_page_from_scroll()
            anchor_page = self.page
        if value == getattr(self, 'zoom_value', None):
            self.sync_zoom_controls()
            if value == 'Fit Height' and self.meta:
                QTimer.singleShot(0, lambda p=anchor_page: self.go(p, force=True))
            return
        self.zoom_value = value
        self.refresh_page_geometry()
        if value == 'Fit Height' and self.meta:
            QTimer.singleShot(0, lambda p=anchor_page: self.go(p, force=True))

    def about(self):
        QMessageBox.about(
            self,
            'About Folio',
            'Folio 0.3.4\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ · images\n\n'
            'Continuous scrolling, text search, bookmarks, print preview, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre.\nAGPL-3.0-or-later.'
        )
