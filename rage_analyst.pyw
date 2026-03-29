#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

# ===== ABSOLUTER SCHUTZ VOR WINERROR 6 =====
# Wir leiten sofort ALLE Konsolenausgaben in ein "Schwarzes Loch" um.
# Das verhindert, dass print()-Befehle (wie die von Pygame) das Programm zum Absturz bringen.
class DummyWriter:
    def write(self, *args, **kwargs): pass
    def flush(self, *args, **kwargs): pass
    def isatty(self): return False

sys.stdout = DummyWriter()
sys.stderr = DummyWriter()

# Unterdrückt die Pygame-Willkommensnachricht VOR DEM IMPORT!
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# Konsole verstecken (falls sie durch .py gestartet wurde)
if os.name == 'nt':
    import ctypes
    try:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.FreeConsole()
    except Exception:
        pass

# ===== Globale Fehlerbehandlung – fängt alles ab =====
import traceback
import tkinter as tk
from tkinter import messagebox

def show_error(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    try:
        with open("rage_error_log.txt", "w") as f:
            f.write(error_msg)
    except:
        pass
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Fataler Fehler", f"Das Skript ist abgestürzt:\n\n{error_msg}")
    except:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = show_error

# Helfer: Runde Ecken für Toplevels
def set_window_rounded(window, radius=20):
    if os.name != 'nt':
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        width = window.winfo_width()
        height = window.winfo_height()
        rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, radius, radius)
        ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
    except Exception:
        pass

# ===== Restliche Imports =====
import time
import threading
import logging
import subprocess
import json
import random
from pynput import keyboard
import pygame
import tkinter.ttk as ttk

# ------------------------------------------------------------
# Python-Version prüfen (pynput ≥ 1.7.8 für 3.13)
# ------------------------------------------------------------
PY_VERSION = sys.version_info[:2]
IS_PY313 = PY_VERSION >= (3, 13)

if IS_PY313:
    try:
        import pynput
        if pynput.__version__ < "1.7.8":
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
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Installation Error",
                f"Package '{pkg}' could not be installed.\n\nPlease run this command manually:\n  {sys.executable} -m pip install {pkg}"
            )
            sys.exit(1)

# ------------------------------------------------------------
# Mixer-Verfügbarkeit prüfen
# ------------------------------------------------------------
MIXER_VERFUEGBAR = False
try:
    pygame.mixer.init()
    MIXER_VERFUEGBAR = True
except Exception as e:
    pass

# ------------------------------------------------------------
# Keine zusätzliche Debug-Logdatei im normalen Betrieb
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ------------------------------------------------------------
# Feste Konfiguration
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

CONFIG_FILE = "rage_analyst_config.json"

def load_config():
    global ZEITFENSTER_SEK, RAGE_SCHWELLE, ZEN_DAUER_MS, ZEICHEN_PRO_WORT, POLL_INTERVAL_MS, SONG_CHECK_MS, FONT_SIZE, WINDOW_X, WINDOW_Y, shuffle_mode, theme_dark, sound_notifications, auto_save_interval, alarm_wpm
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            ZEITFENSTER_SEK = config.get('zeitfenster_sek', ZEITFENSTER_SEK)
            RAGE_SCHWELLE = config.get('rage_schwelle', RAGE_SCHWELLE)
            ZEN_DAUER_MS = config.get('zen_dauer_ms', ZEN_DAUER_MS)
            ZEICHEN_PRO_WORT = config.get('zeichen_pro_wort', ZEICHEN_PRO_WORT)
            POLL_INTERVAL_MS = config.get('poll_interval_ms', POLL_INTERVAL_MS)
            SONG_CHECK_MS = config.get('song_check_ms', SONG_CHECK_MS)
            FONT_SIZE = config.get('font_size', FONT_SIZE)
            WINDOW_X = config.get('window_x', WINDOW_X)
            WINDOW_Y = config.get('window_y', WINDOW_Y)
            shuffle_mode = config.get('shuffle_mode', shuffle_mode)
            theme_dark = config.get('theme_dark', theme_dark)
            sound_notifications = config.get('sound_notifications', sound_notifications)
            auto_save_interval = config.get('auto_save_interval', auto_save_interval)
            alarm_wpm = config.get('alarm_wpm', alarm_wpm)
        except Exception:
            pass

