#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
import json
import tkinter as tk
from tkinter import messagebox, ttk, colorchooser, simpledialog

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
# 5. Configuration handling
# ------------------------------------------------------------
CONFIG_FILE = "wpm_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "wpm_stufen": [
        [20, "🐢", "#4CAF50"],
        [40, "🐇", "#8BC34A"],
        [60, "🚀", "#FFEB3B"],
        [80, "🔥", "#FF9800"],
        [100, "⚡", "#FF5722"],
        [999, "🤬", "#F44336"]
    ],
    "font_size": 36,
    "window_x": 1500,
    "window_y": 100
}

config = DEFAULT_CONFIG.copy()

def load_config():
    global config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            # Merge with defaults in case of missing keys
            for key in DEFAULT_CONFIG:
                if key not in loaded:
                    loaded[key] = DEFAULT_CONFIG[key]
            config = loaded
    except FileNotFoundError:
        save_config()  # create default file
    except Exception as e:
        print(f"⚠️ Could not load config: {e}")

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"⚠️ Could not save config: {e}")

load_config()

# ------------------------------------------------------------
# 6. Main script with intelligent Zen music logic
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# Configuration from config
ZEITFENSTER_SEK: float = 5.0       # rolling window for WPM (seconds)
RAGE_SCHWELLE: int     = 100       # WPM that triggers Zen Mode
ZEN_DAUER_MS: int      = 5_000     # how long Zen popup stays (milliseconds)
ZEICHEN_PRO_WORT: int  = 5         # average characters per word
POLL_INTERVAL_MS: int  = 10        # how often to update WPM (ms) – changed to 10 ms
SONG_CHECK_MS: int     = 1_000     # how often to check if song ended (ms)

# Global state (thread‑safe)
_lock             = threading.Lock()
anschlaege: list[float] = []
beruhigungs_modus: bool  = False

playlist: list[str]     = []
aktueller_song_index: int = 0
aktueller_song_titel: str = ""      # für Anzeige
music_paused: bool = False           # für Pause-Funktion

# Flags for intelligent Zen music handling
musik_lief_vor_zen: bool = False          # Was music playing before Zen Mode?
musik_gestartet_durch_zen: bool = False   # Was the current song started by Zen Mode?

# ------------------------------------------------------------
# 7. Keylogger (pynput 1.7.8+ is compatible)
# ------------------------------------------------------------
def on_press(key) -> None:
    with _lock:
        anschlaege.append(time.time())

def starte_keylogger() -> None:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ------------------------------------------------------------
# 8. Playlist & Audio (with mixer check)
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
    global aktueller_song_titel, music_paused
    if not MIXER_VERFUEGBAR:
        log.warning("Mixer not available – cannot play")
        return
    if not playlist:
        log.warning("No playlist loaded – nothing to play.")
        return

    idx = index % len(playlist)
    song = playlist[idx]
    aktueller_song_titel = os.path.splitext(song)[0]  # ohne .mp3
    try:
        pygame.mixer.music.load(song)
        pygame.mixer.music.play()
        music_paused = False
        log.info("Playing: %s", song)

        if len(playlist) > 1:
            root.after(SONG_CHECK_MS, _song_watcher)

        # Update title label if visible
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
    elif not MIXER_VERFUEGBAR:
        log.warning("Mixer not available – cannot play music")
        if playlist:
            messagebox.showinfo("Info", 
                "Music functions are disabled because pygame.mixer is not available.\n"
                "The WPM overlay will still work.")
    else:
        log.warning("No MP3 files found – nothing played.")

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

def _song_watcher() -> None:
    """Called only when more than one song in playlist.
       Checks if current song ended and plays next, but ONLY in Zen Mode."""
    if not MIXER_VERFUEGBAR:
        return
    if not pygame.mixer.music.get_busy() and not music_paused:
        if beruhigungs_modus:
            spiele_naechsten_song()
    else:
        root.after(SONG_CHECK_MS, _song_watcher)

