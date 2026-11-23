"""Windows still-frame capture shared by settings and the active modes."""
import cv2


BACKENDS = (("DirectShow", cv2.CAP_DSHOW), ("Media Foundation", cv2.CAP_MSMF))


def capture_camera_frame(index, cancelled=lambda: False):
    errors = []
    for name, backend in BACKENDS:
        if cancelled():
            return None
        camera = None
        try:
            camera = cv2.VideoCapture(index, backend)
            if not camera.isOpened():
                errors.append(f"{name}: aygıt açılamadı")
                continue
            for _ in range(4):
                if cancelled():
                    return None
                valid, candidate = camera.read()
                if cancelled():
                    return None
                if valid and candidate is not None and candidate.size:
                    return candidate, name
            errors.append(f"{name}: görüntü alınamadı")
        except cv2.error:
            errors.append(f"{name}: kamera hatası")
        finally:
            if camera is not None:
                camera.release()
    raise RuntimeError(f"Kamera {index} kullanılamadı. " + "; ".join(errors))


def scan_cameras(cancelled=lambda: False):
    devices = {}
    for index in range(10):
        if cancelled():
            break
        try:
            result = capture_camera_frame(index, cancelled)
        except RuntimeError:
            continue
        if result is not None:
            frame, backend = result
            height, width = frame.shape[:2]
            devices[index] = f"Kamera {index} · {width} × {height} · {backend}"
    return devices
