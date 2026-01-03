import sys
import os
from datetime import datetime, timezone, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QCompleter,
    QLabel, QLineEdit, QPushButton, QMessageBox, QSizePolicy, QGridLayout, 
    QScrollArea, QFrame, QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt, QStringListModel, QObject, QThread, pyqtSignal
import requests
import re

ICON_SIZE = 100

class WeatherCard(QFrame):
    def __init__(self, data, unit_symbol, unit):
        super().__init__()

        self.unit_symbol = unit_symbol
        self.unit = unit
        self.data = data

        self.setObjectName("WeatherCard")
        self.setStyleSheet("""
            QFrame#WeatherCard {
                background-color: #EBD5AB;
                border-radius: 12px;
                border: 5px solid #628141;
                color: #1B211A;
            }
        """)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.build_ui()

    def build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(8)

        # ─── Header ───
        city = self.data.get("name", "N/A")
        country = self.data.get("sys", {}).get("country", "")
        header = QLabel(f"📍 {city}, {country}")
        header.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #1B211A")

        main.addWidget(header)

        # ─── Hero (icon + temp) ───
        hero = QHBoxLayout()
        hero.setSpacing(10)

        icon = QLabel()
        icon_code = self.data["weather"][0].get("icon", "")
        pixmap = self.load_weather_icon(icon_code)
        if pixmap:
            icon.setPixmap(pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        temp = QLabel(f"{self.data['main']['temp']:.1f}{self.unit_symbol}")
        temp.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        temp.setStyleSheet("color: #1B211A")

        desc = QLabel(self.data["weather"][0]["description"].capitalize())
        desc.setStyleSheet("color: #628141")

        temp_col = QVBoxLayout()
        temp_col.addWidget(temp)
        temp_col.addWidget(desc)

        hero.addWidget(icon)
        hero.addLayout(temp_col)
        hero.addStretch()

        main.addLayout(hero)

        # ─── Divider ───
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #628141")
        main.addWidget(line)

        # ─── Stats (compact) ───
        stats = QGridLayout()
        stats.setHorizontalSpacing(14)
        stats.setVerticalSpacing(4)

        wind_unit = "m/s" if self.unit == "metric" else "mph"
        tz_offset = self.data.get("timezone", 0)

        sunrise = self.convert_unix_to_local_time(self.data["sys"]["sunrise"], tz_offset)
        sunset = self.convert_unix_to_local_time(self.data["sys"]["sunset"], tz_offset)

        def stat(text):
            lbl = QLabel(text)
            lbl.setFont(QFont("Arial", 9))
            lbl.setStyleSheet("color: #1B211A")
            return lbl

        stats.addWidget(stat(f"💧 {self.data['main']['humidity']}%"), 0, 0)
        stats.addWidget(stat(f"🌬 {self.data['wind']['speed']} {wind_unit}"), 0, 1)
        stats.addWidget(stat(f"📊 {self.data['main']['pressure']} hPa"), 1, 0)
        stats.addWidget(stat(f"🌅 {sunrise}"), 1, 1)
        stats.addWidget(stat(f"🌇 {sunset}"), 2, 0)

        main.addLayout(stats)

    # ───── Helpers (unchanged logic) ─────
    def load_weather_icon(self, icon_code):
        if not icon_code:
            return None
        url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            pixmap = QPixmap()
            pixmap.loadFromData(response.content)
            return pixmap
        except requests.RequestException:
            return None

    def convert_unix_to_local_time(self, unix_ts: int, offset_seconds: int) -> str:
        utc_time = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
        local_time = utc_time + timedelta(seconds=offset_seconds)
        return local_time.strftime("%H:%M")

class CityInput(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.suggestion_list = None

    def set_suggestion_list(self, list_widget):
        self.suggestion_list = list_widget

    def keyPressEvent(self, event):
        if self.suggestion_list and self.suggestion_list.isVisible():
            key = event.key()

            if key == Qt.Key.Key_Down:
                row = self.suggestion_list.currentRow()
                self.suggestion_list.setCurrentRow(row + 1)
                return

            elif key == Qt.Key.Key_Up:
                row = self.suggestion_list.currentRow()
                self.suggestion_list.setCurrentRow(max(0, row - 1))
                return

            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.suggestion_list.currentItem()
                if item:
                    self.parent().insert_suggestion(item)
                return

            elif key == Qt.Key.Key_Escape:
                self.suggestion_list.hide()
                return

        super().keyPressEvent(event)

class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌤️ Weather Reporter")
        self.setGeometry(100, 100, 800, 800)

        # Load API key from environment variable or local .env file
        self.api_key = os.environ.get("OPENWEATHER_API_KEY")
        if not self.api_key:
            env_path = os.path.join(os.path.dirname(__file__), ".env")
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as ef:
                    for line in ef:
                        if line.strip().startswith("OPENWEATHER_API_KEY="):
                            self.api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break

        if not self.api_key:
            QMessageBox.critical(self, "API Key Missing", "OpenWeather API key not found.\nSet the environment variable `OPENWEATHER_API_KEY` or create a `.env` file in the project root with `OPENWEATHER_API_KEY=your_key`.")
            sys.exit(1)
        self.unit = "metric"
        self.unit_symbol = "°C"
        self.cache = {}

        try:
            with open("locations.txt", "r", encoding="utf-8") as f:
                self.cities = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.cities = []

        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        input_layout = QHBoxLayout()

        # 1️⃣ Create the input FIRST
        self.city_input = CityInput(self)
        self.city_input.setPlaceholderText(
            "Enter locations like: London,GB; Rome,IT; New York,US"
        )
        self.city_input.setClearButtonEnabled(True)

        # 2️⃣ Create the suggestion list SECOND
        self.suggestion_list = QListWidget(self)
        self.suggestion_list.hide()
        self.suggestion_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.suggestion_list.itemClicked.connect(self.insert_suggestion)

        # 3️⃣ Link them THIRD (now both exist)
        self.city_input.set_suggestion_list(self.suggestion_list)
        self.city_input.textEdited.connect(self.show_suggestions)

        input_layout.addWidget(self.city_input)

        self.get_weather_btn = QPushButton("Get Weather")
        self.get_weather_btn.clicked.connect(self.on_get_weather)
        input_layout.addWidget(self.get_weather_btn)

        self.unit_toggle_btn = QPushButton("Switch to imperial")
        self.unit_toggle_btn.clicked.connect(self.toggle_unit)
        input_layout.addWidget(self.unit_toggle_btn)

        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.suggestion_list)

        # Scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.cards_widget = QWidget()
        self.grid_layout = QGridLayout()
        self.cards_widget.setLayout(self.grid_layout)
        self.scroll_area.setWidget(self.cards_widget)

        main_layout.addWidget(self.scroll_area)
        self.setLayout(main_layout)


    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #1B211A;
                color: #EBD5AB;
                font-family: Arial;
            }

            QLineEdit {
                background-color: #EBD5AB;
                color: #1B211A;
                font-size: 14px;
                padding: 6px;
                border: 1px solid #628141;
                border-radius: 6px;
            }

            QLineEdit:focus {
                border: 1px solid #628141; /* no highlight change */
                outline: none;
            }

            QPushButton {
                background-color: #628141;
                color: #EBD5AB;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 12px;
            }

            QPushButton:hover {
                background-color: #628141; /* remove hover highlight */
                color: #EBD5AB;
            }

            QPushButton:pressed {
                background-color: #628141;
            }

            QPushButton:disabled {
                background-color: #3f4f2c;
                color: #9fa88c;
            }

            QListWidget {
                background-color: #EBD5AB;
                color: #1B211A;
                border: 1px solid #628141;
                border-radius: 6px;
                max-height: 120px;
            }

            QListWidget::item:selected {
                background-color: #8BAE66;
                color: #1B211A;
            }

            QListWidget::item:selected:!active {
                background-color: #8BAE66;
                color: #1B211A;
            }

            QListWidget::item:hover {
                background-color: #EBD5AB;
            }

            QScrollArea {
                border: none;
            }

            QLabel {
                background: transparent;
            }
        """)
    
    def show_suggestions(self, text):
        fragment = text.split(";")[-1].strip().lower()
        if not fragment or not self.cities:
            self.suggestion_list.hide()
            return

        matches = [
            c for c in self.cities 
            if c.lower().startswith(fragment)
        ][:10]
        self.suggestion_list.clear()
        if matches:
            for m in matches:
                self.suggestion_list.addItem(QListWidgetItem(m))
            self.suggestion_list.setCurrentRow(0)
            self.suggestion_list.show()
        else:
            self.suggestion_list.hide()

    def insert_suggestion(self, item):
        current_text = self.city_input.text()
        current = self.city_input.text()

        parts = [p.strip() for p in current.split(";") if p.strip()]
        parts[-1] = item.text()

        new_text = "; ".join(parts)
        self.city_input.setText(new_text + "; ")
        self.city_input.setCursorPosition(len(self.city_input.text()))
        self.suggestion_list.hide()

    def toggle_unit(self):
        if self.unit == "metric":
            self.unit = "imperial"
            self.unit_symbol = "°F"
            self.unit_toggle_btn.setText("Switch to metric")
        else:
            self.unit = "metric"
            self.unit_symbol = "°C"
            self.unit_toggle_btn.setText("Switch to imperial")
        self.on_get_weather()

    def on_get_weather(self):
        cities = [c.strip() for c in self.city_input.text().split(';') if c.strip()]

        if not cities:
            QMessageBox.warning(self, "Input Error", "Please enter one or more city names.")
            return

        self.get_weather_btn.setEnabled(False)
        self.unit_toggle_btn.setEnabled(False)


        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.threads = []
        self.workers = []
        self.pending_results = 0
        self.any_success = False

        for index, city in enumerate(cities):
            if not re.compile(r"^[A-Za-zÀ-ÿ\s\-']+,\s*[A-Z]{2}$").match(city):
                QMessageBox.warning(
                    self,
                    "Invalid format",
                    f"Invalid location format:\n\n{city}\n\nUse: City,CC (e.g. London,GB)"
                )
                self.get_weather_btn.setEnabled(True)
                self.unit_toggle_btn.setEnabled(True)
                return

            thread = QThread(self)
            worker = WeatherWorker(city, self.unit, self.api_key, index)
            worker.moveToThread(thread)

            thread.started.connect(worker.run)
            worker.finished.connect(self.on_weather_result)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)

            self.threads.append(thread)
            self.workers.append(worker)

            self.pending_results += 1
            thread.start()

    def on_weather_result(self, city, data, error, index):
        self.pending_results -= 1

        if error:
            QMessageBox.critical(self, "Error", f"Failed to fetch weather for '{city}'.")
        elif not data:
            QMessageBox.warning(self, "City Not Found", f"'{city}' was not found.")
        else:
            self.any_success = True
            cols = 2
            card = WeatherCard(data, self.unit_symbol, self.unit)
            row = index // cols
            col = index % cols
            self.grid_layout.addWidget(card, row, col)

        if self.pending_results == 0:
            self.get_weather_btn.setEnabled(True)
            self.unit_toggle_btn.setEnabled(True)

            if not self.any_success:
                QMessageBox.warning(self, "Input Error", "No valid city names to fetch.")

            # Cleanup
            self.threads.clear()
            self.workers.clear()


class WeatherWorker(QObject):
    finished = pyqtSignal(str, object, object, int)

    def __init__(self, city, unit, api_key, index):
        super().__init__()
        self.city = city
        self.unit = unit
        self.api_key = api_key
        self.index = index

    def run(self):
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {
                "q": self.city,
                "appid": self.api_key,
                "units": self.unit
            }
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200: ## success
                self.finished.emit(self.city, response.json(), None, self.index)
            elif response.status_code == 404: ## link broken
                self.finished.emit(self.city, None, None, self.index)
            else:
                response.raise_for_status()

        except Exception as e:
            self.finished.emit(self.city, None, e, self.index)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec())
