import cv2
from io import BytesIO
from queue import Empty, SimpleQueue
from pynput import mouse, keyboard
import time
from datetime import datetime
import os
import ctypes
import sys
import winreg
import tkinter as tk
import threading
from PIL import Image, ImageOps, ImageTk
from spiderpot_support import CaptureStore, circular_icon, launch, load_config, resource, shortcut_label, shortcut_parts, show_captures
from spiderpot_session import DesktopCard, Session
from camera_tools import capture_camera_frame
from spiderpot_mail import ActivityMailer, MailError, decode_enrollment

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
CAPTURE_PREVIEW_MS = 3000
KEY_DOWN = {0x100, 0x104}
KEY_UP = {0x101, 0x105}
MODIFIER_VKS = {0x10, 0x11, 0x12, 0x5B, 0x5C, *range(0xA0, 0xA6)}


def key_vk(key):
    if isinstance(key, int):
        return key
    return getattr(getattr(key, "value", key), "vk", None)


def shortcut_vk(value, *, mode=False):
    modifiers, key = shortcut_parts(value, mode=mode)
    code = ord(key.upper()) if len(key) == 1 else key_vk(getattr(keyboard.Key, key))
    return modifiers, code

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
        self.capture_images = []
        self.monitors = []
        self.is_visible = False
        self.slide_job = None
        self.slide_index = 0
        self.current_slide = []
        config = load_config()
        configured = config["slides"] or (config["wallpaper"],)
        self.slide_paths = [path for path in configured if path and os.path.isfile(path)]
        if not self.slide_paths:
            self.slide_paths = [str(resource("Assets/spiderpot-wallpaper.jpg"))]
        self.slide_seconds = config["slide_seconds"]
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
        self.capture_images.clear()
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
        self.current_slide = self._load_slide(self.slide_index)
        if self.current_slide:
            self._display_slide(self.current_slide)
        else:
            self.photo_images = [None] * len(self.labels)

    def _load_slide(self, index):
        try:
            with Image.open(self.slide_paths[index]) as source:
                photo = ImageOps.exif_transpose(source).convert("RGB")
                return [ImageOps.fit(photo, (mon.width, mon.height), Image.Resampling.LANCZOS)
                        for mon in self.monitors]
        except (OSError, ValueError):
            return []

    def _display_slide(self, frames):
        images = [ImageTk.PhotoImage(frame, master=self.parent) for frame in frames]
        for label, image in zip(self.labels, images):
            label.config(image=image, text="", compound=tk.NONE, padx=0, pady=0)
        self.photo_images = images

    def _cancel_slideshow(self):
        if self.slide_job is not None:
            self.parent.after_cancel(self.slide_job)
            self.slide_job = None

    def _schedule_slide(self):
        if len(self.slide_paths) > 1:
            self.slide_job = self.parent.after(self.slide_seconds * 1000, self._advance_slide)

    def _advance_slide(self):
        self.slide_job = None
        if self._monitor_signature() != self._last_signature:
            self.show_mode(mode_spider=True)
            return
        next_index = (self.slide_index + 1) % len(self.slide_paths)
        following = self._load_slide(next_index)
        if not following:
            self.slide_index = next_index
            self._schedule_slide()
            return
        if not self.current_slide:
            self._display_slide(following)
            self.current_slide, self.slide_index = following, next_index
            self._schedule_slide()
            return
        self._fade_slide(next_index, following, 1)

    def _fade_slide(self, index, following, step):
        if step < 6:
            self._display_slide([Image.blend(old, new, step / 6)
                                 for old, new in zip(self.current_slide, following)])
            self.slide_job = self.parent.after(50, self._fade_slide, index, following, step + 1)
        else:
            self._display_slide(following)
            self.current_slide, self.slide_index = following, index
            self._schedule_slide()

    def show_mode(self, mode_spider=True, *, restart=False):
        self._cancel_slideshow()
        self.ensure_current()
        if mode_spider and restart:
            self.slide_index = 0
            self._preload_images()
        elif mode_spider and self.current_slide:
            self._display_slide(self.current_slide)
        for i, (win, lbl) in enumerate(zip(self.windows, self.labels)):
            image = self.photo_images[i] if mode_spider else None
            text = "Wallpaper Bulunamadı!" if mode_spider and image is None else ""
            lbl.config(image=image or '', text=text, fg="white", font=("Arial", 24),
                       compound=tk.NONE, padx=0, pady=0)
            win.deiconify()
        self.capture_images.clear()
        self.is_visible = True
        if mode_spider:
            self._schedule_slide()

    def show_capture(self, jpeg):
        self._cancel_slideshow()
        self.ensure_current()
        with Image.open(BytesIO(jpeg)) as photo:
            images = []
            for mon in self.monitors:
                bounds = (max(1, int(mon.width * .84)), max(1, int(mon.height * .72)))
                fitted = ImageOps.contain(photo, bounds, Image.Resampling.LANCZOS)
                images.append(ImageTk.PhotoImage(fitted, master=self.parent))

        for mon, win, lbl, image in zip(self.monitors, self.windows, self.labels, images):
            lbl.config(image=image, text="YAKALANDIN!", compound=tk.BOTTOM, fg="white",
                       font=("Segoe UI", max(18, min(48, mon.height // 28)), "bold"),
                       padx=0, pady=12)
            win.deiconify()
        self.capture_images = images
        self.is_visible = True

    def hide(self):
        self._cancel_slideshow()
        for win in self.windows:
            try: win.withdraw()
            except: pass
        if self.capture_images:
            for label in self.labels:
                label.config(image='', text="")
            self.capture_images.clear()
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
        self.last_capture_time = float('-inf')
        self.cooldown_seconds = 3
        self.camera_port = 0
        self.capture_lock = threading.Lock()
        self.session_lock = threading.RLock()
        self.config = config or load_config()
        self.dashboard = None
        self.remote_panel = None
        self.last_summary = ""
        self.card = DesktopCard(root)
        self.countdown_job = None
        self.pending_mode = None
        self.session = None
        self.mailer = None
        enrollment = decode_enrollment(self.config.get('mail_enrollment', ''))
        if enrollment:
            try:
                self.mailer = ActivityMailer(enrollment, self.mail_error)
            except MailError:
                pass
        self.camera_enabled = self.config['camera_enabled']
        self.camera_port = self.config['camera_index']
        self.session_generation = 0
        self.capture_thread = None
        self.capture_preview_job = None
        self.camera_failed_generation = None
        self.tutorial = None
        self.closed = False
        
        self.capture_store = CaptureStore()
        self.capture_store.prune(self.config['retention_days'])
        self.root.after(60000, self._prune)

        self.viewer = SpiderpotViewer(self.root)
        
        self.mouse_listener = None
        self.input_listener = None
        self.key_events = SimpleQueue()
        self.suppressed_keys = set()
        self.passed_keys = set()
        
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
        self.input_listener = keyboard.Listener(win32_event_filter=self._filter_keyboard)
        self.input_listener.start()
        self.root.after(15, self._process_keys)
        
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
        self.mode_hotkeys = {
            shortcut_vk(self.key_spider, mode=True): 'spider',
            shortcut_vk(self.key_black, mode=True): 'black',
            shortcut_vk(self.key_lock, mode=True): 'invisible',
        }
        self.exit_hotkey = shortcut_vk(self.key_exit)

    def _modifiers(self):
        pressed = ctypes.windll.user32.GetAsyncKeyState
        return frozenset(name for name, code in (("ctrl", 0x11), ("alt", 0x12), ("shift", 0x10))
                         if pressed(code) & 0x8000)

    def _filter_keyboard(self, message, data):
        # Never do Tk or camera work on the Windows low-level hook thread.
        vk = data.vkCode
        if message in KEY_UP:
            self.passed_keys.discard(vk)
            if vk in self.suppressed_keys:
                self.suppressed_keys.discard(vk)
                self.input_listener.suppress_event()
            return False
        if message not in KEY_DOWN or vk in MODIFIER_VKS:
            return False
        down = ctypes.windll.user32.GetAsyncKeyState
        if down(0x5B) & 0x8000 or down(0x5C) & 0x8000:
            return False  # Preserve Windows shortcuts, including Win+L.
        modifiers = self._modifiers()
        if (vk == 0x2E and {"ctrl", "alt"} <= modifiers
                or vk == 0x1B and {"ctrl", "shift"} <= modifiers):
            return False  # Leave the Windows emergency shortcuts available.
        mode_shortcut = (modifiers, vk) in self.mode_hotkeys
        if (modifiers, vk) == self.exit_hotkey or mode_shortcut or self.is_active:
            self.key_events.put((vk, modifiers))
        if vk in self.suppressed_keys or ((self.is_active or mode_shortcut) and vk not in self.passed_keys):
            self.suppressed_keys.add(vk)
            self.input_listener.suppress_event()
        self.passed_keys.add(vk)
        return False

    def _process_keys(self):
        if self.closed:
            return
        try:
            for _ in range(128):
                try:
                    key, modifiers = self.key_events.get_nowait()
                except Empty:
                    break
                self.on_global_press(key, modifiers)
        finally:
            if not self.closed:
                self.root.after(15, self._process_keys)

    def setup_tray(self):
        def on_exit(icon, item):
            self.root.after(0, self.real_quit)
        def settings(icon, item):
            self.root.after(0, self.open_settings)
        def captures(icon, item):
            self.root.after(0, self.open_gallery)
        def stop(icon, item):
            self.root.after(0, self.stop_system)
        def tutorial(icon, item):
            self.root.after(0, self.open_tutorial)
        menu = pystray.Menu(
            TrayItem("Dashboard aç", lambda: self.root.after(0, self.open_dashboard)),
            TrayItem("Ayarlar", settings),
            TrayItem("Çıkmadan önce dene", lambda: self.root.after(0, self.open_check)),
            TrayItem("Kullanımı gör", tutorial),
            TrayItem("Fotoğraflar", captures),
            TrayItem("Tuzağı durdur", stop),
            TrayItem("Sistemi Tamamen Kapat", on_exit)
        )
        self.tray_icon = pystray.Icon("Spiderpot", circular_icon(), "Spiderpot (Pasif)", menu=menu)
        self.update_tray_icon()
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def update_tray_icon(self):
        if hasattr(self, 'tray_icon') and self.tray_icon:
            status = "Aktif" if self.is_active else "Pasif"
            self.tray_icon.icon = circular_icon(active=self.is_active)
            self.tray_icon.title = f"Spiderpot ({status}) · Kamera {'açık' if self.camera_allowed() else 'kapalı'}"

    def open_settings(self):
        self.close_tutorial()
        self.stop_system(summary=False)
        launch('--configure')
        self.real_quit()

    def open_dashboard(self):
        if self.dashboard is None or not self.dashboard.winfo_exists():
            from spiderpot_dashboard import Dashboard
            self.dashboard = Dashboard(self)
        self.dashboard.deiconify()
        self.dashboard.lift()

    def close_dashboard(self):
        if self.dashboard is not None and self.dashboard.winfo_exists():
            self.dashboard.destroy()
        self.dashboard = None

    def open_remote_panel(self):
        if self.remote_panel is None:
            from spiderpot_remote_panel import RemotePanel
            self.remote_panel = RemotePanel(self)
        self.remote_panel.deiconify()
        self.remote_panel.lift()

    def open_gallery(self):
        show_captures(tk.Toplevel(self.root), store=self.capture_store)

    def open_tutorial(self):
        from spiderpot_tutorial import SpiderpotTutorial
        self.open_guide(SpiderpotTutorial)

    def open_check(self):
        from spiderpot_tutorial import QuickCheck
        self.open_guide(QuickCheck)

    def open_guide(self, guide_type):
        self.close_dashboard()
        if self.tutorial is not None:
            if type(self.tutorial) is guide_type:
                if not self.is_active:
                    self.tutorial.window.lift()
                return
            self.close_tutorial()
        self.stop_system(summary=False)
        self.card.hide()
        self.tutorial = guide_type(self)
        self.update_tray_icon()

    def close_tutorial(self):
        tutorial = self.tutorial
        if tutorial is not None:
            self.tutorial = None
            tutorial.window.destroy()
            self.stop_system(summary=False)
            self.update_tray_icon()

    def camera_allowed(self):
        tutorial = self.tutorial
        return tutorial.camera_armed if tutorial is not None else self.camera_enabled

    def capture_photo(self):
        with self.session_lock:
            generation = self.session_generation
            if not self._capture_is_current(generation):
                return
            session = self.session
            if session.first_activity is None:
                session.first_activity = datetime.now()
                if self.mailer is not None and self.tutorial is None:
                    session.mail = "E-posta gönderiliyor"
                    self.mailer.send_once(generation, lambda status: self.set_mail_status(session, status))
        if not self.camera_allowed():
            return
        if not self.capture_lock.acquire(blocking=False):
            return
        if (self.capture_preview_job is not None or self.camera_failed_generation == generation
                or time.monotonic() - self.last_capture_time < self.cooldown_seconds):
            self.capture_lock.release()
            return
        self.last_capture_time = time.monotonic()
        self.capture_thread = threading.Thread(target=self._capture, args=(generation,), daemon=True)
        self.capture_thread.start()

    def set_mail_status(self, session, status):
        with self.session_lock:
            session.mail = status

    def mail_error(self, message):
        try:
            if not self.closed:
                self.root.after(0, self.tray_icon.notify, message, 'Spiderpot · E-posta')
        except (RuntimeError, tk.TclError):
            pass

    def _capture(self, generation):
        try:
            if not self._capture_is_current(generation) or not self.camera_allowed():
                return
            tutorial = self.tutorial
            index = tutorial.camera_port if tutorial is not None else self.camera_port
            result = capture_camera_frame(index, lambda: not self._capture_is_current(generation))
            if result is None:
                return
            frame, _ = result
            ret, jpeg = cv2.imencode('.jpg', frame)
            if not ret:
                raise RuntimeError('Fotoğraf hazırlanamadı.')
            photo = jpeg.tobytes()
            # Session lock also guards cancellation before persistence.
            with self.session_lock:
                if not self._capture_is_current(generation):
                    return
                capture_name = self.capture_store.save(photo)
                self.session.photos += 1
                self.session.last_photo = capture_name
            self.root.after(0, self._present_capture, generation, photo, capture_name)
        except Exception as error:
            if self._capture_is_current(generation):
                self.root.after(0, self._capture_error, generation, str(error))
        finally:
            self.capture_lock.release()

    def _capture_is_current(self, generation):
        return self.is_active and not self.closed and generation == self.session_generation

    def _present_capture(self, generation, photo, capture_name):
        if not self._capture_is_current(generation):
            return
        self._cancel_capture_preview()
        self.viewer.show_capture(photo)
        if self.tutorial is not None:
            self.tutorial.photo_captured(capture_name)
            self.tutorial.lift_active_card()
            self.update_tray_icon()
        self.capture_preview_job = self.root.after(
            CAPTURE_PREVIEW_MS, self._restore_after_capture, generation,
        )

    def _cancel_capture_preview(self):
        if self.capture_preview_job is not None:
            self.root.after_cancel(self.capture_preview_job)
            self.capture_preview_job = None

    def _restore_after_capture(self, generation):
        self.capture_preview_job = None
        if self._capture_is_current(generation):
            self._show_active_mode()

    def _capture_error(self, generation, text):
        if self._capture_is_current(generation):
            if self.tutorial is not None:
                self.tutorial.camera_failed(text)
            else:
                self.camera_failed_generation = generation
                self._camera_error(text)

    def _camera_error(self, text):
        self.update_tray_icon()
        try:
            self.tray_icon.notify(text + ' Aygıtı kontrol etmek için Ayarlar > Kamera seç / test.', 'Spiderpot')
        except Exception:
            pass

    def on_move(self, x, y):
        if self.is_active: self.capture_photo()

    def on_click(self, x, y, button, pressed):
        if self.is_active and pressed: self.capture_photo()

    def on_scroll(self, x, y, dx, dy):
        if self.is_active: self.capture_photo()

    def on_global_press(self, key, modifiers=None):
        combination = (self._modifiers() if modifiers is None else modifiers, key_vk(key))
        if combination == self.exit_hotkey:
            self.stop_system()
            return
        mode = self.mode_hotkeys.get(combination)
        if mode is not None:
            now = time.monotonic()
            if now - self.last_trigger_time >= 0.4:
                self.last_trigger_time = now
                self.start_system(mode)
            return
        if self.is_active and key_vk(key) not in MODIFIER_VKS:
            self.capture_photo()

    def start_system(self, mode):
        self.close_dashboard()
        if self.tutorial is not None:
            if self.is_active or not self.tutorial.accepts_mode(mode):
                return
        if self.pending_mode == mode:
            return
        self.cancel_countdown()
        self.card.hide()
        seconds = self.config['arming_seconds']
        if not self.is_active and seconds:
            self.pending_mode = mode
            self.count_down(seconds)
        else:
            self.activate(mode)

    def count_down(self, seconds):
        mode = self.pending_mode
        self.countdown_job = None
        if seconds == 0:
            self.pending_mode = None
            self.card.hide()
            self.activate(mode)
            return
        self.card.countdown(seconds, shortcut_label(self.key_exit))
        self.countdown_job = self.root.after(1000, self.count_down, seconds - 1)

    def cancel_countdown(self):
        if self.pending_mode is not None:
            self.pending_mode = None
            if self.countdown_job is not None:
                self.root.after_cancel(self.countdown_job)
                self.countdown_job = None
            self.card.hide()

    def activate(self, mode):
        if not self.is_active:
            self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll, suppress=True)
            self.mouse_listener.start()
            prevent_sleep()

        # Every activation replaces the display and invalidates the preceding
        # mode's queued camera results, even if a listener is already running.
        with self.session_lock:
            self.session_generation += 1
            if not self.is_active:
                self.session = Session()
            self.is_active = True
            self.active_mode = mode
            self.last_capture_time = float('-inf')
        self._cancel_capture_preview()
        self.update_tray_icon()
        self._show_active_mode(restart=True)
        if self.tutorial is not None:
            self.tutorial.mode_started()

    def _show_active_mode(self, *, restart=False):
        if self.active_mode == 'invisible':
            # Leave the live desktop visible by withdrawing all display windows.
            self.viewer.hide()
        else:
            self.viewer.show_mode(mode_spider=(self.active_mode=='spider'), restart=restart)
        if self.tutorial is not None:
            self.tutorial.lift_active_card()

    def stop_system(self, *, summary=True):
        self.cancel_countdown()
        if not self.is_active: return
        with self.session_lock:
            self.is_active = False
            self.session_generation += 1
            session = self.session
            detail = session.detail(time.monotonic())
        self.active_mode = None
        self._cancel_capture_preview()
        self.update_tray_icon()
        self.viewer.hide()
        
        allow_sleep()

        if self.mouse_listener:
            try: self.mouse_listener.stop()
            except: pass
        if self.tutorial is not None:
            self.tutorial.mode_stopped()
        elif summary:
            self.last_summary = detail
            self.close_dashboard()
            photo = session.last_photo
            def open_photo():
                self.card.hide()
                show_captures(tk.Toplevel(self.root), initial_capture=photo, store=self.capture_store)
            self.card.show("Oturum özeti", detail, milliseconds=5000, open_photo=open_photo if photo else None)
        
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
        if self.remote_panel is not None:
            self.remote_panel.stop()
        allow_sleep()
        self.close_tutorial()
        self.stop_system(summary=False)
        self.card.hide()
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
