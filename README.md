# 🧘‍♂️ Rage-Quit Analyst & Zen Widget

A completely transparent, floating desktop widget written in Python that monitors your typing speed in the background. If you start aggressively smashing your keyboard (Rage Mode!), it temporarily intervenes with a "Zen Mode" popup and automatically plays relaxing music from your custom playlist to help you calm down.

## ✨ Features

* **Transparent Floating UI:** Uses `.pyw` and transparency keying to float seamlessly on your desktop without window borders or a background.
* **Live KPM Tracking:** Calculates Keystrokes Per Minute (KPM) in real-time using background multithreading.
* **Dynamic Zen Playlist:** Automatically detects and plays any `.mp3` files located in the project folder. It perfectly loops a single track or cycles through multiple songs.
* **Drag & Drop:** You can click and drag the floating numbers to move the widget anywhere on your screen.
* **No Console Window:** Runs completely silently in the background without annoying command prompt windows.

## 🛠️ Preparation & Installation

To run this widget properly on your system, follow these simple preparation steps:

### 1. Folder Setup
Create a new folder on your computer for this project (e.g., `Rage-Analyst`). Everything needs to be inside this folder.

### 2. Save the Script
Save the Python code inside this folder and name it exactly **`rage_analyst.pyw`**. 
*(Note: The `w` at the end of `.pyw` is crucial! It tells Windows to run the script as a background GUI app without opening a black command prompt window).*

### 3. Install Dependencies
This script requires two external libraries: `pynput` (to read keystrokes globally) and `pygame` (for asynchronous audio playback). 
Open your terminal or command prompt and run:
```bash
pip install pynput pygame
