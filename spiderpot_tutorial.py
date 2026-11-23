"""Interactive walkthrough driven by the running app's shortcut events."""
import tkinter as tk
from threading import Thread
from tkinter import messagebox
from tkinter import font as tkfont

from PIL import Image, ImageTk

from spiderpot_support import circular_icon, resource, shortcut_label, show_captures
from spiderpot_guide_art import guide_scene, rounded


MODES = (
    ("spider", "key_spider", "Duvar kâğıdı", "Seçtiğiniz görseller tam ekran açılır. Birden fazla görsel seçtiyseniz sırayla gösterilir."),
    ("black", "key_black", "Siyah ekran", "Ekranı siyah bir perde kaplar."),
    ("invisible", "key_lock", "Canlı masaüstü", "Açık uygulamalar ekranda canlı kalır. Fare ve klavye girişi moddan çıkana kadar duraklatılır."),
)

BACKGROUND = "#F8F7F5"
PANEL = "#24232E"
BORDER = "#DAD7D6"
TEXT = "#24212B"
MUTED = "#5F5A65"
ACCENT = "#AF2944"
GREEN = "#287050"


def label(parent, *, size=10, bold=False, color=TEXT, bg=BACKGROUND, **options):
    return tk.Label(parent, bg=bg, fg=color, font=("Segoe UI", size, "bold" if bold else "normal"),
                    anchor="w", justify="left", **options)


def button(parent, text, command, *, primary=False):
    face = tkfont.Font(root=parent, family="Segoe UI", size=10, weight="bold")
    unit = max(1, round(face.metrics("linespace") / 7))
    size = (face.measure(text) + unit*11, face.metrics("linespace") + unit*6)
    images = []
    for fill, edge in ((ACCENT, ACCENT) if primary else ("#FFFFFF", BORDER),
                       ("#91213B", "#91213B") if primary else ("#F1ECEF", "#AA9BA4")):
        tile = rounded((size[0]*2, size[1]*2), unit*6, fill, edge)
        images.append(ImageTk.PhotoImage(tile.resize(size, Image.Resampling.LANCZOS), master=parent))
    color = "white" if primary else TEXT
    widget = tk.Button(parent, text=text, image=images[0], compound="center", command=command,
                       bg=BACKGROUND, activebackground=BACKGROUND, fg=color, activeforeground=color,
                       highlightthickness=0, relief="flat", overrelief="flat", borderwidth=0,
                       font=face, cursor="hand2", padx=0, pady=0, takefocus=True)
    widget.images = images
    def refresh(event=None):
        hot = widget.focus_get() == widget or widget.winfo_containing(*widget.winfo_pointerxy()) == widget
        widget.configure(image=images[int(hot)])
    for event in ("<Enter>", "<Leave>", "<FocusIn>", "<FocusOut>"):
        widget.bind(event, refresh)
    widget.bind("<Return>", lambda event: widget.invoke())
    return widget


