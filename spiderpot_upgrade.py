"""Per-user upgrade: retire known Spiderpot processes and own one startup entry."""
import base64
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import winreg

import psutil

PRODUCT_ID = 'okayrulez.spiderpot'
VERSION = '1.0.14'
LEGACY_NAMES = {'spiderpot.exe', 'spiderpot_sistem.exe'}
RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
UNINSTALL_KEY = r'Software\Microsoft\Windows\CurrentVersion\Uninstall\Spiderpot'
RUNTIME_MUTEXES = ('Local\\Spiderpot.Runtime.v1', 'Local\\Spiderpot_Mutex_Lock', 'Global\\Spiderpot_Mutex_Lock')


class Mutex:
    def __init__(self, name, owned=False, wait_ms=0):
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.ReleaseMutex.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateMutexW(None, False, name)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.existed = ctypes.get_last_error() == 183
        self.owned = False
        if owned:
            result = self.kernel.WaitForSingleObject(self.handle, wait_ms)
            if result not in (0, 0x80):
                self.close()
                raise RuntimeError('Başka bir Spiderpot kurulumu devam ediyor. Tamamlanınca tekrar deneyin.')
            self.owned = True

    def close(self):
        if self.handle:
            if self.owned:
                self.kernel.ReleaseMutex(self.handle)
            self.kernel.CloseHandle(self.handle)
            self.handle = None

    def __enter__(self): return self
    def __exit__(self, *args): self.close()


class RuntimeLock:
    def __init__(self):
        self.locks = []
        self.already_running = False
        try:
            for name in RUNTIME_MUTEXES:
                lock = Mutex(name)
                self.locks.append(lock)
                if lock.existed:
                    self.already_running = True
                    break
        except Exception:
            self.close()
            raise

    def close(self):
        for lock in self.locks:
            lock.close()
        self.locks.clear()


def install_root():
    return Path(os.environ['LOCALAPPDATA']) / 'Programs' / 'Spiderpot'


def startup_folder():
    return Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup'


def is_spiderpot_process(info):
    name = (info.get('name') or '').lower()
    exe = Path(info.get('exe') or '')
    if name in LEGACY_NAMES:
        return exe.name.lower() == name
    # Older source launches count only for exact product entry points.
    args = info.get('cmdline') or []
    return (name in ('python.exe', 'pythonw.exe') and len(args) > 1
            and Path(args[1]).name.lower() in ('spiderpot.py','spiderpot_core.py','temp_spiderpot.py')
            and 'spiderpot' in str(Path(args[1]).parent).lower())


def running_instances():
    current = psutil.Process()
    excluded = {current.pid, *(parent.pid for parent in current.parents())}
    owner = current.username().casefold()
    found = []
    for process in psutil.process_iter(['pid','name','exe','cmdline','username','create_time']):
        try:
            info = process.info
            if info['pid'] not in excluded and (info['username'] or '').casefold() == owner and is_spiderpot_process(info):
                found.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def stop_instances(processes=None):
    processes = running_instances() if processes is None else processes
    if not processes:
        return []
    pids = {process.pid for process in processes}
    # Ask each older UI to exit first. Hidden Tk roots are included by EnumWindows.
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user = ctypes.windll.user32
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    def close_window(window, argument):
        pid = wintypes.DWORD()
        user.GetWindowThreadProcessId(window, ctypes.byref(pid))
        if pid.value in pids:
            user.PostMessageW(window, 0x0010, 0, 0)
        return True
    callback = callback_type(close_window)
    user.EnumWindows(callback, 0)
    _, alive = psutil.wait_procs(processes, timeout=2)
    for process in alive:
        try:
            # psutil verifies PID creation time before terminating a process.
            process.terminate()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=5)
    if alive:
        raise RuntimeError('Eski Spiderpot kapatılamadı. Kendi oturumunuzdaki eski sürümü kapatıp yeniden deneyin.')
    return sorted(pids)


def legacy_startup():
    values = {}
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            for name in ('Spiderpot_App','Spiderpot'):
                try:
                    values[name] = winreg.QueryValueEx(key,name)[0]
                except FileNotFoundError:
                    pass
    except FileNotFoundError:
        pass
    return values


