WPM Live-Overlay with Rage Detection & Zen Mode
================================================

A lightweight, always-on-top overlay that displays your current typing speed (WPM) in real time.
When you type too fast (rage threshold), it triggers a Zen Mode – a full-screen popup that forces
you to take a break and plays calming music. Includes Spotify‑style music controls and a volume slider.

Features
--------
- Live WPM display with colour‑coded emojis (🐢🐇🚀🔥⚡🤬)
- Rolling time window (default 5 seconds) for smooth WPM calculation
- Rage detection – when WPM exceeds a threshold (default 100), Zen Mode activates
- Zen Mode popup – blocks the screen for 5 seconds, plays music (if available)
- Intelligent music handling during Zen Mode:
  * If music was already playing → it keeps playing uninterrupted, Zen Mode just shows the popup
  * If no music was playing → Zen Mode starts a song and stops it afterwards
- Music controls – scan folder for MP3s, previous/next track – **hidden by default, appear on double‑click**
- Volume slider – adjust music volume (hidden together with music controls)
- Drag‑anywhere overlay (click and drag the WPM label)
- Auto‑install missing dependencies (pynput, pygame) on first run
- No console window when saved as .pyw

Recommended Python Version
--------------------------
For best compatibility (especially for pygame.mixer and trouble‑free installation), use
**Python 3.10 or 3.11**. The script has been adapted to work with Python 3.13 as well,
but on 3.13 pygame.mixer may be unavailable – the overlay will then run **without music**
(all other features still work).

| Python Version | Music Support | Status      |
|----------------|---------------|-------------|
| 3.10 / 3.11    | ✅ Full       | recommended |
| 3.12           | ⚠️ limited    | might work, but not tested |
| 3.13           | ⚠️ fallback   | music only if pygame.mixer initialises; otherwise music buttons are disabled |

Installation & Dependencies
---------------------------
The script **automatically installs** the required packages when you run it for the first time.
If you prefer to install them manually, open a terminal and run:

    pip install pynput pygame

- pynput – listens to keyboard events (thread‑safe)
- pygame – plays MP3 files (pygame.mixer)

How to Run
----------
1. Save the script (e.g. as wpm_overlay.pyw).
2. Place some .mp3 files in the **same folder** if you want music (optional).
3. Double‑click the file:
   - Use **.pyw** extension → runs **without a console window** (silent background).
   - Use **.py** extension → shows a console window with log messages (useful for debugging).

The overlay will appear at the top‑right corner of your screen (coordinates +1500+100).
You can drag it anywhere.

Usage
-----
Main Window:
- **WPM label** – shows current words per minute + emoji.  
  **Double‑click** the WPM label to show/hide the music controls (⏮, 🔍▶, ⏭ and volume slider).
- **✖ button** – quits the application (always visible).

Music controls (hidden by default, appear on double‑click):
- **⏮ button** – previous song
- **🔍 ▶ button** – scan folder for MP3s and play the first one
- **⏭ button** – next song
- **Volume slider** – adjust the music volume (only when controls are visible)

Zen Mode:
- When you type faster than the rage threshold (default 100 WPM), a popup appears for 5 seconds.
- During those 5 seconds you cannot type (the popup blocks input).
- Music behaviour:
  * If music was already playing before Zen Mode → it continues, and after Zen Mode it keeps playing.
  * If no music was playing → Zen Mode starts a song and stops it when the popup closes.

All buttons remain clickable even during Zen Mode, so you can still change tracks.

Configuration (inside the script)
---------------------------------
You can tweak these values at the top of the script (after the imports):

    ZEITFENSTER_SEK: float = 5.0       # rolling window for WPM (seconds)
    RAGE_SCHWELLE: int     = 100       # WPM that triggers Zen Mode
    ZEN_DAUER_MS: int      = 5_000     # how long Zen popup stays (milliseconds)
    ZEICHEN_PRO_WORT: int  = 5         # average characters per word
    POLL_INTERVAL_MS: int  = 150       # how often to update WPM (ms)
    SONG_CHECK_MS: int     = 1_000     # how often to check if song ended (ms)

Troubleshooting
---------------
- **Nothing happens when I double‑click the .pyw file**  
  → Check the fehler.log file created in the same folder – it contains error messages.
  → Run the script as .py (with console) to see live errors.

- **Music buttons are disabled / no sound**  
  → The script detected that pygame.mixer is not available. This often happens with Python 3.13.
  → Try installing a different pygame version:
        pip uninstall pygame
        pip install pygame==2.5.2
  → Or switch to Python 3.11 (recommended).

- **pynput installation fails**  
  → Make sure you have an internet connection and that pip is up to date:
        python -m pip install --upgrade pip

- **Overlay does not appear**  
  → The default position is +1500+100 (near the top‑right). If your screen resolution is smaller,
    change the coordinates in the script: root.geometry("+1500+100") → e.g. "+500+50".
