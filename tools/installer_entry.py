"""Single downloadable offline installer for the per-user Spiderpot upgrade."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox
import zipfile

from spiderpot_upgrade import install_bundle, legacy_startup


def extract_payload(archive, destination):
    destination = Path(destination).resolve()
    for name in archive.namelist():
        target = (destination/name).resolve()
        if not target.is_relative_to(destination):
            raise ValueError('Geçersiz kurulum arşivi yolu.')
    archive.extractall(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--quiet',action='store_true')
    parser.add_argument('--run',action='store_true')
    args = parser.parse_args()
    root = tk.Tk()
    root.withdraw()
    try:
        current = Path(os.environ['LOCALAPPDATA'])/'Spiderpot/settings.json'
        enabled = bool(legacy_startup())
        if current.is_file():
            enabled = bool(json.loads(current.read_text(encoding='utf-8')).get('auto_start',False))
        bundle = Path(sys._MEIPASS)/'payload.zip'
        with tempfile.TemporaryDirectory(prefix='Spiderpot-setup-') as scratch:
            with zipfile.ZipFile(bundle) as archive:
                extract_payload(archive,scratch)
            executable = install_bundle(Path(scratch)/'Spiderpot',enabled)
        subprocess.Popen([str(executable),'--run' if args.run else '--configure'],creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as error:
        if not args.quiet:
            messagebox.showerror('Spiderpot kurulamadı',str(error),parent=root)
        raise
    finally:
        root.destroy()


if __name__=='__main__': main()
