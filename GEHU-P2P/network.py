import socket
import threading
import json
import os

class PeerNetwork:
    def __init__(self, port=8081, on_file_received=None, on_peer_discovered=None):
        self.port = port
        self.host = socket.gethostbyname(socket.gethostname())
        self.peers = {}
        self.is_listening = True

        # Callbacks for GUI integration
        self.on_file_received = on_file_received
        self.on_peer_discovered = on_peer_discovered
    
    def discover_peers(self):
        """Broadcast presence to local network"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        message = json.dumps({
            "type": "discover",
            "host": self.host,
            "port": self.port
        })

        try:
            sock.sendto(message.encode(), ('<broadcast>', self.port))
            print("📡 Broadcasting presence to local network...")
        except Exception as e:
            error_msg = f"❌ Error broadcasting presence: {str(e)}"
            print(error_msg)
            if self.on_file_received:
                self.on_file_received(error_msg, ('localhost', self.port))
        finally:
            sock.close()


    def listen_for_peers(self):
        """Listen for incoming peer broadcasts or file transfers"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind(('', self.port))
            print(f"Listening for peers on port {self.port}...")
        except OSError as e:
            error_msg = f"❌ ERROR: Port {self.port} is already in use. Please close the conflicting process or choose a different port."
            print(error_msg)
            if self.on_file_received:
                self.on_file_received(error_msg, ('localhost', self.port))
            return

        while self.is_listening:
            try:
                data, addr = sock.recvfrom(65536)
                if not data:
                    continue

                # Check if data is already a string (i.e., no need to decode)
                message = data.decode() if isinstance(data, bytes) else data
                print(f"Received data: {message}")

                try:
                    message_data = json.loads(message)
                    msg_type = message_data.get("type")

                    if msg_type == "discover":
                        self.peers[addr[0]] = message_data
                        print(f"🔍 Discovered peer: {addr[0]}")
                        if self.on_peer_discovered:
                            self.on_peer_discovered(message_data, addr)

                    elif msg_type == "file_transfer":
                        file_name = message_data["file_name"]
                        file_data = bytes.fromhex(message_data["file_data"])
                        with open(file_name, 'wb') as f:
                            f.write(file_data)
                        print(f"✅ File {file_name} received and saved.")
                        if self.on_file_received:
                            self.on_file_received(f"file:{file_name}", addr)

                except json.JSONDecodeError:
                    # Handle plain-text fallback (e.g., file:<name>:<path>)
                    print(f"📦 Received fallback message from {addr}: {message}")
                    if message.startswith("file:") and self.on_file_received:
                        self.on_file_received(message, addr)

            except Exception as e:
                error_msg = f"❌ Error receiving data: {e}"
                print(error_msg)
                if self.on_file_received:
                    self.on_file_received(error_msg, ('localhost', self.port))

