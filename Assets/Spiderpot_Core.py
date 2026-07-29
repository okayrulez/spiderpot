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
import tempfile
from PIL import Image, ImageTk, ImageDraw, ImageFont

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
    SLIDESHOW_SECONDS = 5
    SLIDESHOW_FADE_STEPS = 10
    SLIDESHOW_FADE_DELAY_MS = 45

    def __init__(self, parent):
        self.parent = parent
        self.windows = []
        self.labels = []
        self.photo_images = []
        self.monitors = []
        self.is_visible = False
        self.slideshow_paths = []
        self.slideshow_index = 0
        self.slideshow_images = []
        self.slideshow_current_pil = []
        self.slideshow_job = None
        self.slideshow_generation = 0
        
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.image_path = os.path.join(base_dir, "spiderman3.jpg")
        self.slideshow_dir = os.path.join(base_dir, "Slayt_Gorselleri")
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
        if mode_spider:
            return self.start_slideshow()

        self.stop_slideshow()
        self.ensure_current()
        for win, lbl in zip(self.windows, self.labels):
            lbl.config(image='', text="")
            win.deiconify()
        self.is_visible = True

    def show_capture(self, image_path, message="YAKALANDIN!"):
        """Çekilen kamera karesini mesajla birlikte bütün ekranlarda göster."""
        self.stop_slideshow()
        self.ensure_current()
        try:
            captured = Image.open(image_path).convert("RGB")
        except Exception:
            return False

        capture_images = []
        for win, lbl, mon in zip(self.windows, self.labels, self.monitors):
            img_ratio = captured.width / captured.height
            mon_ratio = mon.width / mon.height
            if img_ratio > mon_ratio:
                new_h = mon.height
                new_w = int(new_h * img_ratio)
            else:
                new_w = mon.width
                new_h = int(new_w / img_ratio)

            resized = captured.resize((max(new_w, 1), max(new_h, 1)), Image.Resampling.LANCZOS)
            left = max((new_w - mon.width) // 2, 0)
            top = max((new_h - mon.height) // 2, 0)
            screen_image = resized.crop((left, top, left + mon.width, top + mon.height)).convert("RGBA")

            overlay = Image.new("RGBA", screen_image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            font_size = max(44, int(mon.height * 0.10))
            try:
                font = ImageFont.truetype("arialbd.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), message, font=font, stroke_width=2)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            padding_x = max(30, int(mon.width * 0.025))
            padding_y = max(20, int(mon.height * 0.02))
            x = (mon.width - text_w) // 2
            y = max(30, int(mon.height * 0.08))
            banner = (
                x - padding_x,
                y - padding_y,
                x + text_w + padding_x,
                y + text_h + padding_y,
            )
            draw.rounded_rectangle(
                banner,
                radius=max(18, int(font_size * 0.25)),
                fill=(0, 0, 0, 190),
                outline=(255, 35, 35, 255),
                width=max(4, int(font_size * 0.06)),
            )
            draw.text(
                (x, y),
                message,
                font=font,
                fill=(255, 45, 45, 255),
                stroke_width=2,
                stroke_fill=(255, 255, 255, 255),
            )

            composed = Image.alpha_composite(screen_image, overlay).convert("RGB")
            photo = ImageTk.PhotoImage(composed)
            capture_images.append(photo)
            lbl.config(image=photo, text="")
            win.deiconify()

        # Tk PhotoImage nesneleri referans tutulmazsa ekrandan silinir.
        self.capture_images = capture_images
        self.is_visible = True
        return True

    def _cover_for_monitor(self, image, mon):
        img_ratio = image.width / image.height
        mon_ratio = mon.width / mon.height
        if img_ratio > mon_ratio:
            new_h = mon.height
            new_w = int(new_h * img_ratio)
        else:
            new_w = mon.width
            new_h = int(new_w / img_ratio)

        resized = image.resize((max(new_w, 1), max(new_h, 1)), Image.Resampling.LANCZOS)
        left = max((new_w - mon.width) // 2, 0)
        top = max((new_h - mon.height) // 2, 0)
        return resized.crop((left, top, left + mon.width, top + mon.height)).convert("RGB")

    def _load_slideshow_paths(self):
        supported = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        paths = []

        # Kurulum ekranında seçilen ana duvar kâğıdı her zaman ilk görseldir.
        if (
            os.path.isfile(self.image_path)
            and os.path.splitext(self.image_path)[1].lower() in supported
        ):
            paths.append(self.image_path)

        try:
            names = sorted(os.listdir(self.slideshow_dir), key=str.casefold)
        except Exception:
            names = []

        main_name = os.path.basename(self.image_path).casefold()
        for name in names:
            path = os.path.join(self.slideshow_dir, name)
            if (
                os.path.splitext(name)[1].lower() in supported
                and os.path.isfile(path)
                and name.casefold() != main_name
            ):
                paths.append(path)
        return paths

    def start_slideshow(self):
        self.stop_slideshow()
        self.ensure_current()
        self.slideshow_paths = self._load_slideshow_paths()
        self.slideshow_index = 0
        self.slideshow_current_pil = []
        self.slideshow_generation += 1
        generation = self.slideshow_generation

        if not self.slideshow_paths:
            for win, lbl in zip(self.windows, self.labels):
                lbl.config(
                    image="",
                    text="Duvar kâğıdı bulunamadı",
                    fg="white",
                    bg="black",
                    font=("Segoe UI", 24, "bold"),
                    justify="center",
                )
                win.deiconify()
            self.is_visible = True
            return False

        self._show_slideshow_image(generation, fade=False)
        return True

    def _show_slideshow_image(self, generation, fade=True):
        if generation != self.slideshow_generation or not self.slideshow_paths:
            return

        path = self.slideshow_paths[self.slideshow_index]
        try:
            with Image.open(path) as source:
                source = source.convert("RGB")
                next_images = [
                    self._cover_for_monitor(source, mon)
                    for mon in self.monitors
                ]
        except Exception:
            self.slideshow_index = (self.slideshow_index + 1) % len(self.slideshow_paths)
            self.slideshow_job = self.parent.after(
                100,
                lambda: self._show_slideshow_image(generation, fade=False),
            )
            return

        if fade and len(self.slideshow_current_pil) == len(next_images):
            self._fade_slideshow(generation, self.slideshow_current_pil, next_images, 1)
        else:
            self._set_slideshow_images(next_images)
            self.slideshow_current_pil = next_images
            # Tek görsel varsa sabit duvar kâğıdı olarak ekranda kalır.
            if len(self.slideshow_paths) > 1:
                self.slideshow_job = self.parent.after(
                    int(self.SLIDESHOW_SECONDS * 1000),
                    lambda: self._advance_slideshow(generation),
                )

    def _set_slideshow_images(self, pil_images):
        photos = []
        for win, lbl, image in zip(self.windows, self.labels, pil_images):
            photo = ImageTk.PhotoImage(image)
            photos.append(photo)
            lbl.config(image=photo, text="", bg="black")
            win.deiconify()
        self.slideshow_images = photos
        self.is_visible = True

    def _fade_slideshow(self, generation, old_images, next_images, step):
        if generation != self.slideshow_generation:
            return

        alpha = step / self.SLIDESHOW_FADE_STEPS
        blended = [
            Image.blend(old, new, alpha)
            for old, new in zip(old_images, next_images)
        ]
        self._set_slideshow_images(blended)

        if step < self.SLIDESHOW_FADE_STEPS:
            self.slideshow_job = self.parent.after(
                self.SLIDESHOW_FADE_DELAY_MS,
                lambda: self._fade_slideshow(
                    generation,
                    old_images,
                    next_images,
                    step + 1,
                ),
            )
        else:
            self.slideshow_current_pil = next_images
            if len(self.slideshow_paths) > 1:
                self.slideshow_job = self.parent.after(
                    int(self.SLIDESHOW_SECONDS * 1000),
                    lambda: self._advance_slideshow(generation),
                )

    def _advance_slideshow(self, generation):
        if generation != self.slideshow_generation or not self.slideshow_paths:
            return
        self.slideshow_index = (self.slideshow_index + 1) % len(self.slideshow_paths)
        self._show_slideshow_image(generation, fade=True)

    def stop_slideshow(self):
        self.slideshow_generation += 1
        if self.slideshow_job is not None:
            try:
                self.parent.after_cancel(self.slideshow_job)
            except Exception:
                pass
            self.slideshow_job = None
        self.slideshow_images = []
        self.slideshow_current_pil = []

    def hide(self):
        self.stop_slideshow()
        for win in self.windows:
            try: win.withdraw()
            except: pass
        self.is_visible = False

import pystray
from pystray import MenuItem as TrayItem

class SpiderpotApp:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        
        self.is_active = False
        self.active_mode = None
        
        self.cap = None
        self.last_capture_time = 0
        self.cooldown_seconds = 3
        self.capture_feedback_ms = 3000
        self.capture_feedback_job = None
        self.camera_port = 0
        self.camera_ports_to_try = [0, 1, 2, 3, 4]
        self.capture_lock = threading.Lock()
        
        desktop_path = get_desktop_path()
        app_dir = (
            os.path.dirname(sys.executable)
            if getattr(sys, 'frozen', False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        desktop_save_folder = os.path.join(desktop_path, "Spiderpot_Yakalananlar")
        app_save_folder = os.path.join(app_dir, "Spiderpot_Yakalananlar")
        temp_save_folder = os.path.join(tempfile.gettempdir(), "Spiderpot_Yakalananlar")
        self.save_folders = []
        for folder in [desktop_save_folder, app_save_folder, temp_save_folder]:
            if os.path.normcase(os.path.abspath(folder)) not in {
                os.path.normcase(os.path.abspath(existing))
                for existing in self.save_folders
            }:
                self.save_folders.append(folder)
        self.save_folder = self.save_folders[0]
        self.log_paths = [
            os.path.join(folder, "Spiderpot_Log.txt")
            for folder in self.save_folders
        ]
        self.log_path = self.log_paths[0]
        for folder in self.save_folders:
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception:
                pass

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
        
        # Bilgisayarı açık tutma protokolü
        prevent_sleep()

    def _init_camera(self):
        try:
            with self.capture_lock:
                self._ensure_camera_locked()
        except Exception as e:
            self._log_error("Kamera hazirlanamadi.", error=e)

    def _log_error(self, message, **details):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        detail_text = ""
        if details:
            detail_parts = []
            for key, value in details.items():
                if isinstance(value, Exception):
                    value = f"{type(value).__name__}: {value}"
                detail_parts.append(f"{key}={value!r}")
            detail_text = " | " + " | ".join(detail_parts)

        for log_path in getattr(self, "log_paths", [self.log_path]):
            try:
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {message}{detail_text}\n")
                return
            except Exception:
                pass

    def _path_details(self, path):
        try:
            parent = os.path.dirname(path)
            return {
                "path": path,
                "parent": parent,
                "parent_exists": os.path.isdir(parent),
                "parent_writable": os.access(parent, os.W_OK) if os.path.isdir(parent) else False,
                "target_exists": os.path.exists(path),
            }
        except Exception as e:
            return {"path": path, "detail_error": f"{type(e).__name__}: {e}"}

    def _ensure_camera_locked(self):
        if self.cap is not None and self.cap.isOpened():
            return True

        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None

        ports = [self.camera_port] + [
            port for port in self.camera_ports_to_try
            if port != self.camera_port
        ]
        for port in ports:
            cap = None
            try:
                cap = cv2.VideoCapture(port, cv2.CAP_DSHOW)
                opened = cap.isOpened()
            except Exception as e:
                self._log_error("Kamera portu acilamadi.", port=port, error=e)
                opened = False

            if not opened:
                self._log_error("Kamera portu kapali.", port=port)
                try:
                    if cap is not None:
                        cap.release()
                except Exception:
                    pass
                continue

            ok = False
            last_ret = None
            for _ in range(5):
                ret, _frame = cap.read()
                last_ret = ret
                if ret:
                    ok = True
                    break

            if ok:
                self.cap = cap
                self.camera_port = port
                self._log_error("Kamera hazir.", port=port)
                return True

            self._log_error("Kamera portu acildi ama kare vermedi.", port=port, last_ret=last_ret)
            try:
                cap.release()
            except Exception:
                pass

        self._log_error("Calisan kamera bulunamadi.", tried_ports=ports)
        return False

    def _release_camera_locked(self):
        if self.cap is None:
            return

        tmp = self.cap
        self.cap = None
        try:
            tmp.release()
            self._log_error("Kamera serbest birakildi.", camera_port=self.camera_port)
        except Exception as e:
            self._log_error("Kamera serbest birakilamadi.", camera_port=self.camera_port, error=e)

    def _save_frame(self, filepath, frame):
        try:
            ok, encoded = cv2.imencode(".jpg", frame)
            if not ok:
                self._log_error("Foto JPG encode edilemedi.", **self._path_details(filepath))
                return False
            with open(filepath, "wb") as f:
                f.write(encoded.tobytes())
            self._log_error(
                "Foto kaydedildi.",
                bytes=len(encoded),
                frame_shape=getattr(frame, "shape", None),
                **self._path_details(filepath),
            )
            return True
        except Exception as e:
            self._log_error(
                "Foto yazma hatasi.",
                error=e,
                frame_shape=getattr(frame, "shape", None),
                **self._path_details(filepath),
            )
            return False

    def _save_frame_to_available_folder(self, filename, frame):
        self._log_error(
            "Foto kayit denemesi basladi.",
            filename=filename,
            folders=self.save_folders,
            frame_shape=getattr(frame, "shape", None),
        )
        for index, folder in enumerate(self.save_folders, start=1):
            try:
                os.makedirs(folder, exist_ok=True)
            except Exception as e:
                self._log_error("Foto klasoru olusturulamadi.", folder=folder, error=e, attempt=index)
                continue

            filepath = os.path.join(folder, filename)
            self._log_error("Foto klasoru deneniyor.", attempt=index, **self._path_details(filepath))
            if self._save_frame(filepath, frame):
                if folder != self.save_folder:
                    self._log_error("Foto yedek klasore kaydedildi.", attempt=index, path=filepath)
                self.save_folder = folder
                return filepath

            self._log_error("Foto bu klasore kaydedilemedi.", attempt=index, **self._path_details(filepath))

        self._log_error("Foto hicbir klasore kaydedilemedi.", filename=filename, folders=self.save_folders)
        return None

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
        captured_path = None
        with self.capture_lock:
            current_time = time.time()
            if current_time - self.last_capture_time < self.cooldown_seconds:
                return
            self.last_capture_time = current_time

            camera_opened = False
            try:
                if self._ensure_camera_locked():
                    camera_opened = True
                    ret, frame = self.cap.read()
                    if ret:
                        self._log_error(
                            "Kameradan kare alindi.",
                            camera_port=self.camera_port,
                            frame_shape=getattr(frame, "shape", None),
                        )
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"yakalandin_{timestamp}.jpg"
                        captured_path = self._save_frame_to_available_folder(filename, frame)
                    else:
                        self._log_error("Kameradan kare okunamadi.", camera_port=self.camera_port)
            finally:
                if camera_opened:
                    self._release_camera_locked()

        if captured_path:
            self.root.after(0, lambda path=captured_path: self._show_capture_feedback(path))

    def _show_capture_feedback(self, image_path):
        if not self.is_active:
            return
        if not self.viewer.show_capture(image_path):
            self._log_error(f"Yakalandin ekrani gosterilemedi: {image_path}")
            return

        if self.capture_feedback_job is not None:
            try:
                self.root.after_cancel(self.capture_feedback_job)
            except Exception:
                pass
        self.capture_feedback_job = self.root.after(
            self.capture_feedback_ms,
            self._restore_active_mode,
        )

    def _restore_active_mode(self):
        self.capture_feedback_job = None
        if not self.is_active:
            self.viewer.hide()
        elif self.active_mode == 'invisible':
            self.viewer.hide()
        else:
            self.viewer.show_mode(mode_spider=(self.active_mode == 'spider'))

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
        if self.capture_feedback_job is not None:
            try:
                self.root.after_cancel(self.capture_feedback_job)
            except Exception:
                pass
            self.capture_feedback_job = None
        self.update_tray_icon()
        self.viewer.hide()
        
        # Asenkron kapat ki anında tepki versin
        threading.Thread(target=set_antigravity_mode, args=(False,), daemon=True).start()

        if self.mouse_listener:
            try: self.mouse_listener.stop()
            except: pass
        
        # Kamerayı asenkron kapat ki ışık sönsün ve program kilitlenmesin
        def _release_cam():
            with self.capture_lock:
                self._release_camera_locked()
        threading.Thread(target=_release_cam, daemon=True).start()

    def lock_screen(self):
        ctypes.windll.user32.LockWorkStation()

    def real_quit(self):
        allow_sleep()
        self.stop_system()
        if self.input_listener:
            try: self.input_listener.stop()
            except: pass
        if self.mouse_listener:
            try: self.mouse_listener.stop()
            except: pass
        if hasattr(self, 'tray_icon') and self.tray_icon:
            try: self.tray_icon.stop()
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