# ------------------------------------------------------------
# 9. WPM analysis (using configurable stufen)
# ------------------------------------------------------------
def get_wpm_emoji_und_farbe(wpm: int) -> tuple[str, str]:
    stufen = config["wpm_stufen"]
    for schwelle, emoji, farbe in stufen:
        if wpm < schwelle:
            return emoji, farbe
    # Fallback (letzte Stufe)
    letzte = stufen[-1]
    return letzte[1], letzte[2]

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
# 10. Zen Mode popup (with intelligent music control)
# ------------------------------------------------------------
def loese_zen_modus_aus() -> None:
    global beruhigungs_modus, musik_lief_vor_zen, musik_gestartet_durch_zen
    beruhigungs_modus = True
    log.info("Zen Mode activated (WPM >= %d)", RAGE_SCHWELLE)

    # Check if music is currently playing
    if MIXER_VERFUEGBAR:
        musik_lief_vor_zen = pygame.mixer.music.get_busy() or music_paused
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
# 11. Window dragging
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
    # Save new position to config
    config["window_x"] = x
    config["window_y"] = y
    save_config()

# ------------------------------------------------------------
# 12. Toggle music controls (hidden by default)
# ------------------------------------------------------------
def toggle_music_controls(event=None):
    if zeile2.winfo_ismapped():
        zeile2.pack_forget()
        zeile3.pack_forget()
    else:
        # Before showing, update volume scale to current mixer volume
        if MIXER_VERFUEGBAR:
            current_vol = pygame.mixer.music.get_volume()
            volume_var.set(int(current_vol * 100))
        zeile2.pack(side="top", fill="x", pady=(0, 2))
        zeile3.pack(side="top", fill="x", pady=(0, 5))

# ------------------------------------------------------------
# 13. Volume control callback
# ------------------------------------------------------------
def volume_changed(val):
    if MIXER_VERFUEGBAR:
        try:
            pygame.mixer.music.set_volume(float(val) / 100.0)
        except:
            pass

