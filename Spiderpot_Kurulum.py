import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess
import threading
import sys
import shutil

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
        self.selected_wallpaper = os.path.join(self.build_dir, "Assets", "spider_noir.jpg")

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
        
        tk.Label(right_frame, text="Spiderpot Kurulum Sihirbazı", font=("Segoe UI", 16, "bold"), bg="white", fg="red").pack(pady=15)
        
        # --- Settings Frame ---
        settings_frame = tk.Frame(right_frame, bg="white")
        settings_frame.pack(fill=tk.X, padx=20, pady=5)
        
        # 1. Wallpaper Selection
        wp_frame = tk.Frame(settings_frame, bg="white")
        wp_frame.pack(fill=tk.X, pady=5)
        tk.Label(wp_frame, text="Tuzak Wallpaper Seç:", font=("Segoe UI", 10, "bold"), bg="white").pack(side=tk.LEFT)
        self.lbl_wp = tk.Label(wp_frame, text="spiderman3.jpg", font=("Segoe UI", 9), bg="white", fg="blue", width=25, anchor="e")
        self.lbl_wp.pack(side=tk.LEFT, padx=5)
        tk.Button(wp_frame, text="Gözat", command=self.browse_wallpaper, height=1, relief="groove").pack(side=tk.RIGHT)
        
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

        self.btn_build = ttk.Button(right_frame, text="Kurulumu Başlat", command=self.start_build, style="Accent.TButton")
        self.btn_build.pack(pady=15)

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

    def browse_wallpaper(self):
        filepath = filedialog.askopenfilename(title="Wallpaper Seç", filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.bmp")])
        if filepath:
            self.selected_wallpaper = filepath
            filename = os.path.basename(filepath)
            # Kısalt
            if len(filename) > 20: filename = filename[:17] + "..."
            self.lbl_wp.config(text=filename)

    def start_build(self):
        if not os.path.exists(self.core_script):
            messagebox.showerror("Hata", f"Kaynak kod bulunamadı!\n{self.core_script}")
            return
            
        if not os.path.exists(self.selected_wallpaper):
            messagebox.showerror("Hata", f"Seçilen duvar kağıdı bulunamadı!\n{self.selected_wallpaper}")
            return

        self.btn_build.config(state=tk.DISABLED, text="Derleniyor...")
        self.status_label.config(text="Gerekli kütüphaneler kuruluyor ve EXE derleniyor...")

        threading.Thread(target=self.build_exe, daemon=True).start()

    def build_exe(self):
        try:
            # Kill any running old instances and delete from desktop
            desktop_path = self.get_desktop_path()
            old_exes = ["Spiderpot.exe", "Spiderpot_Sistem.exe"]
            for exe_name in old_exes:
                subprocess.run(f"taskkill /F /IM {exe_name}", shell=True, capture_output=True)
                old_path = os.path.join(desktop_path, exe_name)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass
            
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller", "opencv-python", "pynput", "pillow", "pystray", "screeninfo"], capture_output=True)
            
            with open(self.core_script, "r", encoding="utf-8") as f:
                code = f.read()

            # Replace keys
            code = code.replace("self.key_spider = '1'", f"self.key_spider = '{self.k1_entry.get().strip().lower()}'")
            code = code.replace("self.key_black = '2'", f"self.key_black = '{self.k2_entry.get().strip().lower()}'")
            code = code.replace("self.key_lock = '3'", f"self.key_lock = '{self.k3_entry.get().strip().lower()}'")
            code = code.replace("self.key_exit = 'f12'", f"self.key_exit = '{self.ke_combo.get().strip().lower()}'")

            # Rename image references internally to the selected image's name so pyinstaller finds it easily
            selected_filename = os.path.basename(self.selected_wallpaper)
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

            os.chdir(self.build_dir)
            
            # Use the perfect transparent icon from Assets folder
            icon_path = os.path.join(self.build_dir, "Assets", "spider_noir_icon.ico")
            
            # Asset klasörü
            add_data_arg = f"{self.selected_wallpaper};."
            
            cmd = [sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--name", "Spiderpot_Sistem"]
            if self.add_icon_var.get() and os.path.exists(icon_path):
                cmd.append(f"--icon={icon_path}")
            cmd.extend(["--add-data", add_data_arg])
            cmd.append(temp_script)
            
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                dist_dir = os.path.join(self.build_dir, "dist")
                exe_path = os.path.join(dist_dir, "Spiderpot_Sistem.exe")
                
                if os.path.exists(exe_path):
                    desktop_exe = os.path.join(self.get_desktop_path(), "Spiderpot_Sistem.exe")
                    shutil.copy2(exe_path, desktop_exe)
                    
                    self.root.after(0, self.finish_build, True, desktop_exe)
                else:
                    self.root.after(0, self.finish_build, False, "EXE bulunamadı.")
            else:
                self.root.after(0, self.finish_build, False, result.stderr)
                
            try: os.remove(temp_script)
            except: pass
            
        except Exception as e:
            self.root.after(0, self.finish_build, False, str(e))

    def finish_build(self, success, message):
        self.btn_build.config(state=tk.NORMAL, text="Kurulumu Başlat")
        if success:
            self.status_label.config(text="Tamamlandı!", fg="green")
            messagebox.showinfo("Başarılı", f"Spiderpot başarıyla derlendi!\nEXE Dosyası Masaüstüne kaydedildi.\n\nEğer otomatik başlatmayı seçtiyseniz bilgisayar açıldığında kendiliğinden çalışacaktır.")
            try: os.startfile(message)
            except: pass
        else:
            self.status_label.config(text="Derleme hatası!", fg="red")
            messagebox.showerror("Hata", f"Hata detayı:\n{message}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SpiderpotBuilderApp(root)
    root.mainloop()
