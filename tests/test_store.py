"""Hardware-free checks for the preserved modes and Store-specific safeguards."""
import os
from pathlib import Path
import tempfile
from queue import SimpleQueue
import threading
import subprocess
import sys
import time
from types import SimpleNamespace
import unittest
from unittest.mock import ANY, Mock, patch

from PIL import Image
import spiderpot_support as support
from Assets import Spiderpot_Core as core
import camera_tools
from spiderpot_tutorial import SpiderpotTutorial


class ConfigTests(unittest.TestCase):
    def test_default_keys_remain_ctrl_1_2_3_and_f12(self):
        app=core.SpiderpotApp.__new__(core.SpiderpotApp)
        for key in ('key_spider','key_black','key_lock','key_exit'):
            setattr(app,key,support.DEFAULTS[key])
        app._resolve_hotkeys()
        ctrl=frozenset({'ctrl'})
        self.assertEqual(app.mode_hotkeys,{(ctrl,49):'spider',(ctrl,50):'black',(ctrl,51):'invisible'})
        self.assertEqual(app.exit_hotkey,(frozenset(),core.keyboard.Key.f12.value.vk))

    def test_duplicate_or_injected_hotkeys_are_rejected(self):
        for value in ('1', "';x()#", '\n', 'ş'):
            with self.subTest(value=value),self.assertRaises(ValueError):
                support.validate(dict(support.DEFAULTS,key_black=value))

    def test_camera_and_startup_are_opt_in(self):
        self.assertFalse(support.DEFAULTS['camera_enabled'])
        self.assertFalse(support.DEFAULTS['auto_start'])

    def test_custom_shortcuts_use_actual_modifiers_and_reject_conflicts(self):
        config=support.validate({'key_spider':'Ctrl + Q','key_black':'Alt + 8','key_lock':'Shift + F5','key_exit':'Ctrl + Shift + X'})
        self.assertEqual(support.shortcut_label(config['key_lock'],mode=True),'Shift + F5')
        self.assertEqual(support.shortcut_label(config['key_exit']),'Ctrl + Shift + X')
        with self.assertRaises(ValueError):
            support.validate(dict(config,key_exit='ctrl+q'))

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

    def test_playlist_order_survives_removing_the_originals(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,SPIDERPOT_TEST_DATA=directory):
            first, second = Path(directory)/'first.png', Path(directory)/'second.png'
            Image.new('RGB',(12,8),'red').save(first)
            Image.new('RGB',(8,12),'blue').save(second)
            config=support.save_config(dict(support.DEFAULTS,slide_seconds=8),[second,first])
            first.unlink()
            second.unlink()
            saved=support.load_config()
            self.assertEqual(saved,config)
            self.assertEqual(saved['wallpaper'],saved['slides'][0])
            for path, size in zip(saved['slides'], [(8,12),(12,8)]):
                with Image.open(path) as image:
                    self.assertEqual(image.size,size)


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
        app.mailer=None
        app.camera_port=0
        app.session_generation=1
        app.capture_preview_job=None
        app.camera_failed_generation=None
        app.tutorial=None
        app.capture_lock=threading.Lock()
        app.session_lock=threading.RLock()
        app.session=core.Session()
        app.dashboard=None
        app.last_summary=""
        app.pending_mode=None
        app.config={'arming_seconds': 0}
        app.card=Mock()
        app.mouse_listener=None
        app.capture_store=Mock()
        app.root=Mock()
        app.viewer=Mock()
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
        app.root.after.assert_not_called()
        camera.release.assert_called_once()
        self.assertFalse(app.capture_lock.locked())

    def test_dashboard_is_only_selected_from_tray_menu(self):
        app = self.app()
        with patch.object(core.pystray.Icon, "run"), patch.object(core.pystray.Icon, "update_menu"):
            app.setup_tray()
            app.root.after.assert_not_called()
            app.tray_icon()
            app.root.after.assert_not_called()
            action = next(item for item in app.tray_icon.menu.items if item.text == "Dashboard aç")
            action(app.tray_icon)
            app.root.after.assert_called_once_with(0, app.open_dashboard)

    def test_capture_shows_saved_frame_and_then_restores_each_mode(self):
        for mode in ('spider','black','invisible'):
            with self.subTest(mode=mode):
                app=self.app()
                app.active_mode=mode
                frame=core.cv2.UMat(48,64,core.cv2.CV_8UC3,(0,0,0,0)).get()
                camera=Mock()
                camera.isOpened.return_value=True
                camera.read.return_value=(True,frame)
                app.capture_lock.acquire()
                with patch.object(core.cv2,'VideoCapture',return_value=camera):
                    app._capture(1)

                delay,present,generation,jpeg,name=app.root.after.call_args.args
                self.assertEqual(delay,0)
                app.capture_store.save.assert_called_once_with(jpeg)
                present(generation,jpeg,name)
                app.viewer.show_capture.assert_called_once_with(jpeg)
                delay,restore,generation=app.root.after.call_args.args
                self.assertEqual(delay,3000)
                restore(generation)
                if mode=='invisible':
                    app.viewer.hide.assert_called_once()
                else:
                    app.viewer.show_mode.assert_called_once_with(mode_spider=mode=='spider',restart=False)

    def test_queued_photo_does_not_reappear_after_switching_modes(self):
        app=self.app()
        app.update_tray_icon=Mock()
        app.start_system('black')
        app._present_capture(1,b'old frame','old.spcap')
        app.viewer.show_capture.assert_not_called()
        app.viewer.show_mode.assert_called_once_with(mode_spider=False,restart=True)

    def test_camera_falls_back_to_media_foundation(self):
        unavailable, available=Mock(),Mock()
        unavailable.isOpened.return_value=False
        available.isOpened.return_value=True
        frame=core.cv2.UMat(8,8,core.cv2.CV_8UC3,(1,2,3,0)).get()
        available.read.side_effect=[(False,None),(True,frame),(False,None),(True,frame)]
        with patch.object(core.cv2,'VideoCapture',side_effect=[unavailable,available]) as video:
            result,backend=camera_tools.capture_camera_frame(3)
        self.assertIs(result,frame)
        self.assertEqual(backend,'Media Foundation')
        self.assertEqual([call.args for call in video.call_args_list],
                         [(3,core.cv2.CAP_DSHOW),(3,core.cv2.CAP_MSMF)])
        self.assertEqual(available.read.call_count,2)
        unavailable.release.assert_called_once()
        available.release.assert_called_once()

    def test_disabled_camera_does_not_access_hardware(self):
        app=self.app()
        app.camera_enabled=False
        with patch.object(core.cv2,'VideoCapture') as open_camera:
            app.capture_photo()
        open_camera.assert_not_called()

    def test_activity_mail_works_with_camera_off_and_skips_walkthrough(self):
        app=self.app()
        app.camera_enabled=False
        app.mailer=Mock()
        app.on_move(10, 10)
        app.mailer.send_once.assert_called_once_with(app.session_generation, ANY)
        app.tutorial=Mock(camera_armed=False)
        app.on_move(20, 20)
        app.mailer.send_once.assert_called_once()

    def test_summary_includes_only_observed_activity_and_expires(self):
        app = self.app()
        app.camera_enabled = False
        app.mailer = Mock()
        app.on_move(3, 4)
        first = app.session.first_activity
        self.assertIsNotNone(first)
        app.on_scroll(3, 4, 0, 1)
        self.assertEqual(app.session.first_activity, first)
        app.mailer.send_once.call_args.args[1]("E-posta gönderildi")
        with patch.object(core, "allow_sleep"):
            app.stop_system()
        args, kwargs = app.card.show.call_args
        self.assertIn("İlk etkinlik", args[1])
        self.assertIn("E-posta gönderildi", args[1])
        self.assertEqual(kwargs, {"milliseconds": 5000, "open_photo": None})

    def test_pending_countdown_can_be_cancelled_before_monitoring(self):
        app = self.app()
        app.is_active = False
        app.config['arming_seconds'] = 5
        app.key_exit = 'alt+x'
        with patch.object(core.mouse, 'Listener') as listener:
            app.start_system('black')
            app.on_move(1, 1)
            self.assertIsNone(app.session.first_activity)
            app.start_system('black')
            app.card.countdown.assert_called_once()
            app.stop_system()
            app.root.after_cancel.assert_called_once()
            self.assertIsNone(app.pending_mode)
            listener.assert_not_called()

    def test_countdown_activates_latest_mode_then_preserves_session_on_switch(self):
        app = self.app()
        app.is_active = False
        app.config['arming_seconds'] = 1
        app.key_exit = 'f12'
        with patch.object(core.mouse, 'Listener'), patch.object(core, 'prevent_sleep'):
            app.start_system('spider')
            app.start_system('black')
            _, tick, remaining = app.root.after.call_args.args
            tick(remaining)
            self.assertEqual(app.active_mode, 'black')
            original = app.session
            app.start_system('invisible')
            self.assertIs(app.session, original)
            self.assertIsNone(app.pending_mode)

    def test_native_session_windows(self):
        subprocess.run([sys.executable, '-m', 'unittest', '-v', 'tests.session_windows'],
                       cwd=Path(__file__).resolve().parents[1], check=True, timeout=60)

    def test_tutorial_requires_three_shortcuts_and_separate_camera_approval(self):
        app=self.app()
        app.is_active=False
        app.camera_enabled=False
        app.last_trigger_time=0
        app.last_capture_time=0
        app.cooldown_seconds=3
        app.key_spider,app.key_black,app.key_lock,app.key_exit='alt+q','shift+w','ctrl+alt+y','ctrl+shift+x'
        app._resolve_hotkeys()
        app.root.after.side_effect=lambda delay,callback,*args: callback(*args) if delay==0 else 'preview'
        app.update_tray_icon=Mock()
        guide=SpiderpotTutorial.__new__(SpiderpotTutorial)
        guide.app,guide.step,guide.camera_armed,guide.capture_name=app,0,False,None
        guide.camera_port=app.camera_port
        guide.camera_error_text=''
        guide.render,guide.window,guide.status=Mock(),Mock(),Mock()
        guide.active_card,guide.card_heading,guide.card_instructions=Mock(),Mock(),Mock()
        app.tutorial=guide
        camera=Mock()
        frame=core.cv2.UMat(48,64,core.cv2.CV_8UC3,(0,0,0,0)).get()
        camera.isOpened.return_value=True
        camera.read.return_value=(True,frame)
        app.capture_store.save.return_value='test.spcap'

        def press(value, *modifiers):
            app.last_trigger_time=0
            app.on_global_press(core.keyboard.KeyCode.from_vk(ord(value)),frozenset(modifiers))

        with patch.object(core.mouse,'Listener'), \
                patch.object(core,'prevent_sleep'), patch.object(core,'allow_sleep'), \
                patch.object(core.cv2,'VideoCapture',return_value=camera) as video:
            press('W','shift')
            self.assertFalse(app.is_active)
            for step,(key,mods) in enumerate((('Q',('alt',)),('W',('shift',)),('Y',('ctrl','alt')))):
                press(key,*mods)
                self.assertTrue(app.is_active)
                guide.active_card.deiconify.assert_called()
                guide.active_card.lift.assert_called()
                app.capture_photo()
                if step == 0:
                    app.on_global_press(core.keyboard.Key.f12,frozenset())
                    self.assertTrue(app.is_active)
                press('X','ctrl','shift')
                self.assertEqual(guide.step,step+1)
            video.assert_not_called()
            press('Y','ctrl','alt')
            self.assertFalse(app.is_active)
            with patch('spiderpot_tutorial.messagebox.askyesno',return_value=False):
                guide.arm_camera()
            self.assertFalse(guide.camera_armed)
            with patch('spiderpot_tutorial.messagebox.askyesno',return_value=True):
                guide.arm_camera()
            guide.set_camera(1)
            press('Y','ctrl','alt')
            app.on_move(10, 10)
            app.capture_thread.join(timeout=2)
            self.assertFalse(app.capture_thread.is_alive())
            app.capture_photo()
            video.assert_called_once_with(1,core.cv2.CAP_DSHOW)
            app.viewer.show_capture.assert_called_once()
            press('X','ctrl','shift')

        self.assertEqual(guide.step,4)
        self.assertEqual(guide.capture_name,'test.spcap')
        self.assertFalse(app.camera_enabled)
        self.assertFalse(app.camera_allowed())


