"""Offline, packaged release entry point. Original three trap modes remain in Assets."""
import argparse
import ctypes
from ctypes import wintypes
import sys
import tkinter as tk
from tkinter import messagebox
from spiderpot_support import config_path, load_config, show_captures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--captures", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--startup", action="store_true")
    args = parser.parse_args()
    from Assets.Spiderpot_Core import set_dpi_awareness
    set_dpi_awareness()
    root = tk.Tk()
    root.withdraw()
    if args.captures:
        show_captures(root)
        root.deiconify()
        root.mainloop()
        return
    if args.configure or not config_path().is_file() or (not args.run and not args.startup):
        if args.startup:
            root.destroy()  # Startup never prompts before first-run setup.
            return
        from Spiderpot_Kurulum import SpiderpotBuilderApp
        SpiderpotBuilderApp(root)
        root.deiconify()
        root.mainloop()
        return
    from spiderpot_upgrade import RuntimeLock
    runtime = RuntimeLock()
    if runtime.already_running:
        if not args.startup:
            messagebox.showinfo("Spiderpot", "Spiderpot zaten açık. Sağ alttaki kırmızı daire simgesinden ayarlara ulaşabilirsiniz.", parent=root)
        runtime.close()
        root.destroy()
        return
    try:
        from Assets.Spiderpot_Core import SpiderpotApp
        app = SpiderpotApp(root, load_config())
        def callback_error(kind, error, trace):
            app.stop_system()
            messagebox.showerror("Spiderpot", "Tuzak durduruldu.\n" + str(error), parent=root)
        root.report_callback_exception = callback_error
        root.protocol("WM_DELETE_WINDOW", app.real_quit)
        root.mainloop()
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
