import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
from spiderpot_support import (CAMERA_NOTICE, config_path, load_config, save_config, resource,
                               set_startup, launch, show_privacy, circular_icon, package_family,
                               shortcut_label)
from spiderpot_mail import configured_url, decode_enrollment, encode_enrollment
from spiderpot_mail_settings import MailSettings


class MonitorInfo(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                ('work', wintypes.RECT), ('flags', wintypes.DWORD)]


def wizard_geometry(root, scale, preferred=(742, 532)):
    user = ctypes.windll.user32
    point = wintypes.POINT()
    user.GetCursorPos(ctypes.byref(point))
    user.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
    user.MonitorFromPoint.restype = wintypes.HANDLE
    user.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    info = MonitorInfo(size=ctypes.sizeof(MonitorInfo))
    if user.GetMonitorInfoW(user.MonitorFromPoint(point, 2), ctypes.byref(info)):
        work = info.work
    else:
        work = wintypes.RECT(0, 0, root.winfo_screenwidth(), root.winfo_screenheight())
    aw, ah = work.right - work.left, work.bottom - work.top
    # Tk sizes the client area. Reserve space for the native resize frame and title bar as well.
    frame_x, frame_y = round(16*scale), round(42*scale)
    width = min(round(preferred[0]*scale), max(1, round(aw*.88) - frame_x))
    height = min(round(preferred[1]*scale), max(1, round(ah*.80) - frame_y))
    x = work.left + (aw - width - frame_x)//2
    y = work.top + (ah - height - frame_y)//2
    return width, height, x, y


