import json
import os
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_NAME = "Spiderpot"
APP_VERSION = "2026.07.30"
PUBLISHER = "Spiderpot"
SUPPORTED_IMAGES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
DETACHED_PROCESS = getattr(subprocess, "DETACHED_PROCESS", 0)
CREATE_NEW_PROCESS_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def resource_path(*parts):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, *parts)


def get_desktop_path():
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        ) as key:
            return winreg.QueryValueEx(key, "Desktop")[0]
    except Exception:
        return os.path.join(os.path.expanduser("~"), "Desktop")


def get_install_dir():
    local_app_data = os.environ.get(
        "LOCALAPPDATA",
        os.path.join(os.path.expanduser("~"), "AppData", "Local"),
    )
    return os.path.abspath(os.path.join(local_app_data, "Programs", APP_NAME))


def powershell_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


class SpiderpotInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} Kurulum")
        self.root.geometry("780x590")
        self.root.resizable(False, False)
        self.install_dir = get_install_dir()
        self.payload_exe = resource_path("Payload", "Spiderpot_Sistem.exe")
        self.default_wallpaper = resource_path("Assets", "spider_noir.jpg")
        self.selected_wallpapers = [self.default_wallpaper]
        self._build_ui()

    def _build_ui(self):
        try:
            style = ttk.Style()
            style.theme_use("vista")
        except Exception:
            style = ttk.Style()

        container = tk.Frame(self.root, bg="#101114")
        container.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(container, bg="black", width=265)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        try:
            from PIL import Image, ImageTk

            image = Image.open(self.default_wallpaper).convert("RGB")
            target_w, target_h = 265, 590
            image_ratio = image.width / image.height
            target_ratio = target_w / target_h
            if image_ratio > target_ratio:
                new_w = int(image.height * target_ratio)
                offset = (image.width - new_w) // 2
                image = image.crop((offset, 0, offset + new_w, image.height))
            else:
                new_h = int(image.width / target_ratio)
                offset = (image.height - new_h) // 2
                image = image.crop((0, offset, image.width, offset + new_h))
            image = image.resize((target_w, target_h), Image.Resampling.LANCZOS)
            self.hero_image = ImageTk.PhotoImage(image)
            tk.Label(left, image=self.hero_image, bg="black").pack(fill=tk.BOTH, expand=True)
        except Exception:
            tk.Label(
                left,
                text="SPIDERPOT",
                fg="#ff3030",
                bg="black",
                font=("Segoe UI", 24, "bold"),
            ).pack(expand=True)

        right = tk.Frame(container, bg="white")
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(
            right,
            text="Spiderpot Kurulum Sihirbazı",
            font=("Segoe UI", 18, "bold"),
            bg="white",
            fg="#bd1111",
        ).pack(pady=(18, 2))
        tk.Label(
            right,
            text=f"Sürüm {APP_VERSION} • Python gerekmez • Kullanıcı başına kurulum",
            font=("Segoe UI", 9),
            bg="white",
            fg="#666666",
        ).pack(pady=(0, 12))

        settings = tk.Frame(right, bg="white")
        settings.pack(fill=tk.X, padx=24)

        wallpaper_row = tk.Frame(settings, bg="white")
        wallpaper_row.pack(fill=tk.X, pady=5)
        tk.Label(
            wallpaper_row,
            text="Ctrl+1 görselleri",
            font=("Segoe UI", 10, "bold"),
            bg="white",
        ).pack(side=tk.LEFT)
        self.wallpaper_label = tk.Label(
            wallpaper_row,
            text="1 görsel seçildi",
            font=("Segoe UI", 9),
            bg="white",
            fg="#0b63ce",
        )
        self.wallpaper_label.pack(side=tk.LEFT, padx=12)
        ttk.Button(
            wallpaper_row,
            text="Görselleri Seç",
            command=self.select_wallpapers,
        ).pack(side=tk.RIGHT)

        interval_row = tk.Frame(settings, bg="white")
        interval_row.pack(fill=tk.X, pady=5)
        tk.Label(
            interval_row,
            text="Fotoğraf geçiş süresi (saniye)",
            font=("Segoe UI", 10),
            bg="white",
        ).pack(side=tk.LEFT)
        self.interval_entry = ttk.Entry(interval_row, width=8)
        self.interval_entry.insert(0, "5")
        self.interval_entry.pack(side=tk.RIGHT)

        ttk.Separator(settings).pack(fill=tk.X, pady=12)
        tk.Label(
            settings,
            text="Kısayollar (Ctrl ile çalışır)",
            font=("Segoe UI", 11, "bold"),
            bg="white",
        ).pack(anchor="w", pady=(0, 6))

        self.key_spider = self._key_row(settings, "Duvar kâğıdı modu", "1")
        self.key_black = self._key_row(settings, "Siyah ekran modu", "2")
        self.key_lock = self._key_row(settings, "Görünmez tuzak modu", "3")

        exit_row = tk.Frame(settings, bg="white")
        exit_row.pack(fill=tk.X, pady=4)
        tk.Label(exit_row, text="Tuzağı kapatma tuşu", font=("Segoe UI", 10), bg="white").pack(
            side=tk.LEFT
        )
        self.key_exit = ttk.Combobox(
            exit_row,
            values=[
                "f1",
                "f2",
                "f3",
                "f4",
                "f5",
                "f6",
                "f7",
                "f8",
                "f9",
                "f10",
                "f11",
                "f12",
                "esc",
                "end",
            ],
            state="readonly",
            width=7,
        )
        self.key_exit.set("f12")
        self.key_exit.pack(side=tk.RIGHT)

        ttk.Separator(settings).pack(fill=tk.X, pady=12)

        self.auto_start = tk.BooleanVar(value=True)
        self.desktop_shortcut = tk.BooleanVar(value=True)
        self.launch_after_install = tk.BooleanVar(value=True)
        for text, variable in [
            ("Windows açılışında otomatik başlat", self.auto_start),
            ("Masaüstü kısayolu oluştur", self.desktop_shortcut),
            ("Kurulum bitince Spiderpot'u çalıştır", self.launch_after_install),
        ]:
            tk.Checkbutton(
                settings,
                text=text,
                variable=variable,
                bg="white",
                font=("Segoe UI", 10),
                activebackground="white",
            ).pack(anchor="w", pady=2)

        self.status = tk.Label(right, text="", bg="white", fg="#0b63ce", font=("Segoe UI", 9))
        self.status.pack(pady=(12, 4))

        buttons = tk.Frame(right, bg="white")
        buttons.pack(pady=8)
        self.install_button = ttk.Button(
            buttons,
            text="Spiderpot'u Kur / Güncelle",
            command=self.start_install,
        )
        self.install_button.pack(side=tk.LEFT, padx=5)
        self.uninstall_button = ttk.Button(
            buttons,
            text="Kaldır",
            command=self.confirm_uninstall,
        )
        self.uninstall_button.pack(side=tk.LEFT, padx=5)

        tk.Label(
            right,
            text=f"Kurulum konumu: {self.install_dir}",
            bg="white",
            fg="#777777",
            font=("Segoe UI", 8),
            wraplength=460,
        ).pack(pady=(4, 0))

    def _key_row(self, parent, label, default):
        row = tk.Frame(parent, bg="white")
        row.pack(fill=tk.X, pady=4)
        tk.Label(row, text=label, font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT)
        entry = ttk.Entry(row, width=8)
        entry.insert(0, default)
        entry.pack(side=tk.RIGHT)
        return entry

    def select_wallpapers(self):
        selected = filedialog.askopenfilenames(
            title="Ctrl+1 için görselleri seçin",
            filetypes=[
                ("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )
        if selected:
            self.selected_wallpapers = list(selected)
            self.wallpaper_label.config(text=f"{len(selected)} görsel seçildi")

    def _validated_settings(self):
        missing = [path for path in self.selected_wallpapers if not os.path.isfile(path)]
        if missing:
            raise ValueError(f"Seçilen görsel bulunamadı:\n{missing[0]}")

        try:
            interval = float(self.interval_entry.get().strip().replace(",", "."))
        except ValueError as error:
            raise ValueError("Fotoğraf geçiş süresi sayı olmalı.") from error
        if interval <= 0:
            raise ValueError("Fotoğraf geçiş süresi 0'dan büyük olmalı.")

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
            "version": APP_VERSION,
        }

    def start_install(self):
        try:
            config = self._validated_settings()
        except ValueError as error:
            messagebox.showerror("Kurulum Hatası", str(error))
            return

        if not os.path.isfile(self.payload_exe):
            messagebox.showerror(
                "Kurulum Hatası",
                "Kurulum paketinin içindeki Spiderpot uygulaması bulunamadı.",
            )
            return

        self._set_busy(True, "Spiderpot kuruluyor...")
        threading.Thread(
            target=self._install,
            args=(config,),
            daemon=True,
            name="SpiderpotInstaller",
        ).start()

    def _set_busy(self, busy, text=""):
        state = tk.DISABLED if busy else tk.NORMAL
        self.install_button.config(state=state)
        self.uninstall_button.config(state=state)
        self.status.config(text=text, fg="#0b63ce")

    def _stop_existing(self):
        for executable in ("Spiderpot.exe", "Spiderpot_Sistem.exe", "BearPot.exe"):
            subprocess.run(
                ["taskkill", "/F", "/IM", executable],
                capture_output=True,
                creationflags=CREATE_NO_WINDOW,
            )

    def _remove_legacy_launchers(self):
        desktop = get_desktop_path()
        for executable in ("Spiderpot.exe", "Spiderpot_Sistem.exe", "BearPot.exe"):
            legacy_path = os.path.abspath(os.path.join(desktop, executable))
            installed_path = os.path.abspath(os.path.join(self.install_dir, "Spiderpot_Sistem.exe"))
            if (
                os.path.normcase(legacy_path) != os.path.normcase(installed_path)
                and os.path.isfile(legacy_path)
            ):
                try:
                    os.remove(legacy_path)
                except OSError:
                    pass

        startup_shortcut = os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            "Startup",
            "Spiderpot.lnk",
        )
        try:
            if os.path.isfile(startup_shortcut):
                os.remove(startup_shortcut)
        except OSError:
            pass

    def _install(self, config):
        try:
            import winreg

            self._stop_existing()
            self._remove_legacy_launchers()
            os.makedirs(self.install_dir, exist_ok=True)

            installed_exe = os.path.join(self.install_dir, "Spiderpot_Sistem.exe")
            shutil.copy2(self.payload_exe, installed_exe)

            wallpaper_dir = os.path.join(self.install_dir, "Wallpapers")
            if os.path.isdir(wallpaper_dir):
                shutil.rmtree(wallpaper_dir)
            os.makedirs(wallpaper_dir, exist_ok=True)
            for index, source in enumerate(self.selected_wallpapers, start=1):
                extension = os.path.splitext(source)[1].lower()
                if extension not in SUPPORTED_IMAGES:
                    continue
                destination = os.path.join(wallpaper_dir, f"{index:04d}{extension}")
                shutil.copy2(source, destination)

            config_path = os.path.join(self.install_dir, "config.json")
            with open(config_path, "w", encoding="utf-8") as config_file:
                json.dump(config, config_file, ensure_ascii=False, indent=2)

            installed_setup = os.path.join(self.install_dir, "Spiderpot_Setup.exe")
            if getattr(sys, "frozen", False):
                if os.path.normcase(os.path.abspath(sys.executable)) != os.path.normcase(
                    os.path.abspath(installed_setup)
                ):
                    shutil.copy2(sys.executable, installed_setup)

            self._configure_startup(installed_exe)
            self._create_shortcuts(installed_exe)
            self._register_uninstaller(installed_exe, installed_setup)

            if self.launch_after_install.get():
                subprocess.Popen(
                    [installed_exe],
                    cwd=self.install_dir,
                    close_fds=True,
                    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
                )

            self.root.after(0, self._install_finished, True, installed_exe)
        except Exception as error:
            self.root.after(0, self._install_finished, False, f"{type(error).__name__}: {error}")

    def _configure_startup(self, installed_exe):
        import winreg

        run_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            run_path,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if self.auto_start.get():
                winreg.SetValueEx(
                    key,
                    "Spiderpot_App",
                    0,
                    winreg.REG_SZ,
                    f'"{installed_exe}"',
                )
            else:
                try:
                    winreg.DeleteValue(key, "Spiderpot_App")
                except FileNotFoundError:
                    pass

    def _shortcut_paths(self):
        appdata = os.environ.get("APPDATA", "")
        start_menu_dir = os.path.join(
            appdata,
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            APP_NAME,
        )
        return (
            os.path.join(get_desktop_path(), f"{APP_NAME}.lnk"),
            os.path.join(start_menu_dir, f"{APP_NAME}.lnk"),
        )

    def _create_shortcut(self, shortcut_path, target_path):
        os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)
        script = (
            "$w=New-Object -ComObject WScript.Shell;"
            f"$s=$w.CreateShortcut({powershell_quote(shortcut_path)});"
            f"$s.TargetPath={powershell_quote(target_path)};"
            f"$s.WorkingDirectory={powershell_quote(self.install_dir)};"
            f"$s.IconLocation={powershell_quote(target_path + ',0')};"
            "$s.Save()"
        )
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True,
            text=True,
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Kısayol oluşturulamadı.")

    def _create_shortcuts(self, installed_exe):
        desktop_link, start_menu_link = self._shortcut_paths()
        if self.desktop_shortcut.get():
            self._create_shortcut(desktop_link, installed_exe)
        elif os.path.exists(desktop_link):
            os.remove(desktop_link)
        self._create_shortcut(start_menu_link, installed_exe)

    def _register_uninstaller(self, installed_exe, installed_setup):
        import winreg

        uninstall_path = rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, uninstall_path) as key:
            values = {
                "DisplayName": APP_NAME,
                "DisplayVersion": APP_VERSION,
                "Publisher": PUBLISHER,
                "InstallLocation": self.install_dir,
                "DisplayIcon": installed_exe,
                "UninstallString": f'"{installed_setup}" --uninstall',
            }
            for name, value in values.items():
                winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
            winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
            try:
                estimated_size = sum(
                    os.path.getsize(os.path.join(root, file_name))
                    for root, _, files in os.walk(self.install_dir)
                    for file_name in files
                ) // 1024
                winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, estimated_size)
            except Exception:
                pass

    def _install_finished(self, success, detail):
        self._set_busy(False)
        if success:
            self.status.config(text="Kurulum başarıyla tamamlandı.", fg="#198038")
            messagebox.showinfo(
                "Spiderpot Kuruldu",
                "Spiderpot başarıyla kuruldu veya güncellendi.\n\n"
                f"Konum:\n{detail}\n\n"
                "Bu Setup EXE başka bir Windows bilgisayara tek başına gönderilebilir.",
            )
        else:
            self.status.config(text="Kurulum başarısız.", fg="#c1121f")
            messagebox.showerror("Kurulum Hatası", detail)

    def confirm_uninstall(self):
        if not os.path.isdir(self.install_dir):
            messagebox.showinfo("Spiderpot", "Bu kullanıcı için kurulu Spiderpot bulunamadı.")
            return
        if not messagebox.askyesno(
            "Spiderpot'u Kaldır",
            "Spiderpot uygulaması, kısayolları ve ayarları kaldırılsın mı?\n\n"
            "Yakalanan fotoğraflar silinmeyecek.",
        ):
            return
        self._set_busy(True, "Spiderpot kaldırılıyor...")
        threading.Thread(target=self._uninstall, daemon=True, name="SpiderpotUninstaller").start()

    def _uninstall(self):
        try:
            import winreg

            self._stop_existing()

            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                ) as key:
                    try:
                        winreg.DeleteValue(key, "Spiderpot_App")
                    except FileNotFoundError:
                        pass
            except FileNotFoundError:
                pass

            try:
                winreg.DeleteKey(
                    winreg.HKEY_CURRENT_USER,
                    rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\{APP_NAME}",
                )
            except FileNotFoundError:
                pass

            for shortcut in self._shortcut_paths():
                try:
                    if os.path.exists(shortcut):
                        os.remove(shortcut)
                    parent = os.path.dirname(shortcut)
                    if os.path.basename(parent) == APP_NAME and os.path.isdir(parent):
                        os.rmdir(parent)
                except Exception:
                    pass

            running_from_install_dir = (
                getattr(sys, "frozen", False)
                and os.path.commonpath(
                    [os.path.abspath(sys.executable), self.install_dir]
                )
                == self.install_dir
            )
            if running_from_install_dir:
                command = (
                    "Start-Sleep -Seconds 2;"
                    f"Remove-Item -LiteralPath {powershell_quote(self.install_dir)} "
                    "-Recurse -Force -ErrorAction SilentlyContinue"
                )
                subprocess.Popen(
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                    close_fds=True,
                    creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                )
            elif os.path.isdir(self.install_dir):
                shutil.rmtree(self.install_dir)

            self.root.after(0, self._uninstall_finished, True, "")
        except Exception as error:
            self.root.after(0, self._uninstall_finished, False, f"{type(error).__name__}: {error}")

    def _uninstall_finished(self, success, detail):
        self._set_busy(False)
        if success:
            messagebox.showinfo(
                "Spiderpot Kaldırıldı",
                "Spiderpot kaldırıldı. Yakalanan fotoğraflar korunmuştur.",
            )
            self.root.destroy()
        else:
            self.status.config(text="Kaldırma başarısız.", fg="#c1121f")
            messagebox.showerror("Kaldırma Hatası", detail)


def main():
    root = tk.Tk()
    app = SpiderpotInstaller(root)
    if "--uninstall" in sys.argv:
        root.after(200, app.confirm_uninstall)
    root.mainloop()


if __name__ == "__main__":
    main()