class SpiderpotTutorial:
    title = "Kullanımı gör"
    step_count = len(MODES) + 2
    steps = ("Slaytlar", "Siyah ekran", "Masaüstü", "Kamera", "Galeri")

    def __init__(self, app):
        self.app = app
        self.step = 0
        self.camera_armed = False
        self.camera_port = app.camera_port
        self.capture_name = None
        self.camera_error_text = ""
        self.gallery = None
        self.window = tk.Toplevel(app.root, bg=BACKGROUND)
        self.window.withdraw()
        self.window.title(f"Spiderpot · {self.title}")
        self.window.iconbitmap(str(resource("Assets/spiderpot.ico")))
        self.window.protocol("WM_DELETE_WINDOW", app.close_tutorial)
        self.window.resizable(False, False)
        scale = min(float(self.window.tk.call("tk", "scaling")) * .75,
                    (self.window.winfo_screenwidth() - 64) / 640)
        self.scene_size = (round(570*scale), round(150*scale))
        if self.window.winfo_screenheight() < 680*scale:
            self.scene_size = (self.scene_size[0], round(104*scale))
        self.scenes = {}
        self.logo = ImageTk.PhotoImage(circular_icon(round(28*scale)), master=self.window)
        body = tk.Frame(self.window, bg=BACKGROUND, padx=round(20*scale), pady=round(14*scale))
        body.pack(fill="both", expand=True)

        header = tk.Frame(body, bg=BACKGROUND)
        header.pack(fill="x")
        label(header, image=self.logo).pack(side="left")
        label(header, text="Spiderpot", size=13, bold=True).pack(side="left", padx=8)
        self.progress = label(header, size=10, color=MUTED)
        self.progress.pack(side="right")
        self.wallpaper = label(body, bd=0, padx=0, pady=0)
        self.wallpaper.pack(fill="x", pady=(12, 10))
        rail = tk.Frame(body, bg=BACKGROUND)
        rail.pack(fill="x", pady=(0, 12))
        self.segments = []
        self.step_labels = []
        for i, name in enumerate(self.steps):
            rail.columnconfigure(i, weight=1, uniform="step")
            cell = tk.Frame(rail, bg=BACKGROUND)
            cell.grid(row=0, column=i, sticky="ew", padx=(0, 4))
            segment = tk.Frame(cell, height=3, bg=BORDER)
            segment.pack(fill="x")
            caption = label(cell, text=name, size=9, color=MUTED)
            caption.pack(anchor="w", pady=(3, 0))
            self.segments.append(segment)
            self.step_labels.append(caption)

        self.heading = label(body, size=20, bold=True)
        self.heading.pack(fill="x")
        self.instructions = label(body, size=11, color=MUTED, wraplength=self.scene_size[0])
        self.instructions.pack(fill="x", pady=(6, 14))
        self.keycaps = tk.Frame(body, bg=BACKGROUND)
        self.shortcut = label(body, size=11, bold=True, color=TEXT, padx=2, pady=3)
        self.status = label(body, color=ACCENT, wraplength=self.scene_size[0])
        self.buttons = tk.Frame(body, bg=BACKGROUND)
        self.buttons.pack(side="bottom", fill="x", pady=(18, 0))

        self.active_card = tk.Toplevel(self.window, bg=BORDER)
        self.active_card.withdraw()
        self.active_card.overrideredirect(True)
        self.active_card.attributes("-topmost", True)
        card = tk.Frame(self.active_card, bg=PANEL, padx=15, pady=11)
        card.pack(fill="both", expand=True, padx=1, pady=1)
        self.card_heading = label(card, bg=PANEL, size=12, bold=True, color="#A4E4BC", wraplength=300)
        self.card_heading.pack(fill="x")
        self.card_instructions = label(card, bg=PANEL, color="#ECE5EB", wraplength=300)
        self.card_instructions.pack(fill="x", pady=(4, 0))
        self.render()

    def show_step(self, index, scene):
        if scene not in self.scenes:
            image = guide_scene(scene, self.scene_size, self.app.viewer.slide_paths)
            self.scenes[scene] = ImageTk.PhotoImage(image, master=self.window)
        self.wallpaper.configure(image=self.scenes[scene])
        self.progress.configure(text=f"{self.title}  ·  {index + 1} / {len(self.steps)}")
        for i, (bar, caption) in enumerate(zip(self.segments, self.step_labels)):
            bar.configure(bg=ACCENT if i == index else GREEN if i < index else BORDER)
            caption.configure(fg=ACCENT if i == index else GREEN if i < index else MUTED,
                              font=("Segoe UI", 9, "bold" if i == index else "normal"))

    def show_keys(self, key):
        for child in self.keycaps.winfo_children():
            child.destroy()
        self.keycaps.pack(anchor="w")
        label(self.keycaps, text="Modu aç", color=MUTED).pack(side="left", padx=(0, 10))
        face = tkfont.Font(root=self.window, family="Segoe UI", size=11, weight="bold")
        for i, name in enumerate(shortcut_label(getattr(self.app, key), mode=True).split(" + ")):
            if i:
                label(self.keycaps, text="+", color=MUTED).pack(side="left", padx=4)
            size = (max(face.measure(name) + 20, 36), face.metrics("linespace") + 12)
            img = rounded((size[0]*2, size[1]*2), 13, "#FFFFFF", "#BEB5BC")
            cap = ImageTk.PhotoImage(img.resize(size, Image.Resampling.LANCZOS), master=self.window)
            tile = label(self.keycaps, text=name, image=cap, compound="center", bold=True, size=11)
            tile.image = cap
            tile.pack(side="left")

    def render(self):
        self.active_card.withdraw()
        self.keycaps.pack_forget()
        self.status.pack_forget()
        for child in self.buttons.winfo_children():
            child.destroy()
        self.show_step(self.step, ("spider", "black", "invisible", "camera", "gallery")[self.step])

        exit_key = shortcut_label(self.app.key_exit)
        key = None
        if self.step < len(MODES):
            _, key, heading, explanation = MODES[self.step]
            instructions = (f"Kısayola basıp seçtiğiniz görselleri tam ekranda görün. {exit_key} ile geri dönün.",
                            f"Ekranı karartmak için kısayola basın. {exit_key} ile perdeyi kaldırın.",
                            f"Masaüstünüz canlı kalırken girişler duraklatılır. {exit_key} ile denemeyi bitirin.")[self.step]
        elif self.step == len(MODES):
            heading = "Kamerayı deneyin"
            if self.camera_armed:
                key = "key_lock"
                instructions = "Kısayola basın ve fareyi hareket ettirin. O anda çekilen kare ekranda 3 saniye görünür."
            else:
                instructions = ("Seçtiğiniz kamera, hareket algılandığında bir kare çeker. Kare ekranda gösterilir ve "
                                "bu cihazda şifreli saklanır.")
                button(self.buttons, "Kamera ile dene", self.arm_camera, primary=True).pack(side="left")
                button(self.buttons, "Kamera seç / test", self.choose_camera).pack(side="left", padx=8)
            button(self.buttons, "Atla", self.skip_camera).pack(side="right")
        else:
            heading = "Fotoğraflarınızı bulun"
            instructions = ("Galeride deneme sırasında çekilen kareyi açabilirsiniz. " if self.capture_name else "")
            instructions += "Dosyaların yerini görmek için galerideki Klasörü aç düğmesini kullanın."
            button(self.buttons, "Fotoğrafları aç", self.open_gallery, primary=True).pack(side="left")

        if key is not None:
            self.show_keys(key)
        self.status.configure(text=self.camera_error_text)
        self.status.pack(fill="x", pady=(3, 0))
        self.heading.configure(text=heading)
        self.instructions.configure(text=instructions)
        if self.step != len(MODES):
            text = "Tanıtımı bitir" if self.step > len(MODES) else "Tanıtımı kapat"
            button(self.buttons, text, self.app.close_tutorial).pack(side="right")
        self.window.deiconify()
        self.window.lift()

    def choose_camera(self):
        from spiderpot_camera_settings import CameraSettings
        CameraSettings(self.window, self.camera_port, self.set_camera)

    def set_camera(self, index):
        self.camera_port = index
        self.camera_error_text = ""
        self.render()

    def arm_camera(self):
        if not messagebox.askyesno(
            "Spiderpot · Kamera denemesi",
            "Bir test fotoğrafı için kamerayı kullanıp kareyi ekranlarda göstermeye ve "
            "bu cihazda şifreli saklamaya izin veriyor musunuz? Herkesin bilgisi ve izni olduğundan emin olun. "
            "Bu seçim normal kamera ayarınızı değiştirmez.",
            parent=self.window,
            default="no",
        ):
            return
        self.camera_error_text = ""
        self.camera_armed = True
        self.render()

    def accepts_mode(self, mode):
        if self.step < len(MODES):
            expected = MODES[self.step][0]
        else:
            expected = "invisible" if self.step == len(MODES) and self.camera_armed else None
        if expected is not None and mode == expected:
            return True
        self.status.configure(text="Bu adımda pencerede gösterilen kısayolu kullanın.")
        return False

    def mode_started(self):
        self.window.withdraw()
        if self.step < len(MODES):
            heading = f"{MODES[self.step][2]} açık"
            instruction = "Bir sonraki adıma geçin."
        else:
            heading = "Kamera denemesi açık"
            instruction = "Fotoğraf çekmek için fareyi hareket ettirin."
        self.update_card(heading, instruction)
        self.active_card.deiconify()
        self.active_card.geometry("-24+24")
        self.lift_active_card()

    def update_card(self, heading, instruction):
        exit_key = shortcut_label(self.app.key_exit)
        self.card_heading.configure(text=heading)
        self.card_instructions.configure(text=f"{instruction}\nÇıkış  ·  {exit_key}")

    def lift_active_card(self):
        if self.active_card.state() != "withdrawn":
            self.active_card.lift()

    def mode_stopped(self):
        if self.step < len(MODES):
            self.step += 1
        elif self.step == len(MODES):
            self.camera_armed = False
            if self.capture_name:
                self.step += 1
            elif not self.camera_error_text:
                self.camera_error_text = "Fotoğraf çekilmedi. Yeniden deneyebilir veya bu adımı atlayabilirsiniz."
        self.render()

    def photo_captured(self, name):
        self.capture_name = name
        self.camera_armed = False
        self.update_card("Fotoğraf çekildi", "Çektiğiniz kareyi görmek için galeri adımına geçin.")

    def camera_failed(self, reason):
        self.camera_error_text = reason + " Kamera seç / test ile aygıtı kontrol edebilirsiniz."
        self.camera_armed = False
        self.app.stop_system()

    def skip_camera(self):
        self.camera_armed = False
        self.camera_error_text = ""
        self.step += 1
        self.render()

    def open_gallery(self):
        if self.gallery is not None and self.gallery.winfo_exists():
            self.gallery.deiconify()
            self.gallery.lift()
            return
        self.gallery = tk.Toplevel(self.app.root)
        show_captures(self.gallery, initial_capture=self.capture_name, store=self.app.capture_store)
        self.gallery.lift()


