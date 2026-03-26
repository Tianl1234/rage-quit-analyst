#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# ===== GANZ AM ANFANG: KONSOLE SOFORT FREIGEBEN =====
# Schutz: Nur unter Windows ausführen
if os.name == 'nt':
    import ctypes
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.FreeConsole()
    except Exception:
        pass

# ===== FIX FÜR DEN WINERROR 6 IN .PYW DATEIEN =====
# 1. Leitet alle print()-Ausgaben ins Nichts um, damit sie nicht crashen
sys.stdout = open(os.devnull, 'w')
sys.stderr = open(os.devnull, 'w')

# 2. Unterdrückt die Begrüßungsnachricht von Pygame VOR dem Import
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# ===== Globale Fehlerbehandlung – fängt alles ab =====
import traceback
import tkinter as tk
from tkinter import messagebox

def show_error(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fataler Fehler", f"Das Skript ist abgestürzt:\n\n{error_msg}")
    except:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = show_error

# ===== Restliche Imports =====
import time
import threading
import logging
import subprocess
from pynput import keyboard
import pygame

# ------------------------------------------------------------
# Python-Version prüfen (pynput ≥ 1.7.8 für 3.13)
# ------------------------------------------------------------
PY_VERSION = sys.version_info[:2]
IS_PY313 = PY_VERSION >= (3, 13)

if IS_PY313:
    print("🔔 Python 3.13 detected – enabling compatibility mode")
    try:
        import pynput
        if pynput.__version__ < "1.7.8":
            print("⚠️  Old pynput version detected – upgrading...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pynput"])
    except (ImportError, AttributeError):
        pass

# ------------------------------------------------------------
# Fehlende Pakete automatisch installieren
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
                f"  {sys.executable} -m pip install {pkg}"
            )
            sys.exit(1)

# ------------------------------------------------------------
# Mixer-Verfügbarkeit prüfen
# ------------------------------------------------------------
MIXER_VERFUEGBAR = False
try:
    pygame.mixer.init()
    MIXER_VERFUEGBAR = True
    print("✅ pygame.mixer available – music supported")
except Exception as e:
    print(f"⚠️  pygame.mixer not available: {e}")
    print("    Overlay will run without music functions.")

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ------------------------------------------------------------
# Feste Konfiguration (keine externe JSON)
# ------------------------------------------------------------
ZEITFENSTER_SEK: float = 5.0       # rolling window for WPM (seconds)
RAGE_SCHWELLE: int     = 100       # WPM that triggers Zen Mode
ZEN_DAUER_MS: int      = 5_000     # how long Zen popup stays (milliseconds)
ZEICHEN_PRO_WORT: int  = 5         # average characters per word
POLL_INTERVAL_MS: int  = 10        # how often to update WPM (ms)
SONG_CHECK_MS: int     = 1_000     # how often to check if song ended (ms)
FONT_SIZE: int         = 36        # Schriftgröße der WPM-Anzeige
WINDOW_X: int          = 1500      # Startposition X
WINDOW_Y: int          = 100       # Startposition Y

# Feste WPM-Stufen (wie im Original)
WPM_STUFEN = [
    (20,  "🐢", "#4CAF50"),
    (40,  "🐇", "#8BC34A"),
    (60,  "🚀", "#FFEB3B"),
    (80,  "🔥", "#FF9800"),
    (100, "⚡", "#FF5722"),
    (999, "🤬", "#F44336"),
]

# ------------------------------------------------------------
# Globaler Zustand (thread-safe)
# ------------------------------------------------------------
_lock             = threading.Lock()
anschlaege: list[float] = []
beruhigungs_modus: bool  = False

playlist: list[str]     = []
aktueller_song_index: int = 0
aktueller_song_titel: str = ""
music_paused: bool = False
watcher_id = None  # FIX: Speichert die ID des aktuellen Song-Watchers

musik_lief_vor_zen: bool = False
musik_gestartet_durch_zen: bool = False

