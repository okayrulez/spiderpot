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
