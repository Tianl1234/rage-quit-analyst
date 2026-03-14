# ===== Error logging for .pyw mode =====
import sys
import traceback

# If no terminal (e.g. .pyw), redirect errors to a log file
if not sys.stdout:
    try:
        log_file = open("fehler.log", "w", encoding="utf-8")
        sys.stderr = log_file
        sys.stdout = log_file
    except:
        pass

# ===== Rest of imports =====
import time
import threading
import logging
import os
import subprocess
import tkinter as tk
from tkinter import messagebox

# Optionally hide console window (works even with .py)
try:
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
except:
    pass

# ------------------------------------------------------------
# 1. Check Python version (special handling for 3.13)
# ------------------------------------------------------------
PY_VERSION = sys.version_info[:2]
IS_PY313 = PY_VERSION >= (3, 13)

if IS_PY313:
    print("🔔 Python 3.13 detected – enabling compatibility mode")
    # pynput must be at least version 1.7.8
    try:
        import pynput
        if pynput.__version__ < "1.7.8":
            print("⚠️  Old pynput version detected – upgrading...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pynput"])
    except (ImportError, AttributeError):
        pass

# ------------------------------------------------------------
# 2. Auto‑install missing packages
# ------------------------------------------------------------
REQUIRED_PACKAGES = ["pynput", "pygame"]

for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
    except ImportError:
        print(f"🔧 {pkg} not found – attempting installation...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✅ {pkg} installed successfully.")
        except Exception as e:
            print(f"❌ Failed to install {pkg}: {e}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Installation Error",
                f"Package '{pkg}' could not be installed.\n\n"
                "Please run this command manually:\n"
                f"  {sys.executable} -m pip install {pkg}\n\n"
                "Make sure you have a working internet connection."
            )
            sys.exit(1)

# ------------------------------------------------------------
# 3. Now we can import the packages
# ------------------------------------------------------------
from pynput import keyboard
import pygame

# ------------------------------------------------------------
# 4. Check mixer availability
# ------------------------------------------------------------
MIXER_VERFUEGBAR = False
try:
    pygame.mixer.init()
    MIXER_VERFUEGBAR = True
    print("✅ pygame.mixer available – music supported")
except Exception as e:
    print(f"⚠️  pygame.mixer not available: {e}")
    print("   Overlay will run without music functions.")

# ------------------------------------------------------------
# 5. Main script with intelligent Zen music logic
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# Configuration
ZEITFENSTER_SEK: float = 5.0       # rolling window for WPM (seconds)
RAGE_SCHWELLE: int     = 100       # WPM that triggers Zen Mode
ZEN_DAUER_MS: int      = 5_000     # how long Zen popup stays (milliseconds)
ZEICHEN_PRO_WORT: int  = 5         # average characters per word
POLL_INTERVAL_MS: int  = 150       # how often to update WPM (ms)
SONG_CHECK_MS: int     = 1_000     # how often to check if song ended (ms)

# Global state (thread‑safe)
_lock             = threading.Lock()
anschlaege: list[float] = []
beruhigungs_modus: bool  = False

playlist: list[str]     = []
aktueller_song_index: int = 0

# Flags for intelligent Zen music handling
musik_lief_vor_zen: bool = False          # Was music playing before Zen Mode?
musik_gestartet_durch_zen: bool = False   # Was the current song started by Zen Mode?

# ------------------------------------------------------------
# 6. Keylogger (pynput 1.7.8+ is compatible)
# ------------------------------------------------------------
def on_press(key) -> None:
    with _lock:
        anschlaege.append(time.time())

def starte_keylogger() -> None:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ------------------------------------------------------------
# 7. Playlist & Audio (with mixer check)
# ------------------------------------------------------------
def lade_playlist() -> None:
    global playlist
    playlist = sorted(
        f for f in os.listdir() if f.lower().endswith(".mp3")
    )
    log.info("Playlist loaded: %d songs found", len(playlist))
    if not playlist:
        log.warning("No MP3 files in current directory!")