# ------------------------------------------------------------
# Keylogger
# ------------------------------------------------------------
def on_press(key) -> None:
    with _lock:
        anschlaege.append(time.time())

def starte_keylogger() -> None:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ------------------------------------------------------------
# Playlist & Audio
# ------------------------------------------------------------
def lade_playlist() -> None:
    global playlist
    playlist = sorted(f for f in os.listdir() if f.lower().endswith(".mp3"))
    log.info("Playlist loaded: %d songs found", len(playlist))
    if not playlist:
        log.warning("No MP3 files in current directory!")

def spiele_song(index: int) -> None:
    global aktueller_song_titel, music_paused, watcher_id
    if not MIXER_VERFUEGBAR or not playlist:
        return
    idx = index % len(playlist)
    song = playlist[idx]
    aktueller_song_titel = os.path.splitext(song)[0]
    try:
        pygame.mixer.music.load(song)
        pygame.mixer.music.play()
        music_paused = False
        log.info("Playing: %s", song)
        
        # FIX: Alten Watcher abbrechen, falls vorhanden
        if watcher_id is not None:
            root.after_cancel(watcher_id)
            watcher_id = None
            
        if len(playlist) > 1:
            watcher_id = root.after(SONG_CHECK_MS, _song_watcher)
            
        if 'lbl_title' in globals() and lbl_title.winfo_exists():
            lbl_title.config(text=aktueller_song_titel)
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
    elif not MIXER_VERFUEGBAR and playlist:
        messagebox.showinfo("Info", "Music functions are disabled because pygame.mixer is not available.")
    else:
        log.warning("No MP3 files found.")

def toggle_pause():
    global music_paused
    if not MIXER_VERFUEGBAR:
        return
    if music_paused:
        pygame.mixer.music.unpause()
        btn_pause.config(text="⏸️")
        music_paused = False
        log.info("Music unpaused")
    else:
        pygame.mixer.music.pause()
        btn_pause.config(text="▶️")
        music_paused = True
        log.info("Music paused")

def stop_music():
    global watcher_id, music_paused, aktueller_song_titel
    if not MIXER_VERFUEGBAR:
        return
    pygame.mixer.music.stop()
    music_paused = False
    
    # FIX: Auch beim Stoppen den Watcher beenden
    if watcher_id is not None:
        root.after_cancel(watcher_id)
        watcher_id = None
        
    btn_pause.config(text="⏸️")
    aktueller_song_titel = ""
    if 'lbl_title' in globals() and lbl_title.winfo_exists():
        lbl_title.config(text="")
    log.info("Music stopped")

def _song_watcher() -> None:
    global watcher_id
    if not MIXER_VERFUEGBAR:
        return
    if not pygame.mixer.music.get_busy() and not music_paused:
        if beruhigungs_modus:
            spiele_naechsten_song()
    else:
        # FIX: ID aktualisieren
        watcher_id = root.after(SONG_CHECK_MS, _song_watcher)

