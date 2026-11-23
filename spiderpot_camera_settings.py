"""User-initiated camera discovery and an unsaved still preview."""
import tkinter as tk
from tkinter import ttk
from queue import Empty, SimpleQueue
from threading import Event, Thread

from PIL import Image, ImageTk
import cv2

from camera_tools import capture_camera_frame, scan_cameras


class CameraSettings:
    def __init__(self, parent, current, on_select):
        self.window = tk.Toplevel(parent)
        self.window.title("Spiderpot · Kamera aygıtı")
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.cancelled = Event()
        self.results = SimpleQueue()
        self.on_select = on_select
        self.poll_job = None
        self.photo = None
        self.devices = {current: f"Kamera {current} · kayıtlı aygıt"}
        body = ttk.Frame(self.window, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Kamerayı seçin ve deneyin", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(body, wraplength=540, justify="left", text="Tara ve Test Et düğmeleri kamerayı kısa süre açabilir. "
                  "Önizleme kareleri ekranda gösterilir ve kaydedilmez.").pack(anchor="w", pady=(6, 12))
        actions = ttk.Frame(body)
        actions.pack(fill="x")
        self.select = ttk.Combobox(actions, state="readonly", width=36)
        self.select.pack(side="left", padx=(0, 8))
        self.set_devices(self.devices)
        self.scan = ttk.Button(actions, text="Kameraları Tara", command=lambda: self.run("scan"))
        self.scan.pack(side="left", padx=(0, 8))
        self.test = ttk.Button(actions, text="Test Et", command=lambda: self.run("test"))
        self.test.pack(side="left")
        self.status = ttk.Label(body, wraplength=540, justify="left")
        self.status.pack(anchor="w", pady=10)
        self.preview = ttk.Label(body, anchor="center")
        self.preview.pack(fill="both", expand=True)
        self.use = ttk.Button(body, text="Bu kamerayı seç", command=self.confirm)
        self.use.pack(anchor="e", pady=(12, 0))
        self.window.grab_set()

    def set_devices(self, devices):
        self.devices = devices
        self.select.configure(values=list(devices.values()))
        self.select.current(0)

    def run(self, action):
        if self.poll_job is not None:
            return
        index = list(self.devices)[self.select.current()]
        self.status.configure(text="Kameralar taranıyor…" if action == "scan" else "Kamera açılıyor…")
        self.preview.configure(image="")
        self.photo = None
        for button in (self.scan, self.test, self.use):
            button.state(["disabled"])
        self.select.configure(state="disabled")
        self.cancelled.clear()

        def worker():
            try:
                result = (scan_cameras(self.cancelled.is_set) if action == "scan" else
                          capture_camera_frame(index, self.cancelled.is_set))
                self.results.put((action, result, ""))
            except Exception as error:
                self.results.put((action, None, str(error)))

        Thread(target=worker, daemon=True).start()
        self.poll_job = self.window.after(60, self.poll)

    def poll(self):
        try:
            action, result, error = self.results.get_nowait()
        except Empty:
            self.poll_job = self.window.after(60, self.poll)
            return
        self.poll_job = None
        for button in (self.scan, self.test, self.use):
            button.state(["!disabled"])
        self.select.configure(state="readonly")
        if error:
            self.status.configure(text=error)
        elif action == "scan":
            if result:
                self.set_devices(result)
                self.status.configure(text=f"{len(result)} çalışan kamera bulundu.")
            else:
                self.status.configure(text="Çalışan kamera bulunamadı. Windows kamera izinlerini kontrol edin.")
        elif result is not None:
            frame, backend = result
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image.thumbnail((520, 320), Image.Resampling.LANCZOS)
            self.photo = ImageTk.PhotoImage(image, master=self.window)
            self.preview.configure(image=self.photo)
            self.status.configure(text=f"Kamera çalışıyor · {backend} · Bu kare kaydedilmedi.")

    def confirm(self):
        self.on_select(list(self.devices)[self.select.current()])
        self.close()

    def close(self):
        self.cancelled.set()
        if self.poll_job is not None:
            self.window.after_cancel(self.poll_job)
        self.window.destroy()