def spiele_song(index: int) -> None:
    """Play the song at position `index`. Used internally and by manual buttons."""
    if not MIXER_VERFUEGBAR:
        log.warning("Mixer not available – cannot play")
        return
    if not playlist:
        log.warning("No playlist loaded – nothing to play.")
        return

    idx = index % len(playlist)
    song = playlist[idx]
    try:
        pygame.mixer.music.load(song)
        pygame.mixer.music.play()
        log.info("Playing: %s", song)

        if len(playlist) > 1:
            root.after(SONG_CHECK_MS, _song_watcher)
    except Exception as e:
        log.error("Error playing '%s': %s", song, e)

def spiele_naechsten_song() -> None:
    global aktueller_song_index
    if not playlist or not MIXER_VERFUEGBAR:
        return
    aktueller_song_index = (aktueller_song_index + 1) % len(playlist)
    spiele_song(aktueller_song_index)

def vorheriger_song() -> None:
    global aktueller_song_index
    if not playlist or not MIXER_VERFUEGBAR:
        return
    aktueller_song_index = (aktueller_song_index - 1) % len(playlist)
    spiele_song(aktueller_song_index)

def scan_und_spiele() -> None:
    global playlist, aktueller_song_index
    lade_playlist()
    if playlist and MIXER_VERFUEGBAR:
        aktueller_song_index = 0
        spiele_song(0)
        log.info("Scan complete – first song started.")
    elif not MIXER_VERFUEGBAR:
        log.warning("Mixer not available – cannot play music")
        if playlist:
            messagebox.showinfo("Info", 
                "Music functions are disabled because pygame.mixer is not available.\n"
                "The WPM overlay will still work.")
    else:
        log.warning("No MP3 files found – nothing played.")

def _song_watcher() -> None:
    """Called only when more than one song in playlist.
       Checks if current song ended and plays next, but ONLY in Zen Mode."""
    if not MIXER_VERFUEGBAR:
        return
    if not pygame.mixer.music.get_busy():
        if beruhigungs_modus:
            spiele_naechsten_song()
    else:
        root.after(SONG_CHECK_MS, _song_watcher)

# ------------------------------------------------------------
# 8. WPM analysis
# ------------------------------------------------------------
WPM_STUFEN: list[tuple[int, str, str]] = [
    (20,  "🐢", "#4CAF50"),
    (40,  "🐇", "#8BC34A"),
    (60,  "🚀", "#FFEB3B"),
    (80,  "🔥", "#FF9800"),
    (100, "⚡", "#FF5722"),
    (999, "🤬", "#F44336"),
]

def get_wpm_emoji_und_farbe(wpm: int) -> tuple[str, str]:
    for schwelle, emoji, farbe in WPM_STUFEN:
        if wpm < schwelle:
            return emoji, farbe
    return "🤬", "#F44336"

def berechne_wpm() -> int:
    jetzt = time.time()
    grenze = jetzt - ZEITFENSTER_SEK

    with _lock:
        while anschlaege and anschlaege[0] < grenze:
            anschlaege.pop(0)

        if len(anschlaege) < 2:
            return 0

        vergangen = jetzt - anschlaege[0]
        vergangen = max(vergangen, 2.0)
        return round((len(anschlaege) / ZEICHEN_PRO_WORT) / (vergangen / 60))

def analysiere_tippgeschwindigkeit() -> None:
    global beruhigungs_modus

    wpm = berechne_wpm()
    emoji, farbe = get_wpm_emoji_und_farbe(wpm)
    lbl_wpm.config(text=f"{wpm} WPM {emoji}", fg=farbe)

    if wpm >= RAGE_SCHWELLE and not beruhigungs_modus:
        loese_zen_modus_aus()

    root.after(POLL_INTERVAL_MS, analysiere_tippgeschwindigkeit)

