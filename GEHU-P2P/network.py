import socket
import threading
import json
import os

class PeerNetwork:
    def __init__(self, port=8081):
        self.port = port
        self.host = socket.gethostbyname(socket.gethostname())
        self.peers = {}
        self.is_listening = False

    def listen_for_peers(self):
        """Listen for incoming peer broadcasts"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            sock.bind(('', self.port))
            print(f"Listening for peers on port {self.port}...")
        except OSError as e:
            print(f"ERROR: Port {self.port} is already in use. Please close the conflicting process or choose a different port.")
            return  # Exit the function to avoid further issues

        while self.is_listening:
            data, addr = sock.recvfrom(1024)  # Receive data
            if data:
                try:
                    message = data.decode()
                    print(f"Received data: {message}")
                    # Attempt to load JSON
                    message_data = json.loads(message)
                    if message_data.get("type") == "discover":
                        self.peers[addr[0]] = message_data
                        print(f"Discovered peer: {addr[0]}")
                except json.JSONDecodeError:
                    print(f"Received invalid JSON from {addr}")
                except Exception as e:
                    print(f"Error processing data from {addr}: {str(e)}")

    def start_listening(self):
        """Start the listening thread"""
        self.is_listening = True
        listening_thread = threading.Thread(target=self.listen_for_peers)
        listening_thread.start()

    def stop_listening(self):
        """Stop the listening process"""
        self.is_listening = False

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
            print("Broadcasting presence to local network...")
        except Exception as e:
            print(f"Error broadcasting presence: {str(e)}")
        finally:
            sock.close()

    def broadcast(self, message):
        """Broadcast a message to all known peers"""
        for peer_ip in self.peers:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            try:
                sock.sendto(message.encode(), (peer_ip, self.port))
                print(f"Message sent to {peer_ip}")
            except Exception as e:
                print(f"Error sending message to {peer_ip}: {str(e)}")
            finally:
                sock.close()

    def send_file(self, file_path, peer_ip):
        """Send a file to a peer"""
        if not os.path.exists(file_path):
            print(f"File {file_path} does not exist.")
            return

        file_name = os.path.basename(file_path)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
                # Create JSON message with file name and content
                message = json.dumps({
                    "type": "file_transfer",
                    "file_name": file_name,
                    "file_data": file_data.hex()  # Convert binary data to hex string
                })
                sock.sendto(message.encode(), (peer_ip, self.port))
                print(f"File {file_name} sent to {peer_ip}")
        except Exception as e:
            print(f"Error sending file {file_name}: {str(e)}")
        finally:
            sock.close()

    def receive_file(self, data):
        """Process received file data from peers"""
        try:
            message_data = json.loads(data.decode())
            if message_data.get("type") == "file_transfer":
                file_name = message_data["file_name"]
                file_data = bytes.fromhex(message_data["file_data"])  # Convert hex back to bytes
                with open(file_name, 'wb') as file:
                    file.write(file_data)
                print(f"File {file_name} received and saved.")
        except json.JSONDecodeError:
            print("Received invalid file transfer data.")
        except Exception as e:
            print(f"Error receiving file: {str(e)}")