class SpiderpotBuilderApp:
    def __init__(self, root, setup_finish=None):
        self.root = root
        first_setup = not config_path().is_file()
        self.setup_finish = first_setup if setup_finish is None else setup_finish
        self.root.title("Spiderpot Kurulum Sihirbazı")
        self.build_dir = str(resource(''))
        self.core_script = os.path.join(self.build_dir, "Assets", "Spiderpot_Core.py")
        self.config = load_config()
        self.mail_enrollment = decode_enrollment(self.config['mail_enrollment'])
        self.mail_url = configured_url()
        selected = self.config['slides'] or (self.config['wallpaper'],)
        self.selected_wallpapers = [path for path in selected if path and os.path.isfile(path)]
        if not self.selected_wallpapers:
            self.selected_wallpapers = [str(resource('Assets/spiderpot-wallpaper.jpg'))]
        self.camera_index = self.config['camera_index']
        self.slide_seconds_var = tk.IntVar(value=self.config['slide_seconds'])
        self.standalone = getattr(sys, 'frozen', False) and not package_family()

        # Use Windows' native themed controls and scale pixel dimensions with text.
        self.ui_scale = max(1.0, float(root.tk.call("tk", "scaling")) / (96 / 72))
        px = lambda value: round(value * self.ui_scale)
        width, height, x, y = wizard_geometry(root, self.ui_scale)
        self.root.resizable(True, True)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(min(width, px(460)), min(height, px(310)))
        def maximize_first_open(event):
            if event.widget is root:
                root.unbind("<Map>", map_binding)
                root.state("zoomed")
        map_binding = root.bind("<Map>", maximize_first_open, add="+")
        self.root.configure(bg="#f3f3f3")
        try:
            root.iconbitmap(str(resource('Assets/spiderpot.ico')))
        except tk.TclError:
            pass
        style = ttk.Style(root)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        root.option_add("*Font", ("Segoe UI", 10))
        style.configure("Setup.TFrame", background="#f3f3f3")
        style.configure("Setup.TLabel", background="#f3f3f3", foreground="#202020")
        style.configure("Muted.Setup.TLabel", background="#f3f3f3", foreground="#626262", font=("Segoe UI", 9))
        style.configure("Setup.TLabelframe", background="#f3f3f3")
        style.configure("Setup.TLabelframe.Label", background="#f3f3f3", foreground="#202020", font=("Segoe UI", 10, "bold"))
        style.configure("Setup.TCheckbutton", background="#f3f3f3", font=("Segoe UI", 10))
        style.configure("Setup.TButton", padding=(px(10), px(5)))

        header = tk.Frame(root, bg="white", padx=px(18), pady=px(9))
        header.pack(fill="x")
        from PIL import ImageTk
        self.brand_logo = ImageTk.PhotoImage(circular_icon(px(44)))
        tk.Label(header, image=self.brand_logo, bg='white').pack(side='right', padx=(px(12), 0))
        tk.Label(header, text="Spiderpot Kurulumu", bg="white", fg="#202020",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(header, text="Fotoğrafınızı ve kısayollarınızı seçin, ardından Spiderpot'u başlatın.",
                 bg="white", fg="#626262", font=("Segoe UI", 10)).pack(anchor="w", pady=(px(4), 0))
        ttk.Separator(root).pack(fill="x")

        # A conventional Windows wizard button bar, kept separate from settings.
        footer = ttk.Frame(root, style="Setup.TFrame", padding=(px(20), px(13)))
        footer.pack(side="bottom", fill="x")
        self.btn_cancel = ttk.Button(footer, text="İptal", command=root.destroy, style="Setup.TButton")
        self.btn_cancel.pack(side="right")
        self.btn_build = ttk.Button(footer, text="Kaydet ve Devam Et" if self.setup_finish else "Kaydet ve Başlat", command=self.start_build,
                                    style="Setup.TButton", default="active")
        self.btn_build.pack(side="right", padx=(0, px(9)))
        ttk.Button(footer, text="Gizlilik", command=lambda: show_privacy(root), style="Setup.TButton").pack(side="left")
        if self.standalone:
            from spiderpot_upgrade import saved_installer
            if saved_installer().is_file():
                ttk.Button(footer, text="Spiderpot’u kaldır…", command=lambda: self.start_uninstaller(saved_installer()),
                           style="Setup.TButton").pack(side="left", padx=px(6))
        ttk.Separator(root).pack(side="bottom", fill="x")

        main = ttk.Frame(root, style="Setup.TFrame")
        main.pack(fill="both", expand=True)
        left = tk.Frame(main, bg="#10151d", width=px(150))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        image_area = tk.Frame(left, bg="#10151d", height=px(200))
        image_area.pack(fill="x")
        image_area.pack_propagate(False)
        self.wallpaper_preview = tk.Label(image_area, bg="#10151d", bd=0)
        self.wallpaper_preview.pack(fill="both", expand=True)
        self.update_wallpaper_preview()
        tk.Label(left, text="SPIDERPOT", bg="#10151d", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=px(12), pady=px(14))

        scroll_area = ttk.Frame(main, style="Setup.TFrame")
        scroll_area.pack(side="left", fill="both", expand=True)
        def fit_sidebar(event):
            if event.width < px(1080):
                left.pack_forget()
            elif not left.winfo_manager():
                left.pack(side="left", fill="y", before=scroll_area)
        main.bind("<Configure>", fit_sidebar)
        canvas = tk.Canvas(scroll_area, bg="#f3f3f3", highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_area, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        right = ttk.Frame(canvas, style="Setup.TFrame", padding=(px(13), px(10)))
        preferences = ttk.Frame(right, style="Setup.TFrame")
        controls = ttk.Frame(right, style="Setup.TFrame")
        preferences.grid(row=0, column=0, sticky="new")
        controls.grid(row=1, column=0, sticky="new")
        canvas_item = canvas.create_window(0, 0, anchor="nw", window=right)
        def arrange_form(event):
            column_width = max(preferences.winfo_reqwidth(), controls.winfo_reqwidth())
            two_columns = event.width >= 2 * column_width + px(44)
            right.columnconfigure(0, weight=1, uniform="form")
            right.columnconfigure(1, weight=int(two_columns), uniform="form" if two_columns else "")
            controls.grid(row=0 if two_columns else 1, column=int(two_columns), sticky="new",
                          padx=(px(12) if two_columns else 0, 0))
            canvas.configure(scrollregion=canvas.bbox("all"))
        right.bind("<Configure>", arrange_form)
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(canvas_item, width=event.width))
        def scroll_form(event):
            if str(event.widget).startswith(str(canvas)) and event.delta:
                canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        root.bind("<MouseWheel>", scroll_form, add="+")
        self.mail_form = MailSettings(preferences, self.mail_url or (self.mail_enrollment or {}).get('url', ''),
                                      self.mail_enrollment, self.set_mail)
        self.mail_form.pack(fill='x', pady=(0, px(14)))
        wallpaper = ttk.LabelFrame(controls, text="Fotoğraf modu · Slaytlar", style="Setup.TLabelframe", padding=px(12))
        wallpaper.pack(fill="x", pady=(0, px(14)))
        ttk.Button(wallpaper, text="Görselleri düzenle…", command=self.edit_wallpapers, style="Setup.TButton").pack(side="right")
        self.lbl_wp = ttk.Label(wallpaper, text=self.wallpaper_summary(), style="Setup.TLabel", anchor="w")
        self.lbl_wp.pack(side="left", fill="x", expand=True, padx=(0, px(10)))

        shortcuts = ttk.LabelFrame(controls, text="Kısayol ayarları", style="Setup.TLabelframe", padding=px(12))
        shortcuts.pack(fill="x", pady=(0, px(14)))
        shortcuts.columnconfigure(0, weight=1)
        for row, (title, attr, value) in enumerate((
                ("Tuzak 1 · Seçilen fotoğraf", "k1_entry", "1"),
                ("Tuzak 2 · Siyah ekran", "k2_entry", "2"),
                ("Tuzak 3 · Mevcut ekran", "k3_entry", "3"))):
            ttk.Label(shortcuts, text=title, style="Setup.TLabel").grid(row=row, column=0, sticky="w", pady=px(5))
            entry = ttk.Entry(shortcuts, width=20, justify="center")
            entry.insert(0, shortcut_label(self.config[{'k1_entry':'key_spider','k2_entry':'key_black','k3_entry':'key_lock'}[attr]], mode=True))
            entry.grid(row=row, column=2, sticky="e", pady=px(5))
            setattr(self, attr, entry)
        ttk.Separator(shortcuts).grid(row=3, column=0, columnspan=3, sticky="ew", pady=px(7))
        ttk.Label(shortcuts, text="Tuzağı kapatma tuşu", style="Setup.TLabel").grid(row=4, column=0, sticky="w", pady=px(5))
        self.ke_combo = ttk.Combobox(shortcuts, values=[*(f"F{i}" for i in range(1, 13)), "Esc", "End"], width=18, justify="center")
        self.ke_combo.set(shortcut_label(self.config['key_exit']))
        self.ke_combo.grid(row=4, column=2, sticky="e")
        self.arming_var = tk.IntVar(value=self.config['arming_seconds'])
        ttk.Label(shortcuts, text="Başlangıç geri sayımı (sn, 0 = hemen)", style="Setup.TLabel").grid(
            row=6, column=0, sticky="w", pady=px(5))
        ttk.Spinbox(shortcuts, from_=0, to=30, width=6, textvariable=self.arming_var).grid(row=6, column=2, sticky="e")
        ttk.Label(shortcuts, text="Örnek: Ctrl + Q, Alt + Shift + 2 veya F8",
                  style="Muted.Setup.TLabel").grid(row=5, column=0, columnspan=3, sticky="w", pady=(px(8), 0))

        options = ttk.LabelFrame(preferences, text="Kurulum seçenekleri", style="Setup.TLabelframe", padding=px(12))
        options.pack(fill="x")
        self.auto_start_var = tk.BooleanVar(value=first_setup or self.config['auto_start'])
        ttk.Checkbutton(options, text="Windows açıldığında otomatik başlat", variable=self.auto_start_var,
                        style="Setup.TCheckbutton").pack(anchor="w", pady=(0, px(8)))
        self.camera_var = tk.BooleanVar(value=first_setup or self.config['camera_enabled'])
        camera_row = ttk.Frame(options, style="Setup.TFrame")
        camera_row.pack(fill="x", pady=(0, px(8)))
        ttk.Checkbutton(camera_row, text="Etkinlikte kameradan fotoğraf çek", variable=self.camera_var,
                        style="Setup.TCheckbutton").pack(side="left")
        self.camera_button = ttk.Button(camera_row, text=f"Kamera {self.camera_index} · Seç / Test", command=self.edit_camera)
        self.camera_button.pack(side="right")
        self.desktop_shortcut_var = tk.BooleanVar(value=self.config['desktop_shortcut'] or (first_setup and self.standalone))
        if self.standalone:
            ttk.Checkbutton(options, text="Masaüstü kısayolu oluştur", variable=self.desktop_shortcut_var,
                            style="Setup.TCheckbutton").pack(anchor="w", pady=(0, px(8)))
        retention_row = ttk.Frame(options, style='Setup.TFrame')
        retention_row.pack(fill='x')
        ttk.Label(retention_row, text="Fotoğrafları sakla (gün):", style='Setup.TLabel').pack(side='left')
        self.retention_var = tk.IntVar(value=self.config['retention_days'])
        ttk.Spinbox(retention_row, from_=1, to=30, textvariable=self.retention_var, width=5).pack(side='right')
        ttk.Label(options, text="Kamera çekimi açılırken onay istenir. Fotoğraflar yerel ve şifrelidir.",
                  style='Muted.Setup.TLabel').pack(anchor='w', pady=(px(8), 0))

        self.status_label = tk.Label(preferences, text="", bg="#f3f3f3", fg="#626262",
                                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=px(570))
        self.status_label.pack(fill="x", pady=(px(13), px(6)))

    def update_wallpaper_preview(self):
        from PIL import Image, ImageOps, ImageTk
        try:
            with Image.open(resource('Assets/spider_noir.jpg')) as source:
                image = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"),
                                     (round(150 * self.ui_scale), round(200 * self.ui_scale)),
                                     method=Image.Resampling.LANCZOS)
            self.wizard_photo = ImageTk.PhotoImage(image)
            self.wallpaper_preview.configure(image=self.wizard_photo, text="")
        except (OSError, ValueError):
            self.wallpaper_preview.configure(image="", text="Spiderpot", fg="white", font=("Segoe UI", 18, "bold"))

    def get_desktop_path(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            return winreg.QueryValueEx(key, "Desktop")[0]
        except:
            return os.path.join(os.path.expanduser("~"), "Desktop")

    def wallpaper_summary(self):
        count = len(self.selected_wallpapers)
        return f"{count} görsel · {self.slide_seconds_var.get()} sn aralık" if count > 1 else "1 görsel · Sabit"

    def edit_wallpapers(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Spiderpot · Slayt görselleri")
        dialog.transient(self.root)
        dialog.grab_set()
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Fotoğraf modunda gösterilecek görseller").pack(anchor="w")
        listing = tk.Listbox(body, width=58, height=8, exportselection=False)
        listing.pack(fill="both", expand=True, pady=9)
        paths = self.selected_wallpapers[:]
        interval = tk.StringVar(value=str(self.slide_seconds_var.get()))

        def refresh(index=None):
            listing.delete(0, "end")
            for i, path in enumerate(paths, 1):
                listing.insert("end", f"{i}. {Path(path).name}")
            if index is not None and paths:
                listing.selection_set(min(index, len(paths)-1))

        def add():
            files = filedialog.askopenfilenames(parent=dialog, title="Slayt görsellerini seçin",
                                              filetypes=[("Resim dosyaları", "*.jpg *.jpeg *.png *.bmp *.webp")])
            empty_default = paths == [str(resource('Assets/spiderpot-wallpaper.jpg'))]
            if files and empty_default:
                paths.clear()
            paths.extend(path for path in files if path not in paths)
            refresh()

        def change(offset=None):
            if not listing.curselection():
                return
            index = listing.curselection()[0]
            if offset is None:
                paths.pop(index)
            elif 0 <= index+offset < len(paths):
                paths[index], paths[index+offset] = paths[index+offset], paths[index]
                index += offset
            refresh(index)

        def apply():
            try:
                seconds = int(interval.get())
                if not 1 <= seconds <= 300:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Slayt aralığı", "1 ile 300 arasında bir saniye değeri girin.", parent=dialog)
                return
            self.selected_wallpapers = paths or [str(resource('Assets/spiderpot-wallpaper.jpg'))]
            self.slide_seconds_var.set(seconds)
            self.lbl_wp.configure(text=self.wallpaper_summary())
            dialog.destroy()

        actions = ttk.Frame(body)
        actions.pack(fill="x")
        for text, command in (("Görsel ekle…", add), ("Yukarı", lambda: change(-1)),
                              ("Aşağı", lambda: change(1)), ("Çıkar", change)):
            ttk.Button(actions, text=text, command=command).pack(side="left", padx=(0, 5))
        bottom = ttk.Frame(body)
        bottom.pack(fill="x", pady=(12, 0))
        ttk.Label(bottom, text="Görsel süresi (sn)").pack(side="left")
        ttk.Spinbox(bottom, from_=1, to=300, textvariable=interval, width=6).pack(side="left", padx=6)
        ttk.Button(bottom, text="Uygula", command=apply).pack(side="right")
        refresh()

    def edit_camera(self):
        from spiderpot_camera_settings import CameraSettings
        CameraSettings(self.root, self.camera_index, self.set_camera)

    def set_camera(self, index):
        self.camera_index = index
        self.camera_button.configure(text=f"Kamera {index} · Seç / Test")

    def set_mail(self, enrollment):
        self.mail_enrollment = enrollment

    def start_uninstaller(self, installer):
        try:
            subprocess.Popen([str(installer), "--uninstall"], creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as error:
            messagebox.showerror("Kaldırma başlatılamadı", str(error), parent=self.root)
            return
        self.root.destroy()

    def start_build(self):
        try:
            if not self.mail_form.ready_to_save():
                self.mail_form.email.focus_set()
                raise ValueError("E-posta adresinizi kodla doğrulayın veya e-posta alanını önceki değerine döndürün.")
            config = dict(self.config)
            config.update(key_spider=self.k1_entry.get().strip().lower(),
                          key_black=self.k2_entry.get().strip().lower(),
                          key_lock=self.k3_entry.get().strip().lower(),
                          key_exit=self.ke_combo.get().strip().lower(),
                          arming_seconds=self.arming_var.get(),
                          camera_enabled=self.camera_var.get(),
                          camera_index=self.camera_index,
                          slide_seconds=self.slide_seconds_var.get(),
                          desktop_shortcut=self.desktop_shortcut_var.get(),
                          auto_start=self.auto_start_var.get(),
                          mail_enrollment=encode_enrollment(self.mail_enrollment),
                          retention_days=self.retention_var.get())
            from spiderpot_support import validate
            validate(config)
            if config['camera_enabled'] and not self.config['camera_enabled']:
                allowed = messagebox.askyesno("Spiderpot · Kamera kullanımı", CAMERA_NOTICE,
                                              parent=self.root, default="no")
                config['camera_enabled'] = allowed
                self.camera_var.set(allowed)
            startup_changed = config['auto_start'] != self.config['auto_start']
            self.config = save_config(config, self.selected_wallpapers)
            executable = None
            if self.standalone:
                from spiderpot_upgrade import install_bundle
                executable = install_bundle(Path(sys.executable).parent, config['auto_start'],
                                            desktop_shortcut=config['desktop_shortcut'])
            elif startup_changed:
                set_startup(config['auto_start'])
            if self.setup_finish:
                self.show_finish(executable)
            else:
                self.start_runtime(executable)
        except Exception as error:
            self.status_label.config(text="Ayarlar uygulanamadı.", fg="#a4262c")
            messagebox.showerror("Spiderpot", str(error), parent=self.root)

    def start_runtime(self, executable, activity=None):
        arguments = ['--run', activity] if activity else ['--run']
        try:
            if executable is None:
                launch(*arguments)
            else:
                subprocess.Popen([str(executable), *arguments], creationflags=subprocess.CREATE_NO_WINDOW)
        except OSError as error:
            messagebox.showerror("Spiderpot başlatılamadı", str(error), parent=self.root)
            return
        self.root.destroy()

    def show_finish(self, executable):
        for child in self.root.winfo_children():
            child.destroy()
        px = lambda value: round(value * self.ui_scale)
        width, height, x, y = wizard_geometry(self.root, self.ui_scale, (620, 345))
        self.root.state("normal")
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.title("Spiderpot · Kurulum tamamlandı")
        run_when_finished = tk.BooleanVar(value=True)
        def finish():
            if run_when_finished.get():
                self.start_runtime(executable)
            else:
                self.root.destroy()
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        header = tk.Frame(self.root, bg="white", padx=px(24), pady=px(20))
        header.pack(fill="x")
        tk.Label(header, image=self.brand_logo, bg="white").pack(side="right")
        tk.Label(header, text="Kurulum tamamlandı", bg="white", fg="#202020",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Separator(self.root).pack(fill="x")
        body = ttk.Frame(self.root, style="Setup.TFrame", padding=(px(24), px(24)))
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Kısayolları deneyerek öğrenin", style="Setup.TLabel",
                  font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(body, text="Kullanımı gör ile üç ekran modunu, isteğe bağlı kamera denemesini ve "
                  "Fotoğraflar ekranını adım adım deneyebilirsiniz.",
                  style="Setup.TLabel", wraplength=px(555), justify="left").pack(anchor="w", pady=(px(10), 0))
        ttk.Label(body, text="Bitir ile Spiderpot sistem tepsisinde bekler. Tanıtımı oradan da açabilirsiniz.",
                  style="Muted.Setup.TLabel", wraplength=px(555), justify="left").pack(anchor="w", pady=(px(13), 0))
        ttk.Checkbutton(body, text="Bitir'e basınca Spiderpot'u çalıştır", variable=run_when_finished,
                        style="Setup.TCheckbutton").pack(anchor="w", pady=(px(8), 0))
        footer = ttk.Frame(self.root, style="Setup.TFrame", padding=(px(24), px(14)))
        footer.pack(fill="x", side="bottom")
        ttk.Separator(self.root).pack(fill="x", side="bottom")
        ttk.Button(footer, text="Bitir", command=finish,
                   style="Setup.TButton").pack(side="right")
        ttk.Button(footer, text="Çıkmadan önce dene", command=lambda: self.start_runtime(executable, '--check'),
                   style="Setup.TButton").pack(side="right", padx=(0, px(10)))
        ttk.Button(footer, text="Kullanımı gör", command=lambda: self.start_runtime(executable, '--tutorial'),
                   style="Setup.TButton").pack(side="right", padx=(0, px(10)))

if __name__ == "__main__":
    root = tk.Tk()
    app = SpiderpotBuilderApp(root)
    root.mainloop()
