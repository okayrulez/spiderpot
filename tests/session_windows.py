"""Exercise native Tk windows on their own process main thread."""
import time
import unittest
from unittest.mock import Mock, patch

from Assets import Spiderpot_Core as core
import spiderpot_support as support
from spiderpot_tutorial import QuickCheck
from tests import test_store


class SessionWindows(unittest.TestCase):
    def test_countdown_updates_in_place_without_mapping_or_resizing(self):
        root = core.tk.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()
        card = core.DesktopCard(root)
        card.countdown(10, "F12")
        root.update()
        window = card.window
        frame, bounds = window.frame(), window.geometry()
        remaps = []
        window.bind("<Unmap>", lambda event: remaps.append(event))
        window.bind("<Map>", lambda event: remaps.append(event))
        for seconds in (9, 8, 1):
            card.countdown(seconds, "F12")
            root.update()
            self.assertIs(card.window, window)
            self.assertEqual(window.frame(), frame)
            self.assertEqual(window.geometry(), bounds)
            self.assertTrue(window.winfo_viewable())
            self.assertEqual(card.seconds_label.cget("text"), f"{seconds} sn")
        self.assertFalse(remaps)
        ctypes = core.ctypes
        gdi = ctypes.windll.gdi32
        gdi.CreateRectRgn.restype = ctypes.wintypes.HANDLE
        region = ctypes.wintypes.HANDLE(gdi.CreateRectRgn(0, 0, 0, 0))
        try:
            hwnd = ctypes.wintypes.HWND(int(frame, 16))
            self.assertNotEqual(ctypes.windll.user32.GetWindowRgn(hwnd, region), 0)
            self.assertFalse(gdi.PtInRegion(region, 0, 0))
            self.assertTrue(gdi.PtInRegion(region, window.winfo_width()//2, window.winfo_height()//2))
        finally:
            gdi.DeleteObject(region)
        card.hide()
        self.assertIsNone(card.seconds_label)

    def test_quick_check_uses_configured_shortcut_and_real_activity_path(self):
        app = test_store.CaptureTests().app()
        app.is_active = False
        app.key_spider, app.key_black, app.key_lock, app.key_exit = 'alt+q', '2', '3', 'end'
        app._resolve_hotkeys()
        app.last_trigger_time = 0
        app.viewer.slide_paths = [support.resource('Assets/spiderpot-wallpaper.jpg')]
        app.root = core.tk.Tk()
        self.addCleanup(app.root.destroy)
        app.root.withdraw()
        app.mailer = Mock()
        with patch.object(core.mouse, 'Listener'), patch.object(core, 'prevent_sleep'), patch.object(core, 'allow_sleep'):
            app.open_check()
            self.assertIsInstance(app.tutorial, QuickCheck)
            self.assertIn('Alt + Q', app.tutorial.shortcut.cget('text'))
            app.on_global_press(ord('Q'), frozenset({'alt'}))
            app.viewer.show_mode.assert_called_once_with(mode_spider=True, restart=True)
            app.on_move(10, 12)
            app.on_global_press(core.keyboard.Key.end, frozenset())
            self.assertIn('etkinliği algılandı', app.tutorial.instructions.cget('text'))
            self.assertIn('Kamera denenmedi', app.tutorial.instructions.cget('text'))
            app.mailer.send_once.assert_not_called()
            app.mailer.client.alert.assert_not_called()
            app.mailer.client.alert.return_value = False
            app.tutorial.test_mail()
            deadline = time.monotonic() + 3
            def wait_for_mail():
                if app.tutorial.mail_running and time.monotonic() < deadline:
                    app.root.after(20, wait_for_mail)
                else:
                    app.root.quit()
            app.root.after(20, wait_for_mail)
            app.root.mainloop()
            app.mailer.client.alert.assert_called_once_with(app.mailer.token)
            self.assertIn("sınırına ulaşıldı", app.tutorial.status.cget('text'))
            app.tutorial.reset()
            self.assertFalse(app.tutorial.finished)
            app.close_tutorial()

    def test_desktop_card_expires_above_taskbar(self):
        root = core.tk.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()
        card = core.DesktopCard(root)
        card.show('Oturum özeti', '5 sn  ·  Klavye veya fare etkinliği algılanmadı', milliseconds=5000)
        root.update()
        rect = core.ctypes.wintypes.RECT()
        self.assertTrue(core.ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, core.ctypes.byref(rect), 0))
        win = card.window
        self.assertAlmostEqual(win.winfo_rootx() + win.winfo_width(), rect.right - 16, delta=2)
        self.assertAlmostEqual(win.winfo_rooty() + win.winfo_height(), rect.bottom - 14, delta=2)
        started = time.monotonic()
        while card.window is not None and time.monotonic() - started < 6:
            root.update()
            time.sleep(0.02)
        self.assertIsNone(card.window)
        self.assertGreater(time.monotonic() - started, 4.6)

