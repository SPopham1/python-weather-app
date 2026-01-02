# Weather Reporter App

A desktop weather application built with **Python and PyQt6** that allows users to view real-time weather data for multiple cities using the **OpenWeatherMap API**.

The app features a clean card-based UI, unit switching, city suggestions, caching, and detailed weather information including sunrise and sunset times.

---

## Features

- Search weather for **multiple cities at once**
- **Autocomplete suggestions** using a local city list
- Toggle between **metric (°C)** and **imperial (°F)** units
- Weather displayed in responsive **cards**
- **In-memory caching** to reduce API calls
- Local **sunrise and sunset times** (timezone-aware)
- Custom-styled PyQt6 interface
- Weather icons loaded dynamically from OpenWeather

---

## Technologies Used

- **Python 3**
- **PyQt6** (GUI)
- **OpenWeatherMap API**
- **Requests** (HTTP requests)
- **Qt Widgets & Layouts**

---

## How to Run

### 1. Clone the repository
```bash
git clone https://github.com/your-username/weather-reporter.git
cd weather-reporter
```

### 2. Install dependencies
```bash
pip install PyQt6 requests
```

### 3. Set up your OpenWeather API key
You can do either of the following:
#### Option A - Environment variable
```bash
export OPENWEATHER_API_KEY=your_api_key_here
```
#### Option B - .env file
create a .env file in the project root:
```bash
OPENWEATHER_API_KEY=your_api_key_here
```

4. Run the app
```bash
python main.py
```
