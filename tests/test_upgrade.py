import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import zipfile

import spiderpot_upgrade as upgrade
from tools.installer_entry import extract_payload


class UpgradeTests(unittest.TestCase):
    def bundle(self, root):
        root.mkdir(parents=True,exist_ok=True)
        (root/'Spiderpot.exe').write_bytes(b'synthetic test binary')
        (root/'_internal/Assets').mkdir(parents=True,exist_ok=True)
        (root/'_internal/Assets/spiderpot.ico').write_bytes(b'test icon')
        return root

    def test_cleanup_preserves_current_bundle_and_unrelated_desktop_files(self):
        from spiderpot_cleanup import clean_previous
        with tempfile.TemporaryDirectory() as tmp:
            root, desktop = Path(tmp)/'program', Path(tmp)/'desktop'
            desktop.mkdir()
            old = self.bundle(root/'versions'/'1.0.6')
            self.bundle(root/'versions'/'1.0.10')
            duplicate = desktop/'Spiderpot_Sistem.exe'
            duplicate.write_bytes((old/'Spiderpot.exe').read_bytes())
            (desktop/'Spiderpot-other.exe').write_bytes(b'unrelated')
            (desktop/'Spiderpot_Yakalananlar').mkdir()
            with patch('spiderpot_cleanup.recycle') as recycle:
                report = clean_previous(root, '1.0.10', (desktop,), ())
            self.assertEqual(set(report['recycled']), {str(old),str(duplicate)})
            self.assertEqual(recycle.call_count, 2)

    def test_both_old_binary_names_are_recognized(self):
        for name in ('Spiderpot.exe','Spiderpot_Sistem.exe'):
            self.assertTrue(upgrade.is_spiderpot_process({'name':name,'exe':str(Path('C:/old')/name)}))
        self.assertFalse(upgrade.is_spiderpot_process({'name':'python.exe','exe':'C:/Python/python.exe','cmdline':['python','unrelated.py']}))
        self.assertFalse(upgrade.is_spiderpot_process({'name':'spiderpot-editor.exe','exe':'C:/editor/spiderpot-editor.exe'}))

    def test_process_discovery_excludes_other_users_and_current_process(self):
        current=Mock(pid=42)
        current.username.return_value='PC\\Okay'
        current.parents.return_value=[SimpleNamespace(pid=41)]
        items=[SimpleNamespace(info={'pid':pid,'username':owner,'name':'Spiderpot.exe','exe':'C:/old/Spiderpot.exe'})
               for pid,owner in [(42,'PC\\Okay'),(41,'PC\\Okay'),(43,'PC\\Other'),(44,'PC\\Okay')]]
        with patch.object(upgrade.psutil,'Process',return_value=current),patch.object(upgrade.psutil,'process_iter',return_value=items):
            self.assertEqual([p.info['pid'] for p in upgrade.running_instances()],[44])

    def test_deployment_retains_user_data_and_can_be_repeated(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            source=self.bundle(root/'download')
            install=root/'program'
            user_data=root/'captures'
            user_data.mkdir()
            photo=user_data/'old-photo.spcap'
            photo.write_bytes(b'preserve this photo')
            executable=upgrade.deploy(source,install)
            (install/'install.json').write_text(json.dumps({'product_id':upgrade.PRODUCT_ID}))
            (source/'Spiderpot.exe').write_bytes(b'new revision')
            self.assertEqual(upgrade.deploy(source,install),executable)
            self.assertEqual(executable.read_bytes(),b'new revision')
            self.assertEqual(photo.read_bytes(),b'preserve this photo')
            self.assertTrue(list(executable.parent.parent.glob('*.backup-*')))
            self.assertEqual(upgrade.deploy(executable.parent,install),executable)

    def test_unrecognized_install_directory_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as scratch:
            root=Path(scratch)
            source=self.bundle(root/'download')
            install=root/'program'
            target=install/'versions'/upgrade.VERSION
            target.mkdir(parents=True)
            owned=target/'user-file.txt'
            owned.write_text('keep')
            with self.assertRaises(RuntimeError): upgrade.deploy(source,install)
            self.assertEqual(owned.read_text(),'keep')

    def test_incomplete_bundle_and_invalid_version_are_rejected(self):
        with tempfile.TemporaryDirectory() as scratch:
            with self.assertRaises(ValueError): upgrade.deploy(Path(scratch),Path(scratch)/'install')
            with self.assertRaises(ValueError): upgrade.deploy(Path(scratch),version='../escape')

    def test_startup_shortcut_is_backed_up_and_both_registry_names_removed(self):
        with tempfile.TemporaryDirectory() as scratch,patch.dict(os.environ,APPDATA=str(Path(scratch)/'roaming'),LOCALAPPDATA=str(Path(scratch)/'local')):
            folder=upgrade.startup_folder()
            folder.mkdir(parents=True)
            (folder/'Spiderpot.lnk').write_bytes(b'legacy shortcut')
            (folder/'OtherApp.lnk').write_bytes(b'leave alone')
            with patch.object(upgrade.winreg,'CreateKey') as key,patch.object(upgrade.winreg,'DeleteValue') as delete:
                upgrade.clear_startup()
                self.assertEqual({call.args[1] for call in delete.call_args_list},{'Spiderpot','Spiderpot_App'})
            self.assertTrue((folder/'OtherApp.lnk').is_file())
            self.assertFalse((folder/'Spiderpot.lnk').exists())
            backup=list((Path(scratch)/'local/Spiderpot/migration-backups').glob('*.lnk'))
            self.assertEqual(backup[0].read_bytes(),b'legacy shortcut')

    def test_installer_extract_rejects_path_traversal(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive: archive.writestr('../outside.txt','bad')
        data.seek(0)
        with tempfile.TemporaryDirectory() as scratch,zipfile.ZipFile(data) as archive:
            with self.assertRaises(ValueError): extract_payload(archive,scratch)

    def test_exe_install_can_export_and_uninstall_without_removing_user_files(self):
        with tempfile.TemporaryDirectory() as scratch, patch.dict(os.environ,LOCALAPPDATA=scratch):
            base=Path(scratch)
            source=self.bundle(base/'download')
            installer=base/'downloaded-setup.exe'
            installer.write_bytes(b'full offline setup')
            photos=base/'Spiderpot'/'captures'
            photos.mkdir(parents=True)
            photo=photos/'kept.spcap'
            photo.write_bytes(b'encrypted frame')
            with patch.object(Path,'home', return_value=base), patch.object(upgrade,'stop_instances',return_value=[]), \
                    patch.object(upgrade,'set_startup_target'), patch.object(upgrade,'legacy_startup',return_value={}), \
                    patch.object(upgrade,'running_instances',return_value=[]), patch.object(upgrade,'clear_startup'), \
                    patch.object(upgrade,'shortcut'), patch.object(upgrade,'desktop_link',return_value=base/'Desktop'/'Spiderpot.lnk'), \
                    patch.object(upgrade,'register_uninstaller') as register, patch.object(upgrade.winreg,'DeleteKey'):
                executable=upgrade.install_bundle(source,True,desktop_shortcut=True,installer=installer)
                cached=upgrade.saved_installer()
                self.assertEqual(cached.read_bytes(),installer.read_bytes())
                register.assert_called_once_with(upgrade.install_root(),cached,executable)
                leftover=upgrade.install_root()/'old-user-file.txt'
                leftover.write_text('keep me')
                upgrade.uninstall_bundle()
            self.assertFalse(executable.exists())
            self.assertFalse(cached.exists())
            self.assertEqual(photo.read_bytes(),b'encrypted frame')
            self.assertEqual(leftover.read_text(),'keep me')

    def test_compatibility_mutexes_include_old_and_current_names(self):
        self.assertIn('Global\\Spiderpot_Mutex_Lock',upgrade.RUNTIME_MUTEXES)
        self.assertIn('Local\\Spiderpot_Mutex_Lock',upgrade.RUNTIME_MUTEXES)
        with patch.object(upgrade,'Mutex') as factory:
            factory.return_value.existed=True
            runtime=upgrade.RuntimeLock()
            self.assertTrue(runtime.already_running)
            runtime.close()
            factory.return_value.close.assert_called_once()


if __name__=='__main__': unittest.main()
