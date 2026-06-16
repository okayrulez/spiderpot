import cv2
from pynput import mouse, keyboard
import time
from datetime import datetime
import os
import ctypes
import sys
import winreg
import tkinter as tk
import threading
from PIL import Image, ImageTk

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def prevent_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
    except: pass

def allow_sleep():
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    except: pass

def set_dpi_awareness():
    # Tk ile screeninfo'nun AYNI (fiziksel piksel) koordinat sistemini kullanmasini saglar.
    # Aksi halde olceklenmis ekranlarda (orn. %150/%200) tuzak penceresi tum ekrani
    # kaplamaz; ekranin yalnizca bir kosesinde gorunur. Tk olusturulmadan ONCE cagrilmali.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

def set_antigravity_mode(active=True):
    try:
        # Check if admin first, otherwise skip to prevent errors/crashes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            print("[!] Yönetici izni yok, AntiGravity modu (USB Engelleyici) atlandı.")
            return
            
        if active:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\USBSTOR", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 4)
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions", 0, winreg.KEY_SET_VALUE)
            except FileNotFoundError:
                key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions")
            winreg.SetValueEx(key, "DenyUnspecified", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        else:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\USBSTOR", 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "Start", 0, winreg.REG_DWORD, 3)
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions", 0, winreg.KEY_SET_VALUE)
            except FileNotFoundError:
                key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Windows\DeviceInstall\Restrictions")
            winreg.SetValueEx(key, "DenyUnspecified", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
    except Exception as e:
        print(f"[!] AntiGravity Hatası: {e}")

def get_desktop_path():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        return winreg.QueryValueEx(key, "Desktop")[0]
    except:
        return os.path.join(os.path.expanduser("~"), "Desktop")

try:
    from screeninfo import get_monitors
    HAS_SCREENINFO = True
except ImportError:
    HAS_SCREENINFO = False

class SpiderpotViewer:
    def __init__(self, parent):
        self.parent = parent
        self.windows = []
        self.labels = []
        self.photo_images = []
        self.monitors = []
        self.is_visible = False
        
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.image_path = os.path.join(base_dir, "spiderman3.jpg")
        self._create_windows()
        self._preload_images()

    def _create_windows(self):
        for w in self.windows:
            try: w.destroy()
            except: pass
        self.windows.clear()
        self.labels.clear()
        self.photo_images.clear()
        self.monitors.clear()

        use_screeninfo = HAS_SCREENINFO
        if use_screeninfo:
            try:
                self.monitors = get_monitors()
            except:
                use_screeninfo = False

        if not use_screeninfo or not self.monitors:
            class DummyMon:
                def __init__(self, w, h, x, y):
                    self.width = w; self.height = h; self.x = x; self.y = y
            self.monitors = [DummyMon(self.parent.winfo_screenwidth(), self.parent.winfo_screenheight(), 0, 0)]

        for mon in self.monitors:
            win = tk.Toplevel(self.parent)
            win.withdraw()
            # overrideredirect ve -fullscreen çakışıyor, o yüzden sadece -fullscreen kullanıyoruz
            win.geometry(f"{mon.width}x{mon.height}+{mon.x}+{mon.y}")
            win.attributes("-fullscreen", True)
            win.attributes("-topmost", True)
            win.configure(bg='black')
            
            lbl = tk.Label(win, bg='black')
            lbl.pack(expand=True, fill=tk.BOTH)
            
            self.windows.append(win)
            self.labels.append(lbl)
            self.photo_images.append(None)

    def _preload_images(self):
        pil_img_base = None
        if os.path.exists(self.image_path):
            try:
                pil_img_base = Image.open(self.image_path)
            except:
                pass

        for i, mon in enumerate(self.monitors):
            if pil_img_base:
                img_ratio = pil_img_base.width / pil_img_base.height
                mon_ratio = mon.width / mon.height
                # KAPLA (cover): resmi ekrani TAMAMEN dolduracak sekilde olceklendir,
                # tasan kismi merkezden kirp -> kenarda siyah bosluk birakmadan tam ekran.
                if img_ratio > mon_ratio:
                    new_h = mon.height
                    new_w = int(new_h * img_ratio)
                else:
                    new_w = mon.width
                    new_h = int(new_w / img_ratio)

                resized = pil_img_base.resize((max(new_w, 1), max(new_h, 1)), Image.Resampling.LANCZOS)
                left = max((new_w - mon.width) // 2, 0)
                top = max((new_h - mon.height) // 2, 0)
                cropped = resized.crop((left, top, left + mon.width, top + mon.height))
                self.photo_images[i] = ImageTk.PhotoImage(cropped)

    def show_mode(self, mode_spider=True):
        for i, (win, lbl) in enumerate(zip(self.windows, self.labels)):
            if mode_spider:
                if self.photo_images[i]:
                    lbl.config(image=self.photo_images[i])
                else:
                    lbl.config(text="Wallpaper Bulunamadı!", fg="white", font=("Arial", 24))
            else:
                lbl.config(image='', text="")
            
            win.deiconify()
        self.is_visible = True

    def hide(self):
        for win in self.windows:
            try: win.withdraw()
            except: pass
        self.is_visible = False

import pystray
from pystray import MenuItem as TrayItem
from PIL import ImageDraw

class SpiderpotApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        
        self.is_active = False
        self.active_mode = None
        
        self.cap = None
        self.last_capture_time = 0
        self.cooldown_seconds = 1
        self.camera_port = 0
        self.capture_lock = threading.Lock()
        
        desktop_path = get_desktop_path()
        self.save_folder = os.path.join(desktop_path, "Spiderpot_Yakalananlar")
        if not os.path.exists(self.save_folder):
            try: os.makedirs(self.save_folder)
            except: pass

        self.viewer = SpiderpotViewer(self.root)
        
        self.mouse_listener = None
        self.input_listener = None
        
        self.key_spider = '1'
        self.key_black = '2'
        self.key_lock = '3'
        # To handle both local and built versions
        self.key_exit = 'f12'
        
        # Kullanıcının seçtiği tuşları çalışma anında çözümle (vk + özel tuş nesnesi)
        self._resolve_hotkeys()
        self.last_trigger_time = 0.0

        self.setup_tray()

        # TEK global klavye dinleyicisi: hem açma kısayollarını hem de izinsiz giriş
        # tuşlarını yakalar. (Eski GlobalHotKeys + ayrı dinleyici ikilisi, tuş-bırakma
        # olaylarını kaçırıp kısayolu "kilitlediği" için kaldırıldı.)
        self.input_listener = keyboard.Listener(on_press=self.on_global_press)
        self.input_listener.start()
        
        # Pre-initialize camera silently in background on startup to be extremely fast later
        threading.Thread(target=self._init_camera, daemon=True).start()
        
        # Bilgisayarı açık tutma protokolü
        prevent_sleep()

    def _init_camera(self):
        try:
            if self.cap is None or not self.cap.isOpened():
                temp_cap = cv2.VideoCapture(self.camera_port)
                with self.capture_lock:
                    self.cap = temp_cap
        except: pass

    def _resolve_hotkeys(self):
        # Mod tuşlarını sanal tuş koduna (vk) çevir. vk; klavye düzeninden ve Ctrl'nin
        # ürettiği kontrol karakterlerinden (Ctrl+Q -> '\x11' gibi) bağımsız, güvenilir
        # bir eşleşme verir.
        def to_vk(ch):
            try:
                return ord(str(ch).strip().upper()[0])
            except Exception:
                return None

        self.mode_by_vk = {
            to_vk(self.key_spider): 'spider',
            to_vk(self.key_black): 'black',
            to_vk(self.key_lock): 'invisible',
        }
        self.mode_by_vk.pop(None, None)
        self.mode_by_char = {
            str(self.key_spider).lower(): 'spider',
            str(self.key_black).lower(): 'black',
            str(self.key_lock).lower(): 'invisible',
        }
        # Çıkış (kapatma) tuşunu pynput özel tuş nesnesine çevir: f1..f12, esc, end ...
        self.exit_key = getattr(keyboard.Key, str(self.key_exit).strip().lower(), None)

    def _ctrl_is_down(self):
        # Ctrl'yi OS'tan anlık oku: pynput'un kaçırdığı tuş-bırakma olayları yüzünden
        # oluşan "kilitlenmiş modifiye tuş" sorununu tamamen ortadan kaldırır.
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(0x11) & 0x8000)
        except Exception:
            return False

    def _match_mode(self, key):
        vk = getattr(key, 'vk', None)
        if vk in self.mode_by_vk:
            return self.mode_by_vk[vk]
        ch = getattr(key, 'char', None)
        if ch:
            c = ch.lower()
            if c in self.mode_by_char:
                return self.mode_by_char[c]
            # Ctrl+harf kontrol karakteri (ör. Ctrl+Q -> '\x11') -> gerçek harfe çevir
            if len(c) == 1 and ord(c) < 0x20:
                letter = chr(ord(c) + 96)
                if letter in self.mode_by_char:
                    return self.mode_by_char[letter]
        return None

    def setup_tray(self):
        def create_icon_image(color):
            image = Image.new('RGB', (64, 64), color)
            draw = ImageDraw.Draw(image)
            draw.rectangle((16, 16, 48, 48), fill="white")
            draw.ellipse((24, 24, 40, 40), fill=color)
            return image

        def on_exit(icon, item):
            self.root.after(0, self.real_quit)

        menu = pystray.Menu(
            TrayItem("Sistemi Tamamen Kapat", on_exit)
        )
        self.tray_icon = pystray.Icon("Spiderpot", create_icon_image("red"), "Spiderpot (Pasif)", menu=menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def update_tray_icon(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            color = "green" if self.is_active else "red"
            status = "Aktif" if self.is_active else "Pasif"
            def create_icon_image(c):
                img = Image.new('RGB', (64, 64), c)
                dr = ImageDraw.Draw(img)
                dr.rectangle((16, 16, 48, 48), fill="white")
                dr.ellipse((24, 24, 40, 40), fill=c)
                return img
            self.tray_icon.icon = create_icon_image(color)
            self.tray_icon.title = f"Spiderpot ({status})"

    def capture_photo(self):
        with self.capture_lock:
            current_time = time.time()
            if current_time - self.last_capture_time < self.cooldown_seconds:
                return

            if self.cap is not None and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"yakalandin_{timestamp}.jpg"
                    filepath = os.path.join(self.save_folder, filename)
                    cv2.imwrite(filepath, frame)
                    self.last_capture_time = current_time

    def on_move(self, x, y):
        if self.is_active: self.capture_photo()

    def on_click(self, x, y, button, pressed):
        if self.is_active and pressed: self.capture_photo()

    def on_scroll(self, x, y, dx, dy):
        if self.is_active: self.capture_photo()

    def on_global_press(self, key):
        # 1) Gizli çıkış (kapatma) tuşu -> her zaman sistemi durdurur.
        if self.exit_key is not None and key == self.exit_key:
            self.root.after(0, self.stop_system)
            return

        # 2) Açma kısayolu: Ctrl fiziksel basılıyken bir mod tuşu.
        #    Mod tuşları SADECE açar / mod değiştirir; ASLA kapatmaz (kapatma = çıkış tuşu).
        if self._ctrl_is_down():
            mode = self._match_mode(key)
            if mode is not None:
                now = time.time()
                # Oto-tekrar / çift tetik koruması (sıçrama önleme).
                if now - self.last_trigger_time >= 0.4:
                    self.last_trigger_time = now
                    self.root.after(0, lambda m=mode: self.start_system(m))
                return  # mod tuşunu izinsiz-giriş tuşu olarak sayma

        # 3) Sistem aktifken diğer her tuş -> izinsiz giriş, fotoğraf çek.
        if self.is_active and key not in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.capture_photo()

    def start_system(self, mode):
        if not self.is_active:
            # We already load camera asynchronously, so we don't block here.
            # Just fallback to starting thread if not opened yet.
            if self.cap is None or not self.cap.isOpened():
                threading.Thread(target=self._init_camera, daemon=True).start()
                
            self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll, suppress=True)
            self.mouse_listener.start()
            
            # Start antigravity asynchronously so registry logic doesn't block the screen popup
            threading.Thread(target=set_antigravity_mode, args=(True,), daemon=True).start()

        self.is_active = True
        self.active_mode = mode
        self.update_tray_icon()
        if mode == 'invisible':
            self.viewer.hide()
        else:
            self.viewer.show_mode(mode_spider=(mode=='spider'))

    def stop_system(self):
        if not self.is_active: return
        self.is_active = False
        self.active_mode = None
        self.update_tray_icon()
        self.viewer.hide()
        
        # Asenkron kapat ki anında tepki versin
        threading.Thread(target=set_antigravity_mode, args=(False,), daemon=True).start()

        if self.mouse_listener:
            try: self.mouse_listener.stop()
            except: pass
        
        # Kamerayı asenkron kapat ki ışık sönsün ve program kilitlenmesin
        def _release_cam():
            if hasattr(self, 'cap') and self.cap is not None:
                tmp = self.cap
                self.cap = None
                try: tmp.release()
                except: pass
        threading.Thread(target=_release_cam, daemon=True).start()

    def lock_screen(self):
        ctypes.windll.user32.LockWorkStation()

    def real_quit(self):
        allow_sleep()
        self.stop_system()
        if self.input_listener:
            try: self.input_listener.stop()
            except: pass
        
        # Tamamen çıkarken kamerayı serbest bırak
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    # Ekran olceklemesinden (DPI) bagimsiz tam-ekran kaplama icin Tk'den ONCE cagrilir.
    set_dpi_awareness()

    mutex_name = "Global\\Spiderpot_Mutex_Lock"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)

    root = tk.Tk()
    app = SpiderpotApp(root)
    root.mainloop()
