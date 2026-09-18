from .ui_shared import *


class WindowCommandsMixin:
    def bookmark(self):
        if self.meta:
            self.library.toggle_bookmark(self.meta['path'], self.page)
            self.refresh_marks()
            self.statusBar().showMessage('Bookmarks updated')

    def refresh_marks(self):
        self.marks.clear()
        if self.meta:
            for row in self.library.bookmarks(self.meta['path']):
                item = QListWidgetItem(row['label'])
                item.setData(Qt.ItemDataRole.UserRole, row['page'])
                self.marks.addItem(item)

    def book_menu(self, point):
        item = self.books.itemAt(point)
        if not item:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        menu.addAction('Open', lambda: self.open_path(path))
        menu.addAction('Remove from Library', lambda: self.remove_book(path))
        menu.exec(self.books.mapToGlobal(point))

    def remove_book(self, path):
        self.library.remove(path)
        self.refresh_library()
        self.refresh_marks()
        self.statusBar().showMessage('Removed from the library. The original book file was not deleted.')

    def show_text(self):
        if not self.meta or self.working or self.opening:
            return

        def done(response):
            if 'error' in response:
                self.error(response['error'])
                return
            from PySide6.QtWidgets import QPlainTextEdit
            dialog = QDialog(self)
            dialog.setWindowTitle('Page text — select and copy')
            dialog.resize(700, 600)
            layout = QVBoxLayout(dialog)
            text = QPlainTextEdit(response['result'] or 'This page has no text layer.')
            text.setReadOnly(True)
            layout.addWidget(text)
            close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            close.rejected.connect(dialog.reject)
            layout.addWidget(close)
            dialog.exec()

        self.engine.request('text', done, page=self.page)

    def export_pdf(self):
        if not self.meta or self.opening or self.working or getattr(self, 'export_in_progress', False):
            return
        default_name = Path(self.meta['path']).stem + '-export.pdf'
        target, _ = QFileDialog.getSaveFileName(
            self, 'Export as PDF', str(Path.home() / default_name), 'PDF document (*.pdf)'
        )
        if not target:
            return
        if not target.lower().endswith('.pdf'):
            target += '.pdf'

        source_path = self.meta['path']
        source_password = getattr(self, 'current_password', '')
        self.export_in_progress = True
        self.export_button.setEnabled(False)
        self.export_pdf_action.setEnabled(False)
        message = 'Exporting PDF in the background…'
        if self.meta.get('djvu'):
            message = 'Exporting DjVu to an optimized PDF in the background…'
        self.statusBar().showMessage(message + ' You can keep reading while it finishes.')

        worker = EngineClient(self)
        self.export_engine = worker

        def finish(response):
            if getattr(self, 'export_engine', None) is worker:
                self.export_engine = None
            worker.stop()
            worker.deleteLater()
            self.export_in_progress = False
            self.export_button.setEnabled(True)
            self.export_pdf_action.setEnabled(True)
            if 'error' in response:
                self.error(response['error'])
                return
            size_mb = Path(target).stat().st_size / (1024 * 1024) if Path(target).exists() else 0
            self.statusBar().showMessage(f'PDF saved: {target} · {size_mb:.1f} MB')

        def opened(response):
            if 'error' in response:
                finish(response)
                return
            worker.request('export', finish, target=target)

        worker.request('open', opened, path=source_path, password=source_password)

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

        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.printer.setResolution(200)
        self.printer.setDocName(self.meta['title'])
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec() != QPrintDialog.DialogCode.Accepted:
            self.printer = None
            return

        self.print_pages = list(selected_pages)
        if self.printer.pageOrder() == QPrinter.PageOrder.LastPageFirst:
            self.print_pages.reverse()
        if not self.printer.supportsMultipleCopies():
            copies = self.printer.copyCount()
            self.print_pages = (
                self.print_pages * copies if self.printer.collateCopies()
                else [p for p in self.print_pages for _ in range(copies)]
            )

        self.painter = QPainter()
        if not self.painter.begin(self.printer):
            self.painter = self.printer = None
            self.error('Could not start printing.')
            return

        self.working = True
        self.print_index = 0
        self.print_progress = QProgressDialog('Printing pages…', 'Cancel', 0, len(self.print_pages), self)
        self.print_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.print_progress.show()
        self.print_next()

    def print_next(self):
        if self.print_progress.wasCanceled() or self.print_index >= len(self.print_pages):
            self.finish_print(self.print_progress.wasCanceled())
            return
        page = self.print_pages[self.print_index]

        def done(response):
            if 'error' in response:
                self.finish_print(True)
                self.error(response['error'])
                return
            if self.print_progress.wasCanceled():
                self.finish_print(True)
                return
            if self.print_index and not self.printer.newPage():
                self.finish_print(True)
                self.error('The printer did not accept the next page.')
                return
            image = QImage.fromData(base64.b64decode(response['result']['image']))
            viewport = self.printer.pageLayout().paintRectPixels(self.printer.resolution())
            ratio = min(viewport.width() / image.width(), viewport.height() / image.height())
            w, h = image.width() * ratio, image.height() * ratio
            self.painter.drawImage(QRectF((viewport.width() - w) / 2, (viewport.height() - h) / 2, w, h), image)
            self.print_index += 1
            self.print_progress.setValue(self.print_index)
            QTimer.singleShot(0, self.print_next)

        self.engine.request('render', done, page=page, width=2200)

    def finish_print(self, cancelled):
        if cancelled:
            self.printer.abort()
        self.painter.end()
        self.painter = self.printer = None
        self.print_progress.close()
        self.working = False
        self.statusBar().showMessage('Printing cancelled' if cancelled else 'Pages sent to the printer')

    def toggle_theme(self):
        self.dark = not self.dark
        self.apply_style()

    def fullscreen(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def error(self, message):
        self.statusBar().showMessage('Operation failed')
        QMessageBox.warning(self, 'Lexumi', message)

    def about(self):
        QMessageBox.about(
            self, 'About Lexumi',
            'Lexumi 0.3.2\nOffline ebook & document reader for macOS Apple Silicon.\n\n'
            'PDF · DjVu · EPUB · FB2 / FB2.ZIP · MOBI / PRC\nTXT · XPS / OXPS · CBZ · images\n\n'
            'Continuous scrolling, text search, bookmarks, print preview, and PDF export.\n'
            'OCR and DRM are not supported.\n\nPySide6 / Qt, PyMuPDF, DjVuLibre.\nAGPL-3.0-or-later.'
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.add_paths([u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()])

    def keyPressEvent(self, event):
        if self.meta and self.stack.currentIndex() == 1 and not isinstance(self.focusWidget(), QLineEdit):
            if event.key() in (Qt.Key.Key_Right, Qt.Key.Key_Down):
                self.go(self.page + 1)
                event.accept()
                return
            if event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Up):
                self.go(self.page - 1)
                event.accept()
                return
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(160)

    def closeEvent(self, event):
        if getattr(self, 'export_in_progress', False):
            self.statusBar().showMessage('PDF export is still running. Wait for it to finish before closing Lexumi.')
            event.ignore()
            return
        if self.working:
            self.statusBar().showMessage('Wait for the current operation to finish. Printing can be cancelled in its progress window.')
            event.ignore()
            return
        self.engine.stop()
        self.library.close()
        event.accept()
