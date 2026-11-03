"""Hardware-free checks for the preserved modes and Store-specific safeguards."""
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import spiderpot_support as support
from Assets import Spiderpot_Core as core


class ConfigTests(unittest.TestCase):
    def test_default_keys_remain_ctrl_1_2_3_and_f12(self):
        app=core.SpiderpotApp.__new__(core.SpiderpotApp)
        for key in ('key_spider','key_black','key_lock','key_exit'):
            setattr(app,key,support.DEFAULTS[key])
        app._resolve_hotkeys()
        self.assertEqual(app.mode_by_vk,{49:'spider',50:'black',51:'invisible'})
        self.assertEqual(app.exit_key,core.keyboard.Key.f12)

    def test_duplicate_or_injected_hotkeys_are_rejected(self):
        for value in ('1', "';x()#", '\n', 'ş'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                support.validate(dict(support.DEFAULTS,key_black=value))

    def test_camera_and_startup_are_opt_in(self):
        self.assertFalse(support.DEFAULTS['camera_enabled'])
        self.assertFalse(support.DEFAULTS['auto_start'])

    def test_settings_and_wallpaper_survive_source_removal(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,SPIDERPOT_TEST_DATA=directory):
            source=Path(directory)/'source.png'
            Image.new('RGB',(32,24),'red').save(source)
            config=support.save_config(support.DEFAULTS,source)
            source.unlink()
            self.assertTrue(Path(config['wallpaper']).is_file())
            self.assertEqual(support.load_config(),config)
            # Saving the already-managed wallpaper must work too.
            support.save_config(config,config['wallpaper'])


class CaptureTests(unittest.TestCase):
    def test_dpapi_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            store=support.CaptureStore(directory)
            payload=b'\xff\xd8Synthetic test photograph\xff\xd9'
            name=store.save(payload)
            path=Path(directory)/name
            self.assertNotIn(payload,path.read_bytes())
            self.assertEqual(store.read(path),payload)
            data=bytearray(path.read_bytes())
            data[-1]^=255
            path.write_bytes(data)
            with self.assertRaises(OSError): store.read(path)

    def test_retention_and_path_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            store=support.CaptureStore(directory)
            path=Path(directory)/store.save(b'test')
            old=time.time()-8*86400
            os.utime(path,(old,old))
            store.prune(7)
            self.assertEqual(store.entries(),[])
            with self.assertRaises(ValueError): store.read(Path(directory).parent/'outside.spcap')

    def app(self):
        app=core.SpiderpotApp.__new__(core.SpiderpotApp)
        app.is_active=True
        app.closed=False
        app.camera_enabled=True
        app.camera_port=0
        app.session_generation=1
        app.capture_lock=threading.Lock()
        app.session_lock=threading.RLock()
        app.capture_store=Mock()
        app.root=Mock()
        return app

    def test_cancelled_camera_job_cannot_write_a_photo(self):
        app=self.app()
        camera=Mock()
        camera.isOpened.return_value=True
        def read():
            app.is_active=False
            app.session_generation+=1
            return True,object()
        camera.read.side_effect=read
        app.capture_lock.acquire()
        with patch.object(core.cv2,'VideoCapture',return_value=camera): app._capture(1)
        app.capture_store.save.assert_not_called()
        camera.release.assert_called_once()
        self.assertFalse(app.capture_lock.locked())

    def test_disabled_camera_does_not_access_hardware(self):
        app=self.app()
        app.camera_enabled=False
        with patch.object(core.cv2,'VideoCapture') as open_camera:
            app.capture_photo()
        open_camera.assert_not_called()


class ModeTests(unittest.TestCase):
    def test_original_mode_dispatch_and_mouse_trap_remain(self):
        for mode in ('spider','black','invisible'):
            with self.subTest(mode=mode):
                app=core.SpiderpotApp.__new__(core.SpiderpotApp)
                app.is_active=False
                app.session_generation=0
                app.session_lock=threading.RLock()
                app.on_move=app.on_click=app.on_scroll=Mock()
                app.viewer=Mock()
                app.update_tray_icon=Mock()
                with patch.object(core.mouse,'Listener') as listener,patch.object(core,'prevent_sleep'):
                    app.start_system(mode)
                    self.assertTrue(listener.call_args.kwargs['suppress'])
                self.assertTrue(app.is_active)
                if mode=='invisible':
                    app.viewer.hide.assert_called_once()
                    app.viewer.show_mode.assert_not_called()
                else:
                    app.viewer.show_mode.assert_called_once_with(mode_spider=mode=='spider')

    def test_icon_has_transparent_corners_and_red_circle(self):
        icon=support.circular_icon(64)
        self.assertEqual(icon.getpixel((0,0))[3],0)
        self.assertEqual(icon.getpixel((63,63))[3],0)
        red,green,blue,alpha=icon.getpixel((32,10))
        self.assertGreater(red,green*2)
        self.assertEqual(alpha,255)

    def test_tray_goes_green_when_active_and_red_when_stopped(self):
        app=core.SpiderpotApp.__new__(core.SpiderpotApp)
        app.tray_icon=Mock()
        app.camera_enabled=False
        for active in (False,True,False):
            with self.subTest(active=active):
                app.is_active=active
                app.update_tray_icon()
                icon=app.tray_icon.icon
                red,green,blue,alpha=icon.getpixel((32,10))
                self.assertEqual(alpha,255)
                self.assertEqual(icon.getpixel((0,0))[3],0)
                if active:
                    self.assertGreater(green,red*2)
                    self.assertIn('(Aktif)',app.tray_icon.title)
                else:
                    self.assertGreater(red,green*2)
                    self.assertIn('(Pasif)',app.tray_icon.title)
                # White ring remains the same through both state transitions.
                red,green,blue,alpha=icon.getpixel((32,20))
                self.assertGreater(min(red,green,blue),240)


if __name__=='__main__': unittest.main()
