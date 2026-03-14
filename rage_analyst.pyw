"""
WPM Live-Overlay mit Rage-Detection & Zen-Modus
================================================
Verbesserungen gegenüber Original:
  - Thread-sicherer Zugriff auf `anschlaege` via threading.Lock
  - Sauberes Beenden (kein os._exit)
  - Playlist-Logik repariert (Song-Ende-Erkennung funktioniert korrekt)
  - Konsistentes ZEITFENSTER (Kommentar ↔ Code)
  - Alle Magic-Numbers als benannte Konstanten
  - Typ-Annotationen durchgehend
  - WPM-Berechnung präziser (rollendes Fenster)
"""

import os
import time
import threading
import logging
import tkinter as tk
from pynput import keyboard
import pygame

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------
# 1. Konfiguration
# ---------------------------------------------------------
ZEITFENSTER_SEK: float = 5.0       # Rollendes Fenster für WPM-Messung
RAGE_SCHWELLE: int     = 100       # WPM ab der der Zen-Modus ausgelöst wird
ZEN_DAUER_MS: int      = 5_000     # Wie lange das Zen-Popup sichtbar bleibt (ms)
ZEICHEN_PRO_WORT: int  = 5         # Standard: 1 Wort = 5 Tastenanschläge
POLL_INTERVAL_MS: int  = 150       # Wie oft die WPM-Anzeige aktualisiert wird (ms)
SONG_CHECK_MS: int     = 1_000     # Wie oft geprüft wird ob Song zu Ende ist (ms)

# ---------------------------------------------------------
# 2. Globaler Zustand (thread-sicher)
# ---------------------------------------------------------
_lock             = threading.Lock()
anschlaege: list[float] = []
beruhigungs_modus: bool  = False

playlist: list[str]     = []
aktueller_song_index: int = 0

# ---------------------------------------------------------
# 3. Keylogger (Hintergrund-Thread)
# ---------------------------------------------------------
def on_press(key) -> None:
    """Wird in einem eigenen Thread aufgerufen → Lock nötig."""
    with _lock:
        anschlaege.append(time.time())


def starte_keylogger() -> None:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ---------------------------------------------------------
# 4. Playlist & Audio
# ---------------------------------------------------------
def lade_playlist() -> None:
    global playlist
    playlist = sorted(
        f for f in os.listdir() if f.lower().endswith(".mp3")
    )
    log.info("Playlist geladen: %d Songs gefunden", len(playlist))


def spiele_naechsten_song() -> None:
    """Spielt den nächsten Song und plant automatisch den übernächsten."""
    global aktueller_song_index

    if not playlist:
        log.warning("Playlist ist leer – kein Song wird gespielt.")
        return

    song = playlist[aktueller_song_index]
    aktueller_song_index = (aktueller_song_index + 1) % len(playlist)

    try:
        pygame.mixer.music.load(song)
        # loops=-1 wenn nur 1 Song, sonst einmalig + auto-weiter
        loops = -1 if len(playlist) == 1 else 0
        pygame.mixer.music.play(loops=loops)
        log.info("Spiele: %s", song)

        if len(playlist) > 1:
            root.after(SONG_CHECK_MS, _song_watcher)
    except Exception as exc:
        log.error("Fehler beim Abspielen von '%s': %s", song, exc)


def _song_watcher() -> None:
    """Prüft ob der aktuelle Song zu Ende ist und spielt ggf. den nächsten."""
    if not pygame.mixer.music.get_busy():
        if beruhigungs_modus:          # Nur im Zen-Modus weiterspielen
            spiele_naechsten_song()
    else:
        root.after(SONG_CHECK_MS, _song_watcher)

