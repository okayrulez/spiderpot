import threading
import unittest
from unittest.mock import Mock, patch

from spiderpot_router import LEASE_SECONDS, RouterMapping


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = Mock()
        self.router.lanaddr = "192.168.1.20"
        self.router.externalipaddress.return_value = "93.184.216.34"
        self.router.discover.return_value = 1
        self.cancelled = threading.Event()
        self.entry = None
        self.router.getspecificportmapping.side_effect = lambda *_: self.entry
        self.router.addportmapping.side_effect = self.add

    def add(self, external, protocol, client, internal, label, remote, lifetime):
        self.entry = client, internal, label, True, self.returned_lease
        return True

    def open_mapping(self):
        with patch("spiderpot_router.miniupnpc.UPnP", return_value=self.router):
            return RouterMapping.open(49756, [self.router.lanaddr], self.cancelled)

    def test_short_lived_mapping_is_removed_only_if_owned(self):
        self.returned_lease = LEASE_SECONDS
        mapping = self.open_mapping()
        self.assertEqual(mapping.address, "93.184.216.34")
        mapping.close()
        self.router.deleteportmapping.assert_called_once_with(49756, "TCP")
        self.entry = self.router.lanaddr, 49756, "someone else", True, 600
        mapping.close()
        self.router.deleteportmapping.assert_called_once()

    def test_cgnat_does_not_modify_the_router(self):
        self.router.externalipaddress.return_value = "100.69.1.2"
        with self.assertRaisesRegex(ValueError, "CGNAT"):
            self.open_mapping()
        self.router.addportmapping.assert_not_called()

    def test_existing_rule_is_not_overwritten(self):
        self.entry = self.router.lanaddr, 49756, "existing", True, 0
        with self.assertRaisesRegex(ValueError, "zaten"):
            self.open_mapping()
        self.router.addportmapping.assert_not_called()

    def test_permanent_mapping_is_rejected_and_removed(self):
        self.returned_lease = 0
        with self.assertRaisesRegex(ValueError, "süreli"):
            self.open_mapping()
        self.router.deleteportmapping.assert_called_once_with(49756, "TCP")

    def test_stop_before_mapping_leaves_router_unchanged(self):
        self.cancelled.set()
        self.assertIsNone(self.open_mapping())
        self.router.addportmapping.assert_not_called()
