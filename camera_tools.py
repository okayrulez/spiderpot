import cv2


CAMERA_BACKENDS = (
    ("DirectShow", cv2.CAP_DSHOW),
    ("Media Foundation", cv2.CAP_MSMF),
)


def _read_frame(camera, attempts=8):
    frame = None
    for _ in range(attempts):
        ok, candidate = camera.read()
        if ok and candidate is not None and getattr(candidate, "size", 0):
            frame = candidate
    return frame


def capture_camera_frame(camera_index):
    index = int(camera_index)
    errors = []
    for backend_name, backend in CAMERA_BACKENDS:
        camera = None
        try:
            camera = cv2.VideoCapture(index, backend)
            if not camera.isOpened():
                errors.append(f"{backend_name}: aygıt açılamadı")
                continue
            frame = _read_frame(camera)
            if frame is not None:
                return frame, backend_name
            errors.append(f"{backend_name}: görüntü alınamadı")
        except Exception as error:
            errors.append(f"{backend_name}: {type(error).__name__}: {error}")
        finally:
            if camera is not None:
                try:
                    camera.release()
                except Exception:
                    pass
    raise RuntimeError("; ".join(errors) or f"Kamera {index} kullanılamadı.")


def scan_camera_devices(max_devices=8):
    devices = []
    for index in range(max(1, int(max_devices))):
        try:
            frame, backend_name = capture_camera_frame(index)
            height, width = frame.shape[:2]
            devices.append(
                {
                    "index": index,
                    "label": f"Kamera {index} — {width}x{height} ({backend_name})",
                    "backend": backend_name,
                    "width": width,
                    "height": height,
                }
            )
        except Exception:
            continue
    return devices
