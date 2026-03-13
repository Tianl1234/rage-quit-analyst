import os
import time
import threading
import tkinter as tk
from pynput import keyboard
import pygame

# ---------------------------------------------------------
# 1. Globale Variablen & Konfiguration
# ---------------------------------------------------------
ZEITFENSTER = 5.0  # Wir analysieren die Anschläge der letzten 5 Sekunden
RAGE_SCHWELLE = 350 # KPM Limit für den Rage-Modus
anschlaege = []
beruhigungs_modus = False

# Playlist Variablen
playlist = []
aktueller_song_index = 0

# Pygame Mixer für Audio initialisieren
pygame.mixer.init()

# ---------------------------------------------------------
# 2. Hintergrund-Logik (Pynput)
# ---------------------------------------------------------
def on_press(key):
    global anschlaege
    anschlaege.append(time.time())

def starte_keylogger():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

# ---------------------------------------------------------
# 3. Playlist & Audio-Logik
# ---------------------------------------------------------
def lade_playlist():
    global playlist
    playlist = [datei for datei in os.listdir() if datei.lower().endswith(".mp3")]
    print(f"Gefundene Songs: {len(playlist)}")

def spiele_musik():
    global aktueller_song_index, playlist
    
    if not playlist:
        return

    if len(playlist) == 1:
        try:
            pygame.mixer.music.load(playlist[0])
            pygame.mixer.music.play(loops=-1)
        except Exception:
            pass
    else:
        try:
            song = playlist[aktueller_song_index]
            pygame.mixer.music.load(song)
            pygame.mixer.music.play()
            
            aktueller_song_index = (aktueller_song_index + 1) % len(playlist)
            root.after(1000, pruefe_ob_song_zuende_ist)
        except Exception:
            pass

def pruefe_ob_song_zuende_ist():
    global beruhigungs_modus
    if beruhigungs_modus: 
        if not pygame.mixer.music.get_busy(): 
            spiele_musik() 
        else:
            root.after(1000, pruefe_ob_song_zuende_ist)

# ---------------------------------------------------------
# 4. GUI & Analyse-Logik (Tkinter)
# ---------------------------------------------------------
def analysiere_tippgeschwindigkeit():
    global anschlaege, beruhigungs_modus
    jetzt = time.time()

    # Alte Anschläge entfernen, die außerhalb des Fensters (5 Sek) liegen
    while anschlaege and anschlaege[0] < jetzt - ZEITFENSTER:
        anschlaege.pop(0)

    # Exakte Berechnung mit Stoßdämpfer (mindestens 2 Sekunden als Basis)
    if len(anschlaege) > 1:
        zeit_vergangen = jetzt - anschlaege[0]
        rechen_zeit = max(zeit_vergangen, 2.0)
        aktuelle_kpm = int((len(anschlaege) / rechen_zeit) * 60)
    else:
        aktuelle_kpm = 0

    lbl_kpm.config(text=f"{aktuelle_kpm} KPM")

    # Farben & Rage-Trigger
    if aktuelle_kpm < 150:
        lbl_kpm.config(fg="#4CAF50") # Grün (Entspannt)
    elif aktuelle_kpm < RAGE_SCHWELLE:
        lbl_kpm.config(fg="#FF9800") # Orange (Warnung)
    else:
        lbl_kpm.config(fg="#F44336") # Rot (Rage!)
        if not beruhigungs_modus:
            loese_zen_modus_aus()

    root.after(100, analysiere_tippgeschwindigkeit) 

def loese_zen_modus_aus():
    global beruhigungs_modus, anschlaege
    beruhigungs_modus = True

    spiele_musik()

    zen_fenster = tk.Toplevel(root)
    zen_fenster.title("ZEN MODUS")
    zen_fenster.geometry("600x300")
    zen_fenster.attributes('-topmost', True)
    zen_fenster.configure(bg="#2c3e50")
    zen_fenster.overrideredirect(True)

    tk.Label(
        zen_fenster, 
        text="⚠️ RAGE QUIT GEFAHR ⚠️\n\nHände weg von der Tastatur!\nAtme tief durch...", 
        font=("Helvetica", 20, "bold"), 
        fg="white", 
        bg="#2c3e50",
        pady=50
    ).pack(expand=True)

    def schliesse_zen():
        global beruhigungs_modus
        pygame.mixer.music.stop() 
        anschlaege.clear()
        beruhigungs_modus = False
        zen_fenster.destroy()

    # Nach 5000 Millisekunden (5 Sekunden) wird das Popup wieder geschlossen
    zen_fenster.after(5000, schliesse_zen)

# ---------------------------------------------------------
# 5. Fenster verschieben & Schließen
# ---------------------------------------------------------
def start_move(event):
    root.x = event.x
    root.y = event.y

def stop_move(event):
    root.x = None
    root.y = None

def do_move(event):
    deltax = event.x - root.x
    deltay = event.y - root.y
    x = root.winfo_x() + deltax
    y = root.winfo_y() + deltay
    root.geometry(f"+{x}+{y}")

def programm_beenden():
    root.destroy()
    import os
    os._exit(0)

# ---------------------------------------------------------
# 6. Startpunkt (Main)
# ---------------------------------------------------------
if __name__ == "__main__":
    lade_playlist()

    # Hintergrund-Thread für die Tastatur
    thread = threading.Thread(target=starte_keylogger, daemon=True)
    thread.start()

    # GUI Setup
    root = tk.Tk()
    root.overrideredirect(True) 
    root.attributes('-topmost', True) 
    
    # Transparenz einstellen (nur für Windows)
    TRANSPARENT_COLOR = "#000001"
    root.configure(bg=TRANSPARENT_COLOR)
    root.wm_attributes("-transparentcolor", TRANSPARENT_COLOR)
    
    root.geometry("+1500+100")

    frame = tk.Frame(root, bg=TRANSPARENT_COLOR)
    frame.pack()

    lbl_kpm = tk.Label(frame, text="0 KPM", font=("Helvetica", 36, "bold"), fg="#4CAF50", bg=TRANSPARENT_COLOR)
    lbl_kpm.pack(side="left", padx=10)

    btn_close = tk.Button(frame, text="✖", font=("Arial", 8), fg="gray", bg=TRANSPARENT_COLOR, bd=0, activebackground=TRANSPARENT_COLOR, activeforeground="white", cursor="hand2", command=programm_beenden)
    btn_close.pack(side="right", anchor="n")

    # Drag & Drop Events an das Label binden
    lbl_kpm.bind("<ButtonPress-1>", start_move)
    lbl_kpm.bind("<ButtonRelease-1>", stop_move)
    lbl_kpm.bind("<B1-Motion>", do_move)

    # Endlosschleife starten
    analysiere_tippgeschwindigkeit()
    root.mainloop()
