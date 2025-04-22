import socket
import threading
import json
import os
import time

class PeerNetwork:
    def __init__(self, port=8081, on_file_received=None, on_peer_discovered=None):
        self.port = port
        self.host = socket.gethostbyname(socket.gethostname())
        self.peers = {}
        self.is_listening = True
        self.last_broadcast_time = 0  # Track last broadcast time
        
        # Callbacks for GUI integration
        self.on_file_received = on_file_received
        self.on_peer_discovered = on_peer_discovered
    
    def discover_peers(self):
        """Broadcast presence to local network"""
        current_time = time.time()
        if current_time - self.last_broadcast_time < 5:  # Prevent broadcasting too often
            return

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
            self.last_broadcast_time = current_time  # Update the last broadcast time
        except Exception as e:
            error_msg = f"❌ Error broadcasting presence: {str(e)}"
            print(error_msg)
            if self.on_file_received:
                self.on_file_received(error_msg, ('localhost', self.port))
        finally:
            sock.close()
        
    def broadcast(self, message):
        """Broadcast a message to all known peers except itself"""
        for peer_ip in self.peers:
            # Skip the local host IP to prevent sending messages to itself
            if peer_ip != self.host:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    sock.sendto(message.encode(), (peer_ip, self.port))
                    print(f"Message sent to {peer_ip}")
                except Exception as e:
                    print(f"Error sending message to {peer_ip}: {str(e)}")
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
                        peer_ip = addr[0]
                        if peer_ip not in self.peers:  # Avoid adding the same peer multiple times
                            self.peers[peer_ip] = message_data
                            print(f"🔍 Discovered peer: {peer_ip}")
                            if self.on_peer_discovered:
                                self.on_peer_discovered(message_data, addr)

                        else:
                            print(f"Peer {peer_ip} already known.")

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
