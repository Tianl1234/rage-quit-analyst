# 🚀 Rage Quit WPM Overlay

A lightweight, always‑on‑top overlay that displays your current typing speed (WPM) in real time.  
When you type too fast (rage threshold), it triggers a **Zen Mode** – a full‑screen popup that forces you to take a break and plays calming music.  
Includes Spotify‑style music controls with **play/pause, stop, previous/next track, volume slider, and current song title** – all hidden by default and revealed with a double‑click.

---

## ✨ Features

- **Live WPM display** – colour‑coded emojis (🐢🐇🚀🔥⚡🤬) for different speed levels  
- **Rolling time window** (default 5 seconds) for smooth WPM calculation  
- **Rage detection** – when WPM exceeds a threshold (default 100), Zen Mode activates  
- **Zen Mode popup** – blocks the screen for 5 seconds, plays music (if available)  
- **Intelligent music handling** during Zen Mode:  
  - If music was already playing → it keeps playing uninterrupted  
  - If no music was playing → Zen Mode starts a song and stops it afterwards  
- **Music controls** (hidden by default, appear on double‑click):  
  - ⏮ Previous song  
  - 🔍▶ Scan folder for MP3s and play the first one  
  - ⏭ Next song  
  - ⏸️/▶️ Pause / resume  
  - ⏹️ Stop (clears the title)  
  - 🔊 Volume slider  
  - 🎵 Current song title display  
- **Drag‑anywhere overlay** – click and drag the WPM label or any button  
- **No console window** when saved as `.pyw` (automatic console hiding)  
- **Auto‑install missing dependencies** (`pynput`, `pygame`) on first run  
- Works with **Python 3.10–3.13** (fallback if `pygame.mixer` is unavailable – music disabled, overlay still works)

---

## 📦 Installation & Dependencies

The script **automatically installs** the required packages when you run it for the first time.  
If you prefer to install them manually, open a terminal and run:

```bash
pip install pynput pygame
