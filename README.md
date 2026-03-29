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