class ModeTests(unittest.TestCase):
    def test_keyboard_filter_suppresses_mode_and_pairs_releases_without_blocking_windows(self):
        class Suppressed(Exception):
            pass
        app=core.SpiderpotApp.__new__(core.SpiderpotApp)
        app.key_spider,app.key_black,app.key_lock,app.key_exit='alt+q','shift+w','ctrl+alt+y','ctrl+shift+x'
        app._resolve_hotkeys()
        app.key_events=SimpleQueue()
        app.suppressed_keys=set()
        app.passed_keys=set()
        app.input_listener=Mock()
        app.input_listener.suppress_event.side_effect=Suppressed
        app.is_active=False
        down,up=0x100,0x101
        def key(message,vk):
            return app._filter_keyboard(message,SimpleNamespace(vkCode=vk))
        with patch.object(core.ctypes.windll.user32,'GetAsyncKeyState',return_value=0), \
                patch.object(app,'_modifiers',return_value=frozenset({'alt'})):
            with self.assertRaises(Suppressed):
                key(down,ord('Q'))
            self.assertEqual(app.key_events.get_nowait(),(ord('Q'),frozenset({'alt'})))
            with self.assertRaises(Suppressed):
                key(up,ord('Q'))
            key(down,ord('K'))  # Passed before activation; its release must also pass.
            app.is_active=True
            key(up,ord('K'))
            with self.assertRaises(Suppressed):
                key(down,ord('G'))
            app.is_active=False
            with self.assertRaises(Suppressed):
                key(up,ord('G'))
        app.is_active=True
        with patch.object(core.ctypes.windll.user32,'GetAsyncKeyState',return_value=0), \
                patch.object(app,'_modifiers',return_value=frozenset({'ctrl','alt'})):
            self.assertFalse(key(down,0x2E))  # Windows secure shortcut.

    def test_original_mode_dispatch_and_mouse_trap_remain(self):
        for mode in ('spider','black','invisible'):
            with self.subTest(mode=mode):
                app=core.SpiderpotApp.__new__(core.SpiderpotApp)
                app.is_active=False
                app.session_generation=0
                app.capture_preview_job=None
                app.tutorial=None
                app.session_lock=threading.RLock()
                app.pending_mode=None
                app.dashboard=None
                app.config={'arming_seconds': 0}
                app.card=Mock()
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
                    app.viewer.show_mode.assert_called_once_with(mode_spider=mode=='spider',restart=True)

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
        app.tutorial=None
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
