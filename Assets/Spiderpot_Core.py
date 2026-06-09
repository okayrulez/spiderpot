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
            win.overrideredirect(True)
            win.geometry(f"{mon.width}x{mon.height}+{mon.x}+{mon.y}")
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
                if img_ratio > mon_ratio:
                    new_w = mon.width
                    new_h = int(new_w / img_ratio)
                else:
                    new_h = mon.height
                    new_w = int(new_h * img_ratio)
                
                # Pre-resize and cache
                resized = pil_img_base.resize((new_w, new_h), Image.Resampling.LANCZOS)
                self.photo_images[i] = ImageTk.PhotoImage(resized)

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
        
        self.setup_hotkeys()
        self.setup_tray()
        
        self.input_listener = keyboard.Listener(on_press=self.on_input_press)
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

    def setup_hotkeys(self):
        hotkeys = {
            f'<ctrl>+{self.key_spider}': lambda: self.root.after(0, lambda: self.toggle_system('spider')),
            f'<ctrl>+{self.key_black}': lambda: self.root.after(0, lambda: self.toggle_system('black')),
            f'<ctrl>+{self.key_lock}': lambda: self.root.after(0, lambda: self.toggle_system('invisible')),
            f'<{self.key_exit}>': lambda: self.root.after(0, self.stop_system)
        }
        self.hotkey_listener = keyboard.GlobalHotKeys(hotkeys)
        self.hotkey_listener.start()

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

    def on_input_press(self, key):
        if self.is_active:
            if key not in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
                if hasattr(key, 'char') and key.char in ['1', '2', '3']:
                    pass
                else:
                    self.capture_photo()

    def toggle_system(self, mode):
        if self.is_active and self.active_mode == mode:
            self.stop_system()
        else:
            self.start_system(mode)

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
        
        # Kamerayı stop_system'de kapatmıyoruz (hızlı açılış için hep açık kalıyor)

    def lock_screen(self):
        ctypes.windll.user32.LockWorkStation()

    def real_quit(self):
        allow_sleep()
        self.stop_system()
        if self.hotkey_listener:
            try: self.hotkey_listener.stop()
            except: pass
        
        # Tamamen çıkarken kamerayı serbest bırak
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        self.root.destroy()
        sys.exit()

if __name__ == "__main__":
    mutex_name = "Global\\Spiderpot_Mutex_Lock"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183:  # ERROR_ALREADY_EXISTS
        sys.exit(0)

    root = tk.Tk()
    app = SpiderpotApp(root)
    root.mainloop()
