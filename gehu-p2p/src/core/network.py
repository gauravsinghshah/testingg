# network.py
import asyncio
import socket
import struct
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
from config import PSK, SERVICE_TYPE, PORT  # Ensure these are correctly defined in config.py


class P2PListener(ServiceListener):
    """Listens for Zeroconf service announcements on the network."""
    def __init__(self):
        self.services = []

    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info:
            self.services.append(info)

    def remove_service(self, zc, type_, name):
        self.services = [s for s in self.services if s.name != name]

    def update_service(self, zc, type_, name):
        # Optional: handle service updates
        pass


class NetworkManager:
    """Manages peer discovery and chunk-based data transfer."""
    def __init__(self, role):
        self.role = role
        self.peers = set()
        self.zeroconf = Zeroconf()
        self.listener = P2PListener()

    def send_chunks(self, address, chunks):
        """Send a list of data chunks to a peer."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((str(address), PORT))

            for chunk in chunks:
                data = chunk['data']
                chunk_id = chunk['id']
                hash_val = chunk['hash']
                total = chunk['total_chunks']

                # Send chunk metadata
                sock.sendall(struct.pack('!I I I', chunk_id, total, len(hash_val)))
                sock.sendall(hash_val.encode())

                # Send chunk data
                sock.sendall(struct.pack('!I', len(data)))
                sock.sendall(data)

            sock.close()
        except Exception as e:
            print(f"[-] Failed to send to {address}: {e}")

    async def discover_peers(self):
        """Continuously discover peers using Zeroconf and match PSK."""
        ServiceBrowser(self.zeroconf, SERVICE_TYPE, self.listener)
        while True:
            await asyncio.sleep(1)
            valid_peers = [
                s for s in self.listener.services
                if s.properties and s.properties.get(b'psk') == PSK.encode()
            ]
            self.peers = {s.parsed_addresses()[0] for s in valid_peers if s.parsed_addresses()}

    async def start_service(self):
        """Start the peer discovery loop."""
        print("[*] Starting peer discovery service...")
        await self.discover_peers()
