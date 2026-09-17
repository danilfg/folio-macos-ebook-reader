from .ui_shared import *


class WindowReaderMixin:
    def zoom_width_for_page(self, page_index):
        sizes = self.meta.get('page_sizes') or [[595.0, 842.0]] * self.meta['count']
        src_w, src_h = sizes[min(page_index, len(sizes) - 1)]
        src_w = max(1.0, float(src_w))
        src_h = max(1.0, float(src_h))
        mode = self.zoom.currentText()
        viewport_w = max(320, self.scroll.viewport().width() - 58)
        viewport_h = max(320, self.scroll.viewport().height() - 40)
        if mode == 'Fit Width':
            return viewport_w
        if mode == 'Fit Page':
            return min(viewport_w, viewport_h * src_w / src_h)
        return max(240, 595 * int(mode[:-1]) / 100)

    def refresh_page_geometry(self, *_):
        if not self.meta or not self.page_labels:
            return
        self.render_generation += 1
        self.pending_pages.clear()
        self.rendered_signature.clear()
        self.render_busy = False
        max_w = 0
        sizes = self.meta.get('page_sizes') or [[595.0, 842.0]] * self.meta['count']
        for i, label in enumerate(self.page_labels):
            src_w, src_h = sizes[min(i, len(sizes) - 1)]
            width = self.zoom_width_for_page(i)
            height = width * max(1.0, float(src_h)) / max(1.0, float(src_w))
            has_image = label.pixmap() is not None and not label.pixmap().isNull()
            label.setFixedSize(round(width), max(120, round(height)))
            if not has_image:
                label.reset_placeholder()
            max_w = max(max_w, round(width))
        self.pages_container.setMinimumWidth(max_w + 56)
        self.pages_layout.activate()
        self.zoom_footer_label.setText(self.zoom.currentText())
        QTimer.singleShot(0, self.render_visible_pages)

    def set_zoom(self, value):
        idx = self.zoom.findText(value)
        if idx >= 0:
            self.zoom.setCurrentIndex(idx)

    def zoom_step(self, direction):
        values = ['50%', '67%', '75%', '90%', '100%', '110%', '125%', '150%', '175%', '200%', '250%', '300%']
        current = self.zoom.currentText()
        if current not in values:
            current = '100%'
        index = values.index(current)
        index = max(0, min(len(values) - 1, index + direction))
        self.set_zoom(values[index])

    def go(self, page, force=False):
        if not self.meta or page is None or self.opening or self.working:
            return
        page = max(0, min(int(page), self.meta['count'] - 1))
        self.page = page
        self.page_spin.blockSignals(True)
        self.page_spin.setValue(page + 1)
        self.page_spin.blockSignals(False)
        self.page_label = self.page_labels[page] if self.page_labels else None
        if self.page_labels:
            self.pages_layout.activate()
            y = max(0, self.page_labels[page].geometry().top() - 18)
            self.scroll.verticalScrollBar().setValue(y)
        self.library.opened(self.meta['path'], page)
        self.refresh_library()
        self.render_visible_pages()

    def on_scroll(self, *_):
        if not self.meta or not self.page_labels:
            return
        self.update_current_page_from_scroll()
        self.scroll_timer.start(45)

    def update_current_page_from_scroll(self):
        top = self.scroll.verticalScrollBar().value()
        bottom = top + self.scroll.viewport().height()
        best_page = self.page
        best_overlap = -1
        for i, label in enumerate(self.page_labels):
            geom = label.geometry()
            overlap = max(0, min(bottom, geom.bottom()) - max(top, geom.top()))
            if overlap > best_overlap:
                best_overlap = overlap
                best_page = i
            if geom.top() > bottom and best_overlap >= 0:
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
        if not self.page_labels:
            return []
        top = self.scroll.verticalScrollBar().value()
        bottom = top + self.scroll.viewport().height()
        visible = []
        for i, label in enumerate(self.page_labels):
            geom = label.geometry()
            if geom.bottom() >= top and geom.top() <= bottom:
                visible.append(i)
            elif visible and geom.top() > bottom:
                break
        if not visible:
            visible = [self.page]
        start = max(0, visible[0] - 1)
        end = min(len(self.page_labels) - 1, visible[-1] + 1)
        return list(range(start, end + 1))

    def invalidate_visible_renders(self):
        self.render_generation += 1
        for i in self.visible_pages():
            self.rendered_signature.pop(i, None)
            if i < len(self.page_labels):
                self.page_labels[i].reset_placeholder()
        self.pending_pages.clear()
        self.render_busy = False
        self.render_visible_pages()

    def render(self, *_):
        self.render_visible_pages()

    def render_visible_pages(self):
        if not self.meta or self.opening or self.working or not self.page_labels:
            return
        wanted = self.visible_pages()
        wanted_set = set(wanted)
        query = self.search.text() if self.search_bar.isVisible() else ''
        ratio = self.devicePixelRatioF()

        for i, label in enumerate(self.page_labels):
            if i not in wanted_set and min(abs(i - p) for p in wanted) > 3 and label.pixmap() is not None:
                label.reset_placeholder()
                self.rendered_signature.pop(i, None)

        for page in wanted:
            label = self.page_labels[page]
            width = max(160, label.width())
            signature = (width, query)
            if self.rendered_signature.get(page) == signature or page in self.pending_pages:
                continue
            token = self.render_generation
            generation = self.generation
            self.pending_pages.add(page)
            self.render_busy = True

            def done(response, page=page, width=width, signature=signature, token=token, generation=generation, ratio=ratio):
                self.pending_pages.discard(page)
                self.render_busy = bool(self.pending_pages)
                if generation != self.generation or token != self.render_generation or page >= len(self.page_labels):
                    return
                if 'error' in response:
                    if page == self.page:
                        self.error(response['error'])
                    return
                label = self.page_labels[page]
                if label.width() != width:
                    return
                result = response['result']
                image = QImage.fromData(base64.b64decode(result['image']))
                pix = QPixmap.fromImage(image).scaled(
                    max(1, round(label.width() * ratio)), max(1, round(label.height() * ratio)),
                    Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                pix.setDevicePixelRatio(ratio)
                label.setText('')
                label.setPixmap(pix)
                label.matches = result['matches']
                label.update()
                self.rendered_signature[page] = signature
                if page == self.page:
                    self.page_label = label
                self.update_status()

            self.engine.request('render', done, page=page, width=int(width * ratio), query=query)
        self.update_status()

    def update_status(self):
        if not self.meta:
            return
        suffix = 'FB2.ZIP' if self.meta['path'].lower().endswith('.fb2.zip') else Path(self.meta['path']).suffix[1:].upper()
        self.statusBar().showMessage(
            f'{suffix}  ·  Page {self.page + 1} of {self.meta["count"]}  ·  Scroll to read   ⌘F search   ⌘P print'
        )

    def focus_search(self):
        self.search_bar.show()
        self.search.setFocus()
        self.search.selectAll()

    def hide_search(self):
        self.search_bar.hide()
        self.last_query = ''
        self.invalidate_visible_renders()

    def find(self):
        query = self.search.text().strip()
        if not query or not self.meta or self.working or self.opening:
            return
        start = (self.page + 1) if query == self.last_query else self.page
        self.last_query = query
        self.working = True
        self.statusBar().showMessage('Searching text… Large DjVu files can take longer.')

        def done(response):
            self.working = False
            if 'error' in response:
                self.error(response['error'])
            elif response['result'] is None:
                self.statusBar().showMessage('Text not found. Scanned books need an embedded text layer; Folio does not run OCR.')
            else:
                self.invalidate_visible_renders()
                self.go(response['result'])

        self.engine.request('find', done, query=query, start=start)
