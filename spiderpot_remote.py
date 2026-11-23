"""Direct TLS transport for an explicitly enabled Spiderpot session."""

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import ssl
import struct
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

PORT = 49756
MAX_REQUEST = 4096
MAX_FRAME = 2 * 1024 * 1024
QR_PREFIX = "spiderpot://pair/"
BETA_PROTOCOL = "spiderpot-direct-1"


def _write_private(path, content):
    temp = path.with_suffix(".tmp")
    temp.write_bytes(content)
    temp.replace(path)


def host_identity(folder, protect):
    """Persist a certificate with a Windows-user-protected private key password."""
    folder.mkdir(parents=True, exist_ok=True)
    password_file = folder / "identity-password.bin"
    identity_file = folder / "identity.pem"
    if password_file.exists():
        password = protect(password_file.read_bytes(), decrypt=True)
    elif identity_file.exists():
        raise OSError("Spiderpot bağlantı kimliğinin şifresi bulunamadı.")
    else:
        password = secrets.token_hex(32).encode("ascii")
        _write_private(password_file, protect(password))
    if not identity_file.exists():
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Spiderpot Direct")])
        now = datetime.now(timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1))
            .not_valid_after(now + timedelta(days=730))
            .sign(key, hashes.SHA256())
        )
        _write_private(
            identity_file,
            cert.public_bytes(serialization.Encoding.PEM) + key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.BestAvailableEncryption(password),
            ),
        )
    cert = x509.load_pem_x509_certificate(identity_file.read_bytes())
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(identity_file, password=password)
    return context, cert.fingerprint(hashes.SHA256()).hex()


def encode_pairing(addresses, port, name, pin, code):
    payload = json.dumps(
        {"protocol": BETA_PROTOCOL, "hosts": addresses, "port": port,
         "name": name[:40], "pin": pin, "code": code},
        separators=(",", ":"), ensure_ascii=False,
    ).encode()
    return QR_PREFIX + base64.urlsafe_b64encode(payload).decode().rstrip("=")


def checked_host(value):
    value = value.strip()
    if not value:
        return ""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        labels = value.rstrip(".").split(".")
        if not (len(labels) > 1 and len(value) <= 253 and all(
            0 < len(part) <= 63 and part[0].isalnum() and part[-1].isalnum()
            and all(c.isascii() and (c.isalnum() or c == "-") for c in part)
            for part in labels
        )):
            raise ValueError("Geçerli bir dış IP adresi veya DNS adı girin.") from None
        return value.lower()
    if address.is_unspecified or address.is_loopback or address.is_multicast or address.is_link_local:
        raise ValueError("Dış bağlantı için erişilebilir bir IP adresi girin.")
    return str(address)


def _read_exact(connection, size, deadline):
    data = bytearray()
    while len(data) < size:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        connection.settimeout(remaining)
        chunk = connection.recv(size - len(data))
        if not chunk:
            raise EOFError()
        data.extend(chunk)
    return bytes(data)


def _request(connection, timeout):
    deadline = time.monotonic() + timeout
    size, = struct.unpack(">I", _read_exact(connection, 4, deadline))
    if not 0 < size <= MAX_REQUEST:
        raise ValueError("Request size")
    value = json.loads(_read_exact(connection, size, deadline))
    if not isinstance(value, dict):
        raise ValueError("Request format")
    return value


def _response(connection, value, frame=b""):
    header = json.dumps({**value, "bytes": len(frame)}, separators=(",", ":")).encode()
    connection.settimeout(4)
    connection.sendall(struct.pack(">I", len(header)) + header)
    if frame:
        connection.sendall(frame)


