"""Windows dashboard and capture/input adapters for the direct-access beta."""

import ctypes
import io
import ipaddress
from queue import Empty, SimpleQueue
import socket
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import ImageGrab, ImageTk
import psutil
import qrcode

from spiderpot_remote import DirectHost, PORT, checked_host, encode_pairing
from spiderpot_router import RouterMapping
from spiderpot_support import crypt, data_dir, resource


def available_hosts(supports_ipv6):
    public = []
    local = []
    stats = psutil.net_if_stats()
    for interface, entries in psutil.net_if_addrs().items():
        if interface not in stats or not stats[interface].isup:
            continue
        for entry in entries:
            if entry.family != socket.AF_INET and not (supports_ipv6 and entry.family == socket.AF_INET6):
                continue
            address = ipaddress.ip_address(entry.address.split("%")[0])
            if address.is_loopback or address.is_link_local or address.is_multicast or address.is_unspecified:
                continue
            if address.is_global and not address.is_reserved:
                public.append(str(address))
            elif address.version == 4:
                local.append(str(address))
    return list(dict.fromkeys(public)), list(dict.fromkeys(local))


class RemotePanel(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.host = None
        self.badge = None
        self.qr_expiry = None
        self.badge_timer = None
        self.image = None
        self.mapping = None
        self.mapping_job = None
        self.mapping_timer = None
        self.title("Spiderpot · Telefon eşleştir")
        self.iconbitmap(str(resource("Assets/spiderpot.ico")))
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.hide)
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="iPhone ile doğrudan bağlantı", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(body, text="Önce erişimi aç, ardından QR kodunu Spiderpot iPhone uygulamasında okut.",
                  wraplength=420).pack(anchor="w", pady=(4, 14))
        ttk.Label(body, text="Dış bağlantı adresi (isteğe bağlı)").pack(anchor="w")
        self.external = ttk.Entry(body, width=55)
        self.external.pack(fill="x", pady=(3, 5))
        ttk.Label(body, text=f"Mobil veri için erişilebilir IP veya DNS adı · TCP {PORT}", foreground="#505865").pack(anchor="w")
        row = ttk.Frame(body)
        row.pack(fill="x", pady=12)
        self.toggle = ttk.Button(row, text="Erişimi aç", command=self.toggle_host)
        self.toggle.pack(side="left")
        self.pair = ttk.Button(row, text="QR oluştur", command=self.make_qr, state="disabled")
        self.pair.pack(side="left", padx=6)
        self.remove = ttk.Button(row, text="Telefonu kaldır", command=self.forget, state="disabled")
        self.remove.pack(side="left")
        self.internet = ttk.Button(body, text="Ev modeminde 15 dk dış erişim aç",
                                   command=self.open_internet, state="disabled")
        self.internet.pack(anchor="w", pady=(0, 8))
        self.control = tk.BooleanVar(self, False)
        self.control_option = ttk.Checkbutton(body, text="Eşleştirilen telefona fare ve klavye kontrolü ver",
                                              variable=self.control, command=self.update_control, state="disabled")
        self.control_option.pack(anchor="w")
        self.qr = ttk.Label(body, anchor="center")
        self.qr.pack(fill="x")
        self.status = ttk.Label(body, text="Erişim kapalı", wraplength=420)
        self.status.pack(anchor="w", pady=(12, 0))

    def hide(self):
        self.clear_qr()
        self.withdraw()

    def toggle_host(self):
        if self.host is not None:
            self.stop()
            return
        try:
            self.host = DirectHost(data_dir() / "direct-remote", crypt, self.capture, self.input_event)
        except (OSError, ValueError) as error:
            messagebox.showerror("Spiderpot", f"Uzaktan erişim açılamadı.\n{error}", parent=self)
            return
        self.toggle.configure(text="Erişimi kapat")
        for widget in (self.pair, self.remove, self.control_option):
            widget.configure(state="normal")
        if self.mapping_job is None:
            self.internet.configure(state="normal")
        self.status.configure(text=f"Erişim açık · TCP {PORT}")
        self.show_badge()

    def show_badge(self):
        self.badge = tk.Toplevel(self.app.root, bg="#101721")
        self.badge.title("Spiderpot · Uzaktan erişim")
        self.badge.attributes("-topmost", True)
        self.badge.resizable(False, False)
        self.badge.protocol("WM_DELETE_WINDOW", self.stop)
        self.badge.geometry("+24+74")
        row = tk.Frame(self.badge, bg="#101721", padx=12, pady=8)
        row.pack()
        self.badge_text = tk.Label(row, bg="#101721", fg="white", font=("Segoe UI", 10, "bold"))
        self.badge_text.pack(side="left", padx=(0, 10))
        ttk.Button(row, text="Durdur", command=self.stop).pack(side="right")
        self.refresh_badge()

    def refresh_badge(self):
        if self.host is None:
            return
        if self.host.connected:
            text = "Telefon bağlı · " + ("Kontrol açık" if self.control.get() else "Ekran paylaşımı")
        else:
            text = "Telefon bağlantısı bekleniyor"
        self.badge_text.configure(text=text)
        self.badge_timer = self.after(400, self.refresh_badge)

    def clear_qr(self):
        if self.qr_expiry is not None:
            self.after_cancel(self.qr_expiry)
            self.qr_expiry = None
        if self.host is not None:
            self.host.cancel_pairing()
        self.qr.configure(image="")
        self.image = None

    def make_qr(self):
        if self.host is None:
            return
        try:
            outside = checked_host(self.external.get())
        except ValueError as error:
            messagebox.showwarning("Spiderpot", str(error), parent=self)
            return
        public, local = available_hosts(self.host.supports_ipv6)
        mapped = [self.mapping.address] if self.mapping else []
        addresses = list(dict.fromkeys(([outside] if outside else []) + mapped + public + local))[:8]
        if not addresses:
            self.status.configure(text="Ağ adresi bulunamadı.")
            return
        self.clear_qr()
        local_only = not (outside or mapped or public)
        payload = encode_pairing(addresses, self.host.port, socket.gethostname(), self.host.pin,
                                 self.host.pairing_code(), local_only=local_only)
        bitmap = qrcode.make(payload, box_size=4, border=4).convert("RGB")
        self.image = ImageTk.PhotoImage(bitmap, master=self)
        self.qr.configure(image=self.image)
        network = "Bu QR yerel ağ için. Mobil veri için dış erişim aç." if local_only else (
            "Dış adres QR’a eklendi. Mobil veriden erişim iPhone’da sınanır."
        )
        self.status.configure(text=f"QR kodunu 2 dakika içinde iPhone ile okut. {network}")
        self.qr_expiry = self.after(120000, self.expire_qr)

    def open_internet(self):
        if self.host is None or self.mapping_job is not None or self.mapping is not None:
            return
        if not messagebox.askyesno("Spiderpot · Dış erişim",
                                   f"Ev modeminde TCP {self.host.port} için en fazla 15 dakikalık "
                                   "UPnP yönlendirmesi açılsın mı? Durdur düğmesi erişimi kapatır.",
                                   parent=self):
            return
        public, local = available_hosts(False)
        port = self.host.port
        cancelled = threading.Event()
        result = SimpleQueue()
        self.mapping_job = cancelled
        self.internet.configure(state="disabled")
        self.status.configure(text="Ev modemi ve WAN adresi denetleniyor…")

        def work():
            try:
                mapping = RouterMapping.open(port, public + local, cancelled)
                if mapping is not None and cancelled.is_set():
                    mapping.close()
                    mapping = None
                result.put((mapping, ""))
            except ValueError as error:
                result.put((None, str(error)))
            except Exception:
                result.put((None, "Modem UPnP isteğine yanıt vermedi veya yönlendirmeyi reddetti."))

        def finish():
            try:
                mapping, problem = result.get_nowait()
            except Empty:
                self.after(100, finish)
                return
            self.mapping_job = None
            if cancelled.is_set() or self.host is None:
                if mapping is not None:
                    self.release_mapping(mapping)
                if self.host is not None:
                    self.internet.configure(state="normal")
                return
            if mapping is None:
                self.status.configure(text=problem or "Modemde dış erişim açılamadı.")
                self.internet.configure(state="normal")
                return
            self.mapping = mapping
            self.mapping_timer = self.after(max(0, int((mapping.expires_at - time.monotonic()) * 1000)),
                                            self.expire_mapping)
            self.make_qr()

        threading.Thread(target=work, daemon=True).start()
        self.after(100, finish)

    @staticmethod
    def release_mapping(mapping):
        def release():
            try:
                mapping.close()
            except Exception:
                pass  # The router lease will expire even when it is unreachable.

        threading.Thread(target=release, daemon=True).start()

    def expire_mapping(self):
        self.mapping_timer = None
        self.stop()
        self.status.configure(text="Dış erişim süresi doldu. Yeniden başlatmak için Erişimi aç.")

    def expire_qr(self):
        self.qr_expiry = None
        self.clear_qr()
        self.status.configure(text="QR süresi doldu. Gerekirse yeni bir kod oluştur.")

    def forget(self):
        self.host.forget_phone()
        self.clear_qr()
        self.status.configure(text="Telefon eşleşmesi kaldırıldı.")

    def update_control(self):
        if self.host is not None:
            self.host.set_control(self.control.get())

    def stop(self):
        self.clear_qr()
        if self.mapping_job is not None:
            self.mapping_job.set()
        if self.mapping_timer is not None:
            self.after_cancel(self.mapping_timer)
            self.mapping_timer = None
        if self.mapping is not None:
            self.release_mapping(self.mapping)
            self.mapping = None
        if self.host is not None:
            self.host.close()
            self.host = None
        if self.badge_timer is not None:
            self.after_cancel(self.badge_timer)
            self.badge_timer = None
        if self.badge is not None:
            self.badge.destroy()
            self.badge = None
        self.control.set(False)
        self.toggle.configure(text="Erişimi aç")
        for widget in (self.pair, self.remove, self.control_option, self.internet):
            widget.configure(state="disabled")
        self.status.configure(text="Erişim kapalı")

    def capture(self):
        if self.app.is_active or self.app.pending_mode:
            return b""
        try:
            with ImageGrab.grab(all_screens=False) as screenshot:
                screenshot.thumbnail((1280, 800))
                image = io.BytesIO()
                screenshot.save(image, format="JPEG", quality=67)
                return image.getvalue()
        except OSError:
            return b""

    def input_event(self, message):
        if self.app.is_active or self.app.pending_mode:
            return False
        from pynput import keyboard, mouse
        action = message.get("action")
        if action in ("move", "click", "right-click"):
            x, y = message.get("x"), message.get("y")
            if type(x) not in (int, float) or type(y) not in (int, float) or not (0 <= x <= 1 and 0 <= y <= 1):
                return False
            metrics = ctypes.windll.user32.GetSystemMetrics
            pointer = mouse.Controller()
            pointer.position = (round(x * (metrics(0) - 1)), round(y * (metrics(1) - 1)))
            if action != "move":
                pointer.click(mouse.Button.left if action == "click" else mouse.Button.right)
            return True
        if action == "text":
            value = message.get("text")
            if isinstance(value, str) and 0 < len(value) <= 200 and value.isprintable():
                try:
                    keyboard.Controller().type(value)
                except keyboard.Controller.InvalidCharacterException:
                    return False
                return True
        if action in ("enter", "backspace", "escape", "tab", "left", "right", "up", "down"):
            key = getattr(keyboard.Key, "esc" if action == "escape" else action)
            keyboard.Controller().tap(key)
            return True
        return False
