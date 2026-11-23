"""Retire identified per-user program files after the new EXE installation commits."""
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import re
import sys


# Fingerprints of the original standalone executable and previously distributed installers.
RETIRED_BINARIES = {
    'a182d3a37a2a6613b9ac1e08fc0224285239fa68830127b55e9e5299cf3a0f56',
    'bc715df046c775b8879f28265580bfe32493ef3c43d6a3d6a6b000cab911e904',
    '878e75563aac3e925c9ccb793e6a78607f5a4c56c6411c997cd0a80e99d021f3',
    '0bc41e77cd13bee59c1d41a21a10271c7a92038c4d3c3eb81df38be7b6091404',
    '89fb97354e18852330a6ab16112a5671efedcaf6b657f1d9fd54b1aa415f891e',
    '984b8451e77889643d3e35a2cf1c2fd4427187b87747c880ddda5b30ae864f569',
    'f5dc5fd5368c814d4fb368ae20ee30b6cb0393a61ce7aa39b9b99f4c87a32558',
    '64f90d5eb1a666df606f4b689cf3e41c8ca96207ded3220a715fe92ec3c0e660',
    '7005f7b4a08802956902068340a7de5fbd5ec0834b23835ac5c6c13e1a47d34f',
}


def digest(path):
    try:
        with path.open('rb') as stream:
            return hashlib.file_digest(stream, 'sha256').hexdigest()
    except OSError:
        return ''


def direct_child(path, parent):
    return not path.is_symlink() and not path.is_junction() and path.resolve().parent == parent.resolve()


def retired_files(root, version, locations):
    known = set(RETIRED_BINARIES)
    current = tuple(map(int, version.split('.')))
    for name in ('versions', 'installer'):
        parent = root/name
        if not parent.is_dir() or not direct_child(parent, root):
            continue
        for folder in parent.iterdir():
            match = re.fullmatch(r'(\d+\.\d+\.\d+)(\.backup-[a-f0-9]{8})?', folder.name)
            if not match or not folder.is_dir() or not direct_child(folder, parent):
                continue
            number = tuple(map(int, match[1].split('.')))
            if number > current or (number == current and not match[2]):
                continue
            exe = folder/('Spiderpot.exe' if name == 'versions' else f'Spiderpot-{match[1]}-Setup.exe')
            if not exe.is_file() or not direct_child(exe, folder):
                continue
            expected = {exe.name}
            if name == 'versions':
                expected.add('_internal')
                if not (folder/'_internal/Assets/spiderpot.ico').is_file() or not direct_child(folder/'_internal', folder):
                    continue
            if {p.name for p in folder.iterdir()} == expected:
                if fingerprint := digest(exe):
                    known.add(fingerprint)
                yield folder, parent
    for location in set(locations):
        if not location.is_dir():
            continue
        for file in location.glob('Spiderpot*.exe'):
            if file.is_file() and direct_child(file, location) and digest(file) in known:
                yield file, location


class ShellOperation(ctypes.Structure):
    if ctypes.sizeof(ctypes.c_void_p) == 4:
        _pack_ = 1
    _fields_ = [('hwnd', wintypes.HWND), ('operation', wintypes.UINT),
                ('source', wintypes.LPCWSTR), ('dest', wintypes.LPCWSTR),
                ('flags', wintypes.WORD), ('aborted', wintypes.BOOL),
                ('mappings', wintypes.HANDLE), ('title', wintypes.LPCWSTR)]


def recycle(path, parent):
    if not direct_child(path, parent):
        raise ValueError('Temizleme yolu değişti.')
    resolved = path.resolve()
    if ctypes.windll.kernel32.GetDriveTypeW(resolved.anchor) != 3:
        raise OSError('Yalnız yerel diskteki program dosyaları taşınabilir.')
    op = ShellOperation(operation=3, source=str(resolved)+'\0\0', flags=0x40 | 0x10 | 0x400 | 0x4)
    result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if result or op.aborted:
        raise OSError(f'Dosya geri dönüşüm kutusuna taşınamadı ({result}).')


def clean_previous(root, version, locations, protected):
    kept = {Path(p).resolve() for p in (*protected, sys.executable) if p}
    report = {'recycled': [], 'pending': []}
    for path, parent in retired_files(root, version, locations):
        if any(p == path.resolve() or p.is_relative_to(path.resolve()) for p in kept):
            continue
        try:
            recycle(path, parent)
            report['recycled'].append(str(path))
        except (OSError, ValueError):
            report['pending'].append(str(path))
    return report
