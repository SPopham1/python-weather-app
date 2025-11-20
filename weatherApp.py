import sys
import os
from datetime import datetime, timezone, timedelta
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QSizePolicy, QGridLayout, QScrollArea, QFrame,
    QListWidget, QListWidgetItem
)
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtCore import Qt
import requests
import re

ICON_SIZE = 100

class WeatherCard(QFrame):
    def __init__(self, data, unit_symbol, unit):
        super().__init__()
        self.unit_symbol = unit_symbol
        self.unit = unit
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("background-color: #ffe8d6; border: 1px solid #ccc; border-radius: 8px; color: black")
        self.setLayout(QVBoxLayout())

        city_label = QLabel(f"🌇 City: {data.get('name', 'N/A')}")
        city_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        city_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        temp = data['main']['temp']
        temp_label = QLabel(f"🌡️ {temp} {unit_symbol}")

        desc = data['weather'][0]['description'].capitalize()
        desc_label = QLabel(f"🌥️ {desc}")

        humidity_label = QLabel(f"💧 Humidity: {data['main']['humidity']}%")
        wind_unit = "m/s" if unit == "metric" else "mph"
        wind_label = QLabel(f"🌬️ Wind: {data['wind']['speed']} {wind_unit}")
        pressure_label = QLabel(f"📊 Pressure: {data['main']['pressure']} hPa")

        tz_offset = data.get("timezone", 0)
        sunrise = self.convert_unix_to_local_time(data['sys']['sunrise'], tz_offset)
        sunset = self.convert_unix_to_local_time(data['sys']['sunset'], tz_offset)

        sunrise_label = QLabel(f"🌅 Sunrise: {sunrise}")
        sunset_label = QLabel(f"🌇 Sunset: {sunset}")

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_code = data['weather'][0].get("icon", "")
        pixmap = self.load_weather_icon(icon_code)
        if pixmap:
            icon_label.setPixmap(pixmap.scaled(ICON_SIZE, ICON_SIZE, Qt.AspectRatioMode.KeepAspectRatio))

        for lbl in [temp_label, desc_label, humidity_label, wind_label, pressure_label, sunrise_label, sunset_label]:
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFont(QFont("Arial", 10))

        self.layout().addWidget(city_label)
        self.layout().addWidget(icon_label)
        for lbl in [temp_label, desc_label, humidity_label, wind_label, pressure_label, sunrise_label, sunset_label]:
            self.layout().addWidget(lbl)

    def load_weather_icon(self, icon_code):
        if not icon_code:
            return None
        url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            img_data = response.content
            pixmap = QPixmap()
            pixmap.loadFromData(img_data)
            return pixmap
        except requests.RequestException:
            return None

    def convert_unix_to_local_time(self, unix_ts: int, offset_seconds: int) -> str:
        utc_time = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
        local_time = utc_time + timedelta(seconds=offset_seconds)
        return local_time.strftime("%H:%M:%S")


class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌤️ Weather Reporter")
        self.setGeometry(100, 100, 800, 600)

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

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Enter city name(s), comma separated")
        self.city_input.setClearButtonEnabled(True)
        self.city_input.textEdited.connect(self.show_suggestions)

        self.suggestion_list = QListWidget(self)
        self.suggestion_list.hide()
        self.suggestion_list.itemClicked.connect(self.insert_suggestion)

        input_layout.addWidget(self.city_input)

        self.get_weather_btn = QPushButton("Get Weather")
        self.get_weather_btn.clicked.connect(self.on_get_weather)
        input_layout.addWidget(self.get_weather_btn)

        self.unit_toggle_btn = QPushButton("Switch to imperial")
        self.unit_toggle_btn.clicked.connect(self.toggle_unit)
        input_layout.addWidget(self.unit_toggle_btn)

        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.suggestion_list)

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
                background-color: #ffddc0;
            }
            QLineEdit {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #aaa;
                border-radius: 5px;
                color: black;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QListWidget {
                background: white;
                color: black;
                border: 1px solid #aaa;
                max-height: 120px;
            }
        """)
    
    def show_suggestions(self, text):
        fragment = text.split(",")[-1].strip().lower()
        if not fragment or not self.cities:
            self.suggestion_list.hide()
            return

        matches = [c for c in self.cities if fragment in c.lower()]
        self.suggestion_list.clear()
        if matches:
            for m in matches[:10]:
                self.suggestion_list.addItem(QListWidgetItem(m))
            self.suggestion_list.show()
        else:
            self.suggestion_list.hide()

    def insert_suggestion(self, item):
        current_text = self.city_input.text()
        parts = [p.strip() for p in current_text.split(",")]
        parts[-1] = item.text()
        new_text = ", ".join(p for p in parts if p)
        self.city_input.setText(new_text)
        self.city_input.setCursorPosition(len(new_text))
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
        cities = [c.strip() for c in self.city_input.text().split(',') if c.strip()]
        if not cities:
            QMessageBox.warning(self, "Input Error", "Please enter one or more city names.")
            return

        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        cols = 2 if len(cities) <= 4 else 3

        for index, city in enumerate(cities):
            city = city.split(" - ")[0].strip()
            if not re.fullmatch(r"[A-Za-z\s\-']+", city):
                QMessageBox.warning(self, "Input Error", f"Invalid city name: {city}")
                return

            try:
                data = self.fetch_weather_data(city)
                if data:
                    card = WeatherCard(data, self.unit_symbol, self.unit)
                    row = index // cols
                    col = index % cols
                    self.grid_layout.addWidget(card, row, col)
                else:
                    QMessageBox.warning(self, "City Not Found", f"Weather data for '{city}' was not found.")
            except requests.RequestException:
                QMessageBox.critical(self, "Network Error", f"Failed to fetch weather for '{city}'.")

    def fetch_weather_data(self, city: str) -> dict | None:
        cache_key = f"{city.lower()}_{self.unit}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": self.api_key, "units": self.unit}
        response = requests.get(url, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            self.cache[cache_key] = data
            return data
        elif response.status_code == 404:
            return None
        else:
            response.raise_for_status()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec())