# ---------------------------------------------------------
# 5. WPM-Analyse & Anzeige
# ---------------------------------------------------------
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
    """Thread-sicher: liest Anschläge, bereinigt altes Fenster, berechnet WPM."""
    jetzt = time.time()
    grenze = jetzt - ZEITFENSTER_SEK

    with _lock:
        # Altes aus dem Fenster herausrollen
        while anschlaege and anschlaege[0] < grenze:
            anschlaege.pop(0)

        if len(anschlaege) < 2:
            return 0

        vergangen = jetzt - anschlaege[0]
        vergangen = max(vergangen, 0.1)   # Division durch 0 vermeiden
        return round((len(anschlaege) / ZEICHEN_PRO_WORT) / (vergangen / 60))


def analysiere_tippgeschwindigkeit() -> None:
    global beruhigungs_modus

    wpm = berechne_wpm()
    emoji, farbe = get_wpm_emoji_und_farbe(wpm)
    lbl_wpm.config(text=f"{wpm} WPM {emoji}", fg=farbe)

    if wpm >= RAGE_SCHWELLE and not beruhigungs_modus:
        loese_zen_modus_aus()

    root.after(POLL_INTERVAL_MS, analysiere_tippgeschwindigkeit)

# ---------------------------------------------------------
# 6. Zen-Modus Popup
# ---------------------------------------------------------
def loese_zen_modus_aus() -> None:
    global beruhigungs_modus
    beruhigungs_modus = True
    log.info("Zen-Modus aktiviert (WPM >= %d)", RAGE_SCHWELLE)

    spiele_naechsten_song()

    zen = tk.Toplevel(root)
    zen.title("ZEN MODUS")
    zen.geometry("600x300")
    zen.attributes("-topmost", True)
    zen.configure(bg="#2c3e50")
    zen.overrideredirect(True)

    tk.Label(
        zen,
        text="⚠️ RAGE QUIT GEFAHR ⚠️\n\nHände weg von der Tastatur!\nAtme tief durch... 🧘",
        font=("Helvetica", 20, "bold"),
        fg="white",
        bg="#2c3e50",
        pady=50,
    ).pack(expand=True)

    def schliesse_zen() -> None:
        global beruhigungs_modus
        pygame.mixer.music.stop()
        with _lock:
            anschlaege.clear()
        beruhigungs_modus = False
        log.info("Zen-Modus beendet.")
        zen.destroy()

    zen.after(ZEN_DAUER_MS, schliesse_zen)

# ---------------------------------------------------------
# 7. Fenster verschieben (Drag)
# ---------------------------------------------------------
_drag_x: int = 0
_drag_y: int = 0

def start_move(event: tk.Event) -> None:
    global _drag_x, _drag_y
    _drag_x, _drag_y = event.x, event.y

def do_move(event: tk.Event) -> None:
    x = root.winfo_x() + (event.x - _drag_x)
    y = root.winfo_y() + (event.y - _drag_y)
    root.geometry(f"+{x}+{y}")

# ---------------------------------------------------------
# 8. Sauberes Beenden
# ---------------------------------------------------------
def programm_beenden() -> None:
    log.info("Programm wird beendet.")
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    root.destroy()   # mainloop endet → Prozess terminiert sauber

# ---------------------------------------------------------
# 9. Main
# ---------------------------------------------------------
if __name__ == "__main__":
    lade_playlist()

    keylogger_thread = threading.Thread(target=starte_keylogger, daemon=True)
    keylogger_thread.start()

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)

    TRANSPARENT = "#000001"
    root.configure(bg=TRANSPARENT)
    root.wm_attributes("-transparentcolor", TRANSPARENT)
    root.geometry("+1500+100")

    frame = tk.Frame(root, bg=TRANSPARENT)
    frame.pack()

    lbl_wpm = tk.Label(
        frame,
        text="0 WPM 🐢",
        font=("Helvetica", 36, "bold"),
        fg="#4CAF50",
        bg=TRANSPARENT,
    )
    lbl_wpm.pack(side="left", padx=10)

    btn_close = tk.Button(
        frame,
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

    # Drag-Bindungen
    for widget in (lbl_wpm, frame):
        widget.bind("<ButtonPress-1>", start_move)
        widget.bind("<B1-Motion>", do_move)

    analysiere_tippgeschwindigkeit()
    root.mainloop()