class QuickCheck(SpiderpotTutorial):
    title = "Çıkmadan önce dene"
    step_count = 2
    steps = ("Modu dene", "Sonucu gör")

    def __init__(self, app):
        self.finished = False
        self.tested_mode = None
        self.activity_seen = False
        self.mail_status = ""
        self.mail_running = False
        super().__init__(app)

    def render(self):
        self.active_card.withdraw()
        for child in self.buttons.winfo_children():
            child.destroy()
        self.show_step(int(self.finished), self.tested_mode if self.finished else "check")
        self.heading.configure(text="Deneme sonucu" if self.finished else self.title)
        if self.finished:
            title = next(title for mode, _, title, _ in MODES if mode == self.tested_mode)
            camera = "Fotoğraf bu cihazda kaydedildi." if self.capture_name else self.camera_error_text or "Kamera denenmedi."
            activity = "Fare veya klavye etkinliği algılandı." if self.activity_seen else "Etkinlik algılanmadı."
            self.instructions.configure(text=f"{title}\n{activity}\n{camera}")
            self.shortcut.pack_forget()
            if self.capture_name:
                button(self.buttons, "Fotoğrafı aç", self.open_gallery, primary=True).pack(side="left")
            if self.app.mailer is not None:
                mail = button(self.buttons, "E-postayı dene", self.test_mail)
                mail.pack(side="left", padx=4)
                if self.mail_running:
                    mail.configure(state="disabled")
            self.status.configure(text=self.mail_status or ("E-posta bildirimleri kapalı." if self.app.mailer is None else ""))
            button(self.buttons, "Tekrar dene", self.reset).pack(side="left", padx=4)
        else:
            self.instructions.configure(text="Denemek istediğiniz modun kısayoluna basın. Mod açılınca fareyi oynatın, "
                                       f"ardından {shortcut_label(self.app.key_exit)} ile sonucu görün.")
            self.shortcut.configure(text="\n".join(f"{shortcut_label(getattr(self.app, key), mode=True)}   ·   {title}"
                                                   for _, key, title, _ in MODES))
            self.shortcut.pack(anchor="w")
            self.status.configure(text="Bu deneme için kamera açık." if self.camera_armed else "Kamera isteğe bağlı.")
            button(self.buttons, "Kamerayı kapat" if self.camera_armed else "Kamerayı da dene",
                   self.toggle_camera).pack(side="left")
            button(self.buttons, "Kamera seç / test", self.choose_camera).pack(side="left", padx=4)
        self.status.pack(anchor="w", pady=(6, 0))
        button(self.buttons, "Kapat", self.app.close_tutorial).pack(side="right")
        self.window.deiconify()
        self.window.lift()

    def toggle_camera(self):
        if self.camera_armed:
            self.camera_armed = False
            self.render()
        else:
            self.arm_camera()

    def accepts_mode(self, mode):
        if self.finished:
            return False
        self.tested_mode = mode
        return True

    def mode_started(self):
        self.window.withdraw()
        self.update_card("Mod açık", "Şimdi fareyi oynatın veya bir tuşa basın.")
        self.active_card.deiconify()
        self.active_card.geometry("-24+24")
        self.lift_active_card()
        self.watch_activity(self.app.session_generation)

    def watch_activity(self, generation):
        if self.app.tutorial is not self or not self.app._capture_is_current(generation):
            return
        if self.app.session.first_activity:
            if not self.capture_name:
                self.update_card("Etkinlik algılandı", "Kamera fotoğrafı bekleniyor." if self.camera_armed else "Sonucu görmek için moddan çıkın.")
        else:
            self.window.after(100, self.watch_activity, generation)

    def photo_captured(self, name):
        self.capture_name = name
        self.camera_armed = False
        self.update_card("Test fotoğrafı kaydedildi", "Fotoğrafı yeniden açmak için moddan çıkın.")

    def mode_stopped(self):
        self.activity_seen = self.app.session.first_activity is not None
        if self.camera_armed and not self.capture_name:
            self.camera_error_text = "Fotoğraf kaydedilmeden deneme sonlandırıldı."
        self.camera_armed = False
        self.finished = True
        self.render()

    def reset(self):
        self.finished = False
        self.capture_name = None
        if self.gallery is not None and self.gallery.winfo_exists():
            self.gallery.destroy()
        self.gallery = None
        self.camera_error_text = ""
        if not self.mail_running:
            self.mail_status = ""
        self.render()

    def test_mail(self):
        if self.mail_running or self.app.mailer is None:
            return
        self.mail_running = True
        self.mail_status = "Metin bildirimi gönderiliyor…"
        self.render()
        def complete(status):
            if self.app.tutorial is self:
                self.mail_running = False
                self.mail_status = status
                if self.finished:
                    self.render()
        def send():
            from spiderpot_mail import MailError
            try:
                mailer = self.app.mailer
                sent = mailer.client.alert(mailer.token)
                status = "E-posta gönderildi." if sent else "Gönderim sınırına ulaşıldı. Daha sonra tekrar deneyin."
            except MailError as error:
                status = str(error)
            if not self.app.closed:
                self.app.root.after(0, complete, status)
        Thread(target=send, daemon=True).start()