def save_config():
    config = {
        'zeitfenster_sek': ZEITFENSTER_SEK,
        'rage_schwelle': RAGE_SCHWELLE,
        'zen_dauer_ms': ZEN_DAUER_MS,
        'zeichen_pro_wort': ZEICHEN_PRO_WORT,
        'poll_interval_ms': POLL_INTERVAL_MS,
        'song_check_ms': SONG_CHECK_MS,
        'font_size': FONT_SIZE,
        'window_x': WINDOW_X,
        'window_y': WINDOW_Y,
        'shuffle_mode': shuffle_mode,
        'theme_dark': theme_dark,
        'sound_notifications': sound_notifications,
        'auto_save_interval': auto_save_interval,
        'alarm_wpm': alarm_wpm,
    }
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception:
        pass

load_config()

# ------------------------------------------------------------
# Tooltip-Klasse
# ------------------------------------------------------------
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        widget.bind("<Enter>", self.show_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip:
            return
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
        label = tk.Label(self.tooltip, text=self.text, bg="yellow", relief="solid", borderwidth=1)
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

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
watcher_id = None  

musik_lief_vor_zen: bool = False
musik_gestartet_durch_zen: bool = False

shuffle_mode: bool = False

# ------------------------------------------------------------
# Neue Features
# ------------------------------------------------------------
theme_dark: bool = True
min_wpm: int = 999
sound_notifications: bool = True
auto_save_interval: int = 60  # Sekunden
alarm_wpm: int = 150
session_paused: bool = False

settings_window = None
stats_window = None
playlist_window = None

# ------------------------------------------------------------
# Statistiken
# ------------------------------------------------------------
session_start: float = time.time()
max_wpm: int = 0
total_wpm: float = 0.0
wpm_count: int = 0
zen_count: int = 0
keystrokes_total: int = 0

# ------------------------------------------------------------
# Keylogger
# ------------------------------------------------------------
def on_press(key) -> None:
    global keystrokes_total

    char = None
    if hasattr(key, 'char') and key.char is not None:
        char = key.char
    elif isinstance(key, str):
        char = key

    if not char or not char.isalnum():
        return

    with _lock:
        anschlaege.append(time.time())
        keystrokes_total += 1

def starte_keylogger() -> None:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ------------------------------------------------------------
# Hotkeys
# ------------------------------------------------------------
def on_hotkey(key):
    if key == keyboard.Key.f1:
        open_stats()
    elif key == keyboard.Key.f2:
        open_settings()
    elif key == keyboard.Key.f3:
        toggle_theme()
    elif key == keyboard.Key.f4:
        toggle_session_pause()

hotkey_listener = keyboard.Listener(on_press=on_hotkey)
hotkey_listener.start()

# ------------------------------------------------------------
# Playlist & Audio
# ------------------------------------------------------------
def lade_playlist() -> None:
    global playlist
    playlist = sorted(f for f in os.listdir() if f.lower().endswith(".mp3"))
    if shuffle_mode:
        random.shuffle(playlist)

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
        
        if watcher_id is not None:
            root.after_cancel(watcher_id)
            watcher_id = None
            
        if len(playlist) > 1:
            watcher_id = root.after(SONG_CHECK_MS, _song_watcher)
            
        if 'lbl_title' in globals() and lbl_title.winfo_exists():
            lbl_title.config(text=aktueller_song_titel)
    except Exception:
        pass

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
    elif not MIXER_VERFUEGBAR and playlist:
        messagebox.showinfo("Info", "Music functions are disabled because pygame.mixer is not available.")

def toggle_pause():
    global music_paused
    if not MIXER_VERFUEGBAR:
        return
    if music_paused:
        pygame.mixer.music.unpause()
        music_paused = False
    else:
        pygame.mixer.music.pause()
        music_paused = True

def resume_music():
    global music_paused, aktueller_song_index
    if not MIXER_VERFUEGBAR:
        return
    if music_paused:
        pygame.mixer.music.unpause()
        music_paused = False
    elif not pygame.mixer.music.get_busy() and playlist:
        spiele_song(aktueller_song_index)


def stop_music():
    global watcher_id, music_paused, aktueller_song_titel
    if not MIXER_VERFUEGBAR:
        return
    pygame.mixer.music.stop()
    music_paused = False
    
    if watcher_id is not None:
        root.after_cancel(watcher_id)
        watcher_id = None
        
    aktueller_song_titel = ""
    if 'lbl_title' in globals() and lbl_title.winfo_exists():
        lbl_title.config(text="")

def toggle_shuffle():
    global shuffle_mode, playlist
    shuffle_mode = not shuffle_mode
    if shuffle_mode:
        random.shuffle(playlist)
    else:
        playlist = sorted(playlist)
    aktueller_song_index = 0  # Reset index
    save_config()

def toggle_theme():
    global theme_dark
    theme_dark = not theme_dark
    # Vereinfacht: Wechsle nur Hintergrund
    bg_color = "#2c3e50" if theme_dark else "#ffffff"
    fg_color = "white" if theme_dark else "black"
    root.configure(bg=bg_color)
    lbl_wpm.configure(bg=TRANSPARENT, fg=fg_color)
    save_config()

def toggle_session_pause():
    global session_paused
    session_paused = not session_paused
    if session_paused:
        lbl_wpm.config(text="PAUSED")
    else:
        analysiere_tippgeschwindigkeit()

def reset_stats():
    global max_wpm, total_wpm, wpm_count, zen_count, min_wpm, keystrokes_total
    max_wpm = 0
    total_wpm = 0.0
    wpm_count = 0
    zen_count = 0
    min_wpm = 999
    keystrokes_total = 0
    messagebox.showinfo("Reset", "Statistiken zurückgesetzt.")

def open_playlist_editor():
    global playlist_window
    if playlist_window and playlist_window.winfo_exists():
        playlist_window.lift()
        return
    playlist_window = tk.Toplevel(root)
    playlist_window.title("Playlist-Editor")
    playlist_window.geometry("400x300")
    playlist_window.attributes("-topmost", True)

    def on_close():
        global playlist_window
        if playlist_window is not None and playlist_window.winfo_exists():
            try:
                playlist_window.destroy()
            except Exception:
                pass
        playlist_window = None

    playlist_window.protocol("WM_DELETE_WINDOW", on_close)

    listbox = tk.Listbox(playlist_window)
    for song in playlist:
        listbox.insert(tk.END, song)
    listbox.pack(fill=tk.BOTH, expand=True)

    # extra: Schließen-Button für Playlist-Editor
    btn_close_playlist = tk.Button(playlist_window, text="Schließen", command=on_close)
    btn_close_playlist.pack(pady=5)

def auto_save_stats():
    if auto_save_interval > 0:
        export_stats_auto()
        root.after(auto_save_interval * 1000, auto_save_stats)

def export_stats_auto():
    try:
        with open("auto_rage_stats.json", "w") as f:
            json.dump({
                "max_wpm": max_wpm,
                "avg_wpm": round(total_wpm / wpm_count, 1) if wpm_count > 0 else 0,
                "zen_count": zen_count,
                "min_wpm": min_wpm
            }, f)
    except:
        pass

# ------------------------------------------------------------
# WPM Analyse
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
    log.info("Analysiere Tippgeschwindigkeit called")
    global beruhigungs_modus, max_wpm, total_wpm, wpm_count, min_wpm
    wpm = berechne_wpm()
    if wpm > 0:
        max_wpm = max(max_wpm, wpm)
        min_wpm = min(min_wpm, wpm)
        total_wpm += wpm
        wpm_count += 1
        if wpm >= alarm_wpm and sound_notifications and MIXER_VERFUEGBAR:
            try:
                pygame.mixer.Sound("alarm.wav").play()  # Annahme, alarm.wav existiert
            except:
                pass
    emoji, farbe = get_wpm_emoji_und_farbe(wpm)
    lbl_wpm.config(text=f"{wpm} WPM {emoji}", fg=farbe)
    if wpm >= RAGE_SCHWELLE and not beruhigungs_modus:
        loese_zen_modus_aus()
    if not session_paused:
        root.after(POLL_INTERVAL_MS, analysiere_tippgeschwindigkeit)

# ------------------------------------------------------------
# Zen-Modus
# ------------------------------------------------------------
def loese_zen_modus_aus() -> None:
    global beruhigungs_modus, musik_lief_vor_zen, musik_gestartet_durch_zen, zen_count
    beruhigungs_modus = True
    zen_count += 1

    if MIXER_VERFUEGBAR:
        musik_lief_vor_zen = pygame.mixer.music.get_busy() or music_paused
        if not musik_lief_vor_zen:
            spiele_naechsten_song()
            musik_gestartet_durch_zen = True
        else:
            musik_gestartet_durch_zen = False
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
                stop_music()
            except Exception:
                pass

        with _lock:
            anschlaege.clear()
        beruhigungs_modus = False
        zen.destroy()

    zen.after(ZEN_DAUER_MS, schliesse_zen)

# ------------------------------------------------------------
# Fenster verschieben
# ------------------------------------------------------------
_drag_x: int = 0
_drag_y: int = 0

def start_move(event: tk.Event) -> None:
    global _drag_x, _drag_y
    _drag_x, _drag_y = event.x_root, event.y_root

def do_move(event: tk.Event) -> None:
    global _drag_x, _drag_y
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
# Einstellungen
# ------------------------------------------------------------
def open_settings():
    global settings_window
    if settings_window and settings_window.winfo_exists():
        settings_window.lift()
        return
    settings_window = tk.Toplevel(root)
    settings_window.title("Einstellungen")
    settings_window.geometry("500x500")
    settings_window.attributes("-topmost", True)

    def on_close():
        global settings_window
        try:
            settings_window.destroy()
        except Exception:
            pass
        settings_window = None

    settings_window.protocol("WM_DELETE_WINDOW", on_close)

    notebook = ttk.Notebook(settings_window)
    notebook.pack(fill="both", expand=True)

    # Tab 1: Grundlagen
    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="Grundlagen")

    tk.Label(tab1, text="Zeitfenster (Sekunden):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    zeit_var = tk.DoubleVar(value=ZEITFENSTER_SEK)
    tk.Entry(tab1, textvariable=zeit_var).grid(row=0, column=1, padx=10, pady=5)

    tk.Label(tab1, text="Rage-Schwelle (WPM):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    rage_var = tk.IntVar(value=RAGE_SCHWELLE)
    tk.Entry(tab1, textvariable=rage_var).grid(row=1, column=1, padx=10, pady=5)

    tk.Label(tab1, text="Zen-Dauer (ms):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    zen_var = tk.IntVar(value=ZEN_DAUER_MS)
    tk.Entry(tab1, textvariable=zen_var).grid(row=2, column=1, padx=10, pady=5)

    tk.Label(tab1, text="Zeichen pro Wort:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    zeichen_var = tk.IntVar(value=ZEICHEN_PRO_WORT)
    tk.Entry(tab1, textvariable=zeichen_var).grid(row=3, column=1, padx=10, pady=5)

    # Tab 2: Erweitert
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="Erweitert")

    tk.Label(tab2, text="Poll-Intervall (ms):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    poll_var = tk.IntVar(value=POLL_INTERVAL_MS)
    tk.Entry(tab2, textvariable=poll_var).grid(row=0, column=1, padx=10, pady=5)

    tk.Label(tab2, text="Song-Check (ms):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    song_var = tk.IntVar(value=SONG_CHECK_MS)
    tk.Entry(tab2, textvariable=song_var).grid(row=1, column=1, padx=10, pady=5)

    tk.Label(tab2, text="Schriftgröße:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    font_var = tk.IntVar(value=FONT_SIZE)
    tk.Entry(tab2, textvariable=font_var).grid(row=2, column=1, padx=10, pady=5)

    tk.Label(tab2, text="Alarm-WPM:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    alarm_var = tk.IntVar(value=alarm_wpm)
    tk.Entry(tab2, textvariable=alarm_var).grid(row=3, column=1, padx=10, pady=5)

    tk.Label(tab2, text="Auto-Save-Intervall (s):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
    auto_var = tk.IntVar(value=auto_save_interval)
    tk.Entry(tab2, textvariable=auto_var).grid(row=4, column=1, padx=10, pady=5)

    sound_var = tk.BooleanVar(value=sound_notifications)
    tk.Checkbutton(tab2, text="Sound-Benachrichtigungen", variable=sound_var).grid(row=5, column=0, columnspan=2, pady=5)

    # Tab 3: Aktionen
    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="Aktionen")

    tk.Button(tab3, text="Thema wechseln", command=toggle_theme).pack(pady=10)
    tk.Button(tab3, text="Session Pause/Resume", command=toggle_session_pause).pack(pady=10)
    tk.Button(tab3, text="Playlist-Editor öffnen", command=open_playlist_editor).pack(pady=10)

    def save_settings():
        global ZEITFENSTER_SEK, RAGE_SCHWELLE, ZEN_DAUER_MS, ZEICHEN_PRO_WORT, POLL_INTERVAL_MS, SONG_CHECK_MS, FONT_SIZE, alarm_wpm, auto_save_interval, sound_notifications
        ZEITFENSTER_SEK = zeit_var.get()
        RAGE_SCHWELLE = rage_var.get()
        ZEN_DAUER_MS = zen_var.get()
        ZEICHEN_PRO_WORT = zeichen_var.get()
        POLL_INTERVAL_MS = poll_var.get()
        SONG_CHECK_MS = song_var.get()
        FONT_SIZE = font_var.get()
        alarm_wpm = alarm_var.get()
        auto_save_interval = auto_var.get()
        sound_notifications = sound_var.get()
        save_config()
        lbl_wpm.config(font=("Helvetica", FONT_SIZE, "bold"))
        settings_window.destroy()
        messagebox.showinfo("Einstellungen", "Einstellungen gespeichert.")

    tk.Button(settings_window, text="Speichern", command=save_settings).pack(pady=10)
    settings_window.update_idletasks()
    set_window_rounded(settings_window, radius=16)

# ------------------------------------------------------------
# Statistiken
# ------------------------------------------------------------
def open_stats():
    global max_wpm, total_wpm, wpm_count, zen_count, session_start, min_wpm, stats_window
    if stats_window and stats_window.winfo_exists():
        stats_window.lift()
        return
    stats_window = tk.Toplevel(root)
    stats_window.title("Statistiken")
    stats_window.geometry("400x300")
    stats_window.attributes("-topmost", True)

    def on_close():
        global stats_window
        if hasattr(stats_window, '_update_timer'):
            try:
                stats_window.after_cancel(stats_window._update_timer)
            except Exception:
                pass
        try:
            stats_window.destroy()
        except Exception:
            pass
        stats_window = None

    stats_window.protocol("WM_DELETE_WINDOW", on_close)

    # Separator function for dynamic updates
    stats_labels = {}

    def update_stats_labels():
        if not stats_window.winfo_exists():
            return
        current_session_time = int(time.time() - session_start)
        current_avg_wpm = round(total_wpm / wpm_count, 1) if wpm_count > 0 else 0
        current_min_wpm = min_wpm if min_wpm != 999 else 0

        stats_labels['session_time'].config(text=f"Sitzungsdauer: {current_session_time // 60}m {current_session_time % 60}s")
        stats_labels['max_wpm'].config(text=f"Maximale WPM: {max_wpm}")
        stats_labels['min_wpm'].config(text=f"Minimale WPM: {current_min_wpm}")
        stats_labels['avg_wpm'].config(text=f"Durchschnittliche WPM: {current_avg_wpm}")
        stats_labels['zen_count'].config(text=f"Zen-Modi ausgelöst: {zen_count}")
        stats_labels['keystrokes'].config(text=f"Gesamte Tastenanschläge (gesamt): {keystrokes_total}")

        stats_window._update_timer = stats_window.after(500, update_stats_labels)

    stats_labels['session_time'] = tk.Label(stats_window, text="", font=("Arial", 12))
    stats_labels['session_time'].pack(pady=10)

    stats_labels['max_wpm'] = tk.Label(stats_window, text="", font=("Arial", 12))
    stats_labels['max_wpm'].pack(pady=5)

    stats_labels['min_wpm'] = tk.Label(stats_window, text="", font=("Arial", 12))
    stats_labels['min_wpm'].pack(pady=5)

    stats_labels['avg_wpm'] = tk.Label(stats_window, text="", font=("Arial", 12))
    stats_labels['avg_wpm'].pack(pady=5)

    stats_labels['zen_count'] = tk.Label(stats_window, text="", font=("Arial", 12))
    stats_labels['zen_count'].pack(pady=5)

    stats_labels['keystrokes'] = tk.Label(stats_window, text="", font=("Arial", 12))
    stats_labels['keystrokes'].pack(pady=5)

    btn_reset = tk.Button(stats_window, text="Statistiken zurücksetzen", command=reset_stats)
    btn_reset.pack(pady=10)

    def export_stats():
        current_session_time = int(time.time() - session_start)
        current_avg_wpm = round(total_wpm / wpm_count, 1) if wpm_count > 0 else 0
        current_min_wpm = min_wpm if min_wpm != 999 else 0
        try:
            with open("rage_stats.csv", "w") as f:
                f.write("Statistik,Wert\n")
                f.write(f"Sitzungsdauer,{current_session_time}\n")
                f.write(f"Maximale WPM,{max_wpm}\n")
                f.write(f"Minimale WPM,{current_min_wpm}\n")
                f.write(f"Durchschnittliche WPM,{current_avg_wpm}\n")
                f.write(f"Zen-Modi,{zen_count}\n")
                f.write(f"Tastenanschläge,{keystrokes_total}\n")
            messagebox.showinfo("Export", "Statistiken nach rage_stats.csv exportiert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Export fehlgeschlagen: {e}")

    tk.Button(stats_window, text="Exportieren (CSV)", command=export_stats).pack(pady=20)

    stats_window._update_timer = stats_window.after(500, update_stats_labels)
    stats_window.update_idletasks()
    set_window_rounded(stats_window, radius=16)

# ------------------------------------------------------------
# Beenden
# ------------------------------------------------------------
def programm_beenden() -> None:
    global WINDOW_X, WINDOW_Y
    WINDOW_X = root.winfo_x()
    WINDOW_Y = root.winfo_y()
    save_config()
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
    log.info("Configured background")
    
    if os.name == 'nt':
        root.wm_attributes("-transparentcolor", TRANSPARENT)
        log.info("Set transparent color")
    else:
        try:
            root.wm_attributes("-transparent", True)
            log.info("Set transparent")
        except Exception:
            pass
            
    root.geometry(f"+{WINDOW_X}+{WINDOW_Y}")
    log.info("Set geometry")

    btn_state = "normal" if MIXER_VERFUEGBAR else "disabled"
    volume_state = tk.NORMAL if MIXER_VERFUEGBAR else tk.DISABLED

    frame = tk.Frame(root, bg=TRANSPARENT)
    frame.pack()

    def create_circle_button(parent, text, command, diameter=30, bg_color="#2c3e50", fg_color="white"):
        canvas = tk.Canvas(parent, width=diameter, height=diameter, bg=TRANSPARENT, highlightthickness=0, bd=0)
        oval = canvas.create_oval(0, 0, diameter, diameter, fill=bg_color, outline=bg_color)
        canvas.create_text(diameter/2, diameter/2, text=text, fill=fg_color, font=("Segoe UI", int(diameter/2)), anchor="center")
        def on_click(event):
            try:
                command()
            except Exception:
                pass
        canvas.bind("<Button-1>", on_click)
        canvas.bind("<Enter>", lambda e: canvas.itemconfig(oval, fill="#34495e"))
        canvas.bind("<Leave>", lambda e: canvas.itemconfig(oval, fill=bg_color))
        canvas.configure(cursor="hand2")
        return canvas

    # ---- Zeile 1: WPM-Anzeige + Schließen-Button ----
    zeile1 = tk.Frame(frame, bg=TRANSPARENT)
    zeile1.pack(side="top", fill="x")

    lbl_wpm = tk.Label(zeile1, text="0 WPM 🐢", font=("Helvetica", FONT_SIZE, "bold"),
                       fg="#4CAF50", bg=TRANSPARENT)
    lbl_wpm.pack(side="left", padx=10)
    log.info("WPM label created")

    btn_close = create_circle_button(zeile1, "✖", programm_beenden, diameter=30, bg_color="#2c3e50", fg_color="white")
    btn_close.pack(side="right", anchor="n", padx=4)

    btn_minimize = create_circle_button(zeile1, "_", lambda: root.iconify(), diameter=30, bg_color="#2c3e50", fg_color="white")
    btn_minimize.pack(side="right", anchor="n", padx=4)

    btn_stats = create_circle_button(zeile1, "📊", open_stats, diameter=30, bg_color="#2c3e50", fg_color="white")
    btn_stats.pack(side="right", anchor="n", padx=4)

    btn_settings = create_circle_button(zeile1, "⚙️", open_settings, diameter=30, bg_color="#2c3e50", fg_color="white")
    btn_settings.pack(side="right", anchor="n", padx=4)

    # ---- Zeile 2: Musik-Buttons (versteckt) ----
    zeile2 = tk.Frame(frame, bg=TRANSPARENT)

    btn_prev = create_circle_button(zeile2, "⏮", vorheriger_song, diameter=40, bg_color="#2c3e50")
    btn_prev.pack(side="left", padx=5)

    btn_play_scan = create_circle_button(zeile2, "🔍▶", scan_und_spiele, diameter=40, bg_color="#2c3e50")
    btn_play_scan.pack(side="left", padx=5)

    btn_next = create_circle_button(zeile2, "⏭", spiele_naechsten_song, diameter=40, bg_color="#2c3e50")
    btn_next.pack(side="left", padx=5)

    btn_resume = create_circle_button(zeile2, "▶", resume_music, diameter=40, bg_color="#2c3e50")
    btn_resume.pack(side="left", padx=5)

    btn_pause = create_circle_button(zeile2, "⏸️", toggle_pause, diameter=40, bg_color="#2c3e50")
    btn_pause.pack(side="left", padx=5)

    btn_stop = create_circle_button(zeile2, "⏹️", stop_music, diameter=40, bg_color="#2c3e50")
    btn_stop.pack(side="left", padx=5)

    btn_shuffle = create_circle_button(zeile2, "🔀", toggle_shuffle, diameter=40, bg_color="#2c3e50")
    btn_shuffle.pack(side="left", padx=5)


    if shuffle_mode:
        btn_shuffle.config(bg="#4CAF50")

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

    # Tooltips
    ToolTip(btn_minimize, "Fenster minimieren")
    ToolTip(btn_stats, "Statistiken anzeigen (F1)")
    ToolTip(btn_settings, "Einstellungen öffnen (F2)")
    ToolTip(btn_shuffle, "Shuffle ein/aus")
    ToolTip(btn_play_scan, "Playlist scannen und spielen")

    lbl_wpm.bind("<Double-Button-1>", toggle_music_controls)

    for widget in (lbl_wpm, zeile1, frame):
        widget.bind("<ButtonPress-1>", start_move, add="+")
        widget.bind("<B1-Motion>", do_move, add="+")

    analysiere_tippgeschwindigkeit()
    log.info("Initial WPM analysis started")

    auto_save_stats()
    log.info("Auto save started")

    log.info("Entering mainloop")
    root.mainloop()