# ------------------------------------------------------------
# 9. Zen Mode popup (with intelligent music control)
# ------------------------------------------------------------
def loese_zen_modus_aus() -> None:
    global beruhigungs_modus, musik_lief_vor_zen, musik_gestartet_durch_zen
    beruhigungs_modus = True
    log.info("Zen Mode activated (WPM >= %d)", RAGE_SCHWELLE)

    # Check if music is currently playing
    if MIXER_VERFUEGBAR:
        musik_lief_vor_zen = pygame.mixer.music.get_busy()
        if not musik_lief_vor_zen:
            # No music before → start a song
            spiele_naechsten_song()
            musik_gestartet_durch_zen = True
            log.info("Zen Mode starts its own song")
        else:
            # Music already playing → let it continue
            musik_gestartet_durch_zen = False
            log.info("Zen Mode keeps existing music playing")
    else:
        musik_lief_vor_zen = False
        musik_gestartet_durch_zen = False

    # Create Zen popup
    zen = tk.Toplevel(root)
    zen.title("ZEN MODE")
    zen.geometry("600x300")
    zen.attributes("-topmost", True)
    zen.configure(bg="#2c3e50")
    zen.overrideredirect(True)

    text = "⚠️ RAGE QUIT DANGER ⚠️\n\nHands off the keyboard!\nTake a deep breath... 🧘"
    if not MIXER_VERFUEGBAR:
        text += "\n\n(Note: Music is disabled)"
    
    tk.Label(
        zen,
        text=text,
        font=("Helvetica", 20, "bold"),
        fg="white",
        bg="#2c3e50",
        pady=50,
    ).pack(expand=True)

    def schliesse_zen() -> None:
        global beruhigungs_modus, musik_gestartet_durch_zen, musik_lief_vor_zen
        # Stop music only if it was started by Zen Mode AND no music was playing before
        if MIXER_VERFUEGBAR and musik_gestartet_durch_zen and not musik_lief_vor_zen:
            try:
                pygame.mixer.music.stop()
                log.info("Zen Mode stops its own song")
            except Exception as e:
                log.error("Could not stop music: %s", e)

        with _lock:
            anschlaege.clear()

        beruhigungs_modus = False
        log.info("Zen Mode ended.")
        zen.destroy()

    zen.after(ZEN_DAUER_MS, schliesse_zen)

# ------------------------------------------------------------
# 10. Window dragging
# ------------------------------------------------------------
_drag_x: int = 0
_drag_y: int = 0

def start_move(event: tk.Event) -> None:
    global _drag_x, _drag_y
    _drag_x, _drag_y = event.x, event.y

def do_move(event: tk.Event) -> None:
    x = root.winfo_x() + (event.x - _drag_x)
    y = root.winfo_y() + (event.y - _drag_y)
    root.geometry(f"+{x}+{y}")

# ------------------------------------------------------------
# 11. Toggle music controls (hidden by default)
# ------------------------------------------------------------
def toggle_music_controls(event=None):
    if zeile2.winfo_ismapped():
        zeile2.pack_forget()
    else:
        # Before showing, update volume scale to current mixer volume
        if MIXER_VERFUEGBAR:
            current_vol = pygame.mixer.music.get_volume()
            volume_var.set(int(current_vol * 100))
        zeile2.pack(side="top", fill="x", pady=(0, 5))

# ------------------------------------------------------------
# 12. Volume control callback
# ------------------------------------------------------------
def volume_changed(val):
    if MIXER_VERFUEGBAR:
        try:
            pygame.mixer.music.set_volume(float(val) / 100.0)
        except:
            pass

# ------------------------------------------------------------
# 13. Clean exit
# ------------------------------------------------------------
def programm_beenden() -> None:
    log.info("Shutting down.")
    if MIXER_VERFUEGBAR:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass
    root.destroy()