def clear_startup():
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
        for name in ('Spiderpot_App','Spiderpot'):
            try:
                winreg.DeleteValue(key,name)
            except FileNotFoundError:
                pass
    for name in ('Spiderpot.lnk','Spiderpot_Sistem.lnk'):
        path = startup_folder()/name
        if path.is_file():
            # Move rather than destroy the original shortcut.
            backup = Path(os.environ['LOCALAPPDATA'])/'Spiderpot/migration-backups'
            backup.mkdir(parents=True,exist_ok=True)
            path.replace(backup/(uuid.uuid4().hex+'-'+name))


def set_startup_target(executable, enabled, arguments=('--startup',)):
    clear_startup()
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,RUN_KEY) as key:
            value = subprocess.list2cmdline([str(executable),*arguments])
            winreg.SetValueEx(key,'Spiderpot',0,winreg.REG_SZ,value)


def start_menu_shortcut():
    return Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/Spiderpot.lnk'


def desktop_link():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as key:
            desktop = os.path.expandvars(winreg.QueryValueEx(key, 'Desktop')[0])
    except OSError:
        desktop = str(Path.home()/'Desktop')
    return Path(desktop)/'Spiderpot.lnk'


def saved_installer(root=None):
    return Path(root or install_root())/'installer'/VERSION/f'Spiderpot-{VERSION}-Setup.exe'


def shortcut(executable, path=None, *, remove=False, root=None):
    path = start_menu_shortcut() if path is None else path
    if remove and not path.is_file():
        return
    if not remove:
        path.parent.mkdir(parents=True,exist_ok=True)
    code = '''[Console]::InputEncoding = [Text.Encoding]::UTF8
$p = [Console]::In.ReadToEnd() | ConvertFrom-Json
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($p.path)
if (Test-Path -LiteralPath $p.path) {
    if (-not $s.TargetPath.StartsWith($p.ownedPrefix, [StringComparison]::OrdinalIgnoreCase)) { exit 0 }
    if ($p.remove) { Remove-Item -LiteralPath $p.path -ErrorAction Stop; exit 0 }
}
if ($p.remove) { exit 0 }
$s.TargetPath = $p.target
$s.WorkingDirectory = $p.directory
$s.IconLocation = $p.target + ',0'
$s.Save()
'''
    encoded = base64.b64encode(code.encode('utf-16-le')).decode('ascii')
    payload = json.dumps({
        'path': str(path), 'target': str(executable), 'directory': str(executable.parent),
        'ownedPrefix': str(Path(root or install_root()).resolve()) + os.sep, 'remove': remove,
    }, ensure_ascii=False)
    subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand',encoded],
                   input=payload.encode('utf-8'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                   creationflags=subprocess.CREATE_NO_WINDOW,check=True)


def deploy(source, root=None, version=VERSION):
    source = Path(source).resolve()
    root = Path(root) if root is not None else install_root()
    if not version or any(c not in '0123456789.' for c in version):
        raise ValueError('Geçersiz sürüm numarası.')
    if not (source/'Spiderpot.exe').is_file() or not (source/'_internal/Assets/spiderpot.ico').is_file():
        raise ValueError('Spiderpot paketi eksik. ZIP dosyasının tamamını çıkarın.')
    target = root/'versions'/version
    if target.resolve() == source:
        return target/'Spiderpot.exe'
    stage = root/'versions'/('.pending-'+uuid.uuid4().hex)
    stage.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(source,stage)
    if target.exists():
        # Only a previously recorded Spiderpot install may be replaced.
        marker = root/'install.json'
        if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('product_id') != PRODUCT_ID:
            raise RuntimeError('Hedefte tanınmayan dosyalar var. Kurulum güvenle durduruldu.')
        target.replace(target.with_name(version+'.backup-'+uuid.uuid4().hex[:8]))
    stage.replace(target)
    return target/'Spiderpot.exe'


def register_uninstaller(root, setup, executable):
    fields = {
        'DisplayName': 'Spiderpot', 'Publisher': 'Okay Dedeoglu', 'DisplayVersion': VERSION,
        'InstallLocation': str(root), 'DisplayIcon': str(executable),
        'UninstallString': subprocess.list2cmdline([str(setup), '--uninstall']),
    }
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        for field, value in fields.items():
            winreg.SetValueEx(key, field, 0, winreg.REG_SZ, value)
        for field in ('NoModify', 'NoRepair'):
            winreg.SetValueEx(key, field, 0, winreg.REG_DWORD, 1)