# ------------------------------------------------------------
# WPM Analyse (feste Stufen)
# ------------------------------------------------------------
def get_wpm_emoji_und_farbe(wpm: int) -> tuple[str, str]:
    for schwelle, emoji, farbe in WPM_STUFEN:
        if wpm < schwelle:
            return emoji, farbe
    return WPM_STUFEN[-1][1], WPM_STUFEN[-1][2]

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
# Zen-Modus
# ------------------------------------------------------------
def loese_zen_modus_aus() -> None:
    global beruhigungs_modus, musik_lief_vor_zen, musik_gestartet_durch_zen
    beruhigungs_modus = True
    log.info("Zen Mode activated (WPM >= %d)", RAGE_SCHWELLE)

    if MIXER_VERFUEGBAR:
        musik_lief_vor_zen = pygame.mixer.music.get_busy() or music_paused
        if not musik_lief_vor_zen:
            spiele_naechsten_song()
            musik_gestartet_durch_zen = True
            log.info("Zen Mode starts its own song")
        else:
            musik_gestartet_durch_zen = False
            log.info("Zen Mode keeps existing music playing")
    else:
        musik_lief_vor_zen = False
        musik_gestartet_durch_zen = False

    zen = tk.Toplevel(root)
    zen.title("ZEN MODE")
    zen.geometry("600x300")
    zen.attributes("-topmost", True)
    zen.configure(bg="#2c3e50")
    zen.overrideredirect(True)

    text = "⚠️ RAGE QUIT DANGER ⚠️\n\nHands off the keyboard!\nTake a deep breath... 🧘"
    if not MIXER_VERFUEGBAR:
        text += "\n\n(Note: Music is disabled)"
    
    tk.Label(zen, text=text, font=("Helvetica", 20, "bold"), fg="white", bg="#2c3e50", pady=50).pack(expand=True)

    def schliesse_zen() -> None:
        global beruhigungs_modus, musik_gestartet_durch_zen, musik_lief_vor_zen
        if MIXER_VERFUEGBAR and musik_gestartet_durch_zen and not musik_lief_vor_zen:
            try:
                stop_music() # Nutzt die eigene Funktion, um Watcher sauber zu beenden
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
# Fenster verschieben (Gefixt!)
# ------------------------------------------------------------
_drag_x: int = 0
_drag_y: int = 0

def start_move(event: tk.Event) -> None:
    global _drag_x, _drag_y
    # FIX: Absolute Bildschirmkoordinaten nutzen
    _drag_x, _drag_y = event.x_root, event.y_root

def do_move(event: tk.Event) -> None:
    global _drag_x, _drag_y
    # FIX: Deltas berechnen
    deltax = event.x_root - _drag_x
    deltay = event.y_root - _drag_y
    
    x = root.winfo_x() + deltax
    y = root.winfo_y() + deltay
    root.geometry(f"+{x}+{y}")
    
    _drag_x, _drag_y = event.x_root, event.y_root

# ------------------------------------------------------------
# Toggle Musiksteuerung (per Doppelklick)
# ------------------------------------------------------------
def toggle_music_controls(event=None):
    if zeile2.winfo_ismapped():
        zeile2.pack_forget()
        zeile3.pack_forget()
    else:
        if MIXER_VERFUEGBAR:
            current_vol = pygame.mixer.music.get_volume()
            volume_var.set(int(current_vol * 100))
        zeile2.pack(side="top", fill="x", pady=(0, 2))
        zeile3.pack(side="top", fill="x", pady=(0, 5))

# ------------------------------------------------------------
# Lautstärkeregelung
# ------------------------------------------------------------
def volume_changed(val):
    if MIXER_VERFUEGBAR:
        try:
            pygame.mixer.music.set_volume(float(val) / 100.0)
        except:
            pass

# ------------------------------------------------------------
# Beenden
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
    sys.exit(0)

