from __future__ import annotations

from PySide6.QtCore import QByteArray, QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMessageBox, QToolBar, QToolButton, QWidget

from .ui_shared import PageLabel


def two_page_icon(size=22):
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"
        fill="none" stroke="#567064" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="5" width="8" height="14" rx="1.5"/>
        <rect x="13" y="5" width="8" height="14" rx="1.5"/>
        <path d="M12 6v12"/>
    </svg>'''
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


class WindowV037Mixin:
    """v0.3.7: optional two-page spread layout with spread-aware zoom/navigation."""

    def build_ui(self):
        if not hasattr(self, 'two_page_mode'):
            self.two_page_mode = False
        self.page_rows = {}
        self._programmatic_scroll = False
        super().build_ui()

        bar = self.findChild(QToolBar, 'MainToolbar')
        self.two_page_button = QToolButton()
        self.two_page_button.setIcon(two_page_icon())
        self.two_page_button.setToolTip('Two-page spread')
        self.two_page_button.setCheckable(True)
        self.two_page_button.setChecked(self.two_page_mode)
        self.two_page_button.toggled.connect(self.toggle_two_page_mode)

        before_action = None
        if bar is not None:
            for action in bar.actions():
                if bar.widgetForAction(action) is self.zoom_menu_button:
                    before_action = action
                    break
            if before_action is not None:
                bar.insertWidget(before_action, self.two_page_button)
            else:
                bar.addWidget(self.two_page_button)

        self.two_page_menu_action = QAction('Two-page spread', self)
        self.two_page_menu_action.setCheckable(True)
        self.two_page_menu_action.setChecked(self.two_page_mode)
        self.two_page_menu_action.setShortcut('Ctrl+Shift+2')
        self.two_page_menu_action.toggled.connect(self.toggle_two_page_mode)
        self.addAction(self.two_page_menu_action)

        for top_action in self.menuBar().actions():
            menu = top_action.menu()
            if menu and top_action.text().replace('&', '') == 'View':
                menu.addSeparator()
                menu.addAction(self.two_page_menu_action)
                break

        self._rewire_spread_navigation()
        self._style_two_page_button()

    def _rewire_spread_navigation(self):
        for action, callback in (
            (getattr(self, 'prev_action', None), self.go_previous_display),
            (getattr(self, 'next_action', None), self.go_next_display),
        ):
            if action is None:
                continue
            try:
                action.triggered.disconnect()
            except (TypeError, RuntimeError):
                pass
            action.triggered.connect(callback)

        for action in self.actions():
            text = action.text()
            if text == 'Previous page with Up Arrow':
                try:
                    action.triggered.disconnect()
                except (TypeError, RuntimeError):
                    pass
                action.triggered.connect(self.go_previous_display)
            elif text == 'Next page with Down Arrow':
                try:
                    action.triggered.disconnect()
                except (TypeError, RuntimeError):
                    pass
                action.triggered.connect(self.go_next_display)

    def _style_two_page_button(self):
        if not hasattr(self, 'two_page_button'):
            return
        if self.dark:
            checked_bg, checked_border = '#294437', '#5ea381'
        else:
            checked_bg, checked_border = '#dfeee4', '#2f7a59'
        self.two_page_button.setStyleSheet(
            'QToolButton::menu-indicator { image: none; width: 0px; height: 0px; }'
            f'QToolButton:checked {{ background:{checked_bg}; border-color:{checked_border}; }}'
        )

    def apply_style(self):
        super().apply_style()
        self._style_two_page_button()

    def spread_gap(self):
        return 18

    def spread_start(self, page):
        return max(0, int(page) - (int(page) % 2))

    def toggle_two_page_mode(self, checked=None):
        target = (not self.two_page_mode) if checked is None else bool(checked)
        if target == self.two_page_mode:
            self._sync_two_page_controls()
            return

        anchor_page = self.page
        cached = {}
        for index, label in enumerate(getattr(self, 'page_labels', [])):
            pix = label.pixmap()
            if pix is not None and not pix.isNull():
                cached[index] = pix.copy()

        self.two_page_mode = target
        self._sync_two_page_controls()

        if self.meta:
            self.build_page_placeholders(cached)
            QTimer.singleShot(0, lambda p=anchor_page: self.go(p, force=True))
        self.update_status()

    def _sync_two_page_controls(self):
        for control in (
            getattr(self, 'two_page_button', None),
            getattr(self, 'two_page_menu_action', None),
        ):
            if control is None:
                continue
            control.blockSignals(True)
            control.setChecked(self.two_page_mode)
            control.blockSignals(False)

    def clear_pages(self):
        while self.pages_layout.count():
            item = self.pages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.page_labels = []
        self.page_label = None
        self.page_rows = {}
        self.pending_pages.clear()
        self.rendered_signature.clear()
        self.render_busy = False

    def _restore_cached_pixmap(self, label, cached_pixmaps, index):
        pix = (cached_pixmaps or {}).get(index)
        if pix is not None and not pix.isNull():
            label.setText('')
            label.setPixmap(pix)

    def build_page_placeholders(self, cached_pixmaps=None):
        self.clear_pages()
        count = self.meta['count']

        if self.two_page_mode:
            for start in range(0, count, 2):
                row = QWidget()
                row.setObjectName('pageSpreadRow')
                row.setStyleSheet('QWidget#pageSpreadRow { background: transparent; border: 0; }')
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(self.spread_gap())
                row_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                for index in range(start, min(start + 2, count)):
                    label = PageLabel(index)
                    self._restore_cached_pixmap(label, cached_pixmaps, index)
                    self.page_labels.append(label)
                    self.page_rows[index] = row
                    row_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)
                self.pages_layout.addWidget(row, 0, Qt.AlignmentFlag.AlignHCenter)
        else:
            for index in range(count):
                label = PageLabel(index)
                self._restore_cached_pixmap(label, cached_pixmaps, index)
                self.page_labels.append(label)
                self.page_rows[index] = label
                self.pages_layout.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.refresh_page_geometry()

    def zoom_width_for_page(self, page_index):
        if not self.two_page_mode:
            return super().zoom_width_for_page(page_index)

        sizes = self.meta.get('page_sizes') or [[595.0, 842.0]] * self.meta['count']
        src_w, src_h = sizes[min(page_index, len(sizes) - 1)]
        src_w = max(1.0, float(src_w))
        src_h = max(1.0, float(src_h))
        mode = self.current_zoom_text()
        viewport_w = max(320, self.scroll.viewport().width() - 58)
        viewport_h = max(320, self.scroll.viewport().height() - 40)
        pair_width = max(160, (viewport_w - self.spread_gap()) / 2.0)

        if mode == 'Fit Width':
            return pair_width
        if mode == 'Fit Height':
            by_height = max(160, viewport_h * src_w / src_h)
            return min(pair_width, by_height)
        return max(160, 595 * int(mode[:-1]) / 100)

    def refresh_page_geometry(self, *_):
        if not self.meta or not self.page_labels:
            return
        if not self.two_page_mode:
            return super().refresh_page_geometry(*_)

        self.render_generation += 1
        self.pending_pages.clear()
        self.render_busy = False
        sizes = self.meta.get('page_sizes') or [[595.0, 842.0]] * self.meta['count']
        max_row_width = 0

        for index, label in enumerate(self.page_labels):
            src_w, src_h = sizes[min(index, len(sizes) - 1)]
            width = self.zoom_width_for_page(index)
            height = width * max(1.0, float(src_h)) / max(1.0, float(src_w))
            has_image = label.pixmap() is not None and not label.pixmap().isNull()
            label.setFixedSize(round(width), max(120, round(height)))
            if not has_image:
                label.reset_placeholder()

        for start in range(0, len(self.page_labels), 2):
            pair = self.page_labels[start:start + 2]
            row_width = sum(label.width() for label in pair)
            if len(pair) == 2:
                row_width += self.spread_gap()
            row = self.page_rows.get(start)
            if row is not None:
                row.setMinimumWidth(row_width)
                row.setFixedHeight(max(label.height() for label in pair))
                if row.layout() is not None:
                    row.layout().activate()
            max_row_width = max(max_row_width, row_width)

        self.pages_container.setMinimumWidth(max_row_width + 56)
        self.pages_layout.activate()
        self.sync_zoom_controls()
        self.render_debounce_timer.start(350)

    def _page_top(self, page):
        page = max(0, min(int(page), len(self.page_labels) - 1))
        if self.two_page_mode:
            row = self.page_rows.get(page) or self.page_rows.get(self.spread_start(page))
            if row is not None:
                return row.mapTo(self.pages_container, QPoint(0, 0)).y()
        label = self.page_labels[page]
        return label.mapTo(self.pages_container, QPoint(0, 0)).y()

    def go(self, page, force=False):
        if not self.meta or page is None or self.opening or self.working:
            return
        if not self.two_page_mode:
            return super().go(page, force)

        page = max(0, min(int(page), self.meta['count'] - 1))
        self.page = page
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page + 1)
        self.page_spin.blockSignals(False)
        self.page_label = self.page_labels[page] if self.page_labels else None

        if self.page_labels:
            self.pages_layout.activate()
            y = max(0, self._page_top(page) - 18)
            self._programmatic_scroll = True
            self.scroll.verticalScrollBar().setValue(y)
            self._programmatic_scroll = False

        self.library.opened(self.meta['path'], page)
        self.refresh_library()
        self.render_visible_pages()
        self.update_status()

    def go_next_display(self):
        if not self.meta:
            return
        if not self.two_page_mode:
            self.go(self.page + 1)
            return
        target = self.spread_start(self.page) + 2
        if target < self.meta['count']:
            self.go(target)

    def go_previous_display(self):
        if not self.meta:
            return
        if not self.two_page_mode:
            self.go(self.page - 1)
            return
        target = self.spread_start(self.page) - 2
        if target >= 0:
            self.go(target)

    def keyPressEvent(self, event):
        if (
            self.two_page_mode
            and self.meta
            and self.stack.currentIndex() == 1
            and not isinstance(self.focusWidget(), QLineEdit)
        ):
            if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
                self.go_next_display()
                event.accept()
                return
            if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                self.go_previous_display()
                event.accept()
                return
        super().keyPressEvent(event)

    def on_scroll(self, *_):
        if self.two_page_mode and self._programmatic_scroll:
            return
        return super().on_scroll(*_)

    def update_current_page_from_scroll(self):
        if not self.two_page_mode:
            return super().update_current_page_from_scroll()
        if not self.page_labels:
            return

        top = self.scroll.verticalScrollBar().value()
        bottom = top + self.scroll.viewport().height()
        best_page = self.spread_start(self.page)
        best_overlap = -1

        for start in range(0, len(self.page_labels), 2):
            row = self.page_rows.get(start)
            if row is None:
                continue
            row_top = row.mapTo(self.pages_container, QPoint(0, 0)).y()
            row_bottom = row_top + row.height()
            overlap = max(0, min(bottom, row_bottom) - max(top, row_top))
            if overlap > best_overlap:
                best_overlap = overlap
                best_page = start
            if row_top > bottom and best_overlap >= 0:
                break

        if best_page != self.page:
            self.page = best_page
            self.page_label = self.page_labels[best_page]
            self.page_spin.blockSignals(True)
            self.page_spin.setValue(best_page + 1)
            self.page_spin.blockSignals(False)
            self.library.opened(self.meta['path'], best_page)
            self.refresh_library()
        self.update_status()

    def visible_pages(self):
        if not self.two_page_mode:
            return super().visible_pages()
        if not self.page_labels:
            return []

        top = self.scroll.verticalScrollBar().value()
        bottom = top + self.scroll.viewport().height()
        visible_starts = []

        for start in range(0, len(self.page_labels), 2):
            row = self.page_rows.get(start)
            if row is None:
                continue
            row_top = row.mapTo(self.pages_container, QPoint(0, 0)).y()
            row_bottom = row_top + row.height()
            if row_bottom >= top and row_top <= bottom:
                visible_starts.append(start)
            elif visible_starts and row_top > bottom:
                break

        if not visible_starts:
            visible_starts = [self.spread_start(self.page)]

        first = max(0, visible_starts[0] - 2)
        last = min(len(self.page_labels) - 1, visible_starts[-1] + 3)
        return list(range(first, last + 1))

    def update_status(self):
        if not self.meta or not self.two_page_mode:
            return super().update_status()
        start = self.spread_start(self.page)
        end = min(start + 1, self.meta['count'] - 1)
        suffix = self._display_ext(self.meta['path']) if hasattr(self, '_display_ext') else 'BOOK'
        if start == end:
            page_text = f'Page {start + 1} of {self.meta["count"]}'
        else:
            page_text = f'Pages {start + 1}–{end + 1} of {self.meta["count"]}'
        self.statusBar().showMessage(
            f'{suffix}  ·  {page_text}  ·  Two-page spread   ⌘F search   ⌘P print'
        )

    def about(self):
        QMessageBox.about(
            self,
            'About Lexumi',
            'Lexumi 0.3.7\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\n'
            'TXT · XPS / OXPS · CBZ / CBR · images\n\n'
            'Continuous scrolling, one-page and two-page reading, ebook covers with first-page fallback, '
            'text search, bookmarks, print preview, and PDF export.\n'
            'OCR and DRM are not supported.\n\n'
            'PySide6 / Qt, PyMuPDF, DjVuLibre, libarchive.\nAGPL-3.0-or-later.'
        )
