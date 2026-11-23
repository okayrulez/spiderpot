"""Transient desktop cards and in-memory session totals."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from datetime import datetime
import time
import tkinter as tk

from PIL import ImageTk
from spiderpot_support import circular_icon


@dataclass
class Session:
    started: float = field(default_factory=time.monotonic)
    first_activity: datetime | None = None
    photos: int = 0
    last_photo: str | None = None
    mail: str = ""

    def detail(self, ended):
        seconds = max(0, int(ended - self.started))
        minutes, seconds = divmod(seconds, 60)
        duration = f"{minutes} dk {seconds} sn" if minutes else f"{seconds} sn"
        activity = (f"İlk etkinlik {self.first_activity:%H.%M.%S}" if self.first_activity
                    else "Klavye veya fare etkinliği algılanmadı")
        lines = [f"{duration}  ·  {activity}"]
        if self.photos:
            lines.append(f"{self.photos} yerel fotoğraf")
        if self.mail:
            lines.append(self.mail)
        return "\n".join(lines)


class DesktopCard:
    def __init__(self, root):
        self.root = root
        self.window = None
        self.timer = None
        self.seconds_label = None

    def hide(self):
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.window is not None:
            self.window.destroy()
            self.window = None
            self.seconds_label = None

    def countdown(self, seconds, exit_key):
        if self.seconds_label is not None:
            self.seconds_label.configure(text=f"{seconds} sn")
            return
        self.show("Mod başlatılıyor", f"İptal  ·  {exit_key}", seconds=seconds)

    def show(self, title, detail, *, milliseconds=None, open_photo=None, seconds=None):
        self.hide()
        surface = "#202129"
        window = self.window = tk.Toplevel(self.root, bg=surface)
        window.withdraw()
        window.overrideredirect(True)
        window.attributes("-topmost", True)
        scale = float(window.tk.call("tk", "scaling")) * .75
        def px(value):
            return max(1, round(value * scale))
        body = tk.Frame(window, bg=surface, padx=px(12), pady=px(6))
        body.pack(fill="both", expand=True)
        window.logo = ImageTk.PhotoImage(circular_icon(px(18)), master=window)
        tk.Label(body, image=window.logo, bg=surface, bd=0).grid(row=0, column=0, rowspan=2, padx=(0, px(8)))
        tk.Label(body, text=title, bg=surface, fg="#FAF8FA", font=("Segoe UI", 10, "bold"),
                 bd=0, padx=0, pady=0).grid(row=0, column=1, sticky="w")
        tk.Label(body, text=detail, bg=surface, fg="#C2BDC8", justify="left", bd=0, padx=0, pady=0,
                 wraplength=px(250), font=("Segoe UI", 9)).grid(row=1, column=1, sticky="w")
        if seconds is not None:
            self.seconds_label = tk.Label(body, text=f"{seconds} sn", width=5, bg=surface, fg="#FFC0C9",
                                         font=("Segoe UI", 11, "bold"), bd=0, padx=0, pady=0)
            self.seconds_label.grid(row=0, column=2, rowspan=2, padx=(px(8), 0))
        if open_photo:
            tk.Button(body, text="Fotoğrafı aç", command=open_photo, bd=0, bg=surface, fg="#FFC0C9",
                      activebackground=surface, activeforeground="white", font=("Segoe UI", 9, "bold"),
                      cursor="hand2", padx=0, pady=0).grid(row=2, column=1, sticky="w", pady=(2, 0))
        window.update_idletasks()
        user32 = ctypes.windll.user32
        area = wintypes.RECT()
        if not user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):
            area.right, area.bottom = window.winfo_screenwidth(), window.winfo_screenheight()
        x = max(area.left, area.right - window.winfo_reqwidth() - 16)
        y = max(area.top, area.bottom - window.winfo_reqheight() - 14)
        window.geometry(f"+{x}+{y}")
        # Keep typing focus in the user's foreground app when the card appears.
        hwnd = wintypes.HWND(int(window.frame(), 16))
        style = user32.GetWindowLongW(hwnd, -20)
        user32.SetWindowLongW(hwnd, -20, style | 0x08000000 | 0x80)
        # Win32 owns the region after SetWindowRgn succeeds. Clip both the pixels
        # and the hit area, including on systems without compositor corner styling.
        gdi = ctypes.windll.gdi32
        gdi.CreateRoundRectRgn.restype = wintypes.HANDLE
        diameter = min(px(30), window.winfo_reqheight())
        region = gdi.CreateRoundRectRgn(0, 0, window.winfo_reqwidth()+1, window.winfo_reqheight()+1,
                                        diameter, diameter)
        if region and not user32.SetWindowRgn(hwnd, wintypes.HANDLE(region), False):
            gdi.DeleteObject(wintypes.HANDLE(region))
        window.deiconify()
        if milliseconds is not None:
            self.timer = self.root.after(milliseconds, self.hide)