# ------------------------------------------------------------
# Hauptprogramm
# ------------------------------------------------------------
if __name__ == "__main__":
    lade_playlist()

    keylogger_thread = threading.Thread(target=starte_keylogger, daemon=True)
    keylogger_thread.start()

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    TRANSPARENT = "#000001"
    root.configure(bg=TRANSPARENT)
    
    # FIX: Transparenz-Feature sicher auf Nicht-Windows Systemen umgehen
    if os.name == 'nt':
        root.wm_attributes("-transparentcolor", TRANSPARENT)
    else:
        try:
            root.wm_attributes("-transparent", True)
        except Exception:
            pass
            
    root.geometry(f"+{WINDOW_X}+{WINDOW_Y}")

    btn_state = "normal" if MIXER_VERFUEGBAR else "disabled"
    volume_state = tk.NORMAL if MIXER_VERFUEGBAR else tk.DISABLED

    frame = tk.Frame(root, bg=TRANSPARENT)
    frame.pack()

    # ---- Zeile 1: WPM-Anzeige + Schließen-Button ----
    zeile1 = tk.Frame(frame, bg=TRANSPARENT)
    zeile1.pack(side="top", fill="x")

    lbl_wpm = tk.Label(zeile1, text="0 WPM 🐢", font=("Helvetica", FONT_SIZE, "bold"),
                       fg="#4CAF50", bg=TRANSPARENT)
    lbl_wpm.pack(side="left", padx=10)

    btn_close = tk.Button(zeile1, text="✖", font=("Arial", 8), fg="gray", bg=TRANSPARENT,
                          bd=0, activebackground=TRANSPARENT, activeforeground="white",
                          cursor="hand2", command=programm_beenden)
    btn_close.pack(side="right", anchor="n")

    # ---- Zeile 2: Musik-Buttons (versteckt) ----
    zeile2 = tk.Frame(frame, bg=TRANSPARENT)

    btn_prev = tk.Button(zeile2, text="⏮", font=("Segoe UI", 14), fg="white", bg="#2c3e50",
                         bd=0, padx=10, activebackground="#34495e", activeforeground="white",
                         cursor="hand2", state=btn_state, command=vorheriger_song)
    btn_prev.pack(side="left", padx=5)

    btn_play_scan = tk.Button(zeile2, text="🔍 ▶", font=("Segoe UI", 14), fg="white", bg="#2c3e50",
                               bd=0, padx=10, activebackground="#34495e", activeforeground="white",
                               cursor="hand2", state=btn_state, command=scan_und_spiele)
    btn_play_scan.pack(side="left", padx=5)

    btn_next = tk.Button(zeile2, text="⏭", font=("Segoe UI", 14), fg="white", bg="#2c3e50",
                         bd=0, padx=10, activebackground="#34495e", activeforeground="white",
                         cursor="hand2", state=btn_state, command=spiele_naechsten_song)
    btn_next.pack(side="left", padx=5)

    btn_pause = tk.Button(zeile2, text="⏸️", font=("Segoe UI", 14), fg="white", bg="#2c3e50",
                          bd=0, padx=10, activebackground="#34495e", activeforeground="white",
                          cursor="hand2", state=btn_state, command=toggle_pause)
    btn_pause.pack(side="left", padx=5)

    btn_stop = tk.Button(zeile2, text="⏹️", font=("Segoe UI", 14), fg="white", bg="#2c3e50",
                         bd=0, padx=10, activebackground="#34495e", activeforeground="white",
                         cursor="hand2", state=btn_state, command=stop_music)
    btn_stop.pack(side="left", padx=5)

    # ---- Zeile 3: Titel + Lautstärke (versteckt) ----
    zeile3 = tk.Frame(frame, bg=TRANSPARENT)

    lbl_title = tk.Label(zeile3, text="", font=("Arial", 10), fg="white", bg="#2c3e50",
                         padx=5, pady=2)
    lbl_title.pack(side="left", padx=5)

    volume_var = tk.DoubleVar(value=50)
    volume_scale = tk.Scale(zeile3, from_=0, to=100, orient="horizontal",
                            variable=volume_var, command=volume_changed, length=100,
                            showvalue=0, bg="#2c3e50", fg="white", troughcolor="#34495e",
                            sliderlength=20, state=volume_state)
    volume_scale.pack(side="left", padx=5)

    zeile2.pack_forget()
    zeile3.pack_forget()

    lbl_wpm.bind("<Double-Button-1>", toggle_music_controls)

    for widget in (btn_prev, btn_play_scan, btn_next, btn_pause, btn_stop, lbl_wpm, zeile1, frame):
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)

    analysiere_tippgeschwindigkeit()

    if not MIXER_VERFUEGBAR:
        log.info("Note: Music controls disabled (pygame.mixer not available)")
        root.after(1000, lambda: messagebox.showinfo("Music disabled",
            "pygame.mixer is not available.\nMusic controls have been disabled.\nThe WPM overlay will still work."))

    root.mainloop()
