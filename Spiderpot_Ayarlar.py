import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_VERSION = "1.0.0"
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def resource_path(*parts):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *parts)


def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def get_user_data_dir():
    local_app_data = os.environ.get(
        "LOCALAPPDATA",
        os.path.join(os.path.expanduser("~"), "AppData", "Local"),
    )
    return os.path.abspath(os.path.join(local_app_data, "Spiderpot"))


def load_config():
    for path in (
        os.path.join(get_user_data_dir(), "config.json"),
        os.path.join(get_app_dir(), "config.json"),
    ):
        try:
            with open(path, "r", encoding="utf-8") as config_file:
                data = json.load(config_file)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


class SpiderpotSettings:
    def __init__(self, root):
        self.root = root
        self.root.title("Spiderpot Ayarlar ve Gizlilik")
        self.root.geometry("760x680")
        self.root.resizable(False, False)
        self.config = load_config()
        self.default_wallpaper = resource_path("Assets", "spider_noir.jpg")
        self.selected_wallpapers = self._existing_wallpapers() or [self.default_wallpaper]
        self._build_ui()

    def _existing_wallpapers(self):
        wallpaper_dir = os.path.join(get_user_data_dir(), "Wallpapers")
        try:
            return [
                os.path.join(wallpaper_dir, name)
                for name in sorted(os.listdir(wallpaper_dir), key=str.casefold)
                if (
                    os.path.isfile(os.path.join(wallpaper_dir, name))
                    and os.path.splitext(name)[1].lower() in SUPPORTED_IMAGES
                )
            ]
        except Exception:
            return []

    def _build_ui(self):
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass

        outer = tk.Frame(self.root, bg="#f4f5f7")
        outer.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(outer, bg="#12141a", height=105)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(
            header,
            text="SPIDERPOT",
            fg="#ff3434",
            bg="#12141a",
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w", padx=28, pady=(17, 0))
        tk.Label(
            header,
            text=f"Ayarlar ve Gizlilik  •  Sürüm {APP_VERSION}",
            fg="#d7d9df",
            bg="#12141a",
            font=("Segoe UI", 10),
        ).pack(anchor="w", padx=30)

        body = tk.Frame(outer, bg="#f4f5f7")
        body.pack(fill=tk.BOTH, expand=True, padx=28, pady=18)

        privacy = tk.LabelFrame(
            body,
            text=" Kamera ve yerel fotoğraf kaydı ",
            bg="white",
            fg="#991b1b",
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=12,
        )
        privacy.pack(fill=tk.X)
        tk.Label(
            privacy,
            text=(
                "Spiderpot, yalnızca bir tuzak modu siz tarafından etkinleştirildikten sonra "
                "fare veya klavye etkileşimi algılarsa kameradan tek kare alır. Fotoğraf "
                "Masaüstü\\Spiderpot_Yakalananlar klasöründe yerel olarak saklanır; "
                "internete gönderilmez ve üçüncü taraflarla paylaşılmaz."
            ),
            bg="white",
            fg="#222222",
            justify=tk.LEFT,
            wraplength=650,
            font=("Segoe UI", 9),
        ).pack(anchor="w")

        self.camera_consent = tk.BooleanVar(
            value=bool(self.config.get("camera_consent", False))
        )
        tk.Checkbutton(
            privacy,
            text="Bu kullanım biçimini anladım ve kamera özelliğini etkinleştiriyorum.",
            variable=self.camera_consent,
            bg="white",
            activebackground="white",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(10, 0))
        tk.Label(
            privacy,
            text="Onay vermezseniz ekran modları çalışır; fotoğraf çekilmez.",
            bg="white",
            fg="#666666",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=(22, 0))

        settings = tk.LabelFrame(
            body,
            text=" Tuzak ayarları ",
            bg="white",
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=12,
        )
        settings.pack(fill=tk.X, pady=(14, 0))

        image_row = tk.Frame(settings, bg="white")
        image_row.pack(fill=tk.X, pady=4)
        tk.Label(image_row, text="Ctrl+1 görselleri", bg="white", font=("Segoe UI", 9)).pack(
            side=tk.LEFT
        )
        self.image_count_label = tk.Label(
            image_row,
            text=f"{len(self.selected_wallpapers)} görsel",
            bg="white",
            fg="#0b63ce",
            font=("Segoe UI", 9),
        )
        self.image_count_label.pack(side=tk.LEFT, padx=12)
        ttk.Button(image_row, text="Görselleri Seç", command=self.select_wallpapers).pack(
            side=tk.RIGHT
        )

        self.interval_entry = self._entry_row(
            settings,
            "Fotoğraf geçiş süresi (sn)",
            str(self.config.get("slideshow_seconds", 5)),
        )
        self.key_spider = self._entry_row(
            settings,
            "Duvar kâğıdı modu (Ctrl +)",
            str(self.config.get("key_spider", "1")),
        )
        self.key_black = self._entry_row(
            settings,
            "Siyah ekran modu (Ctrl +)",
            str(self.config.get("key_black", "2")),
        )
        self.key_lock = self._entry_row(
            settings,
            "Görünmez tuzak modu (Ctrl +)",
            str(self.config.get("key_lock", "3")),
        )

        exit_row = tk.Frame(settings, bg="white")
        exit_row.pack(fill=tk.X, pady=4)
        tk.Label(exit_row, text="Tuzağı kapatma tuşu", bg="white", font=("Segoe UI", 9)).pack(
            side=tk.LEFT
        )
        self.key_exit = ttk.Combobox(
            exit_row,
            values=[f"f{index}" for index in range(1, 13)] + ["esc", "end"],
            state="readonly",
            width=10,
        )
        self.key_exit.set(str(self.config.get("key_exit", "f12")))
        self.key_exit.pack(side=tk.RIGHT)

        tk.Label(
            settings,
            text=(
                "Otomatik başlangıç Windows tarafından yönetilir; "
                "Görev Yöneticisi > Başlangıç uygulamaları bölümünden kapatılabilir."
            ),
            bg="white",
            fg="#666666",
            justify=tk.LEFT,
            wraplength=630,
            font=("Segoe UI", 8),
        ).pack(anchor="w", pady=(8, 0))

        self.status = tk.Label(body, text="", bg="#f4f5f7", fg="#0b63ce", font=("Segoe UI", 9))
        self.status.pack(pady=(14, 5))
        buttons = tk.Frame(body, bg="#f4f5f7")
        buttons.pack()
        ttk.Button(
            buttons,
            text="Ayarları Kaydet ve Spiderpot'u Başlat",
            command=self.save_and_start,
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons, text="Kapat", command=self.root.destroy).pack(side=tk.LEFT, padx=5)

    def _entry_row(self, parent, label, default):
        row = tk.Frame(parent, bg="white")
        row.pack(fill=tk.X, pady=4)
        tk.Label(row, text=label, bg="white", font=("Segoe UI", 9)).pack(side=tk.LEFT)
        entry = ttk.Entry(row, width=12)
        entry.insert(0, default)
        entry.pack(side=tk.RIGHT)
        return entry

    def select_wallpapers(self):
        paths = filedialog.askopenfilenames(
            title="Ctrl+1 için görselleri seçin",
            filetypes=[
                ("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )
        if paths:
            self.selected_wallpapers = list(paths)
            self.image_count_label.config(text=f"{len(paths)} görsel")

    def _validated_config(self):
        try:
            interval = float(self.interval_entry.get().strip().replace(",", "."))
        except ValueError as error:
            raise ValueError("Geçiş süresi sayı olmalı.") from error
        if interval <= 0:
            raise ValueError("Geçiş süresi 0'dan büyük olmalı.")

        keys = {
            "key_spider": self.key_spider.get().strip().lower(),
            "key_black": self.key_black.get().strip().lower(),
            "key_lock": self.key_lock.get().strip().lower(),
            "key_exit": self.key_exit.get().strip().lower(),
        }
        if any(not value for value in keys.values()):
            raise ValueError("Kısayol alanları boş bırakılamaz.")
        if len({keys["key_spider"], keys["key_black"], keys["key_lock"]}) != 3:
            raise ValueError("Üç tuzak modu farklı tuşlar kullanmalı.")

        return {
            **keys,
            "slideshow_seconds": interval,
            "camera_consent": bool(self.camera_consent.get()),
            "version": APP_VERSION,
        }

    def save_and_start(self):
        try:
            config = self._validated_config()
            user_data_dir = get_user_data_dir()
            os.makedirs(user_data_dir, exist_ok=True)

            wallpaper_dir = os.path.join(user_data_dir, "Wallpapers")
            staged_dir = os.path.join(user_data_dir, "Wallpapers.new")
            if os.path.isdir(staged_dir):
                shutil.rmtree(staged_dir)
            os.makedirs(staged_dir, exist_ok=True)
            for index, source in enumerate(self.selected_wallpapers, start=1):
                extension = os.path.splitext(source)[1].lower()
                if extension not in SUPPORTED_IMAGES or not os.path.isfile(source):
                    continue
                shutil.copy2(source, os.path.join(staged_dir, f"{index:04d}{extension}"))
            if not os.listdir(staged_dir):
                raise ValueError("En az bir geçerli görsel seçmelisiniz.")
            if os.path.isdir(wallpaper_dir):
                shutil.rmtree(wallpaper_dir)
            os.replace(staged_dir, wallpaper_dir)

            config_path = os.path.join(user_data_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file, ensure_ascii=False, indent=2)

            self._restart_system()
            self.status.config(text="Ayarlar kaydedildi. Spiderpot çalışıyor.", fg="#198038")
            messagebox.showinfo(
                "Spiderpot",
                "Ayarlar kaydedildi.\n\n"
                + (
                    "Kamera özelliği açık."
                    if config["camera_consent"]
                    else "Kamera özelliği kapalı; fotoğraf çekilmeyecek."
                ),
            )
        except Exception as error:
            self.status.config(text="Ayarlar kaydedilemedi.", fg="#c1121f")
            messagebox.showerror("Spiderpot Ayarları", str(error))

    def _restart_system(self):
        subprocess.run(
            ["taskkill", "/F", "/IM", "Spiderpot_Sistem.exe"],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
        )
        system_exe = os.path.join(get_app_dir(), "Spiderpot_Sistem.exe")
        if not os.path.isfile(system_exe):
            raise FileNotFoundError(f"Spiderpot sistem uygulaması bulunamadı:\n{system_exe}")
        subprocess.Popen(
            [system_exe],
            cwd=get_app_dir(),
            close_fds=True,
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
        )


def main():
    root = tk.Tk()
    SpiderpotSettings(root)
    root.mainloop()


if __name__ == "__main__":
    main()