# ------------------------------------------------------------
# 14. Settings window
# ------------------------------------------------------------
def open_settings():
    settings = tk.Toplevel(root)
    settings.title("Einstellungen")
    settings.geometry("600x500")
    settings.resizable(False, False)
    settings.transient(root)
    settings.grab_set()

    # Notebook for tabs
    notebook = ttk.Notebook(settings)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Tab 1: WPM Stufen
    frame_stufen = ttk.Frame(notebook)
    notebook.add(frame_stufen, text="WPM Stufen")

    # Treeview for stufen
    columns = ("Schwellwert", "Emoji", "Farbe")
    tree = ttk.Treeview(frame_stufen, columns=columns, show="headings", height=8)
    tree.heading("Schwellwert", text="WPM <")
    tree.heading("Emoji", text="Emoji")
    tree.heading("Farbe", text="Farbe (Hex)")
    tree.column("Schwellwert", width=100, anchor="center")
    tree.column("Emoji", width=100, anchor="center")
    tree.column("Farbe", width=150, anchor="center")

    # Scrollbar
    scrollbar = ttk.Scrollbar(frame_stufen, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    scrollbar.grid(row=0, column=1, sticky="ns")
    frame_stufen.grid_rowconfigure(0, weight=1)
    frame_stufen.grid_columnconfigure(0, weight=1)

    # Buttons for stufen
    btn_frame = ttk.Frame(frame_stufen)
    btn_frame.grid(row=1, column=0, columnspan=2, pady=10)

    def load_stufen_into_tree():
        tree.delete(*tree.get_children())
        for stufe in config["wpm_stufen"]:
            tree.insert("", "end", values=stufe)

    load_stufen_into_tree()

    def add_stufe():
        # Simple dialog to enter values
        new_window = tk.Toplevel(settings)
        new_window.title("Neue Stufe")
        new_window.geometry("300x200")
        new_window.transient(settings)
        new_window.grab_set()

        tk.Label(new_window, text="Schwellwert (WPM <):").pack(pady=5)
        entry_schwelle = tk.Entry(new_window)
        entry_schwelle.pack()

        tk.Label(new_window, text="Emoji:").pack(pady=5)
        entry_emoji = tk.Entry(new_window)
        entry_emoji.pack()

        tk.Label(new_window, text="Farbe (Hex oder Name):").pack(pady=5)
        entry_farbe = tk.Entry(new_window)
        entry_farbe.pack()

        def pick_color():
            color = colorchooser.askcolor(title="Farbe wählen")[1]
            if color:
                entry_farbe.delete(0, tk.END)
                entry_farbe.insert(0, color)

        tk.Button(new_window, text="Farbe auswählen", command=pick_color).pack(pady=5)

        def save_new():
            try:
                schwelle = int(entry_schwelle.get())
                emoji = entry_emoji.get()
                farbe = entry_farbe.get()
                config["wpm_stufen"].append([schwelle, emoji, farbe])
                # Sort by threshold
                config["wpm_stufen"].sort(key=lambda x: x[0])
                save_config()
                load_stufen_into_tree()
                new_window.destroy()
            except ValueError:
                messagebox.showerror("Fehler", "Schwellwert muss eine Zahl sein")

        tk.Button(new_window, text="Speichern", command=save_new).pack(pady=10)

    def edit_stufe():
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])
        values = item["values"]
        if not values:
            return

        new_window = tk.Toplevel(settings)
        new_window.title("Stufe bearbeiten")
        new_window.geometry("300x200")
        new_window.transient(settings)
        new_window.grab_set()

        tk.Label(new_window, text="Schwellwert (WPM <):").pack(pady=5)
        entry_schwelle = tk.Entry(new_window)
        entry_schwelle.insert(0, values[0])
        entry_schwelle.pack()

        tk.Label(new_window, text="Emoji:").pack(pady=5)
        entry_emoji = tk.Entry(new_window)
        entry_emoji.insert(0, values[1])
        entry_emoji.pack()

        tk.Label(new_window, text="Farbe (Hex oder Name):").pack(pady=5)
        entry_farbe = tk.Entry(new_window)
        entry_farbe.insert(0, values[2])
        entry_farbe.pack()

        def pick_color():
            color = colorchooser.askcolor(title="Farbe wählen")[1]
            if color:
                entry_farbe.delete(0, tk.END)
                entry_farbe.insert(0, color)

        tk.Button(new_window, text="Farbe auswählen", command=pick_color).pack(pady=5)

        def save_edit():
            try:
                schwelle = int(entry_schwelle.get())
                emoji = entry_emoji.get()
                farbe = entry_farbe.get()
                # Find and replace
                for i, st in enumerate(config["wpm_stufen"]):
                    if st[0] == values[0] and st[1] == values[1] and st[2] == values[2]:
                        config["wpm_stufen"][i] = [schwelle, emoji, farbe]
                        break
                config["wpm_stufen"].sort(key=lambda x: x[0])
                save_config()
                load_stufen_into_tree()
                new_window.destroy()
            except ValueError:
                messagebox.showerror("Fehler", "Schwellwert muss eine Zahl sein")

        tk.Button(new_window, text="Speichern", command=save_edit).pack(pady=10)

    def delete_stufe():
        selected = tree.selection()
        if not selected:
            return
        item = tree.item(selected[0])
        values = item["values"]
        if not values:
            return
        if messagebox.askyesno("Löschen", "Wirklich löschen?"):
            for i, st in enumerate(config["wpm_stufen"]):
                if st[0] == values[0] and st[1] == values[1] and st[2] == values[2]:
                    del config["wpm_stufen"][i]
                    break
            save_config()
            load_stufen_into_tree()

    ttk.Button(btn_frame, text="Hinzufügen", command=add_stufe).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Bearbeiten", command=edit_stufe).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Löschen", command=delete_stufe).pack(side="left", padx=5)

    # Tab 2: Overlay-Einstellungen
    frame_overlay = ttk.Frame(notebook)
    notebook.add(frame_overlay, text="Overlay")

    # Schriftgröße
    ttk.Label(frame_overlay, text="Schriftgröße WPM:").grid(row=0, column=0, sticky="w", padx=10, pady=10)
    font_var = tk.IntVar(value=config["font_size"])
    font_spin = ttk.Spinbox(frame_overlay, from_=10, to=100, textvariable=font_var, width=10)
    font_spin.grid(row=0, column=1, padx=10, pady=10)

    # Vorschau-Label (optional)
    preview = tk.Label(frame_overlay, text="123 WPM 🐢", font=("Helvetica", config["font_size"]), fg="#4CAF50")
    preview.grid(row=1, column=0, columnspan=2, pady=10)

    def update_preview(*args):
        preview.config(font=("Helvetica", font_var.get()))
    font_var.trace_add("write", update_preview)

    # Position (wird beim Verschieben gespeichert, hier nur Info)
    ttk.Label(frame_overlay, text=f"Aktuelle Position: X={config['window_x']}, Y={config['window_y']} (wird beim Verschieben gespeichert)").grid(row=2, column=0, columnspan=2, pady=10)

    # Tab 3: Info
    frame_info = ttk.Frame(notebook)
    notebook.add(frame_info, text="Info")
    ttk.Label(frame_info, text="WPM Overlay mit Rage Detection\nVersion 2.0\n\nEinstellungen werden automatisch gespeichert.").pack(pady=20)

    # Save button for overlay settings
    def save_overlay_settings():
        config["font_size"] = font_var.get()
        save_config()
        lbl_wpm.config(font=("Helvetica", config["font_size"]))
        messagebox.showinfo("Info", "Einstellungen gespeichert")

    ttk.Button(frame_overlay, text="Speichern", command=save_overlay_settings).grid(row=3, column=0, columnspan=2, pady=10)

    # Close button
    ttk.Button(settings, text="Schließen", command=settings.destroy).pack(pady=5)

