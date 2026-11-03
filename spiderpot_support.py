"""Store packaging, local settings, circular branding and encrypted photographs."""
import asyncio
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import uuid

from PIL import Image, ImageDraw

VERSION = "1.0.1"
CAMERA_NOTICE = (
    "Kamera seçeneği açıkken, başlattığınız tuzakta fare veya klavye etkinliği olduğunda fotoğraf çekilir. "
    "Üç modda da kamera kullanılabilir; tuzak ekranına ek bir bildirim bandı eklenmez. Mikrofon ve video kaydı yoktur.\n\n"
    "Fotoğraflar yalnız bu cihazda Windows hesabınıza bağlı şifrelenerek saklanır ve otomatik gönderilmez. "
    "Fotoğraflar bölümünden görüntüleyebilir, dışa aktarabilir veya silebilirsiniz. Varsayılan saklama süresi 7 gündür.\n\n"
    "Kayda girecek kişileri bilgilendirmek ve gerekli izinleri almak sizin sorumluluğunuzdadır. "
    "Kamera Windows izinleriyle engellenmişse bu izinler aşılmaz. F12 tuzağı ve çekimleri durdurur.\n\n"
    "Bu cihazda etkinlikte fotoğraf çekimini açmak istiyor musunuz?"
)


def resource(name):
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def package_family():
    size = wintypes.UINT(0)
    function = ctypes.windll.kernel32.GetCurrentPackageFamilyName
    result = function(ctypes.byref(size), None)
    if result == 15700:
        return None
    if result != 122:
        raise ctypes.WinError(result)
    buffer = ctypes.create_unicode_buffer(size.value)
    result = function(ctypes.byref(size), buffer)
    if result:
        raise ctypes.WinError(result)
    return buffer.value


def data_dir():
    override = os.environ.get("SPIDERPOT_TEST_DATA")
    if override:
        folder = Path(override)
    else:
        family = package_family()
        folder = Path(os.environ["LOCALAPPDATA"])
        folder = folder / "Packages" / family / "LocalState" / "Spiderpot" if family else folder / "Spiderpot"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def circular_icon(size=64, active=False):
    """Shared circular brand; the tray turns green while a trap is active."""
    scale = 4
    image = Image.new("RGBA", (size*scale, size*scale))
    draw = ImageDraw.Draw(image)
    def box(a, b):
        return (round(size*scale*a), round(size*scale*a), round(size*scale*b), round(size*scale*b))
    draw.ellipse(box(.06, .94), fill="#008000" if active else "#d52b38")
    draw.ellipse(box(.27, .73), outline="white", width=max(1, round(size*scale*.09)))
    return image.resize((size, size), Image.Resampling.LANCZOS)


DEFAULTS = {"key_spider": "1", "key_black": "2", "key_lock": "3", "key_exit": "f12",
            "camera_enabled": False, "camera_index": 0, "retention_days": 7,
            "auto_start": False, "wallpaper": ""}


def validate(config):
    values = {key: config.get(key, default) for key, default in DEFAULTS.items()}
    keys = [str(values[key]).strip().lower() for key in ("key_spider", "key_black", "key_lock")]
    if any(len(key) != 1 or not key.isascii() or not key.isalnum() for key in keys) or len(set(keys)) != 3:
        raise ValueError("Mod tuşları farklı tek harf veya rakam olmalıdır.")
    for name, key in zip(("key_spider", "key_black", "key_lock"), keys):
        values[name] = key
    if values["key_exit"] not in ["f"+str(i) for i in range(1, 13)] + ["esc", "end"]:
        raise ValueError("Geçersiz çıkış tuşu.")
    for field, low, high in (("camera_index", 0, 9), ("retention_days", 1, 30)):
        if type(values[field]) is not int or not low <= values[field] <= high:
            raise ValueError("Geçersiz kamera veya saklama ayarı.")
    if any(type(values[field]) is not bool for field in ("camera_enabled", "auto_start")):
        raise ValueError("Geçersiz kamera veya başlangıç seçimi.")
    if not isinstance(values["wallpaper"], str):
        raise ValueError("Geçersiz fotoğraf yolu.")
    return values


def config_path():
    return data_dir() / "settings.json"


