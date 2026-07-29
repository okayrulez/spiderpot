import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess
import threading
import sys
import shutil
import tempfile

BUILDER_VERSION = "2026-07-28 19:43"

class SpiderpotBuilderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spiderpot Setup Wizard")
        from PIL import Image, ImageTk
        self.root.geometry("750x550")
        self.root.resizable(False, False)
        
        try:
            style = ttk.Style()
            style.theme_use('vista')
        except: pass

        desktop_path = self.get_desktop_path()
        self.build_dir = os.path.dirname(os.path.abspath(__file__))
        self.core_script = os.path.join(self.build_dir, "Assets", "Spiderpot_Core.py")
        self.selected_wallpapers = [
            os.path.join(self.build_dir, "Assets", "spider_noir.jpg")
        ]
        self.slideshow_dir = os.path.join(self.build_dir, "Assets", "Slayt_Gorselleri")

        main_frame = tk.Frame(root, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel for image
        left_frame = tk.Frame(main_frame, bg="black", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)

        # Load and crop image
        try:
            img_path = r"C:\Users\oktay.dedeoglu\Downloads\spider-noir-2026-5120x2880-24881.jpg"
            img = Image.open(img_path)
            target_width, target_height = 250, 550
            img_ratio = img.width / img.height
            target_ratio = target_width / target_height
            
            if img_ratio > target_ratio:
                new_w = int(img.height * target_ratio)
                offset = (img.width - new_w) // 2
                img = img.crop((offset, 0, offset + new_w, img.height))
            else:
                new_h = int(img.width / target_ratio)
                offset = (img.height - new_h) // 2
                img = img.crop((0, offset, img.width, offset + new_h))
                
            img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            self.wizard_photo = ImageTk.PhotoImage(img)
            tk.Label(left_frame, image=self.wizard_photo, bg="black").pack(fill=tk.BOTH, expand=True)
        except Exception:
            tk.Label(left_frame, text="Spiderpot", fg="red", bg="black", font=("Segoe UI", 24, "bold")).pack(expand=True)

        # Right panel for settings
        right_frame = tk.Frame(main_frame, bg="white")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        tk.Label(right_frame, text="Spiderpot Kurulum Sihirbazı", font=("Segoe UI", 16, "bold"), bg="white", fg="red").pack(pady=(12, 2))
        tk.Label(
            right_frame,
            text=f"Sürüm: {BUILDER_VERSION} - kamera ışığı yalnızca yakalamada yanar",
            font=("Segoe UI", 8),
            bg="white",
            fg="#666666",
        ).pack(pady=(0, 8))
        
        # --- Settings Frame ---
        settings_frame = tk.Frame(right_frame, bg="white")
        settings_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # 1. Wallpaper Selection
        wp_frame = tk.Frame(settings_frame, bg="white")
        wp_frame.pack(fill=tk.X, pady=5)
        tk.Label(wp_frame, text="Ctrl+1 Görselleri:", font=("Segoe UI", 10, "bold"), bg="white").pack(side=tk.LEFT)
        self.lbl_wp = tk.Label(wp_frame, text="1 görsel seçildi", font=("Segoe UI", 9), bg="white", fg="blue", width=22, anchor="e")
        self.lbl_wp.pack(side=tk.LEFT, padx=5)
        tk.Button(wp_frame, text="Çoklu Seç", command=self.browse_wallpaper, height=1, relief="groove").pack(side=tk.RIGHT)

        interval_frame = tk.Frame(settings_frame, bg="white")
        interval_frame.pack(fill=tk.X, pady=2)
        tk.Label(interval_frame, text="Ctrl+1 Foto Geçiş Aralığı (sn):", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT)
        self.slide_interval_entry = ttk.Entry(interval_frame, width=6)
        self.slide_interval_entry.insert(0, "5")
        self.slide_interval_entry.pack(side=tk.RIGHT)
        
        ttk.Separator(settings_frame, orient='horizontal').pack(fill='x', pady=10)

        # 2. Key Settings
        tk.Label(settings_frame, text="Kısayol Ayarları (Tümü Ctrl ile çalışır)", font=("Segoe UI", 11, "bold"), bg="white").pack(anchor="w", pady=5)

        # Trap 1
        k1_frame = tk.Frame(settings_frame, bg="white")
        k1_frame.pack(fill=tk.X, pady=2)
        tk.Label(k1_frame, text="Tuzak 1 (Wallpaper) Tuşu:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT)
        self.k1_entry = ttk.Entry(k1_frame, width=5)
        self.k1_entry.insert(0, "1")
        self.k1_entry.pack(side=tk.RIGHT)

        # Trap 2
        k2_frame = tk.Frame(settings_frame, bg="white")
        k2_frame.pack(fill=tk.X, pady=2)
        tk.Label(k2_frame, text="Tuzak 2 (Siyah Ekran) Tuşu:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT)
        self.k2_entry = ttk.Entry(k2_frame, width=5)
        self.k2_entry.insert(0, "2")
        self.k2_entry.pack(side=tk.RIGHT)

        # Lock
        k3_frame = tk.Frame(settings_frame, bg="white")
        k3_frame.pack(fill=tk.X, pady=2)
        tk.Label(k3_frame, text="Anında Kilitleme Tuşu:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT)
        self.k3_entry = ttk.Entry(k3_frame, width=5)
        self.k3_entry.insert(0, "3")
        self.k3_entry.pack(side=tk.RIGHT)

        # Exit
        ke_frame = tk.Frame(settings_frame, bg="white")
        ke_frame.pack(fill=tk.X, pady=2)
        tk.Label(ke_frame, text="Tuzağı Kapatma Tuşu:", font=("Segoe UI", 10), bg="white").pack(side=tk.LEFT)
        self.ke_combo = ttk.Combobox(ke_frame, values=["f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "esc", "end"], state="readonly", width=5)
        self.ke_combo.set("f12")
        self.ke_combo.pack(side=tk.RIGHT)

        ttk.Separator(settings_frame, orient='horizontal').pack(fill='x', pady=10)

        self.auto_start_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Windows açılışında arka planda gizlice otomatik başlat", variable=self.auto_start_var, bg="white", font=("Segoe UI", 10)).pack(anchor="w", pady=5)

        self.add_icon_var = tk.BooleanVar(value=True)
        tk.Checkbutton(settings_frame, text="Masaüstü simgesi (Icon) oluşturulsun mu?", variable=self.add_icon_var, bg="white", font=("Segoe UI", 10)).pack(anchor="w", pady=5)

        # --- Build Button & Status ---
        self.status_label = tk.Label(right_frame, text="", fg="blue", bg="white")
        self.status_label.pack(pady=5)

        button_frame = tk.Frame(right_frame, bg="white")
        button_frame.pack(pady=12)

        self.btn_build = ttk.Button(
            button_frame,
            text="Bu PC'ye Kur",
            command=self.start_build,
            style="Accent.TButton",
        )
        self.btn_build.pack(side=tk.LEFT, padx=5)

        self.btn_portable = ttk.Button(
            button_frame,
            text="Başka PC İçin EXE Üret",
            command=self.start_portable_build,
        )
        self.btn_portable.pack(side=tk.LEFT, padx=5)

        # Style configurations
        try:
            style.configure("Accent.TButton", font=("Segoe UI", 12, "bold"))
        except: pass

    def get_desktop_path(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            return winreg.QueryValueEx(key, "Desktop")[0]
        except:
            return os.path.join(os.path.expanduser("~"), "Desktop")

    def replace_existing_exe(self, source, destination):
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)

        if os.path.normcase(source) == os.path.normcase(destination):
            return destination

        destination_dir = os.path.dirname(destination)
        if destination_dir:
            os.makedirs(destination_dir, exist_ok=True)

        if os.path.exists(destination):
            try:
                os.remove(destination)
            except PermissionError:
                raise PermissionError(
                    "Aynı isimdeki eski EXE silinemedi. Dosya şu an çalışıyor "
                    "veya başka bir program tarafından tutuluyor olabilir; kapatıp tekrar deneyin."
                )

        shutil.copy2(source, destination)
        return destination

    def browse_wallpaper(self):
        filepaths = filedialog.askopenfilenames(
            title="Ctrl+1 için istediğiniz tüm görselleri seçin",
            filetypes=[
                ("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp *.webp"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )
        if filepaths:
            self.selected_wallpapers = list(filepaths)
            count = len(self.selected_wallpapers)
            self.lbl_wp.config(text=f"{count} görsel seçildi")

    def start_build(self):
        self._begin_build(install_locally=True)

    def start_portable_build(self):
        output_path = filedialog.asksaveasfilename(
            title="Başka bilgisayara gönderilecek EXE'yi kaydet",
            initialdir=self.get_desktop_path(),
            initialfile="Spiderpot_Baska_PC.exe",
            defaultextension=".exe",
            filetypes=[("Windows Uygulaması", "*.exe")],
        )
        if not output_path:
            return
        self._begin_build(install_locally=False, output_path=output_path)

    def _begin_build(self, install_locally, output_path=None):
        if not os.path.exists(self.core_script):
            messagebox.showerror("Hata", f"Kaynak kod bulunamadı!\n{self.core_script}")
            return
            
        missing_wallpapers = [
            path for path in self.selected_wallpapers
            if not os.path.exists(path)
        ]
        if not self.selected_wallpapers or missing_wallpapers:
            missing_text = "\n".join(missing_wallpapers[:5])
            messagebox.showerror(
                "Hata",
                "Seçilen görsellerden bazıları bulunamadı!"
                + (f"\n{missing_text}" if missing_text else ""),
            )
            return

        interval_text = self.slide_interval_entry.get().strip().replace(",", ".")
        try:
            self.slide_interval_seconds = float(interval_text)
        except ValueError:
            messagebox.showerror("Hata", "Foto geçiş aralığı sayı olmalı. Örn: 5 veya 2,5")
            return

        if self.slide_interval_seconds <= 0:
            messagebox.showerror("Hata", "Foto geçiş aralığı 0'dan büyük olmalı.")
            return

        self.btn_build.config(state=tk.DISABLED)
        self.btn_portable.config(state=tk.DISABLED)
        self.status_label.config(
            text="Gerekli kütüphaneler kuruluyor ve EXE derleniyor...",
            fg="blue",
        )

        threading.Thread(
            target=self.build_exe,
            args=(install_locally, output_path),
            daemon=True,
        ).start()

    def build_exe(self, install_locally=True, output_path=None):
        temp_script = None
        slideshow_stage_dir = None
        try:
            desktop_path = self.get_desktop_path()

            # Yalnızca "Bu PC'ye Kur" akışı mevcut kurulumu değiştirir.
            if install_locally:
                old_exes = ["Spiderpot.exe", "Spiderpot_Sistem.exe", "BearPot.exe"]
                for exe_name in old_exes:
                    subprocess.run(f"taskkill /F /IM {exe_name}", shell=True, capture_output=True)
                    old_path = os.path.join(desktop_path, exe_name)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except:
                            pass

                # Önce önceki otomatik başlangıç kayıtlarını temizle; seçim açıksa
                # başarılı kurulumdan sonra güncel hedefle yeniden oluşturulacak.
                try:
                    import winreg
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
                except Exception:
                    pass

                try:
                    old_shortcut = os.path.join(
                        os.getenv("APPDATA"),
                        "Microsoft",
                        "Windows",
                        "Start Menu",
                        "Programs",
                        "Startup",
                        "Spiderpot.lnk",
                    )
                    if os.path.exists(old_shortcut):
                        os.remove(old_shortcut)
                except Exception:
                    pass
            
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "opencv-python", "pynput", "pillow", "pystray", "screeninfo"], capture_output=True)
            
            with open(self.core_script, "r", encoding="utf-8") as f:
                code = f.read()

            # Replace keys
            code = code.replace("self.key_spider = '1'", f"self.key_spider = '{self.k1_entry.get().strip().lower()}'")
            code = code.replace("self.key_black = '2'", f"self.key_black = '{self.k2_entry.get().strip().lower()}'")
            code = code.replace("self.key_lock = '3'", f"self.key_lock = '{self.k3_entry.get().strip().lower()}'")
            code = code.replace("self.key_exit = 'f12'", f"self.key_exit = '{self.ke_combo.get().strip().lower()}'")
            code = code.replace(
                "SLIDESHOW_SECONDS = 5",
                f"SLIDESHOW_SECONDS = {self.slide_interval_seconds!r}",
            )

            # Rename image references internally to the selected image's name so pyinstaller finds it easily
            selected_wallpaper = self.selected_wallpapers[0]
            selected_filename = os.path.basename(selected_wallpaper)
            code = code.replace("spiderman3.jpg", selected_filename)

            if self.auto_start_var.get():
                auto_start_code = """
try:
    import sys, os, winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, "Spiderpot_App", 0, winreg.REG_SZ, sys.executable)
except: pass
"""
                code = auto_start_code + "\n" + code

            temp_script = os.path.join(self.build_dir, "Temp_Spiderpot.py")
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write(code)

            # Use the perfect transparent icon from Assets folder
            icon_path = os.path.join(self.build_dir, "Assets", "spider_noir_icon.ico")
            
            # İlk seçilen görsel ana wallpaper olarak, diğerleri ise Ctrl+1 akışına
            # sıralı ve benzersiz adlarla paketlenir.
            add_data_arg = f"{selected_wallpaper};."
            slideshow_stage_dir = tempfile.mkdtemp(
                prefix="Spiderpot_Slayt_",
                dir=self.build_dir,
            )
            selected_normalized = {
                os.path.normcase(os.path.abspath(path))
                for path in self.selected_wallpapers
            }

            for index, path in enumerate(self.selected_wallpapers[1:], start=1):
                staged_name = f"{index:04d}_{os.path.basename(path)}"
                shutil.copy2(path, os.path.join(slideshow_stage_dir, staged_name))

            supported = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
            folder_index = len(self.selected_wallpapers)
            if os.path.isdir(self.slideshow_dir):
                for name in sorted(os.listdir(self.slideshow_dir), key=str.casefold):
                    source = os.path.join(self.slideshow_dir, name)
                    if (
                        os.path.isfile(source)
                        and os.path.splitext(name)[1].lower() in supported
                        and os.path.normcase(os.path.abspath(source)) not in selected_normalized
                    ):
                        staged_name = f"{folder_index:04d}_{name}"
                        shutil.copy2(source, os.path.join(slideshow_stage_dir, staged_name))
                        folder_index += 1
            
            cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--name", "Spiderpot_Sistem"]
            if self.add_icon_var.get() and os.path.exists(icon_path):
                cmd.append(f"--icon={icon_path}")
            cmd.extend(["--add-data", add_data_arg])
            if os.listdir(slideshow_stage_dir):
                slideshow_data_arg = f"{slideshow_stage_dir};Slayt_Gorselleri"
                cmd.extend(["--add-data", slideshow_data_arg])
            cmd.append(temp_script)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.build_dir,
            )

            if result.returncode == 0:
                dist_dir = os.path.join(self.build_dir, "dist")
                exe_path = os.path.join(dist_dir, "Spiderpot_Sistem.exe")
                
                if os.path.exists(exe_path):
                    destination = (
                        os.path.join(self.get_desktop_path(), "Spiderpot_Sistem.exe")
                        if install_locally
                        else output_path
                    )
                    self.replace_existing_exe(exe_path, destination)

                    if install_locally and self.auto_start_var.get():
                        # Başlangıç (Startup) klasörüne kısayol ekle
                        try:
                            startup_folder = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
                            shortcut_path = os.path.join(startup_folder, "Spiderpot.lnk")
                            ps_script = f"$s=(New-Object -COM WScript.Shell).CreateShortcut('{shortcut_path}');$s.TargetPath='{destination}';$s.WorkingDirectory='{self.get_desktop_path()}';$s.Save()"
                            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        except:
                            pass

                    self.root.after(
                        0,
                        self.finish_build,
                        True,
                        destination,
                        install_locally,
                    )
                else:
                    self.root.after(0, self.finish_build, False, "EXE bulunamadı.", install_locally)
            else:
                self.root.after(0, self.finish_build, False, result.stderr, install_locally)
                
        except Exception as e:
            self.root.after(0, self.finish_build, False, str(e), install_locally)
        finally:
            if temp_script and os.path.exists(temp_script):
                try:
                    os.remove(temp_script)
                except:
                    pass
            if slideshow_stage_dir and os.path.isdir(slideshow_stage_dir):
                try:
                    shutil.rmtree(slideshow_stage_dir)
                except:
                    pass

    def finish_build(self, success, message, install_locally=True):
        self.btn_build.config(state=tk.NORMAL)
        self.btn_portable.config(state=tk.NORMAL)
        if success:
            self.status_label.config(text="Tamamlandı!", fg="green")
            if install_locally:
                messagebox.showinfo(
                    "Başarılı",
                    "Spiderpot bu bilgisayara kuruldu!\n"
                    "EXE dosyası Masaüstüne kaydedildi.\n\n"
                    "Eğer otomatik başlatmayı seçtiyseniz bilgisayar açıldığında "
                    "kendiliğinden çalışacaktır.",
                )
                try:
                    os.startfile(message)
                except:
                    pass
            else:
                messagebox.showinfo(
                    "Başarılı",
                    "Başka bilgisayara gönderilecek Spiderpot EXE hazır!\n\n"
                    f"Kaydedilen dosya:\n{message}\n\n"
                    "Bu bilgisayardaki mevcut Spiderpot değiştirilmedi ve yeni EXE çalıştırılmadı.",
                )
                try:
                    os.startfile(os.path.dirname(message))
                except:
                    pass
        else:
            self.status_label.config(text="Derleme hatası!", fg="red")
            messagebox.showerror("Hata", f"Hata detayı:\n{message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpiderpotBuilderApp(root)
    root.mainloop()
