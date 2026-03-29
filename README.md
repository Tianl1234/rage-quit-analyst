# 🧘‍♂️ Rage Analyst (WPM Monitor & Zen Mode)

**Rage Analyst** is a lightweight, transparent desktop overlay for Windows that monitors your typing speed (WPM) in real-time. It doesn't just track your performance—it acts as your digital therapist. If you start typing too fast (a sign of "keyboard rage"), it triggers **Zen Mode** to force a break.

---

## ✨ Features

* **Real-time WPM Tracking**: Smoothly calculates your words-per-minute using a rolling time window.
* **Dynamic Emojis**: Visual feedback on your typing "vibe":
    * 🐢 (20 WPM) -> 🚀 (60 WPM) -> ⚡ (100 WPM) -> 🤬 (RAGE).
* **Zen Mode**: When you exceed the "Rage Threshold," the app locks the screen with a calming message and optionally plays music to lower your cortisol levels.
* **Integrated Music Player**: Control your `.mp3` playlist directly from the overlay (supports Shuffle, Play/Pause, and Volume).
* **Transparent Overlay**: Stays on top of all windows without being intrusive.
* **Session Stats**: Tracks Max WPM, Average WPM, Total Keystrokes, and how many times you nearly lost your cool (Zen Count).

---

## 🚀 Quick Start

### Prerequisites
* **Python 3.10+** (Fully compatible with Python 3.13).
* **Windows** (Optimized for Win32 API console hiding and transparency).

### Installation
1.  Clone this repository or save the script.
2.  Install dependencies:
    ```bash
    pip install pynput pygame
    ```
3.  Place some `.mp3` files in the same folder as the script for the music feature.
4.  (Optional) Add an `alarm.wav` for high-speed alerts.

### Usage
Run the script:
```bash
python rage_analyst.py
⌨️ Controls & HotkeysActionControlMove WindowClick and drag any part of the UI.Music ControlsDouble-click the WPM label to show/hide.StatisticsPress F1 or click the 📊 icon.SettingsPress F2 or click the ⚙️ icon.Toggle ThemePress F3 (Switch between Dark/Light).Pause SessionPress F4 to stop tracking temporarily.🛠 ConfigurationThe app creates a rage_analyst_config.json file where you can permanently save your preferences:rage_schwelle: The WPM limit before Zen Mode triggers.zeitfenster_sek: How many seconds of history to use for calculation.font_size: Adjust the UI size to fit your monitor.📝 Technical NotesPerformance: Uses a dedicated thread for the keylogger to ensure zero input lag.Safety: Includes a DummyWriter to prevent "WinError 6" crashes when running as a windowed process without a console.Privacy: This is a local-only tool. No keystrokes are saved or transmitted; only timestamps are kept in memory for WPM calculation.
