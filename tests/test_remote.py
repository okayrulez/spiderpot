import hashlib
import json
from pathlib import Path
import socket
import ssl
import struct
import tempfile
import time
import unittest

from spiderpot_remote import DirectHost, encode_pairing
from spiderpot_support import crypt


def read_exact(connection, length):
    result = bytearray()
    while len(result) < length:
        chunk = connection.recv(length - len(result))
        if not chunk:
            raise EOFError()
        result.extend(chunk)
    return bytes(result)


def exchange(connection, request):
    encoded = json.dumps(request).encode("utf-8")
    connection.sendall(struct.pack(">I", len(encoded)) + encoded)
    size, = struct.unpack(">I", read_exact(connection, 4))
    response = json.loads(read_exact(connection, size))
    return response, read_exact(connection, response["bytes"])


class DirectHostTests(unittest.TestCase):
    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        self.folder = Path(self.storage.name)
        self.events = []
        self.host = self.start()

    def start(self):
        def record(event):
            self.events.append(event)
            return True
        host = DirectHost(self.folder, crypt, lambda: b"synthetic-frame", record,
                          port=0, bind="127.0.0.1")
        self.addCleanup(host.close)
        return host

    def dial(self):
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection = context.wrap_socket(socket.create_connection(("127.0.0.1", self.host.port), timeout=4))
        self.assertEqual(connection.version(), "TLSv1.3")
        self.assertEqual(hashlib.sha256(connection.getpeercert(binary_form=True)).hexdigest(), self.host.pin)
        return connection

    def test_pair_frame_input_and_revoke(self):
        code = self.host.pairing_code()
        self.assertTrue(encode_pairing(["127.0.0.1"], self.host.port, "PC", self.host.pin, code)
                        .startswith("spiderpot://pair/"))
        with self.dial() as connection:
            self.assertFalse(exchange(connection, {"type": "frame"})[0]["ok"])
        with self.dial() as connection:
            self.assertFalse(exchange(connection, {"type": "pair", "code": "wrong"})[0]["ok"])
        with self.dial() as connection:
            token = exchange(connection, {"type": "pair", "code": code})[0]["token"]
        with self.dial() as connection:
            self.assertFalse(exchange(connection, {"type": "pair", "code": code})[0]["ok"])
        with self.dial() as connection:
            self.assertTrue(exchange(connection, {"type": "hello", "token": token})[0]["ok"])
            frame, payload = exchange(connection, {"type": "frame"})
            self.assertFalse(frame["control"])
            self.assertEqual(payload, b"synthetic-frame")
            request = {"type": "input", "action": "click", "x": 0.5, "y": 0.5}
            self.assertFalse(exchange(connection, request)[0]["ok"])
            self.assertEqual(self.events, [])
            self.host.set_control(True)
            self.assertTrue(exchange(connection, request)[0]["ok"])
            self.assertEqual(self.events, [request])
            self.host.forget_phone()
            with self.assertRaises((OSError, EOFError)):
                exchange(connection, request)
        with self.dial() as connection:
            self.assertFalse(exchange(connection, {"type": "hello", "token": token})[0]["ok"])

    def test_identity_and_pairing_survive_host_restart(self):
        with self.dial() as connection:
            token = exchange(connection, {"type": "pair", "code": self.host.pairing_code()})[0]["token"]
        pin = self.host.pin
        self.host.close()
        self.host = self.start()
        self.assertEqual(self.host.pin, pin)
        self.assertNotIn(token, self.host.device_file.read_text("ascii"))
        with self.dial() as connection:
            self.assertTrue(exchange(connection, {"type": "hello", "token": token})[0]["ok"])

    def test_expired_qr_rejected(self):
        code = self.host.pairing_code()
        self.host.expiry = time.monotonic() - 1
        with self.dial() as connection:
            self.assertFalse(exchange(connection, {"type": "pair", "code": code})[0]["ok"])
