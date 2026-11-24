"""Explicit, short-lived IPv4 access through a compatible home router."""

import ipaddress
import secrets
import time

import miniupnpc


LEASE_SECONDS = 900


class RouterMapping:
    def __init__(self, router, port, address):
        self.router = router
        self.port = port
        self.address = address
        self.label = "Spiderpot-" + secrets.token_hex(8)
        self.expires_at = 0.0

    @classmethod
    def open(cls, port, local_addresses, cancelled):
        router = miniupnpc.UPnP()
        router.discoverdelay = 1500
        if not router.discover():
            raise ValueError("Modemde UPnP bulunamadı. Varsa dış IP veya DNS adresini elle gir.")
        router.selectigd()
        if router.lanaddr not in local_addresses:
            raise ValueError("Modemin seçtiği yerel adres bu PC’ye ait değil.")
        address = ipaddress.IPv4Address(router.externalipaddress())
        if not address.is_global or address.is_multicast or address.is_reserved:
            if address in ipaddress.IPv4Network("100.64.0.0/10"):
                raise ValueError("Modem CGNAT arkasında. UPnP ile internetten doğrudan erişim açılamaz.")
            raise ValueError("Modemin WAN IPv4 adresi genel değil. Çift NAT veya CGNAT olabilir.")
        mapping = cls(router, port, str(address))
        if router.getspecificportmapping(port, "TCP") is not None:
            raise ValueError(f"Modemde TCP {port} zaten yönlendirilmiş. Mevcut kuralı kullanıyorsan dış adresi elle gir.")
        if cancelled.is_set():
            return None
        starts = time.monotonic()
        if not router.addportmapping(port, "TCP", router.lanaddr, port, mapping.label, "", LEASE_SECONDS):
            raise ValueError("Modem süreli TCP yönlendirmesini açamadı.")
        try:
            entry = router.getspecificportmapping(port, "TCP")
            if not mapping.owns(entry) or not entry[3] or not 0 < entry[4] <= LEASE_SECONDS:
                raise ValueError("Modem süreli yönlendirmeyi doğrulamadı.")
            if cancelled.is_set():
                mapping.close()
                return None
            mapping.expires_at = min(starts + LEASE_SECONDS, time.monotonic() + entry[4])
        except Exception:
            mapping.close()
            raise
        return mapping

    def owns(self, entry):
        return entry is not None and entry[:3] == (self.router.lanaddr, self.port, self.label)

    def close(self):
        if self.owns(self.router.getspecificportmapping(self.port, "TCP")):
            self.router.deleteportmapping(self.port, "TCP")
