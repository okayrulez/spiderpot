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
from spiderpot_support import CaptureStore, circular_icon, launch, load_config, resource

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
            
        configured = load_config()["wallpaper"]
        self.image_path = configured if configured and os.path.isfile(configured) else str(resource("Assets/spiderpot-wallpaper.jpg"))
        self._last_signature = None
        self.rebuild()

    def _monitor_signature(self):
        # Mevcut monitor yapisinin parmak izi (degisince pencereleri yenilemek icin).
        try:
            return tuple((m.width, m.height, m.x, m.y) for m in get_monitors())
        except Exception:
            return None

    def rebuild(self):
        # Pencereleri GUNCEL monitor yapisina gore (yeniden) olusturur.
        self._create_windows()
        self._preload_images()
        self._last_signature = self._monitor_signature()

    def ensure_current(self):
        # Monitorler degistiyse (takma/cikarma/cozunurluk) pencereleri tazele.
        if self._monitor_signature() != self._last_signature:
            self.rebuild()

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
            # DPI farkindaligi acik oldugu icin geometri her monitoru fiziksel piksel
            # olarak TAM kaplar. -fullscreen yerine overrideredirect kullaniyoruz: cok
            # monitorlu kurulumda her pencere kendi monitorune kesin oturur (-fullscreen
            # ikincil ekranlarda primary'ye kayabiliyor ve resim boyutuyla uyusmuyor).
            win.overrideredirect(True)
            win.geometry(f"{mon.width}x{mon.height}{mon.x:+d}{mon.y:+d}")
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
        self.ensure_current()
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
    def __init__(self, root, config=None):
        self.root = root
        self.root.withdraw()
        
        self.is_active = False
        self.active_mode = None
        
        self.cap = None
        self.last_capture_time = 0
        self.cooldown_seconds = 1
        self.camera_port = 0
        self.capture_lock = threading.Lock()
        self.session_lock = threading.RLock()
        self.config = config or load_config()
        self.camera_enabled = self.config['camera_enabled']
        self.camera_port = self.config['camera_index']
        self.session_generation = 0
        self.capture_thread = None
        self.closed = False
        
        self.capture_store = CaptureStore()
        self.capture_store.prune(self.config['retention_days'])
        self.root.after(60000, self._prune)

        self.viewer = SpiderpotViewer(self.root)
        
        self.mouse_listener = None
        self.input_listener = None
        
        self.key_spider = '1'
        self.key_black = '2'
        self.key_lock = '3'
        # To handle both local and built versions
        self.key_exit = 'f12'
        for name in ('key_spider', 'key_black', 'key_lock', 'key_exit'):
            setattr(self, name, self.config[name])
        
        # Kullanıcının seçtiği tuşları çalışma anında çözümle (vk + özel tuş nesnesi)
        self._resolve_hotkeys()
        self.last_trigger_time = 0.0

        self.setup_tray()

        # TEK global klavye dinleyicisi: hem açma kısayollarını hem de izinsiz giriş
        # tuşlarını yakalar. (Eski GlobalHotKeys + ayrı dinleyici ikilisi, tuş-bırakma
        # olaylarını kaçırıp kısayolu "kilitlediği" için kaldırıldı.)
        self.input_listener = keyboard.Listener(on_press=self.on_global_press)
        self.input_listener.start()
        
        # Camera remains closed until an explicitly enabled trap receives input.

    def _init_camera(self):
        pass  # Compatibility with older builders; no eager camera access.

    def _prune(self):
        if self.closed:
            return
        try:
            self.capture_store.prune(self.config['retention_days'])
        finally:
            self.root.after(60000, self._prune)

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
        def on_exit(icon, item):
            self.root.after(0, self.real_quit)
        def settings(icon, item):
            self.root.after(0, self.open_settings)
        def captures(icon, item):
            self.root.after(0, lambda: launch('--captures'))
        def stop(icon, item):
            self.root.after(0, self.stop_system)
        menu = pystray.Menu(
            TrayItem("Ayarlar", settings, default=True),
            TrayItem("Fotoğraflar", captures),
            TrayItem("Tuzağı durdur", stop),
            TrayItem("Sistemi Tamamen Kapat", on_exit)
        )
        self.tray_icon = pystray.Icon("Spiderpot", circular_icon(), "Spiderpot (Pasif)", menu=menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def update_tray_icon(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            status = "Aktif" if self.is_active else "Pasif"
            self.tray_icon.icon = circular_icon(active=self.is_active)
            self.tray_icon.title = f"Spiderpot ({status}) · Kamera {'açık' if self.camera_enabled else 'kapalı'}"

    def open_settings(self):
        self.stop_system()
        launch('--configure')
        self.real_quit()

    def capture_photo(self):
        if not self.is_active or not self.camera_enabled or self.closed:
            return
        if not self.capture_lock.acquire(blocking=False):
            return
        if time.monotonic() - self.last_capture_time < self.cooldown_seconds:
            self.capture_lock.release()
            return
        generation = self.session_generation
        self.last_capture_time = time.monotonic()
        self.capture_thread = threading.Thread(target=self._capture, args=(generation,), daemon=True)
        self.capture_thread.start()

    def _capture(self, generation):
        camera = None
        try:
            if not self.is_active or generation != self.session_generation:
                return
            camera = cv2.VideoCapture(self.camera_port, cv2.CAP_DSHOW)
            if not camera.isOpened():
                raise RuntimeError('Kamera açılamadı. Windows kamera izinlerini kontrol edin.')
            for _ in range(4):
                if not self.is_active or self.closed or generation != self.session_generation:
                    return
                ret, frame = camera.read()
                if not ret:
                    raise RuntimeError('Kameradan görüntü alınamadı.')
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                raise RuntimeError('Fotoğraf hazırlanamadı.')
            # Session lock also guards cancellation before persistence.
            with self.session_lock:
                if self.is_active and not self.closed and generation == self.session_generation:
                    self.capture_store.save(jpeg.tobytes())
        except Exception as error:
            self.camera_enabled = False
            if not self.closed:
                self.root.after(0, lambda text=str(error): self._camera_error(text))
        finally:
            if camera is not None:
                camera.release()
            self.capture_lock.release()

    def _camera_error(self, text):
        self.update_tray_icon()
        try:
            self.tray_icon.notify(text + ' Fotoğraf çekimi kapatıldı; tuzak çalışmaya devam ediyor.', 'Spiderpot')
        except Exception:
            pass

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
            self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll, suppress=True)
            self.mouse_listener.start()
            prevent_sleep()
            with self.session_lock:
                self.session_generation += 1

        self.is_active = True
        self.active_mode = mode
        self.update_tray_icon()
        if mode == 'invisible':
            self.viewer.hide()
        else:
            self.viewer.show_mode(mode_spider=(mode=='spider'))

    def stop_system(self):
        if not self.is_active: return
        with self.session_lock:
            self.is_active = False
            self.session_generation += 1
        self.active_mode = None
        self.update_tray_icon()
        self.viewer.hide()
        
        allow_sleep()

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
        self.closed = True
        if self.input_listener:
            try: self.input_listener.stop()
            except: pass
        
        # Tamamen çıkarken kamerayı serbest bırak
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            
        self.tray_icon.stop()
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