def install_bundle(source, enabled, root=None, *, desktop_shortcut=False, installer=None):
    root = Path(root) if root is not None else install_root()
    marker = root/'install.json'
    with Mutex('Local\\Spiderpot.Update.v1',owned=True,wait_ms=10000):
        if root.is_symlink() or root.is_junction():
            raise RuntimeError('Güvenli olmayan kurulum yolu.')
        if root.exists() and any(root.iterdir()):
            recorded = marker.is_file() and json.loads(marker.read_text(encoding='utf-8')).get('product_id') == PRODUCT_ID
            legacy = not marker.exists() and (root/'Spiderpot_Sistem.exe').is_file()
            if not recorded and not legacy:
                raise RuntimeError('Kurulum klasöründe tanınmayan dosyalar var.')
        previous = legacy_startup()
        stopped = stop_instances()
        executable = deploy(source,root)
        set_startup_target(executable,enabled)
        shortcut(executable, root=root)
        shortcut(executable, desktop_link(), remove=not desktop_shortcut, root=root)
        record = {'product_id':PRODUCT_ID,'version':VERSION,'executable':str(executable),
                  'updated_at':datetime.now(timezone.utc).isoformat(),'replaced_processes':stopped}
        marker.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        setup = saved_installer(root)
        if installer and Path(installer).resolve() != setup.resolve():
            setup.parent.mkdir(parents=True, exist_ok=True)
            staging = setup.with_suffix('.tmp')
            shutil.copy2(installer, staging)
            staging.replace(setup)
        if setup.is_file():
            register_uninstaller(root, setup, executable)
        if installer:
            from spiderpot_cleanup import clean_previous
            try:
                record['cleanup'] = clean_previous(root, VERSION,
                                                   (root, desktop_link().parent, Path.home()/'Downloads'),
                                                   (installer, executable, setup))
            except OSError as error:
                record['cleanup'] = {'error': str(error)}
            marker.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        backup = Path(os.environ['LOCALAPPDATA'])/'Spiderpot/migration-backups'
        backup.mkdir(parents=True,exist_ok=True)
        (backup/(datetime.now().strftime('%Y%m%d-%H%M%S')+'-startup.json')).write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
        return executable


def uninstall_bundle():
    root = install_root()
    expected = root.parent.resolve()/'Spiderpot'
    if root.resolve() != expected or root.is_symlink() or root.is_junction():
        raise RuntimeError("Güvenli olmayan kurulum yolu.")
    with Mutex('Local\\Spiderpot.Update.v1', owned=True, wait_ms=10000):
        record = json.loads((root/'install.json').read_text(encoding='utf-8'))
        executable = Path(record['executable']).resolve()
        if (record.get('product_id') != PRODUCT_ID or executable.name != 'Spiderpot.exe'
                or not executable.is_relative_to(expected/'versions')):
            raise RuntimeError("Tanınan bir Spiderpot EXE kurulumu bulunamadı.")
        processes = [process for process in running_instances()
                     if Path(process.info['exe']).resolve().is_relative_to(expected)]
        stop_instances(processes)
        retired = expected.with_name('.spiderpot-uninstall-'+uuid.uuid4().hex)
        owned = [root/name for name in ('versions', 'installer', 'install.json') if (root/name).exists()]
        if any(path.is_symlink() or path.is_junction() or path.resolve().parent != expected for path in owned):
            raise RuntimeError("Kaldırma hedefi doğrulanamadı.")
        retired.mkdir()
        moved = []
        try:
            for path in owned:
                for attempt in range(20):
                    try:
                        path.replace(retired/path.name)
                        moved.append(path)
                        break
                    except PermissionError:
                        if attempt == 19:
                            raise
                        time.sleep(.25)
        except OSError:
            for path in reversed(moved):
                (retired/path.name).replace(path)
            retired.rmdir()
            raise
        if not any(root.iterdir()):
            root.rmdir()
        clear_startup()
        shortcut(executable, remove=True, root=expected)
        shortcut(executable, desktop_link(), remove=True, root=expected)
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
        except FileNotFoundError:
            pass
        if retired.resolve().parent != expected.parent or retired.is_junction() or retired.is_symlink():
            raise RuntimeError("Kaldırma hedefi doğrulanamadı.")
        shutil.rmtree(retired)
