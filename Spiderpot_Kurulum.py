import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess
import threading
import sys
import shutil
from spiderpot_support import (CAMERA_NOTICE, load_config, save_config, resource,
                               set_startup, launch, show_privacy, circular_icon)

class SpiderpotBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spiderpot Kurulum Sihirbazı")
        self.build_dir = str(resource(''))
        self.core_script = os.path.join(self.build_dir, "Assets", "Spiderpot_Core.py")
        self.config = load_config()
        selected = self.config['wallpaper']
        self.selected_wallpaper = selected if selected and os.path.isfile(selected) else str(resource('Assets/spiderpot-wallpaper.jpg'))

        # Use Windows' native themed controls and scale pixel dimensions with text.
        self.ui_scale = max(1.0, float(root.tk.call("tk", "scaling")) / (96 / 72))
        px = lambda value: round(value * self.ui_scale)
        self.root.geometry(f"{px(900)}x{px(735)}")
        self.root.resizable(False, False)
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

        header = tk.Frame(root, bg="white", padx=px(24), pady=px(17))
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
        self.btn_cancel = ttk.Button(footer, text="İptal", command=root.destroy, style="Setup.TButton", width=11)
        self.btn_cancel.pack(side="right")
        self.btn_build = ttk.Button(footer, text="Kaydet ve Başlat", command=self.start_build,
                                    style="Setup.TButton", width=19, default="active")
        self.btn_build.pack(side="right", padx=(0, px(9)))
        ttk.Button(footer, text="Gizlilik", command=lambda: show_privacy(root), style="Setup.TButton").pack(side="left")
        ttk.Button(footer, text="Fotoğraflar", command=lambda: launch('--captures'), style="Setup.TButton").pack(side="left", padx=px(7))
        ttk.Separator(root).pack(side="bottom", fill="x")

        main = ttk.Frame(root, style="Setup.TFrame")
        main.pack(fill="both", expand=True)
        left = tk.Frame(main, bg="#10151d", width=px(210))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        image_area = tk.Frame(left, bg="#10151d", height=px(280))
        image_area.pack(fill="x")
        image_area.pack_propagate(False)
        self.wallpaper_preview = tk.Label(image_area, bg="#10151d", bd=0)
        self.wallpaper_preview.pack(fill="both", expand=True)
        self.update_wallpaper_preview()
        tk.Label(left, text="SPIDERPOT", bg="#10151d", fg="white",
                 font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=px(20), pady=(px(20), px(8)))
        tk.Label(left, text="Sizin fotoğrafınız.\nSizin kısayollarınız.", bg="#10151d", fg="#c3cbd5",
                 justify="left", font=("Segoe UI", 10)).pack(anchor="w", padx=px(20))
        tk.Label(left, text="1  Ayarları seçin\n2  Kurulumu başlatın\n3  Kısayollarla kullanın", bg="#10151d", fg="#9daabd",
                 justify="left", font=("Segoe UI", 9)).pack(anchor="w", padx=px(20), pady=px(22))

        right = ttk.Frame(main, style="Setup.TFrame", padding=(px(26), px(19)))
        right.pack(side="left", fill="both", expand=True)
        wallpaper = ttk.LabelFrame(right, text="Tuzak fotoğrafı", style="Setup.TLabelframe", padding=px(12))
        wallpaper.pack(fill="x", pady=(0, px(14)))
        ttk.Button(wallpaper, text="Gözat…", command=self.browse_wallpaper, style="Setup.TButton", width=10).pack(side="right")
        self.lbl_wp = ttk.Label(wallpaper, text=os.path.basename(self.selected_wallpaper), style="Setup.TLabel", anchor="w")
        self.lbl_wp.pack(side="left", fill="x", expand=True, padx=(0, px(10)))

        shortcuts = ttk.LabelFrame(right, text="Kısayol ayarları", style="Setup.TLabelframe", padding=px(12))
        shortcuts.pack(fill="x", pady=(0, px(14)))
        shortcuts.columnconfigure(0, weight=1)
        for row, (title, attr, value) in enumerate((
                ("Tuzak 1 · Seçilen fotoğraf", "k1_entry", "1"),
                ("Tuzak 2 · Siyah ekran", "k2_entry", "2"),
                ("Tuzak 3 · Mevcut ekran", "k3_entry", "3"))):
            ttk.Label(shortcuts, text=title, style="Setup.TLabel").grid(row=row, column=0, sticky="w", pady=px(5))
            ttk.Label(shortcuts, text="Ctrl +", style="Muted.Setup.TLabel").grid(row=row, column=1, padx=(px(16), px(7)))
            entry = ttk.Entry(shortcuts, width=7, justify="center")
            entry.insert(0, self.config[{'k1_entry':'key_spider','k2_entry':'key_black','k3_entry':'key_lock'}[attr]])
            entry.grid(row=row, column=2, sticky="e", pady=px(5))
            setattr(self, attr, entry)
        ttk.Separator(shortcuts).grid(row=3, column=0, columnspan=3, sticky="ew", pady=px(7))
        ttk.Label(shortcuts, text="Tuzağı kapatma tuşu", style="Setup.TLabel").grid(row=4, column=0, sticky="w", pady=px(5))
        self.ke_combo = ttk.Combobox(shortcuts, values=["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "esc", "end"], state="readonly", width=5, justify="center")
        self.ke_combo.set(self.config['key_exit'])
        self.ke_combo.grid(row=4, column=2, sticky="e")

        options = ttk.LabelFrame(right, text="Kurulum seçenekleri", style="Setup.TLabelframe", padding=px(12))
        options.pack(fill="x")
        self.auto_start_var = tk.BooleanVar(value=self.config['auto_start'])
        ttk.Checkbutton(options, text="Windows açıldığında otomatik başlat", variable=self.auto_start_var,
                        style="Setup.TCheckbutton").pack(anchor="w", pady=(0, px(8)))
        self.camera_var = tk.BooleanVar(value=self.config['camera_enabled'])
        ttk.Checkbutton(options, text="Etkinlikte kameradan fotoğraf çek", variable=self.camera_var,
                        command=self.confirm_camera, style="Setup.TCheckbutton").pack(anchor="w", pady=(0, px(8)))
        retention_row = ttk.Frame(options, style='Setup.TFrame')
        retention_row.pack(fill='x')
        ttk.Label(retention_row, text="Fotoğrafları sakla (gün):", style='Setup.TLabel').pack(side='left')
        self.retention_var = tk.IntVar(value=self.config['retention_days'])
        ttk.Spinbox(retention_row, from_=1, to=30, textvariable=self.retention_var, width=5).pack(side='right')
        ttk.Label(options, text="Kamera varsayılan kapalıdır. Fotoğraflar yerel ve şifrelidir.", style='Muted.Setup.TLabel').pack(anchor='w', pady=(px(8), 0))

        self.status_label = tk.Label(right, text="Hazır. Tüm bileşenler uygulamaya dahildir; indirme yapılmaz.", bg="#f3f3f3", fg="#626262",
                                     font=("Segoe UI", 9), anchor="w", justify="left", wraplength=px(570))
        self.status_label.pack(fill="x", pady=(px(13), px(6)))

    def update_wallpaper_preview(self):
        from PIL import Image, ImageOps, ImageTk
        try:
            with Image.open(resource('Assets/spider_noir.jpg')) as source:
                image = ImageOps.fit(ImageOps.exif_transpose(source).convert("RGB"),
                                     (round(210 * self.ui_scale), round(280 * self.ui_scale)),
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

    def browse_wallpaper(self):
        filepath = filedialog.askopenfilename(title="Wallpaper Seç", filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp")])
        if filepath:
            self.selected_wallpaper = filepath
            filename = os.path.basename(filepath)
            # Kısalt
            if len(filename) > 38: filename = filename[:35] + "..."
            self.lbl_wp.config(text=filename)
            self.update_wallpaper_preview()

    def confirm_camera(self):
        if self.camera_var.get():
            if not messagebox.askyesno("Spiderpot · Kamera kullanımı", CAMERA_NOTICE, parent=self.root, default="no"):
                self.camera_var.set(False)

    def start_build(self):
        try:
            config = dict(self.config)
            config.update(key_spider=self.k1_entry.get().strip().lower(),
                          key_black=self.k2_entry.get().strip().lower(),
                          key_lock=self.k3_entry.get().strip().lower(),
                          key_exit=self.ke_combo.get(),
                          camera_enabled=self.camera_var.get(),
                          auto_start=self.auto_start_var.get(),
                          retention_days=self.retention_var.get())
            from spiderpot_support import validate
            validate(config)
            if not os.path.isfile(self.selected_wallpaper):
                raise ValueError("Seçilen fotoğraf bulunamadı. Yeniden seçin.")
            startup_changed = config['auto_start'] != self.config['auto_start']
            self.config = save_config(config, self.selected_wallpaper)
            from spiderpot_support import package_family
            if getattr(sys,'frozen',False) and not package_family():
                from pathlib import Path
                from spiderpot_upgrade import install_bundle
                executable = install_bundle(Path(sys.executable).parent,config['auto_start'])
                subprocess.Popen([str(executable),'--run'],creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                if startup_changed:
                    set_startup(config['auto_start'])
                launch('--run')
            self.root.destroy()
        except Exception as error:
            self.status_label.config(text="Ayarlar uygulanamadı.", fg="#a4262c")
            messagebox.showerror("Spiderpot", str(error), parent=self.root)

if __name__ == "__main__":
    root = tk.Tk()
    app = SpiderpotBuilderApp(root)
    root.mainloop()