# ------------------------------------------------------------
# 15. Clean exit
# ------------------------------------------------------------
def programm_beenden() -> None:
    log.info("Shutting down.")
    save_config()
    if MIXER_VERFUEGBAR:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass
    root.destroy()

# ------------------------------------------------------------
# 16. Main program
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
    root.geometry(f"+{config['window_x']}+{config['window_y']}")

    # If mixer unavailable, disable music buttons and volume
    btn_state = "normal" if MIXER_VERFUEGBAR else "disabled"
    volume_state = tk.NORMAL if MIXER_VERFUEGBAR else tk.DISABLED

    # Main frame
    frame = tk.Frame(root, bg=TRANSPARENT)
    frame.pack()

    # ---- Row 1: WPM display + close button + settings button ----
    zeile1 = tk.Frame(frame, bg=TRANSPARENT)
    zeile1.pack(side="top", fill="x")

    lbl_wpm = tk.Label(
        zeile1,
        text="0 WPM 🐢",
        font=("Helvetica", config["font_size"], "bold"),
        fg="#4CAF50",
        bg=TRANSPARENT,
    )
    lbl_wpm.pack(side="left", padx=10)

    btn_settings = tk.Button(
        zeile1,
        text="⚙️",
        font=("Arial", 8),
        fg="gray",
        bg=TRANSPARENT,
        bd=0,
        activebackground=TRANSPARENT,
        activeforeground="white",
        cursor="hand2",
        command=open_settings
    )
    btn_settings.pack(side="right", anchor="n", padx=2)

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

    # ---- Row 2: Music control buttons (hidden by default) ----
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

    # Pause button
    btn_pause = tk.Button(
        zeile2,
        text="⏸️",
        font=("Segoe UI", 14),
        fg="white",
        bg="#2c3e50",
        bd=0,
        padx=10,
        activebackground="#34495e",
        activeforeground="white",
        cursor="hand2",
        state=btn_state,
        command=toggle_pause
    )
    btn_pause.pack(side="left", padx=5)

    # ---- Row 3: Title and volume (hidden by default) ----
    zeile3 = tk.Frame(frame, bg=TRANSPARENT)

    # Title label
    lbl_title = tk.Label(
        zeile3,
        text="",
        font=("Arial", 10),
        fg="white",
        bg="#2c3e50",
        padx=5,
        pady=2
    )
    lbl_title.pack(side="left", padx=5)

    # Volume slider
    volume_var = tk.DoubleVar(value=50)  # default 50%
    volume_scale = tk.Scale(
        zeile3,
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

    # Initially hide rows 2 and 3
    zeile2.pack_forget()
    zeile3.pack_forget()

    # Bind double-click on WPM label to toggle music controls
    lbl_wpm.bind("<Double-Button-1>", toggle_music_controls)

    # Make all visible widgets draggable (except volume scale – it has its own bindings)
    for widget in (btn_prev, btn_play_scan, btn_next, btn_pause, lbl_wpm, zeile1, frame):
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
