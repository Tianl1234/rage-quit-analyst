#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
WPM Live-Overlay mit Rage-Detection & Zen-Modus
================================================
- Speziell angepasst für Python 3.13
- Automatische Erkennung und Fallback bei fehlendem pygame.mixer
- pynput wird auf kompatible Version aktualisiert
"""

import sys
import subprocess
import tkinter as tk
from tkinter import messagebox

# ------------------------------------------------------------
# 1. Python-Version prüfen (für 3.13 spezielle Behandlung)
# ------------------------------------------------------------
PY_VERSION = sys.version_info[:2]
IS_PY313 = PY_VERSION >= (3, 13)

if IS_PY313:
    # Kein Abbruch, aber Hinweis
    print("🔔 Python 3.13 erkannt – aktiviere Kompatibilitätsmodus")
    
    # pynput muss mindestens Version 1.7.8 sein
    try:
        import pynput
        from pynput import keyboard
        # Prüfen, ob alt
        if pynput.__version__ < "1.7.8":
            print("⚠️  Veraltete pynput-Version erkannt – aktualisiere...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pynput"])
    except (ImportError, AttributeError):
        pass

# ------------------------------------------------------------
# 2. Fehlende Pakete installieren/aktualisieren
# ------------------------------------------------------------
REQUIRED_PACKAGES = ["pynput", "pygame"]

for pkg in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
    except ImportError:
        print(f"🔧 {pkg} nicht gefunden – versuche Installation...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pkg],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"✅ {pkg} erfolgreich installiert.")
        except Exception as e:
            print(f"❌ Installation von {pkg} fehlgeschlagen: {e}")
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Installationsfehler",
                f"Das Paket '{pkg}' konnte nicht installiert werden.\n\n"
                "Bitte führe folgenden Befehl manuell aus:\n"
                f"  {sys.executable} -m pip install {pkg}\n\n"
                "Stelle sicher, dass du eine stabile Internetverbindung hast."
            )
            sys.exit(1)

# ------------------------------------------------------------
# 3. Jetzt können die Pakete importiert werden
# ------------------------------------------------------------
import time
import threading
import logging
import os
from pynput import keyboard
import pygame

# ------------------------------------------------------------
# 4. Mixer-Verfügbarkeit prüfen
# ------------------------------------------------------------
MIXER_VERFUEGBAR = False
try:
    pygame.mixer.init()
    MIXER_VERFUEGBAR = True
    print("✅ pygame.mixer verfügbar – Musik wird unterstützt")
except Exception as e:
    print(f"⚠️  pygame.mixer nicht verfügbar: {e}")
    print("   Das Overlay läuft trotzdem, aber ohne Musik-Funktionen.")

# ------------------------------------------------------------
# 5. Restliches Skript mit Fallback-Logik
# ------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# Konfiguration
ZEITFENSTER_SEK: float = 5.0
RAGE_SCHWELLE: int     = 100
ZEN_DAUER_MS: int      = 5_000
ZEICHEN_PRO_WORT: int  = 5
POLL_INTERVAL_MS: int  = 150
SONG_CHECK_MS: int     = 1_000

# Globaler Zustand
_lock             = threading.Lock()
anschlaege: list[float] = []
beruhigungs_modus: bool  = False

playlist: list[str]     = []
aktueller_song_index: int = 0

# ------------------------------------------------------------
# 6. Keylogger (pynput 1.7.8+ ist kompatibel)
# ------------------------------------------------------------
def on_press(key) -> None:
    with _lock:
        anschlaege.append(time.time())

def starte_keylogger() -> None:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ------------------------------------------------------------
# 7. Playlist & Audio (mit Mixer-Prüfung)
# ------------------------------------------------------------
def lade_playlist() -> None:
    global playlist
    playlist = sorted(
        f for f in os.listdir() if f.lower().endswith(".mp3")
    )
    log.info("Playlist geladen: %d Songs gefunden", len(playlist))
    if not playlist:
        log.warning("Keine MP3-Dateien im aktuellen Verzeichnis!")

def spiele_song(index: int) -> None:
    if not MIXER_VERFUEGBAR:
        log.warning("Mixer nicht verfügbar – kein Abspielen möglich")
        return
    if not playlist:
        log.warning("Keine Playlist geladen – nichts abgespielt.")
        return

    idx = index % len(playlist)
    song = playlist[idx]
    try:
        pygame.mixer.music.load(song)
        pygame.mixer.music.play()
        log.info("Spiele: %s", song)

        if len(playlist) > 1:
            root.after(SONG_CHECK_MS, _song_watcher)
    except Exception as e:
        log.error("Fehler beim Abspielen von '%s': %s", song, e)

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
        log.info("Scan abgeschlossen – erster Song gestartet.")
    elif not MIXER_VERFUEGBAR:
        log.warning("Mixer nicht verfügbar – kann keine Musik abspielen")
        # Trotzdem Playlist anzeigen
        if playlist:
            messagebox.showinfo("Info", 
                "Musik-Funktionen sind deaktiviert, da pygame.mixer nicht verfügbar ist.\n"
                "Das WPM-Overlay funktioniert trotzdem.")
    else:
        log.warning("Keine MP3-Dateien gefunden – nichts abgespielt.")

def _song_watcher() -> None:
    if not MIXER_VERFUEGBAR:
        return
    if not pygame.mixer.music.get_busy():
        if beruhigungs_modus:
            spiele_naechsten_song()
    else:
        root.after(SONG_CHECK_MS, _song_watcher)

# ------------------------------------------------------------
# 8. WPM-Analyse (unverändert)
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
# 9. Zen-Modus Popup (mit Mixer-Prüfung)
# ------------------------------------------------------------
def loese_zen_modus_aus() -> None:
    global beruhigungs_modus
    beruhigungs_modus = True
    log.info("Zen-Modus aktiviert (WPM >= %d)", RAGE_SCHWELLE)

    if MIXER_VERFUEGBAR:
        spiele_naechsten_song()

    zen = tk.Toplevel(root)
    zen.title("ZEN MODUS")
    zen.geometry("600x300")
    zen.attributes("-topmost", True)
    zen.configure(bg="#2c3e50")
    zen.overrideredirect(True)

    text = "⚠️ RAGE QUIT GEFAHR ⚠️\n\nHände weg von der Tastatur!\nAtme tief durch... 🧘"
    if not MIXER_VERFUEGBAR:
        text += "\n\n(Hinweis: Musik ist deaktiviert)"
    
    tk.Label(
        zen,
        text=text,
        font=("Helvetica", 20, "bold"),
        fg="white",
        bg="#2c3e50",
        pady=50,
    ).pack(expand=True)

    def schliesse_zen() -> None:
        global beruhigungs_modus
        if MIXER_VERFUEGBAR:
            try:
                pygame.mixer.music.stop()
            except Exception as e:
                log.error("Musik konnte nicht gestoppt werden: %s", e)

        with _lock:
            anschlaege.clear()

        beruhigungs_modus = False
        log.info("Zen-Modus beendet.")
        zen.destroy()

    zen.after(ZEN_DAUER_MS, schliesse_zen)

# ------------------------------------------------------------
# 10. Fenster verschieben (Drag)
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
# 11. Sauberes Beenden
# ------------------------------------------------------------
def programm_beenden() -> None:
    log.info("Programm wird beendet.")
    if MIXER_VERFUEGBAR:
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass
    root.destroy()

# ------------------------------------------------------------
# 12. Hauptprogramm
# ------------------------------------------------------------
if __name__ == "__main__":
    # Mixer ist bereits getestet (siehe oben)
    
    # Playlist laden (falls vorhanden)
    lade_playlist()

    # Keylogger-Thread starten
    keylogger_thread = threading.Thread(target=starte_keylogger, daemon=True)
    keylogger_thread.start()

    # Hauptfenster erstellen
    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    TRANSPARENT = "#000001"
    root.configure(bg=TRANSPARENT)
    root.wm_attributes("-transparentcolor", TRANSPARENT)
    root.geometry("+1500+100")

    # Falls Mixer nicht verfügbar, Buttons deaktivieren (optional)
    btn_state = "normal" if MIXER_VERFUEGBAR else "disabled"

    # Haupt-Frame
    frame = tk.Frame(root, bg=TRANSPARENT)
    frame.pack()

    # ---- Zeile 1: WPM-Anzeige + Schließen-Button ----
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

    # ---- Zeile 2: Steuerungs-Buttons (Spotify-Stil) ----
    zeile2 = tk.Frame(frame, bg=TRANSPARENT)
    zeile2.pack(side="top", fill="x", pady=(0, 5))

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

    # Drag-Funktionalität für alle Elemente
    for widget in (btn_prev, btn_play_scan, btn_next, lbl_wpm, frame):
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)

    # WPM-Überwachung starten
    analysiere_tippgeschwindigkeit()

    # Hinweis bei deaktivierter Musik
    if not MIXER_VERFUEGBAR:
        log.info("Hinweis: Musik-Buttons sind deaktiviert (kein pygame.mixer)")
        # Kurzes Popup beim Start
        root.after(1000, lambda: messagebox.showinfo(
            "Musik deaktiviert",
            "pygame.mixer ist nicht verfügbar.\n"
            "Die Musiksteuerung wurde deaktiviert.\n"
            "Das WPM-Overlay funktioniert trotzdem."
        ))

    # Hauptschleife
    root.mainloop()
