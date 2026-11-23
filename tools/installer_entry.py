"""Single downloadable offline installer for the per-user Spiderpot upgrade."""
import argparse
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from queue import Empty, SimpleQueue
import tkinter as tk
from tkinter import messagebox, ttk
import zipfile

from spiderpot_upgrade import Mutex, install_bundle, install_root, legacy_startup, uninstall_bundle


def extract_payload(archive, destination):
    destination = Path(destination).resolve()
    for name in archive.namelist():
        target = (destination/name).resolve()
        if not target.is_relative_to(destination):
            raise ValueError('Geçersiz kurulum arşivi yolu.')
    archive.extractall(destination)


def uninstall(root, staged):
    executable = Path(sys.executable).resolve()
    if not staged:
        if not messagebox.askyesno(
            "Spiderpot'u kaldır", "Bu bilgisayardaki Spiderpot EXE kurulumu kaldırılsın mı? "
            "Fotoğraflarınız ve ayarlarınız korunur.", parent=root, default="no",
        ):
            return
        if executable.is_relative_to(install_root().resolve()):
            worker = Path(tempfile.mkdtemp(prefix='Spiderpot-uninstall-'))/'uninstall.exe'
            shutil.copy2(executable, worker)
            subprocess.Popen([str(worker),'--uninstall-staged'],creationflags=subprocess.CREATE_NO_WINDOW)
            return
    try:
        uninstall_bundle()
        messagebox.showinfo("Spiderpot kaldırıldı", "EXE kurulumu kaldırıldı. Fotoğraflarınız ve ayarlarınız korundu.", parent=root)
    finally:
        if staged:
            schedule_worker_cleanup(executable)


def schedule_worker_cleanup(executable):
    folder = executable.parent
    if (executable.name != 'uninstall.exe' or not folder.name.startswith('Spiderpot-uninstall-')
            or folder.parent != Path(tempfile.gettempdir()).resolve()):
        return
    path = str(executable).replace("'", "''")
    folder_path = str(folder).replace("'", "''")
    script = f"""
for ($attempt = 0; $attempt -lt 30; $attempt++) {{
    try {{
        Remove-Item -LiteralPath '{path}' -ErrorAction Stop
        Remove-Item -LiteralPath '{folder_path}' -ErrorAction SilentlyContinue
        break
    }} catch {{ Start-Sleep -Milliseconds 500 }}
}}
"""
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],
                     creationflags=subprocess.CREATE_NO_WINDOW)


def install(report):
    current = Path(os.environ['LOCALAPPDATA'])/'Spiderpot/settings.json'
    enabled = bool(legacy_startup())
    desktop = False
    if current.is_file():
        config = json.loads(current.read_text(encoding='utf-8'))
        enabled = config.get('auto_start') is True
        desktop = config.get('desktop_shortcut') is True
    bundle = Path(sys._MEIPASS)/'payload.zip'
    with tempfile.TemporaryDirectory(prefix='Spiderpot-setup-') as scratch:
        with zipfile.ZipFile(bundle) as archive:
            extract_payload(archive, scratch)
        report('Spiderpot bu bilgisayara kuruluyor…')
        return install_bundle(Path(scratch)/'Spiderpot', enabled, desktop_shortcut=desktop,
                              installer=Path(sys.executable))


def launch_app(executable, run):
    subprocess.Popen([str(executable), '--run' if run else '--setup'], creationflags=subprocess.CREATE_NO_WINDOW)


def show_installation(root, run):
    events = SimpleQueue()
    root.title('Spiderpot · Kurulum hazırlanıyor')
    root.resizable(False, False)
    body = ttk.Frame(root, padding=(26, 20))
    body.pack(fill='both', expand=True)
    ttk.Label(body, text='Spiderpot kurulumu', font=('Segoe UI', 15, 'bold')).pack(anchor='w')
    status = ttk.Label(body, text='Kurulum dosyaları açılıyor…', font=('Segoe UI', 10))
    status.pack(anchor='w', pady=(8, 14))
    bar = ttk.Progressbar(body, mode='indeterminate', length=320)
    bar.pack(fill='x')
    bar.start(18)
    root.protocol('WM_DELETE_WINDOW', lambda: root.iconify())
    root.update_idletasks()
    x = max(0, (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2)
    y = max(0, (root.winfo_screenheight() - root.winfo_reqheight()) // 2)
    root.geometry(f'+{x}+{y}')
    root.deiconify()
    root.lift()

    def work():
        try:
            executable = install(lambda text: events.put(('status', text)))
            events.put(('ready', executable))
        except Exception as error:
            events.put(('error', str(error)))

    def poll():
        try:
            kind, value = events.get_nowait()
        except Empty:
            root.after(100, poll)
            return
        if kind == 'status':
            status.configure(text=value)
            root.after(100, poll)
            return
        bar.stop()
        try:
            if kind == 'error':
                messagebox.showerror('Spiderpot işlemi tamamlanamadı', value, parent=root)
            else:
                launch_app(value, run)
        except OSError as error:
            messagebox.showerror('Spiderpot başlatılamadı', str(error), parent=root)
        root.quit()

    root.after(100, poll)
    root.after_idle(threading.Thread(target=work).start)
    root.mainloop()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet',action='store_true')
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--uninstall',action='store_true')
    parser.add_argument('--uninstall-staged',action='store_true',help=argparse.SUPPRESS)
    args = parser.parse_args()
    root = tk.Tk()
    root.withdraw()
    try:
        if args.uninstall or args.uninstall_staged:
            uninstall(root, args.uninstall_staged)
            return
        with Mutex(r'Local\Spiderpot.SetupUI.v1') as guard:
            if guard.existed:
                if not args.quiet:
                    messagebox.showinfo('Spiderpot kurulumu', 'Kurulum zaten açık.', parent=root)
                return
            if args.quiet:
                launch_app(install(lambda text: None), args.run)
            else:
                show_installation(root, args.run)
    except Exception as error:
        if not args.quiet:
            messagebox.showerror('Spiderpot işlemi tamamlanamadı',str(error),parent=root)
        raise
    finally:
        root.destroy()


if __name__=='__main__': main()
