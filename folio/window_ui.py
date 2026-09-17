from .ui_shared import *


class WindowUiMixin:
    def action(self, name, slot, shortcut=None, icon=None, tooltip=None):
        a = QAction(line_icon(icon) if icon else QIcon(), name, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(shortcut)
        a.setToolTip(tooltip or name)
        self.addAction(a)
        return a

    def add_toolbar_action(self, bar, name, slot, shortcut=None, icon=None, tooltip=None):
        act = self.action(name, slot, shortcut, icon, tooltip)
        bar.addAction(act)
        return act

    def _build_zoom_menu(self):
        menu = QMenu(self)
        self.zoom_actions = {}
        for value in ['Fit Width', 'Fit Height', *self.zoom_numeric_values]:
            action = menu.addAction(value, lambda checked=False, v=value: self.set_zoom(v))
            action.setCheckable(True)
            self.zoom_actions[value] = action
        self.zoom_menu = menu

    def show_zoom_menu(self):
        self.zoom_menu.adjustSize()
        pos = self.zoom_menu_button.mapToGlobal(QPoint(0, self.zoom_menu_button.height() + 4))
        self.zoom_menu.exec(pos)

    def sync_zoom_controls(self):
        current = getattr(self, 'zoom_value', 'Fit Width')
        if hasattr(self, 'zoom_actions'):
            for value, action in self.zoom_actions.items():
                action.setChecked(value == current)
        label = current if current in ('Fit Width', 'Fit Page') else current
        if hasattr(self, 'zoom_footer_label'):
            self.zoom_footer_label.setText(label)

    def build_ui(self):
        bar = self.addToolBar('Reader')
        bar.setMovable(False)
        bar.setObjectName('MainToolbar')
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        bar.setIconSize(QPixmap(20, 20).size())

        file_menu = self.menuBar().addMenu('File')
        open_action = self.action('Openâ€¦', self.choose_open, QKeySequence.StandardKey.Open, 'open', 'Open bookâ€¦')
        file_menu.addAction(open_action)
        bar.addAction(open_action)
        folder_action = self.action('Add folderâ€¦', self.import_folder, 'Ctrl+Shift+O')
        file_menu.addAction(folder_action)

        export_menu = file_menu.addMenu('Export asâ€¦')
        self.export_pdf_action = self.action('PDF documentâ€¦', self.export_pdf, 'Ctrl+Shift+S')
        export_menu.addAction(self.export_pdf_action)

        print_action = self.action('Printâ€¦', self.print_book, QKeySequence.StandardKey.Print, 'print', 'Print with previewâ€¦')
        file_menu.addAction(print_action)
        bar.addAction(print_action)
        file_menu.addSeparator()
        file_menu.addAction(self.action('Close Window', self.close, QKeySequence.StandardKey.Close))

        bar.addSeparator()
        self.prev_action = self.add_toolbar_action(bar, 'Previous page', lambda: self.go(self.page - 1), 'Left', 'prev', 'Previous page')
        self.page_spin = QSpinBox()
        self.page_spin.setObjectName('pageSpin')
        self.page_spin.setRange(1, 1)
        self.page_spin.setFixedWidth(68)
        self.page_spin.setKeyboardTracking(False)
        self.page_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.page_spin.valueChanged.connect(lambda x: self.go(x - 1))
        self.page_spin.setToolTip('Current page')
        bar.addWidget(self.page_spin)
        self.page_total = QLabel(' / â€”  ')
        bar.addWidget(self.page_total)
        self.next_action = self.add_toolbar_action(bar, 'Next page', lambda: self.go(self.page + 1), 'Right', 'next', 'Next page')
        self.action('Previous page with Up Arrow', lambda: self.go(self.page - 1), 'Up')
        self.action('Next page with Down Arrow', lambda: self.go(self.page + 1), 'Down')

        bar.addSeparator()
        self.fit_width_button = QToolButton()
        self.fit_width_button.setIcon(line_icon('fit_width'))
        self.fit_width_button.setToolTip('Fit page width')
        self.fit_width_button.clicked.connect(lambda: self.set_zoom('Fit Width'))
        bar.addWidget(self.fit_width_button)

        self.fit_height_button = QToolButton()
        self.fit_height_button.setIcon(line_icon('fit_page'))
        self.fit_height_button.setToolTip('Fit page height')
        self.fit_height_button.clicked.connect(lambda: self.set_zoom('Fit Height'))
        bar.addWidget(self.fit_height_button)

        self.zoom_menu_button = QToolButton()
        self.zoom_menu_button.setIcon(line_icon('search'))
        self.zoom_menu_button.setToolTip('Zoom')
        self.zoom_menu_button.clicked.connect(self.show_zoom_menu)
        bar.addWidget(self.zoom_menu_button)
        self._build_zoom_menu()

        bookmark_action = self.add_toolbar_action(bar, 'Bookmark', self.bookmark, 'Ctrl+D', 'bookmark', 'Add or remove bookmark')
        bar.addSeparator()

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(spacer)

        self.export_button = QToolButton()
        self.export_button.setIcon(line_icon('export'))
        self.export_button.setToolTip('Export PDF')
        self.export_button.clicked.connect(self.export_pdf)
        self.export_button.setAutoRaise(False)
        bar.addWidget(self.export_button)

        theme_action = self.add_toolbar_action(bar, 'Toggle theme', self.toggle_theme, 'Ctrl+Shift+L', 'theme', 'Toggle light / dark theme')

        view_menu = self.menuBar().addMenu('View')
        view_menu.addAction(self.action('Sidebar', lambda: self.sidebar.setVisible(not self.sidebar.isVisible()), 'Ctrl+B'))
        view_menu.addAction(self.action('Full Screen', self.fullscreen, 'Ctrl+Shift+F'))
        view_menu.addAction(self.action('Page Text', self.show_text, 'Ctrl+Shift+C'))
        view_menu.addSeparator()
        view_menu.addAction(self.action('Zoom In', lambda: self.zoom_step(1), 'Ctrl++'))
        view_menu.addAction(self.action('Zoom Out', lambda: self.zoom_step(-1), 'Ctrl+-'))
        view_menu.addAction(self.action('Actual Size', lambda: self.set_zoom('100%'), 'Ctrl+0'))
        view_menu.addAction(self.action('Fit Width', lambda: self.set_zoom('Fit Width')))
        view_menu.addAction(self.action('Fit Height', lambda: self.set_zoom('Fit Height')))

        help_menu = self.menuBar().addMenu('Help')
        help_menu.addAction(self.action('About Folio', self.about))

        self.splitter = QSplitter()
        self.sidebar = QWidget()
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 18, 12, 14)
        brand = QLabel('FOLIO')
        brand.setObjectName('brand')
        side.addWidget(brand)
        subtitle = QLabel('Your library. On your Mac.')
        subtitle.setObjectName('muted')
        side.addWidget(subtitle)
        side.addSpacing(10)

        self.tabs = QTabWidget()
        self.tabs.setObjectName('sidebarTabs')
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setUsesScrollButtons(False)
        lib = QWidget()
        lib_layout = QVBoxLayout(lib)
        lib_layout.setContentsMargins(0, 10, 0, 0)
        self.filter = QLineEdit()
        self.filter.setPlaceholderText('Search your library')
        self.filter.textChanged.connect(self.refresh_library)
        lib_layout.addWidget(self.filter)
        self.books = QListWidget()
        self.books.setWordWrap(True)
        self.books.setSpacing(8)
        self.books.itemClicked.c²È="25ÍÉ½±°¹Í•Ñ±¥¹µ•¹Ğ¡EĞ¹±¥¹µ•¹Ñ±…œ¹±¥¹!•¹Ñ•ÈğEĞ¹±¥¹µ•¹Ñ±…œ¹±¥¹Q½À¤(€€€€€€€Í•±˜¹ÍÉ½±°¹Í•Ñ]¥‘•ÑI•Í¥é…‰±”¡QÉÕ”¤(€€€€€€€Í•±˜¹ÍÉ½±°¹Í•Ñ=‰©•Ñ9…µ” Á…•É•„œ¤(€€€€€€€Í•±˜¹Á…•Í}½¹Ñ…¥¹•È€ôE]¥‘•Ğ ¤(€€€€€€€Í•±˜¹Á…•Í}½¹Ñ…¥¹•È¹Í•Ñ=‰©•Ñ9…µ” Á…•Í½¹Ñ…¥¹•Èœ¤(€€€€€€€Í•±˜¹Á…•Í}±…å½ÕĞ€ôEY	½á1…å½ÕĞ¡Í•±˜¹Á…•Í}½¹Ñ…¥¹•È¤(€€€€€€€Í•±˜¹Á…•Í}±…å½ÕĞ¹Í•Ñ½¹Ñ•¹ÑÍ5…É¥¹Ì ÈĞ°€ÈĞ°€ÈĞ°€ÈĞ¤(€€€€€€€Í•±˜¹Á…•Í}±…å½ÕĞ¹Í•ÑMÁ…¥¹œ Äà¤(€€€€€€€Í•±˜¹Á…•Í}±…å½ÕĞ¹Í•Ñ±¥¹µ•¹Ğ¡EĞ¹±¥¹µ•¹Ñ±…œ¹±¥¹!•¹Ñ•ÈğEĞ¹±¥¹µ•¹Ñ±…œ¹±¥¹Q½À¤(€€€€€€€Í•±˜¹ÍÉ½±°¹Í•Ñ]¥‘•Ğ¡Í•±˜¹Á…•Í}½¹Ñ…¥¹•È¤(€€€€€€€Í•±˜¹ÍÉ½±°¹Ù•ÉÑ¥…±MÉ½±±	…È ¤¹Ù…±Õ•¡…¹•¹½¹¹•Ğ¡Í•±˜¹½¹}ÍÉ½±°¤(€€€€€€€±…å½ÕĞ¹…‘‘]¥‘•Ğ¡Í•±˜¹ÍÑ…¬°€Ä¤(€€€€€€€Í•±˜¹ÍÑ…¬¹…‘‘]¥‘•Ğ¡Í•±˜¹ÍÉ½±°¤((€€€€€€€Í•±˜¹é½½µ}™½½Ñ•È€ôE]¥‘•Ğ ¤(€€€€€€€Í•±˜¹é½½µ}™½½Ñ•È¹Í•Ñ=‰©•Ñ9…µ” é½½µ½½Ñ•Èœ¤(€€€€€€€é±…å½ÕĞ€ôE!	½á1…å½ÕĞ¡Í•±˜¹é½½µ}™½½Ñ•È¤(€€€€€€€é±…å½ÕĞ¹Í•Ñ½¹Ñ•¹ÑÍ5…É¥¹Ì ÄÀ°€Ô°€ÄÈ°€Ô¤(€€€€€€€é±…å½ÕĞ¹…‘‘MÑÉ•Ñ  Ä¤(€€€€€€€™½½Ñ•É}™¥Ñ}İ¥‘Ñ €ôEQ½½±	ÕÑÑ½¸ ¤(€€€€€€€™½½Ñ•É}™¥Ñ}İ¥‘Ñ ¹Í•Ñ%½¸¡±¥¹•}¥½¸ ™¥Ñ}İ¥‘Ñ œ¤¤(€€€€€€€™½½Ñ•É}™¥Ñ}İ¥‘Ñ ¹Í•ÑQ½½±Q¥À ¥ĞÁ…”İ¥‘Ñ œ¤(€€€€€€€™½½Ñ•É}™¥Ñ}İ¥‘Ñ ¹±¥­•¹½¹¹•Ğ¡±…µ‰‘„èÍ•±˜¹Í•Ñ}é½½´ ¥Ğ]¥‘Ñ œ¤¤(€€€€€€€é±…å½ÕĞ¹…‘‘]¥‘•Ğ¡™½½Ñ•É}™¥Ñ}İ¥‘Ñ ¤(€€€€€€€™½½Ñ•É}™¥Ñ}¡•¥¡Ğ€ôEQ½½±	ÕÑÑ½¸ ¤(€€€€€€€™½½Ñ•É}™¥Ñ}¡•¥¡Ğ¹Í•Ñ%½¸¡±¥¹•}¥½¸ ™¥Ñ}Á…”œ¤¤(€€€€€€€™½½Ñ•É}™¥Ñ}¡•¥¡Ğ¹Í•ÑQ½½±Q¥À ¥ĞÁ…”¡•¥¡Ğœ¤(€€€€€€€™½½Ñ•É}™¥Ñ}¡•¥¡Ğ¹±¥­•¹½¹¹•Ğ¡±…µ‰‘„èÍ•±˜¹Í•Ñ}é½½´ ¥Ğ!•¥¡Ğœ¤¤(€€€€€€€é±…å½ÕĞ¹…‘‘]¥‘•Ğ¡™½½Ñ•É}™¥Ñ}¡•¥¡Ğ¤(€€€€€€€é½½µ}½ÕĞ€ôEQ½½±	ÕÑÑ½¸ ¤(€€€€€€€é½½µ}½ÕĞ¹Í•Ñ%½¸¡±¥¹•}¥½¸ é½½µ}½ÕĞœ¤¤(€€€€€€€é½½µ}½ÕĞ¹Í•ÑQ½½±Q¥À i½½´½ÕĞœ¤(€€€€€€€é½½µ}½ÕĞ¹±¥­•¹½¹¹•Ğ¡±…µ‰‘„èÍ•±˜¹é½½µ}ÍÑ•À ´Ä¤¤(€€€€€€€é±…å½ÕĞ¹…‘‘]¥‘•Ğ¡é½½µ}½ÕĞ¤(€€€€€€€Í•±˜¹é½½µ}™½½Ñ•É}±…‰•°€ôE1…‰•° ¥Ğ]¥‘Ñ œ¤(€€€€€€€Í•±˜¹é½½µ}™½½Ñ•É}±…‰•°¹Í•Ñ5¥¹¥µÕµ]¥‘Ñ  ÜÈ¤(€€€€€€€Í•±˜¹é½½µ}™½½Ñ•É}±…‰•°¹Í•Ñ±¥¹µ•¹Ğ¡EĞ¹±¥¹µ•¹Ñ±…œ¹±¥¹•¹Ñ•È¤(€€€€€€€é±…å½ÕĞ¹…‘‘]¥‘•Ğ¡Í•±˜¹é½½µ}™½½Ñ•É}±…‰•°¤(€€€€€€€é½½µ}¥¸€ôEQ½½±	ÕÑÑ½¸ ¤(€€€€€€€é½½µ}¥¸¹Í•Ñ%½¸¡±¥¹•}¥½¸ é½½µ}¥¸œ¤¤(€€€€€€€é½½µ}¥¸¹Í•ÑQ½½±Q¥À i½½´¥¸œ¤(€€€€€€€é½½µ}¥¸¹±¥­•¹½¹¹•Ğ¡±…µ‰‘„èÍ•±˜¹é½½µ}ÍÑ•À Ä¤¤(€€€€€€€é±…å½ÕĞ¹…‘‘]¥‘•Ğ¡é½½µ}¥¸¤(€€€€€€€±…å½ÕĞ¹…‘‘]¥‘•Ğ¡Í•±˜¹é½½µ}™½½Ñ•È¤(€€€€€€€Í•±˜¹é½½µ}™½½Ñ•È¹¡¥‘” ¤((€€€€€€€Í•±˜¹ÍÁ±¥ÑÑ•È¹…‘‘]¥‘•Ğ¡É¥¡Ğ¤(€€€€€€€Í•±˜¹ÍÁ±¥ÑÑ•È¹Í•ÑM¥é•Ì¡lÈäÀ°€ääÁt¤(€€€€€€€Í•±˜¹ÍÁ±¥ÑÑ•È¹ÍÁ±¥ÑÑ•É5½Ù•¹½¹¹•Ğ¡±…µ‰‘„€©|èÍ•±˜¹É•Í¥é•}Ñ¥µ•È¹ÍÑ…ÉĞ ÄÔÀ¤¤(€€€€€€€Í•±˜¹Í•Ñ•¹ÑÉ…±]¥‘•Ğ¡Í•±˜¹ÍÁ±¥ÑÑ•È¤(€€€€€€€Í•±˜¹ÍÑ…ÑÕÍ	…È ¤¹Í¡½İ5•ÍÍ…” =Á•¸„‰½½¬ƒ
