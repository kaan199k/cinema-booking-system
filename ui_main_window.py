import random
import string
from typing import Dict, Tuple, Set

import os
import sys

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QGridLayout,
    QTextEdit,
    QSizePolicy,
    QDialog,
    QTableWidget,
    QTableWidgetItem,
    QGraphicsDropShadowEffect,
    QApplication,
    QHeaderView,
    QFrame,
)
from PyQt5.QtGui import QPalette, QColor, QFont

from data import ROWS, NUM_COLUMNS
from themes import THEMES, apply_theme_to_palette, Theme
from storage import (
    init_db,
    save_booking,
    get_taken_seats,
    mark_seats_taken,
    get_stats_by_movie,
    get_all_movie_titles,
    get_halls_for_movie,
    get_show_times,
    get_movie_id_for_title,
    cancel_booking,
)
from i18n import get_translations
from ticket_pdf import generate_ticket_pdf
from admin_window import AdminWindow

SeatKey = str  # e.g. "A5"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # DB
        init_db()

        # Language
        self.current_lang = "en"
        self.translations = get_translations(self.current_lang)

        # Theme - CHANGED DEFAULT TO DARK
        self.current_theme: Theme = THEMES["dark"]
        self.current_theme_name: str = "dark"

        # ticket types & prices
        self.ticket_prices: Dict[str, float] = {
            "Standard": 12.0,
            "Student": 9.0,
            "Child": 8.0,
            "VIP": 18.0,
        }

        # UI references
        self.labels: Dict[str, QLabel] = {}
        self.seat_buttons: Dict[SeatKey, QPushButton] = {}
        self.selected_seats: Dict[SeatKey, bool] = {}
        self.taken_seats: Set[SeatKey] = set()

        # Window setup
        self.setMinimumSize(1150, 750)
        self.resize(1280, 800)

        self._build_ui()
        # Apply 'dark' initially instead of 'light'
        self._apply_theme("dark")
        self._update_texts()

    # ---------- helpers ----------

    def _t(self, key: str) -> str:
        return self.translations.get(key, key)

    # ---------- UI BUILD ----------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        central.setLayout(main_layout)

        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()

        main_layout.addWidget(left_panel, 35)
        main_layout.addWidget(right_panel, 65)

    def _build_left_panel(self) -> QWidget:
        container = QFrame()
        container.setObjectName("panelFrame")
        self._apply_card_shadow(container)

        layout = QVBoxLayout()
        layout.setSpacing(16)
        layout.setContentsMargins(20, 24, 20, 24)
        container.setLayout(layout)

        # -- Header --
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        self.title_label = QLabel(self._t("app_title"))
        self.title_label.setObjectName("h1")
        self.title_label.setWordWrap(True)

        self.subtitle_label = QLabel(self._t("subtitle"))
        self.subtitle_label.setObjectName("subtitle")

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        layout.addLayout(header_layout)

        layout.addSpacing(10)

        # -- Booking Form --

        # Movie
        self.movie_combo = QComboBox()
        self._load_movies()
        self.movie_combo.currentIndexChanged.connect(self._on_movie_changed)
        layout.addWidget(self._labeled_widget("movie_label", self.movie_combo))

        # Hall & Time (Row)
        row_ht = QHBoxLayout()
        row_ht.setSpacing(10)

        self.hall_combo = QComboBox()
        self.hall_combo.addItem("Select hall…")
        self.hall_combo.setEnabled(False)
        self.hall_combo.currentIndexChanged.connect(self._on_hall_changed)

        self.time_combo = QComboBox()
        self.time_combo.addItem("Select time…")
        self.time_combo.setEnabled(False)
        self.time_combo.currentIndexChanged.connect(self._on_time_changed)

        row_ht.addWidget(self._labeled_widget("hall_label", self.hall_combo))
        row_ht.addWidget(self._labeled_widget("time_label", self.time_combo))
        layout.addLayout(row_ht)

        # Client Name
        self.client_name_edit = QLineEdit()
        self.client_name_edit.setPlaceholderText("Enter client name...")
        self.client_name_edit.textChanged.connect(self._update_summary)
        layout.addWidget(self._labeled_widget("client_label", self.client_name_edit))

        # Ticket Type
        self.ticket_type_combo = QComboBox()
        self.ticket_type_combo.addItems(list(self.ticket_prices.keys()))
        self.ticket_type_combo.currentIndexChanged.connect(self._update_price_display)
        layout.addWidget(self._plain_labeled_widget("Ticket Type", self.ticket_type_combo))

        # -- Prices --
        price_row = QHBoxLayout()
        self.price_label = QLabel("Price: —")
        self.price_label.setObjectName("priceLabel")
        self.total_label = QLabel("Total: —")
        self.total_label.setObjectName("totalLabel")

        price_row.addWidget(self.price_label)
        price_row.addStretch()
        price_row.addWidget(self.total_label)
        layout.addLayout(price_row)

        # -- Settings (Lang + Theme) --
        line = QFrame()
        line.setObjectName("divider")
        line.setFrameShape(QFrame.HLine)
        layout.addWidget(line)

        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(15)

        # Lang
        lang_v = QVBoxLayout()
        lang_v.setSpacing(5)
        self.lang_lbl = QLabel(self._t("lang_group"))
        self.lang_lbl.setObjectName("fieldLabel")
        self.labels["lang_group"] = self.lang_lbl

        lang_btn_row = QHBoxLayout()
        lang_btn_row.setSpacing(5)
        self.lang_en_btn = QPushButton("EN")
        self.lang_en_btn.setCheckable(True)
        self.lang_bg_btn = QPushButton("BG")
        self.lang_bg_btn.setCheckable(True)
        self.lang_en_btn.setFixedWidth(40)
        self.lang_bg_btn.setFixedWidth(40)

        self.lang_en_btn.clicked.connect(lambda: self._set_language("en"))
        self.lang_bg_btn.clicked.connect(lambda: self._set_language("bg"))

        lang_btn_row.addWidget(self.lang_en_btn)
        lang_btn_row.addWidget(self.lang_bg_btn)
        lang_v.addWidget(self.lang_lbl)
        lang_v.addLayout(lang_btn_row)

        # Theme
        theme_v = QVBoxLayout()
        theme_v.setSpacing(5)
        self.theme_lbl = QLabel(self._t("theme_group"))
        self.theme_lbl.setObjectName("fieldLabel")
        self.labels["theme_group"] = self.theme_lbl

        theme_btn_row = QHBoxLayout()
        theme_btn_row.setSpacing(5)
        self.light_btn = QPushButton("Light")
        self.dark_btn = QPushButton("Dark")
        self.night_btn = QPushButton("Night")

        # Kept order: Light, Dark, Night
        for btn, name in [(self.light_btn, "light"), (self.dark_btn, "dark"), (self.night_btn, "night")]:
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, n=name: self._apply_theme(n))
            theme_btn_row.addWidget(btn)

        theme_v.addWidget(self.theme_lbl)
        theme_v.addLayout(theme_btn_row)

        settings_layout.addLayout(lang_v)
        settings_layout.addStretch()
        settings_layout.addLayout(theme_v)
        layout.addLayout(settings_layout)

        # -- Summary --
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(120)
        layout.addWidget(self._labeled_widget("summary_label", self.summary_text))

        # -- Actions --
        self.confirm_btn = QPushButton(self._t("confirm_button"))
        self.confirm_btn.setObjectName("primaryButton")
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self._handle_booking)
        self.confirm_btn.setMinimumHeight(48)
        layout.addWidget(self.confirm_btn)

        tools_row = QHBoxLayout()
        self.stats_btn = QPushButton("Stats")
        self.stats_btn.setObjectName("ghostButton")
        self.stats_btn.clicked.connect(self._open_stats_dialog)

        self.admin_btn = QPushButton("Admin")
        self.admin_btn.setObjectName("ghostButton")
        self.admin_btn.clicked.connect(self._open_admin_window)

        tools_row.addWidget(self.stats_btn)
        tools_row.addWidget(self.admin_btn)
        layout.addLayout(tools_row)

        # -- Cancel --
        cancel_row = QHBoxLayout()
        self.cancel_code_edit = QLineEdit()
        self.cancel_code_edit.setPlaceholderText("Booking Code")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.clicked.connect(self._handle_cancel_booking)

        cancel_row.addWidget(self.cancel_code_edit, 2)
        cancel_row.addWidget(self.cancel_btn, 1)
        layout.addLayout(cancel_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        layout.addStretch(1)
        return container

    def _build_right_panel(self) -> QWidget:
        container = QFrame()
        container.setObjectName("panelFrame")
        self._apply_card_shadow(container)

        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)
        container.setLayout(layout)

        self.seat_subtitle_label = QLabel(self._t("seat_subtitle"))
        self.seat_subtitle_label.setObjectName("subtitle")
        self.seat_subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.seat_subtitle_label)

        # Screen visual
        screen_frame = QFrame()
        screen_frame.setObjectName("screenFrame")
        screen_frame.setFixedHeight(35)

        sf_layout = QVBoxLayout(screen_frame)
        sf_layout.setContentsMargins(0, 0, 0, 0)

        self.screen_label = QLabel("S C R E E N")
        self.screen_label.setAlignment(Qt.AlignCenter)
        self.screen_label.setObjectName("screenText")
        sf_layout.addWidget(self.screen_label)

        layout.addWidget(screen_frame)

        # Seat Grid Container
        grid_container = QWidget()
        grid_layout_outer = QHBoxLayout(grid_container)
        grid_layout_outer.addStretch()

        self.seat_grid = QGridLayout()
        self.seat_grid.setSpacing(12)
        grid_layout_outer.addLayout(self.seat_grid)

        grid_layout_outer.addStretch()
        layout.addWidget(grid_container)

        self._build_seat_buttons()

        layout.addStretch(1)
        return container

    def _build_seat_buttons(self) -> None:
        self.seat_buttons.clear()
        self.selected_seats.clear()

        while self.seat_grid.count():
            item = self.seat_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for row_index, row_label in enumerate(ROWS):
            lbl = QLabel(row_label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold; font-size: 14px; opacity: 0.5;")
            self.seat_grid.addWidget(lbl, row_index, 0)

            for col in range(1, NUM_COLUMNS + 1):
                seat_id = f"{row_label}{col}"
                btn = QPushButton(str(col))
                btn.setProperty("seat_id", seat_id)
                btn.clicked.connect(self._on_seat_clicked)

                btn.setFixedSize(42, 38)

                self._style_seat_button(btn, selected=False, taken=False)

                self.seat_grid.addWidget(btn, row_index, col)
                self.seat_buttons[seat_id] = btn
                self.selected_seats[seat_id] = False

    # ---------- LABEL HELPERS ----------

    def _labeled_widget(self, label_key: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        lbl = QLabel(self._t(label_key))
        lbl.setObjectName("fieldLabel")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        container.setLayout(layout)

        self.labels[label_key] = lbl
        return container

    def _plain_labeled_widget(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        lbl = QLabel(label_text)
        lbl.setObjectName("fieldLabel")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        container.setLayout(layout)
        return container

    def _apply_card_shadow(self, widget: QWidget) -> None:
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(40)
        effect.setOffset(0, 10)
        effect.setColor(QColor(0, 0, 0, 30))
        widget.setGraphicsEffect(effect)

    def _style_seat_button(self, btn: QPushButton, selected: bool, taken: bool = False) -> None:
        theme = self.current_theme

        if taken:
            bg = theme.border
            color = theme.muted_text
            border_col = theme.border
            cursor = "not-allowed"
        else:
            cursor = "pointer"
            if selected:
                bg = theme.success
                color = "#ffffff"
                border_col = theme.success
            else:
                bg = theme.window_bg
                color = theme.text
                border_col = theme.border

        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {bg};
                color: {color};
                border: 1px solid {border_col};
                border-radius: 8px 8px 12px 12px; 
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                border-color: {theme.accent};
            }}
            """
        )
        if taken:
            btn.setEnabled(False)
        else:
            btn.setEnabled(True)
            btn.setCursor(Qt.PointingHandCursor)

    def _generate_booking_code(self) -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # ---------- THEME & LANGUAGE ----------

    def _apply_theme(self, theme_name: str) -> None:
        theme = THEMES.get(theme_name, THEMES["light"])
        self.current_theme = theme
        self.current_theme_name = theme_name

        palette = QPalette()
        apply_theme_to_palette(theme, palette)
        QApplication.instance().setPalette(palette)

        style = f"""
        * {{
            font-family: 'Segoe UI', 'Helvetica Neue', sans-serif;
            font-size: 13px;
            color: {theme.text};
        }}
        QMainWindow {{
            background-color: {theme.window_bg};
        }}
        QFrame#panelFrame {{
            background-color: {theme.panel_bg};
            border-radius: 16px;
            border: 1px solid {theme.border};
        }}
        QFrame#divider {{
            color: {theme.border}; 
            background-color: {theme.border};
        }}

        /* Typo */
        QLabel#h1 {{
            font-size: 24px;
            font-weight: 800;
            color: {theme.text};
        }}
        QLabel#subtitle {{
            font-size: 13px;
            color: {theme.muted_text};
        }}
        QLabel#fieldLabel {{
            font-size: 12px;
            font-weight: 600;
            color: {theme.muted_text};
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        QLabel#priceLabel, QLabel#totalLabel {{
            font-size: 14px;
            font-weight: bold;
            color: {theme.text};
        }}

        /* Screen Visual */
        QFrame#screenFrame {{
            background-color: {theme.border}; 
            border-radius: 8px;
        }}
        QLabel#screenText {{
            color: {theme.muted_text};
            font-weight: bold;
            letter-spacing: 8px;
            font-size: 12px;
        }}

        /* Inputs */
        QLineEdit, QComboBox, QTextEdit {{
            background-color: {theme.window_bg};
            border: 1px solid {theme.border};
            border-radius: 8px;
            padding: 8px 10px;
            selection-background-color: {theme.accent};
        }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
            border: 2px solid {theme.accent};
            background-color: {theme.panel_bg};
        }}
        QComboBox::drop-down {{
            border: 0;
            width: 20px;
        }}

        /* Buttons */
        QPushButton {{
            background-color: {theme.window_bg};
            border: 1px solid {theme.border};
            border-radius: 6px;
            padding: 6px;
            font-weight: 600;
        }}
        QPushButton:checked {{
            background-color: {theme.accent_soft};
            color: {theme.accent};
            border: 1px solid {theme.accent};
        }}
        QPushButton:hover {{
            border-color: {theme.accent};
        }}

        QPushButton#primaryButton {{
            background-color: {theme.accent};
            color: white;
            border: none;
            font-size: 15px;
            border-radius: 8px;
        }}
        QPushButton#primaryButton:hover {{
            background-color: {theme.accent_hover};
        }}
        QPushButton#primaryButton:disabled {{
            background-color: {theme.border};
            color: {theme.muted_text};
        }}

        QPushButton#ghostButton {{
            background-color: transparent;
            border: 1px solid {theme.border};
            color: {theme.muted_text};
        }}
        QPushButton#ghostButton:hover {{
            background-color: {theme.window_bg};
            color: {theme.text};
            border-color: {theme.text};
        }}

        QPushButton#dangerButton {{
            background-color: transparent;
            border: 1px solid {theme.error};
            color: {theme.error};
        }}
        QPushButton#dangerButton:hover {{
            background-color: {theme.error};
            color: white;
        }}

        /* Scrollbar */
        QScrollBar:vertical {{
            border: none;
            background: {theme.window_bg};
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {theme.border};
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.muted_text};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        """

        QApplication.instance().setStyleSheet(style)

        self.light_btn.setChecked(theme_name == "light")
        self.dark_btn.setChecked(theme_name == "dark")
        self.night_btn.setChecked(theme_name == "night")

        # Redraw seats
        for seat_id, btn in self.seat_buttons.items():
            selected = self.selected_seats.get(seat_id, False)
            taken = seat_id in self.taken_seats
            self._style_seat_button(btn, selected=selected, taken=taken)

    def _set_language(self, lang_code: str) -> None:
        self.current_lang = lang_code
        self.translations = get_translations(lang_code)
        self._update_texts()

    def _update_texts(self) -> None:
        self.setWindowTitle(self._t("app_title"))

        if "lang_group" in self.labels: self.labels["lang_group"].setText(self._t("lang_group"))
        if "theme_group" in self.labels: self.labels["theme_group"].setText(self._t("theme_group"))

        self.title_label.setText(self._t("app_title"))
        self.subtitle_label.setText(self._t("subtitle"))
        self.seat_subtitle_label.setText(self._t("seat_subtitle"))

        for key, lbl in self.labels.items():
            lbl.setText(self._t(key))

        self.confirm_btn.setText(self._t("confirm_button"))
        if "stats_button" in self.translations:
            self.stats_btn.setText(self._t("stats_button"))
        self.lang_en_btn.setText(self._t("lang_en"))
        self.lang_bg_btn.setText(self._t("lang_bg"))

        self.lang_en_btn.setChecked(self.current_lang == "en")
        self.lang_bg_btn.setChecked(self.current_lang == "bg")

        self._update_summary()

    # ---------- LOGIC ----------

    def _load_movies(self) -> None:
        self.movie_combo.blockSignals(True)
        self.movie_combo.clear()
        self.movie_combo.addItem("Select movie…")
        for title in get_all_movie_titles():
            self.movie_combo.addItem(title)
        self.movie_combo.blockSignals(False)

    def _get_current_show_key(self) -> Tuple[str, str, str] | None:
        if (
                self.movie_combo.currentIndex() <= 0
                or self.hall_combo.currentIndex() <= 0
                or self.time_combo.currentIndex() <= 0
        ):
            return None
        movie_title = self.movie_combo.currentText()
        hall = self.hall_combo.currentText()
        time = self.time_combo.currentText()
        movie_id = get_movie_id_for_title(movie_title)
        if not movie_id:
            return None
        return movie_id, hall, time

    def _load_taken_seats_for_current_show(self) -> None:
        key = self._get_current_show_key()
        if key is None:
            self.taken_seats = set()
            for seat_id, btn in self.seat_buttons.items():
                selected = self.selected_seats.get(seat_id, False)
                self._style_seat_button(btn, selected=selected, taken=False)
            return
        movie_id, hall, time = key
        taken = get_taken_seats(movie_id, hall, time)
        self.taken_seats = taken
        for seat_id, btn in self.seat_buttons.items():
            selected = self.selected_seats.get(seat_id, False)
            is_taken = seat_id in self.taken_seats
            if is_taken:
                self.selected_seats[seat_id] = False
                selected = False
            self._style_seat_button(btn, selected=selected, taken=is_taken)

    def _on_movie_changed(self, index: int) -> None:
        self.hall_combo.blockSignals(True)
        self.time_combo.blockSignals(True)
        self.hall_combo.clear()
        self.time_combo.clear()
        self.hall_combo.addItem("Select hall…")
        self.time_combo.addItem("Select time…")
        self.hall_combo.setEnabled(False)
        self.time_combo.setEnabled(False)
        self.hall_combo.blockSignals(False)
        self.time_combo.blockSignals(False)
        for seat in list(self.selected_seats.keys()):
            self.selected_seats[seat] = False
        self._load_taken_seats_for_current_show()
        self._update_price_display()
        if index <= 0:
            self._update_summary()
            self._update_confirm_state()
            return
        movie_title = self.movie_combo.currentText()
        halls = get_halls_for_movie(movie_title)
        self.hall_combo.blockSignals(True)
        for hall in halls:
            self.hall_combo.addItem(hall)
        self.hall_combo.blockSignals(False)
        self.hall_combo.setEnabled(True)
        self._update_summary()
        self._update_confirm_state()

    def _on_hall_changed(self, index: int) -> None:
        self.time_combo.blockSignals(True)
        self.time_combo.clear()
        self.time_combo.addItem("Select time…")
        self.time_combo.blockSignals(False)
        self.time_combo.setEnabled(False)
        if index <= 0:
            self._load_taken_seats_for_current_show()
            self._update_summary()
            self._update_confirm_state()
            return
        movie_title = self.movie_combo.currentText()
        hall_name = self.hall_combo.currentText()
        times = get_show_times(movie_title, hall_name)
        self.time_combo.blockSignals(True)
        for t in times:
            self.time_combo.addItem(t)
        self.time_combo.blockSignals(False)
        self.time_combo.setEnabled(True)
        self._load_taken_seats_for_current_show()
        self._update_summary()
        self._update_confirm_state()

    def _on_time_changed(self, index: int) -> None:
        self._load_taken_seats_for_current_show()
        self._update_summary()
        self._update_confirm_state()

    def _on_seat_clicked(self) -> None:
        btn: QPushButton = self.sender()  # type: ignore
        seat_id: SeatKey = btn.property("seat_id")
        if seat_id in self.taken_seats:
            return
        current = self.selected_seats.get(seat_id, False)
        new_state = not current
        self.selected_seats[seat_id] = new_state
        self._style_seat_button(btn, selected=new_state, taken=False)
        self._update_summary()
        self._update_confirm_state()
        self._update_price_display()

    def _collect_selected_seats(self) -> Tuple[SeatKey, ...]:
        return tuple(sorted([s for s, sel in self.selected_seats.items() if sel]))

    def _get_current_ticket_type(self) -> str:
        return self.ticket_type_combo.currentText() or "Standard"

    def _get_price_info(self) -> Tuple[float, float]:
        ticket_type = self._get_current_ticket_type()
        price_per_seat = self.ticket_prices.get(ticket_type, 0.0)
        seats_count = len(self._collect_selected_seats())
        total_price = price_per_seat * seats_count
        return price_per_seat, total_price

    def _update_price_display(self) -> None:
        price_per_seat, total_price = self._get_price_info()
        if price_per_seat == 0:
            self.price_label.setText("Price: —")
        else:
            self.price_label.setText(f"Price: {price_per_seat:.2f} лв.")
        if total_price == 0:
            self.total_label.setText("Total: —")
        else:
            self.total_label.setText(f"Total: {total_price:.2f} лв.")

    def _update_summary(self) -> None:
        movie_title = self.movie_combo.currentText() if self.movie_combo.currentIndex() > 0 else "—"
        hall = self.hall_combo.currentText() if self.hall_combo.currentIndex() > 0 else "—"
        time = self.time_combo.currentText() if self.time_combo.currentIndex() > 0 else "—"
        client_name = self.client_name_edit.text().strip() or "—"
        seats = self._collect_selected_seats()
        seats_str = ", ".join(seats) if seats else "—"
        ticket_type = self._get_current_ticket_type()
        text = (
            f"{self._t('movie_label')}: {movie_title}\n"
            f"{self._t('hall_label')}: {hall}\n"
            f"{self._t('time_label')}: {time}\n"
            f"{self._t('client_summary')}: {client_name}\n"
            f"{self._t('seats_summary')}: {seats_str}\n"
            f"Ticket Type: {ticket_type}\n"
        )
        self.summary_text.setPlainText(text)

    def _update_confirm_state(self) -> None:
        has_movie = self.movie_combo.currentIndex() > 0
        has_hall = self.hall_combo.currentIndex() > 0
        has_time = self.time_combo.currentIndex() > 0
        has_name = bool(self.client_name_edit.text().strip())
        has_seats = len(self._collect_selected_seats()) > 0
        self.confirm_btn.setEnabled(has_movie and has_hall and has_time and has_name and has_seats)

    def _open_pdf(self, path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["open", path])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            current = self.status_label.text()
            self.status_label.setText(f"{current}\n(Could not open PDF: {e})")

    def _handle_booking(self) -> None:
        movie_title = self.movie_combo.currentText()
        hall = self.hall_combo.currentText()
        time = self.time_combo.currentText()
        client_name = self.client_name_edit.text().strip()
        seats = self._collect_selected_seats()
        if not client_name:
            self.status_label.setText(self._t("status_missing_name"))
            return
        if not seats:
            self.status_label.setText(self._t("status_missing_seats"))
            return
        movie_id = get_movie_id_for_title(movie_title)
        code = self._generate_booking_code()
        ticket_type = self._get_current_ticket_type()
        price_per_seat, total_price = self._get_price_info()
        save_booking(
            movie_id=movie_id,
            movie_title=movie_title,
            hall=hall,
            show_time=time,
            client_name=client_name,
            seats=seats,
            booking_code=code,
            ticket_type=ticket_type,
            price_per_seat=price_per_seat,
            total_price=total_price,
        )
        mark_seats_taken(movie_id, hall, time, seats)
        self._load_taken_seats_for_current_show()
        pdf_path = generate_ticket_pdf(
            booking_code=code,
            movie_title=movie_title,
            hall=hall,
            show_time=time,
            client_name=client_name,
            seats=seats,
        )
        self._open_pdf(str(pdf_path))
        msg_template = self._t("status_booked")
        base_text = msg_template.format(
            movie=movie_title,
            hall=hall,
            time=time,
            client=client_name,
            seats=", ".join(seats),
            code=code,
        )
        extra_price = ""
        if price_per_seat > 0:
            extra_price = f"\nType: {ticket_type} · Total: {total_price:.2f} лв."
        self.status_label.setText(f"{base_text}{extra_price}")
        for seat in seats:
            self.selected_seats[seat] = False
        self._update_summary()
        self._update_confirm_state()
        self._update_price_display()

    def _handle_cancel_booking(self) -> None:
        code = self.cancel_code_edit.text().strip()
        if not code:
            self.status_label.setText("Enter booking code to cancel.")
            return
        ok, reason = cancel_booking(code)
        if ok:
            self.status_label.setText(f"Booking {code} canceled.")
            self._load_taken_seats_for_current_show()
            self._update_price_display()
        else:
            if reason == "not_found":
                self.status_label.setText(f"No booking found with code {code}.")
            elif reason == "already_canceled":
                self.status_label.setText(f"Booking {code} is already canceled.")
            else:
                self.status_label.setText(f"Could not cancel booking {code}.")

    def _open_stats_dialog(self) -> None:
        dlg = StatsDialog(self, lang=self.current_lang)
        dlg.exec_()

    def _open_admin_window(self) -> None:
        dlg = AdminWindow(self)
        dlg.exec_()
        self._load_movies()
        self._update_summary()
        self._update_confirm_state()


class StatsDialog(QDialog):
    def __init__(self, parent=None, lang: str = "en"):
        super().__init__(parent)
        self.lang = lang
        self.translations = get_translations(lang)
        self.setWindowTitle(self.translations.get("stats_title", "Statistics"))
        self.resize(500, 400)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(
            [
                self.translations.get("stats_movie_column", "Movie"),
                self.translations.get("stats_tickets_column", "Tickets"),
            ]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self.table)
        self.setLayout(layout)
        self._load_data()

    def _load_data(self) -> None:
        rows = get_stats_by_movie()
        self.table.setRowCount(len(rows))
        for i, (title, count) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(title))
            self.table.setItem(i, 1, QTableWidgetItem(str(count)))K