# ------------------------------------------------------------
# 14. Main program
# ------------------------------------------------------------
if __name__ == "__main__":
    # Load playlist (if any)
    lade_playlist()

    # Start keylogger thread
    keylogger_thread = threading.Thread(target=starte_keylogger, daemon=True)
    keylogger_thread.start()

    # Create main window
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    TRANSPARENT = "#000001"
    root.configure(bg=TRANSPARENT)
    root.wm_attributes("-transparentcolor", TRANSPARENT)
    root.geometry("+1500+100")

    # If mixer unavailable, disable music buttons and volume
    btn_state = "normal" if MIXER_VERFUEGBAR else "disabled"
    volume_state = tk.NORMAL if MIXER_VERFUEGBAR else tk.DISABLED

    # Main frame
    frame = tk.Frame(root, bg=TRANSPARENT)
    frame.pack()

    # ---- Row 1: WPM display + close button ----
    zeile1 = tk.Frame(frame, bg=TRANSPARENT)
    zeile1.pack(side="top", fill="x")

    lbl_wpm = tk.Label(
        zeile1,
        text="0 WPM 🐢",
        font=("Helvetica", 36, "bold"),
        fg="#4CAF50",
        bg=TRANSPARENT,
    )
    lbl_wpm.pack(side="left", padx=10)

    btn_close = tk.Button(
        zeile1,
        text="✖",
        font=("Arial", 8),
        fg="gray",
        bg=TRANSPARENT,
        bd=0,
        activebackground=TRANSPARENT,
        activeforeground="white",
        cursor="hand2",
        command=programm_beenden,
    )
    btn_close.pack(side="right", anchor="n")

    # ---- Row 2: Music controls (hidden by default) ----
    zeile2 = tk.Frame(frame, bg=TRANSPARENT)

    # Previous button
    btn_prev = tk.Button(
        zeile2,
        text="⏮",
        font=("Segoe UI", 14),
        fg="white",
        bg="#2c3e50",
        bd=0,
        padx=10,
        activebackground="#34495e",
        activeforeground="white",
        cursor="hand2",
        state=btn_state,
        command=vorheriger_song
    )
    btn_prev.pack(side="left", padx=5)

    # Scan & play button
    btn_play_scan = tk.Button(
        zeile2,
        text="🔍 ▶",
        font=("Segoe UI", 14),
        fg="white",
        bg="#2c3e50",
        bd=0,
        padx=10,
        activebackground="#34495e",
        activeforeground="white",
        cursor="hand2",
        state=btn_state,
        command=scan_und_spiele
    )
    btn_play_scan.pack(side="left", padx=5)

    # Next button
    btn_next = tk.Button(
        zeile2,
        text="⏭",
        font=("Segoe UI", 14),
        fg="white",
        bg="#2c3e50",
        bd=0,
        padx=10,
        activebackground="#34495e",
        activeforeground="white",
        cursor="hand2",
        state=btn_state,
        command=spiele_naechsten_song
    )
    btn_next.pack(side="left", padx=5)

    # Volume slider
    volume_var = tk.DoubleVar(value=50)  # default 50%
    volume_scale = tk.Scale(
        zeile2,
        from_=0, to=100,
        orient="horizontal",
        variable=volume_var,
        command=volume_changed,
        length=100,
        showvalue=0,
        bg="#2c3e50",
        fg="white",
        troughcolor="#34495e",
        sliderlength=20,
        state=volume_state
    )
    volume_scale.pack(side="left", padx=5)

    # Initially hide row 2
    zeile2.pack_forget()

    # Bind double-click on WPM label to toggle music controls
    lbl_wpm.bind("<Double-Button-1>", toggle_music_controls)

    # Make all visible widgets draggable (except volume scale – it has its own bindings)
    for widget in (btn_prev, btn_play_scan, btn_next, lbl_wpm, zeile1, frame):
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)

    # Start WPM monitoring
    analysiere_tippgeschwindigkeit()

    # Info popup if music disabled
    if not MIXER_VERFUEGBAR:
        log.info("Note: Music controls disabled (pygame.mixer not available)")
        root.after(1000, lambda: messagebox.showinfo(
            "Music disabled",
            "pygame.mixer is not available.\n"
            "Music controls have been disabled.\n"
            "The WPM overlay will still work."
        ))

    # Main loop
    root.mainloop()
