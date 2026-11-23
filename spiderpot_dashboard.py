"""The desktop control panel opened from the notification area."""
import tkinter as tk
from PIL import ImageTk

from spiderpot_guide_art import guide_scene
from spiderpot_support import circular_icon, resource, shortcut_label
from spiderpot_tutorial import ACCENT, BACKGROUND, MUTED, TEXT, MODES, button, label


class Dashboard(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root, bg=BACKGROUND)
        self.title("Spiderpot · Kontrol paneli")
        self.iconbitmap(str(resource("Assets/spiderpot.ico")))
        self.resizable(False, False)
        box = tk.Frame(self, bg=BACKGROUND, padx=20, pady=16)
        box.pack(fill="both", expand=True)
        header = tk.Frame(box, bg=BACKGROUND)
        header.pack(fill="x")
        self.logo = ImageTk.PhotoImage(circular_icon(32, active=app.is_active), master=self)
        label(header, image=self.logo).pack(side="left")
        label(header, text="Spiderpot", bold=True, size=14).pack(side="left", padx=7)
        button(header, "Ayarlar", app.open_settings).pack(side="right")
        label(box, text="Kontrol paneli", bold=True, size=22).pack(anchor="w", pady=(10, 0))
        state = "Mod etkin" if app.is_active else "Geri sayım sürüyor" if app.pending_mode else "Mod seçmeye hazır"
        label(box, text=state, color=ACCENT).pack(anchor="w", pady=(0, 10))
        cards = tk.Frame(box, bg=BACKGROUND)
        cards.pack(fill="x")
        scale = min(float(self.tk.call("tk", "scaling"))*.75, (self.winfo_screenwidth()-80)/620)
        for i, (mode, key, title, _) in enumerate(MODES):
            tile = tk.Frame(cards, bg="white", highlightthickness=1, highlightbackground="#DEDADB")
            tile.grid(row=0, column=i, padx=(0, 8 if i < 2 else 0), sticky="nsew")
            art = guide_scene(mode, (round(170*scale), round(66*scale)), app.viewer.slide_paths)
            photo = ImageTk.PhotoImage(art, master=self)
            thumbnail = tk.Label(tile, image=photo, bg="white", bd=0)
            thumbnail.image = photo
            thumbnail.pack(padx=6, pady=6)
            label(tile, text=title, bg="white", size=11, bold=True).pack(anchor="w", padx=8)
            label(tile, text=shortcut_label(getattr(app,key), mode=True), bg="white", color=MUTED).pack(anchor="w", padx=8)
            tk.Button(tile, text="Modu aç", font=("Segoe UI", 10, "bold"), bd=0, cursor="hand2",
                      bg="white", fg=ACCENT, activeforeground=ACCENT, command=lambda m=mode: app.start_system(m)
                      ).pack(anchor="w", padx=6, pady=(3, 6))
        camera = "açık" if app.camera_enabled else "kapalı"
        mail = "doğrulandı" if app.mailer else "kapalı"
        label(box, text=f"Kamera {camera}    ·    E-posta {mail}", color=MUTED).pack(anchor="w", pady=(12, 4))
        if app.last_summary:
            label(box, text="Son oturum", bold=True).pack(anchor="w")
            label(box, text=app.last_summary, color=MUTED).pack(anchor="w")
        footer = tk.Frame(box, bg=BACKGROUND)
        footer.pack(fill="x", pady=(10, 0))
        button(footer, "Fotoğraflar", app.open_gallery, primary=True).pack(side="left")
        button(footer, "Çıkmadan önce dene", app.open_check).pack(side="left", padx=5)
        button(footer, "Kullanımı gör", app.open_tutorial).pack(side="left")
        button(box, "Telefon eşleştir", app.open_remote_panel).pack(anchor="w", pady=(8, 0))