class DirectHost:
    def __init__(self, folder, protect, capture, input_event, *, port=PORT, bind=None):
        context, pin = host_identity(folder, protect)
        self.pin = pin
        self.context = context
        self.capture = capture
        self.input_event = input_event
        self.device_file = folder / "paired-phone.sha256"
        self.device_hash = self.device_file.read_text("ascii").strip() if self.device_file.exists() else ""
        self.lock = threading.Lock()
        self.workers = threading.BoundedSemaphore(6)
        self.connections = set()
        self.closed = threading.Event()
        self.session = None
        self.control = False
        self.code = ""
        self.expiry = 0
        self.listener = self._listen(port, bind)
        self.port = self.listener.getsockname()[1]
        threading.Thread(target=self._accept, daemon=True).start()

    @staticmethod
    def _listen(port, bind):
        if bind is None:
            try:
                listener = socket.create_server(("::", port), family=socket.AF_INET6, dualstack_ipv6=True)
            except (OSError, ValueError):
                listener = socket.create_server(("0.0.0.0", port))
        else:
            listener = socket.create_server((bind, port))
        listener.settimeout(0.25)
        return listener

    def pairing_code(self):
        with self.lock:
            self.code = secrets.token_urlsafe(24)
            self.expiry = time.monotonic() + 120
            return self.code

    def cancel_pairing(self):
        with self.lock:
            self.code = ""

    def forget_phone(self):
        with self.lock:
            self.device_file.unlink(missing_ok=True)
            self.device_hash = ""
            self.code = ""
            if self.session is not None:
                self._close_connection(self.session)

    def set_control(self, enabled):
        with self.lock:
            self.control = enabled

    @property
    def connected(self):
        with self.lock:
            return self.session is not None

    @staticmethod
    def _close_connection(connection):
        try:
            connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        connection.close()

    def close(self):
        self.closed.set()
        self.listener.close()
        with self.lock:
            self.code = ""
            for connection in self.connections:
                self._close_connection(connection)

    def _accept(self):
        while not self.closed.is_set():
            try:
                raw, _ = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            if self.workers.acquire(blocking=False):
                threading.Thread(target=self._handle, args=(raw,), daemon=True).start()
            else:
                raw.close()

    def _authenticate(self, connection, message):
        kind = message.get("type")
        with self.lock:
            if self.closed.is_set():
                return {"ok": False, "error": "closed"}
            if kind == "pair":
                code = message.get("code")
                if (not self.code or time.monotonic() >= self.expiry
                        or not isinstance(code, str) or not code.isascii()
                        or not hmac.compare_digest(self.code, code)):
                    return {"ok": False, "error": "pairing_expired"}
                if self.session is not None:
                    return {"ok": False, "error": "busy"}
                token = secrets.token_urlsafe(32)
                digest = hashlib.sha256(token.encode()).hexdigest()
                _write_private(self.device_file, digest.encode("ascii"))
                self.device_hash = digest
                self.code = ""
                return {"ok": True, "token": token}
            token = message.get("token")
            digest = hashlib.sha256(token.encode()).hexdigest() if isinstance(token, str) else ""
            if kind != "hello" or not digest or not hmac.compare_digest(digest, self.device_hash):
                return {"ok": False, "error": "unauthorized"}
            if self.session is not None:
                return {"ok": False, "error": "busy"}
            self.session = connection
            return {"ok": True}

    def _handle(self, raw):
        connection = raw
        try:
            raw.settimeout(5)
            with self.lock:
                if self.closed.is_set():
                    return
                connection = self.context.wrap_socket(raw, server_side=True, do_handshake_on_connect=False)
                self.connections.add(connection)
            connection.do_handshake()
            hello = _request(connection, 5)
            response = self._authenticate(connection, hello)
            _response(connection, response)
            if not response["ok"] or hello["type"] != "hello":
                return
            last_frame = 0.0
            while not self.closed.is_set():
                message = _request(connection, 12)
                if message.get("type") == "frame":
                    delay = 0.15 - (time.monotonic() - last_frame)
                    if delay > 0 and self.closed.wait(delay):
                        break
                    jpeg = self.capture()
                    last_frame = time.monotonic()
                    if not jpeg or len(jpeg) > MAX_FRAME:
                        _response(connection, {"ok": False, "error": "screen_unavailable"})
                        continue
                    with self.lock:
                        control = self.control
                    _response(connection, {"ok": True, "control": control}, jpeg)
                elif message.get("type") == "input":
                    with self.lock:
                        allowed = self.control and not self.closed.is_set() and self.input_event(message)
                    _response(connection, {"ok": bool(allowed), "error": "" if allowed else "input_disabled"})
                else:
                    break
        except (OSError, EOFError, ValueError, TypeError):
            pass
        finally:
            with self.lock:
                self.connections.discard(connection)
                if self.session is connection:
                    self.session = None
            connection.close()
            self.workers.release()