ÜƒŠ2a<œ¤(€€€€€€€Í•±˜¹Íå¹}é½½µ}½¹ÑÉ½±Ì ¤((€€€‘•˜…ÁÁ±å}ÍÑå±”¡Í•±˜¤è(€€€€€€€¥˜Í•±˜¹‘…É¬è(€€€€€€€€€€€‰œ°Á…¹•°°¥¹¬°µÕÑ•°‰½É‘•È°…¹Ù…Ì°Á…”°…•¹Ğ°…•¹Ñ}Í½™Ğ°¡½Ù•È€ô€ (€€€€€€€€€€€€€€€€œŒÄäÅÈĞœ°€œŒÈÈÈàÌÄœ°€œ”İ”å•˜œ°€œ„É…‘‰œ°€œŒÌàĞÄÔÀœ°€œŒÄÄÄØÅˆœ°€œ˜á˜á˜Øœ°€œŒÕ•„ÌàÄœ°€œŒÈäĞĞÌÜœ°€œŒÉ„ÌÄÍˆœ(€€€€€€€€€€€€¤(€€€€€€€€€€€Í•±•Ñ•‘}¥¹¬€ô€œ˜Ñ˜İ˜Ôœ(€€€€€€€€€€€µ•¹Õ}‰œ€ô€œŒÄĞÅ„ÈÌœ(€€€€€€€•±Í”è(€€€€€€€€€€€‰œ°Á…¹•°°¥¹¬°µÕÑ•°‰½É‘•È°…¹Ù…Ì°Á…”°…•¹Ğ°…•¹Ñ}Í½™Ğ°¡½Ù•È€ô€ (€€€€€€€€€€€€€€€€œ˜á˜Ù˜Äœ°€œ™™™™™˜œ°€œŒÈĞÌÌÉœ°€œŒİˆàÌİ”œ°€œ‘”Éàœ°€œ”Ñ”İ”Èœ°€œ™™™™™˜œ°€œŒÉ˜İ„Ôäœ°€œ‘™••”Ğœ°€œ˜É˜Ù˜Äœ(€€€€€€€€€€€€¤(€€€€€€€€€€€Í•±•Ñ•‘}¥¹¬€ô€œŒÈĞÌÌÉœ(€€€€€€€€€€€µ•¹Õ}‰œ€ô€œ™™™™™˜œ(€€€€€€€Í•±˜¹Í•ÑMÑå±•M¡••Ğ¡˜œœœ(€€€€€€€E5…¥¹]¥¹‘½Ü±E]¥‘•Ğíì‰…­É½Õ¹éí‰ôì½±½Èéí¥¹­ôì™½¹Ğµ™…µ¥±äè‰!•±Ù•Ñ¥„9•Õ”ˆ°‰É¥…°ˆì™½¹ĞµÍ¥é”èÄÍÁàìõô(€€€€€€€EQ½½±	…Èíì‰½É‘•ÈèÀì‰½É‘•Èµ‰½ÑÑ½´èÅÁàÍ½±¥í‰½É‘•ÉôìÁ…‘‘¥¹œèáÁà€ÄÁÁàìÍÁ…¥¹œèÙÁàìõô(€€€€€€€EQ½½±	…ÈèéÍ•Á…É…Ñ½Èíìİ¥‘Ñ èÅÁàìµ…É¥¸èÙÁà€áÁàì‰…­É½Õ¹éí‰½É‘•Éôìõô(€€€€€€€EQ½½±	ÕÑÑ½¸íì‰½É‘•ÈèÅÁàÍ½±¥í‰½É‘•Éôì‰½É‘•ÈµÉ…‘¥ÕÌèÄÁÁàìÁ…‘‘¥¹œèÕÁàì‰…­É½Õ¹éíÁ…¹•±ôìµ¥¸µİ¥‘Ñ èÈÙÁàìµ¥¸µ¡•¥¡ĞèÈÙÁàìõô(€€€€€€€EQ½½±	…ÈEQ½½±	ÕÑÑ½¸íìµ…àµİ¥‘Ñ èÌÉÁàìµ…àµ¡•¥¡ĞèÌÉÁàìõô(€€€€€€€EQ½½±	ÕÑÑ½¸èéµ•¹Ôµ¥¹‘¥…Ñ½Èíì¥µ…”é¹½¹”ìİ¥‘Ñ èÁÁàì¡•¥¡ĞèÁÁàìõô(€€€€€€€EQ½½±	ÕÑÑ½¸é¡½Ù•È±EAÕÍ¡	ÕÑÑ½¸é¡½Ù•Èíì‰½É‘•Èµ½±½Èéí…•¹Ñôì‰…­É½Õ¹éí¡½Ù•Éôìõô(€€€€€€€EAÕÍ¡	ÕÑÑ½¸íì‰½É‘•ÈèÅÁàÍ½±¥í‰½É‘•Éôì‰½É‘•ÈµÉ…‘¥ÕÌèÄÉÁàìÁ…‘‘¥¹œèáÁà€ÄÉÁàì‰…­É½Õ¹éíÁ…¹•±ôìõô(€€€€€€€E1¥¹•‘¥Ğ±EMÁ¥¹	½àíìÁ…‘‘¥¹œèİÁà€ÄÁÁàì‰½É‘•ÈèÅÁàÍ½±¥í‰½É‘•Éôì‰½É‘•ÈµÉ…‘¥ÕÌèÄÉÁàì‰…­É½Õ¹éíÁ…¹•±ôìÍ•±•Ñ¥½¸µ‰…­É½Õ¹µ½±½Èéí…•¹Ñôìõô(€€€€€€€EMÁ¥¹	½àÁ…•MÁ¥¸íìµ¥¸µİ¥‘Ñ èØÉÁàìõô(€€€€€€€E1¥ÍÑ]¥‘•Ğ±EQÉ••]¥‘•Ğíì‰½É‘•ÈèÀì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğì½ÕÑ±¥¹”èÀìõô(€€€€€€€E1¥ÍÑ]¥‘•Ğèé¥Ñ•´íìÁ…‘‘¥¹œèÀìµ…É¥¸èÀ€À€áÁà€Àì‰½É‘•ÈèÅÁàÍ½±¥ÑÉ…¹ÍÁ…É•¹Ğì‰½É‘•ÈµÉ…‘¥ÕÌèÄÙÁàìõô(€€€€€€€E1¥ÍÑ]¥‘•Ğèé¥Ñ•´éÍ•±•Ñ•íì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğì½±½ÈéíÍ•±•Ñ•‘}¥¹­ôì‰½É‘•ÈèÅÁàÍ½±¥ÑÉ…¹ÍÁ…É•¹Ğìõô(€€€€€€€EQÉ••]¥‘•Ğèé¥Ñ•´é¡½Ù•Èíì‰…­É½Õ¹éí¡½Ù•Éôì‰½É‘•ÈµÉ…‘¥ÕÌèÄÁÁàìõô(€€€€€€€EQÉ••]¥‘•Ğèé¥Ñ•´éÍ•±•Ñ•íì‰…­É½Õ¹éí…•¹Ñ}Í½™Ñôì½±½ÈéíÍ•±•Ñ•‘}¥¹­ôì‰½É‘•ÈµÉ…‘¥ÕÌèÄÉÁàìõô(€€€€€€€EQ…‰]¥‘•ĞèéÁ…¹”íì‰½É‘•ÈèÀìõô(€€€€€€€EQ…‰	…ÈèéÑ…ˆíìÁ…‘‘¥¹œèáÁà€áÁà€åÁàìµ…É¥¸µÉ¥¡ĞèÄÁÁàì‰½É‘•ÈèÀì‰½É‘•Èµ‰½ÑÑ½´èÉÁàÍ½±¥ÑÉ…¹ÍÁ…É•¹Ğì‰½É‘•ÈµÉ…‘¥ÕÌèÀì½±½ÈéíµÕÑ•‘ôì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğìµ¥¸µİ¥‘Ñ èÀìõô(€€€€€€€EQ…‰	…ÈèéÑ…ˆé¡½Ù•Èíì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğì½±½Èéí¥¹­ôìõô(€€€€€€€EQ…‰	…ÈèéÑ…ˆéÍ•±•Ñ•íì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğì½±½Èéí…•¹Ñôì‰½É‘•ÈèÀì‰½É‘•Èµ‰½ÑÑ½´èÉÁàÍ½±¥í…•¹Ñôì™½¹Ğµİ•¥¡ĞèØÀÀìõô(€€€€€€€EMÉ½±±É•„Á…•É•„±E]¥‘•ĞÁ…•Í½¹Ñ…¥¹•Èíì‰…­É½Õ¹éí…¹Ù…Íôì‰½É‘•ÈèÀìõô(€€€€€€€E1…‰•°‰½½­A…”íì‰…­É½Õ¹éíÁ…•ôì½±½ÈèŒå…„Ìå”ì‰½É‘•ÈèÅÁàÍ½±¥€™ÕÀìõô(€€€€€€€E1…‰•°‰É…¹íì™½¹ĞµÍ¥é”èÈÍÁàì™½¹Ğµİ•¥¡ĞèÜÀÀì±•ÑÑ•ÈµÍÁ…¥¹œèÑÁàìõô(€€€€€€€E1…‰•°µÕÑ•íì½±½ÈéíµÕÑ•‘ôì™½¹ĞµÍ¥é”èÄÅÁàìõô(€€€€€€€E1…‰•°•å•‰É½Üíì½±½Èéí…•¹Ñôì™½¹ĞµÍ¥é”èÄÅÁàì™½¹Ğµİ•¥¡ĞèØÀÀì±•ÑÑ•ÈµÍÁ…¥¹œèÉÁàìõô(€€€€€€€E1…‰•°¡•…‘±¥¹”íì™½¹ĞµÍ¥é”èÌÑÁàì™½¹Ğµİ•¥¡ĞèØÀÀìÁ…‘‘¥¹œèÄáÁà€À€áÁàìõô(€€€€€€€E1…‰•°‘•ÍÉ¥ÁÑ¥½¸íì½±½ÈéíµÕÑ•‘ôì™½¹ĞµÍ¥é”èÄÕÁàìÁ…‘‘¥¹œèÑÁàìõô(€€€€€€€EAÕÍ¡	ÕÑÑ½¸ÁÉ¥µ…Éäíì‰…­É½Õ¹éí…•¹Ñôì½±½Èéİ¡¥Ñ”ì‰½É‘•ÈèÀìÁ…‘‘¥¹œèÄÉÁà€ÈÙÁàì™½¹Ğµİ•¥¡ĞèØÀÀìõô(€€€€€€€E]¥‘•Ğé½½µ½½Ñ•Èíì‰½É‘•ÈµÑ½ÀèÅÁàÍ½±¥í‰½É‘•Éôì‰…­É½Õ¹éí‰ôìõô(€€€€€€€E]¥‘•ĞÁÉ¥¹Ñ…¹Ù…Ìíì‰…­É½Õ¹è‘™”É‘˜ìõô(€€€€€€€E]¥‘•ĞÁÉ¥¹ÑM•ÑÑ¥¹Ìíì‰…­É½Õ¹éíÁ…¹•±ôì‰½É‘•ÈµÉ¥¡ĞèÅÁàÍ½±¥í‰½É‘•Éôìõô(€€€€€€€E1…‰•°ÁÉ¥¹ÑQ¥Ñ±”íì™½¹ĞµÍ¥é”èÈáÁàì™½¹Ğµİ•¥¡ĞèØÀÀìÁ…‘‘¥¹œµ‰½ÑÑ½´èÄÉÁàìõô(€€€€€€€E1…‰•°ÁÉ¥¹ÑA…”íì‰…­É½Õ¹è™™™™™˜ì½±½ÈèŒÜÜÜì‰½É‘•ÈèÅÁàÍ½±¥€Œå•„ìõô(€€€€€€€EMÉ½±±	…ÈéÙ•ÉÑ¥…°íì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğìİ¥‘Ñ èÄÉÁàìµ…É¥¸èáÁà€ÉÁà€áÁà€ÉÁàìõô(€€€€€€€EMÉ½±±	…Èèé¡…¹‘±”éÙ•ÉÑ¥…°íì‰…­É½Õ¹éí‰½É‘•Éôìµ¥¸µ¡•¥¡ĞèĞÁÁàì‰½É‘•ÈµÉ…‘¥ÕÌèÙÁàìõô(€€€€€€€EMÉ½±±	…Èèé¡…¹‘±”éÙ•ÉÑ¥…°é¡½Ù•Èíì‰…­É½Õ¹éí…•¹Ñôìõô(€€€€€€€EMÉ½±±	…Èèé…‘µ±¥¹”éÙ•ÉÑ¥…°±EMÉ½±±	…ÈèéÍÕˆµ±¥¹”éÙ•ÉÑ¥…°±EMÉ½±±	…Èèé…‘µÁ…”éÙ•ÉÑ¥…°±EMÉ½±±	…ÈèéÍÕˆµÁ…”éÙ•ÉÑ¥…°íì‰…­É½Õ¹é¹½¹”ì¡•¥¡ĞèÀìõô(€€€€€€€EMÉ½±±	…Èé¡½É¥é½¹Ñ…°íì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğì¡•¥¡ĞèÄÉÁàìµ…É¥¸èÉÁà€áÁà€ÉÁà€áÁàìõô(€€€€€€€EMÉ½±±	…Èèé¡…¹‘±”é¡½É¥é½¹Ñ…°íì‰…­É½Õ¹éí‰½É‘•Éôìµ¥¸µİ¥‘Ñ èĞÁÁàì‰½É‘•ÈµÉ…‘¥ÕÌèÙÁàìõô(€€€€€€€EMÉ½±±	…Èèé¡…¹‘±”é¡½É¥é½¹Ñ…°é¡½Ù•Èíì‰…­É½Õ¹éí…•¹Ñôìõô(€€€€€€€EMÉ½±±	…Èèé…‘µ±¥¹”é¡½É¥é½¹Ñ…°±EMÉ½±±	…ÈèéÍÕˆµ±¥¹”é¡½É¥é½¹Ñ…°±EMÉ½±±	…Èèé…‘µÁ…”é¡½É¥é½¹Ñ…°±EMÉ½±±	…ÈèéÍÕˆµÁ…”é¡½É¥é½¹Ñ…°íì‰…­É½Õ¹é¹½¹”ìİ¥‘Ñ èÀìõô(€€€€€€€EMÑ…ÑÕÍ	…Èíì‰½É‘•ÈµÑ½ÀèÅÁàÍ½±¥í‰½É‘•Éôì½±½ÈéíµÕÑ•‘ôìÁ…‘‘¥¹œèÍÁàìõô(€€€€€€€E5•¹Ôíì‰…­É½Õ¹éíµ•¹Õ}‰ôì‰½É‘•ÈèÅÁàÍ½±¥í‰½É‘•ÉôìÁ…‘‘¥¹œèÙÁà€Àìõô(€€€€€€€E5•¹Ôèé¥Ñ•´íìÁ…‘‘¥¹œèİÁà€ÈáÁà€İÁà€ÄÑÁàì‰…­É½Õ¹éÑÉ…¹ÍÁ…É•¹Ğìõô(€€€€€€€E5•¹Ôèé¥Ñ•´éÍ•±•Ñ•íì‰…­É½Õ¹éí…•¹Ñôì½±½Èéİ¡¥Ñ”ìõô(€€€€€€€€œœœ¤(€€€€€€€Í•±˜¹É•™É•Í¡}±¥‰É…Éä ¤(€€€€€€€Í•±˜¹Íå¹}é½½µ}½¹ÑÉ½±Ì ¤(