def load_config():
    try:
        return validate(json.loads(config_path().read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        return dict(DEFAULTS)


def save_config(config, wallpaper=None):
    values = validate(config)
    if wallpaper:
        # Keep a private local copy so moving the selected source doesn't break Ctrl+1.
        with Image.open(wallpaper) as source:
            from PIL import ImageOps
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((7680, 4320), Image.Resampling.LANCZOS)
            target = data_dir() / "wallpaper.jpg"
            temporary = data_dir() / "wallpaper.tmp"
            image.save(temporary, format="JPEG", quality=95)
            temporary.replace(target)
            values["wallpaper"] = str(target)
    path = config_path()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
    return values


def command(*arguments):
    if getattr(sys, "frozen", False):
        return [sys.executable, *arguments]
    return [sys.executable, str(resource("Spiderpot.py")), *arguments]


def launch(*arguments):
    return subprocess.Popen(command(*arguments), creationflags=subprocess.CREATE_NO_WINDOW)


def set_startup(enabled):
    if package_family():
        async def change():
            from winrt.windows.applicationmodel import StartupTask, StartupTaskState
            task = await StartupTask.get_async("SpiderpotStartup")
            if enabled:
                state = await task.request_enable_async()
                if state != StartupTaskState.ENABLED:
                    raise RuntimeError("Otomatik başlatma Windows tarafından kapalı tutuluyor. Windows Ayarlar > Uygulamalar > Başlangıç bölümünden Spiderpot'u açabilirsiniz.")
            else:
                task.disable()
        asyncio.run(change())
    else:
        from spiderpot_upgrade import set_startup_target
        if getattr(sys,'frozen',False):
            set_startup_target(Path(sys.executable),enabled)
        else:
            set_startup_target(Path(sys.executable),enabled,(str(resource('Spiderpot.py')),'--startup'))


class Blob(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("data", ctypes.POINTER(ctypes.c_ubyte))]


def crypt(data, decrypt=False):
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, output = Blob(len(data), buffer), Blob()
    api = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    if decrypt:
        fn = api.CryptUnprotectData
        fn.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        ok = fn(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output))
    else:
        fn = api.CryptProtectData
        fn.argtypes = [ctypes.POINTER(Blob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
        ok = fn(ctypes.byref(source), "Spiderpot", None, None, None, 1, ctypes.byref(output))
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(output.data, output.size)
    finally:
        kernel.LocalFree(output.data)


class CaptureStore:
    def __init__(self, folder=None):
        self.folder = Path(folder) if folder else data_dir() / "captures"
        self.folder.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def save(self, jpeg):
        encrypted = crypt(jpeg)
        name = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex + ".spcap"
        with self.lock:
            (self.folder / name).write_bytes(encrypted)
        return name

    def entries(self):
        with self.lock:
            return sorted(self.folder.glob("*.spcap"), reverse=True)

    def read(self, path):
        path = Path(path).resolve()
        if path.parent != self.folder.resolve() or path.suffix != ".spcap":
            raise ValueError("Geçersiz fotoğraf yolu.")
        with self.lock:
            return crypt(path.read_bytes(), decrypt=True)

    def delete(self, path):
        path = Path(path).resolve()
        if path.parent != self.folder.resolve() or path.suffix != ".spcap":
            raise ValueError("Geçersiz fotoğraf yolu.")
        with self.lock:
            path.unlink(missing_ok=True)

    def prune(self, days):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for path in self.entries():
            if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
                self.delete(path)


def privacy_text():
    return resource("store/privacy-tr.txt").read_text(encoding="utf-8")


def show_privacy(parent):
    import tkinter as tk
    from tkinter import ttk
    window = tk.Toplevel(parent)
    window.title("Spiderpot · Gizlilik")
    window.geometry("820x650")
    text = tk.Text(window, wrap="word", padx=20, pady=20, font=("Segoe UI", 10))
    scrollbar = ttk.Scrollbar(window, command=text.yview)
    text.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    text.pack(fill="both", expand=True)
    text.insert("1.0", privacy_text())
    text.configure(state="disabled")


def show_captures(root):
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from PIL import ImageTk
    root.title("Spiderpot · Fotoğraflar")
    root.iconbitmap(str(resource("Assets/spiderpot.ico")))
    root.geometry("980x720")
    store = CaptureStore()
    store.prune(load_config()["retention_days"])
    ttk.Label(root, text="Şifreli fotoğraflar · Yalnız bu Windows hesabıyla açılır", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=18)
    body = ttk.Frame(root, padding=18)
    body.pack(fill="both", expand=True)
    listing = tk.Listbox(body, width=34, font=("Segoe UI", 10), exportselection=False)
    listing.pack(side="left", fill="y", padx=(0, 15))
    preview = ttk.Label(body, text="Henüz fotoğraf yok.", anchor="center")
    preview.pack(side="left", fill="both", expand=True)
    paths = []
    def reload():
        nonlocal paths
        paths = store.entries()
        listing.delete(0, "end")
        for path in paths:
            utc = datetime.strptime(path.name[:15], "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
            listing.insert("end", utc.astimezone().strftime("%d.%m.%Y %H:%M:%S"))
        preview.configure(image="", text="Bir fotoğraf seçin." if paths else "Henüz fotoğraf yok.")
        preview.image = None
    def selected():
        choice = listing.curselection()
        return paths[choice[0]] if choice else None
    def display(event=None):
        if not selected():
            return
        try:
            image = Image.open(io.BytesIO(store.read(selected())))
            image.thumbnail((650, 490))
            photo = ImageTk.PhotoImage(image)
            preview.configure(image=photo, text="")
            preview.image = photo
        except (OSError, ValueError) as error:
            messagebox.showerror("Fotoğraf açılamadı", str(error), parent=root)
    def export():
        path = selected()
        if not path:
            return
        destination = filedialog.asksaveasfilename(parent=root, title="JPEG dışa aktar · Şifrelenmez", defaultextension=".jpg", initialfile=path.stem+".jpg", filetypes=[("JPEG", "*.jpg")])
        if destination:
            try:
                Path(destination).write_bytes(store.read(path))
            except OSError as error:
                messagebox.showerror("Dışa aktarılamadı", str(error), parent=root)
    def delete(all_photos=False):
        targets = paths[:] if all_photos else ([selected()] if selected() else [])
        if targets and messagebox.askyesno("Fotoğrafları sil", f"{len(targets)} fotoğraf kalıcı olarak silinsin mi?", parent=root, default="no"):
            for path in targets:
                store.delete(path)
            reload()
    listing.bind("<<ListboxSelect>>", display)
    actions = ttk.Frame(root, padding=18)
    actions.pack(fill="x")
    for name, callback in (("Yenile", reload), ("Dışa aktar…", export), ("Seçiliyi sil", delete), ("Tümünü sil", lambda: delete(True)), ("Gizlilik", lambda: show_privacy(root))):
        ttk.Button(actions, text=name, command=callback).pack(side="left", padx=(0, 9))
    ttk.Label(root, text="Dışa aktarılan JPEG şifrelenmez; uygulamanın otomatik temizliğine dahil değildir.").pack(anchor="w", padx=18, pady=(0, 18))
    reload()
