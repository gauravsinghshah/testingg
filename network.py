import socket
import threading
import os
import json
import time
import base64

class PeerNetwork:
    def __init__(self, port=8080, file_port=8081, on_peer_discovered=None, on_file_received=None, on_message_received=None, on_file_ack=None):
        self.port = port
        self.file_port = file_port
        self.message_port = 50008
        self.ack_port = 50010
        self.on_peer_discovered = on_peer_discovered
        self.on_file_received = on_file_received
        self.on_message_received = on_message_received
        self.on_file_ack = on_file_ack
        self.peers = []
        self.chunk_size = 1024 * 512

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('', self.port))

    def split_file_into_chunks(self, file_path):
        with open(file_path, 'rb') as f:
            data = f.read()
        chunks = [data[i:i+self.chunk_size] for i in range(0, len(data), self.chunk_size)]
        return chunks
    

    def listen_for_messages(self):
        print(f" Listening for messages on TCP port {self.message_port}...")
        msg_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        msg_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            msg_socket.bind(('', self.message_port))
            msg_socket.listen(5)

            while True:
                try:
                    conn, addr = msg_socket.accept()
                    thread = threading.Thread(target=self._handle_message, args=(conn, addr))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                    print(f" Error accepting message connection: {e}")
        except Exception as e:
            print(f" Error setting up message listener: {e}")

    def _handle_message(self, conn, addr):
        try:
            data = conn.recv(4096)
            if data:
                message = data.decode('utf-8')
                print(f" Received message from {addr[0]}: {message}")
                if self.on_message_received:
                    self.on_message_received(message, addr)
        except Exception as e:
            print(f" Error handling message: {e}")
        finally:
            conn.close()


    def send_file_chunks(self, file_path, peer_ip):
        file_name = os.path.basename(file_path)
        chunks = self.split_file_into_chunks(file_path)
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            try:
                header = json.dumps({
                    'file_name': file_name,
                    'chunk_index': i,
                    'total_chunks': total_chunks,
                    'chunk_size': len(chunk),
                    'chunk_data': base64.b64encode(chunk).decode('utf-8'),
                    'timestamp': time.time()
                })

                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(10)
                    s.connect((peer_ip, self.file_port))
                    s.sendall(header.encode('utf-8') + b'\n')

                print(f" Sent chunk {i+1}/{total_chunks} to {peer_ip}")
                time.sleep(0.1)

            except Exception as e:
                print(f" Error sending chunk {i} to {peer_ip}: {e}")

    def _handle_file_connection(self, conn, addr):
        try:
            header_data = b''
            while True:
                chunk = conn.recv(1024)
                if not chunk or b'\n' in chunk:
                    header_data += chunk.split(b'\n')[0]
                    break
                header_data += chunk
                if b'\n' in header_data:
                    header_data = header_data.split(b'\n')[0]
                    break

            if not header_data:
                print(f"⚠️ Empty header received from {addr[0]}")
                return

            print(f"📦 Raw header data from {addr[0]}: {header_data}")

            try:
                header = json.loads(header_data.decode('utf-8'))
                required_keys = ['file_name', 'chunk_index', 'total_chunks', 'chunk_data']
                for key in required_keys:
                    if key not in header:
                        print(f"⚠️ Missing key in received chunk header from {addr[0]}: {key}")
                        return

                file_name = header['file_name']
                chunk_index = header['chunk_index']
                total_chunks = header['total_chunks']
                chunk_data = base64.b64decode(header['chunk_data'])
                print(f" 📥 Chunk {chunk_index + 1}/{total_chunks} received from {addr[0]}: {file_name}")

                if self.on_file_received:
                    file_chunk_info = {
                        'file_name': file_name,
                        'chunk_index': chunk_index,
                        'total_chunks': total_chunks,
                        'data': chunk_data,
                        'sender': addr[0]
                    }
                    self.on_file_received(file_chunk_info, addr)

            except json.JSONDecodeError as jde:
                print(f"❌ JSON decode error from {addr[0]}: {jde}")
            except Exception as e:
                print(f"❌ Error parsing chunk header from {addr[0]}: {e}")

        except Exception as e:
            print(f"❌ Error receiving chunk from {addr[0]}: {e}")

        finally:
            conn.close()

    # Other methods remain unchanged (listen_for_peers, discover_peers, send_message, etc.)


    def listen_for_peers(self):
        """Listen for incoming peer broadcasts"""
        print(f" Listening for peer discovery on UDP port {self.port}...")
        while True:
            try:
                message, address = self.socket.recvfrom(1024)
                message = message.decode('utf-8')
                if message == "DISCOVER_PEER":
                    peer_ip = address[0]
                    # Only add peer if not already in list (comparing just IP)
                    if peer_ip not in [p[0] if isinstance(p, tuple) else p for p in self.peers]:
                        self.peers.append(address)
                        print(f"Discovered new peer: {peer_ip}")
                        if self.on_peer_discovered:
                            self.on_peer_discovered(message, address)
                    # Send response to let the peer know we exist
                    self.socket.sendto(b"PEER_ACK", address)
            except Exception as e:
                print(f" Error in listening for peers: {e}")

    def discover_peers(self):
        """Broadcast to discover peers"""
        try:
            print(" Broadcasting peer discovery...")
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            broadcast_socket.sendto(b"DISCOVER_PEER", ("<broadcast>", self.port))
            broadcast_socket.close()
        except Exception as e:
            print(f" Error broadcasting discovery: {e}")

    def listen_for_files(self):
        """Listen for incoming file transfers over TCP"""
        print(f" Listening for incoming files on TCP port {self.file_port}...")
        file_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        file_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        file_socket.bind(('', self.file_port))
        file_socket.listen(5)

        while True:
            try:
                conn, addr = file_socket.accept()
                thread = threading.Thread(target=self._handle_file_connection, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f" Error in file listener: {e}")

    def listen_for_acks(self):
        """Listen for file reception acknowledgements"""
        print(f" Listening for file ACKs on TCP port {self.ack_port}...")
        ack_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ack_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ack_socket.bind(('', self.ack_port))
        ack_socket.listen(5)

        while True:
            try:
                conn, addr = ack_socket.accept()
                thread = threading.Thread(target=self._handle_ack, args=(conn, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                print(f" Error in ACK listener: {e}")

    def _handle_ack(self, conn, addr):
        """Handle incoming file acknowledgement"""
        try:
            data = conn.recv(1024)
            if data:
                ack_data = json.loads(data.decode('utf-8'))
                file_name = ack_data.get('file_name', 'unknown')
                status = ack_data.get('status', 'unknown')
                print(f" Received ACK from {addr[0]} for file {file_name}: {status}")
                if self.on_file_ack:
                    self.on_file_ack(file_name, status, addr)
        except Exception as e:
            print(f" Error handling ACK: {e}")
        finally:
            conn.close()

    def send_file_ack(self, peer_ip, file_name, status):
        """Send acknowledgement for received file"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)  # Set timeout for connection
                s.connect((peer_ip, self.ack_port))
                
                ack_data = json.dumps({
                    'file_name': file_name,
                    'status': status,
                    'timestamp': time.time()
                })
                
                s.sendall(ack_data.encode('utf-8'))
                print(f" ACK sent to {peer_ip} for file {file_name}")
                return True
        except Exception as e:
            print(f" Error sending ACK to {peer_ip}: {e}")
            return False

    def _handle_file_connection(self, conn, addr):
        """Handle incoming file connection"""
        try:
            print(f" Incoming file connection from {addr[0]}...")
            # First receive the header with metadata
            header_data = b''
            while True:
                chunk = conn.recv(1024)
                if not chunk or b'\n' in chunk:
                    header_data += chunk.split(b'\n')[0]
                    break
                header_data += chunk
                if b'\n' in header_data:
                    header_data = header_data.split(b'\n')[0]
                    break
            
            if not header_data:
                print(f" Empty header from {addr[0]}")
                return
            
            # Parse header
            try:
                header = json.loads(header_data.decode('utf-8'))
                file_name = header['file_name']
                file_size = int(header['file_size'])
                print(f" Receiving file: {file_name} ({file_size} bytes) from {addr[0]}")
            except Exception as e:
                print(f" Error parsing file header: {e}")
                return
            
            # Receive file data
            received_data = b''
            remaining = file_size
            
            # Receive any data that might have come with the header
            if b'\n' in chunk:
                received_data += chunk.split(b'\n', 1)[1]
                remaining -= len(received_data)
            
            # Continue receiving data
            while remaining > 0:
                chunk = conn.recv(min(4096, remaining))
                if not chunk:
                    break
                received_data += chunk
                remaining -= len(chunk)
                
                # Print progress for large files
                if file_size > 1000000:  # 1MB
                    percent = int((file_size - remaining) / file_size * 100)
                    if percent % 10 == 0:
                        print(f" Receiving {file_name}: {percent}% complete")
            
            print(f"📦 Received file: {file_name} ({len(received_data)} bytes) from {addr[0]}")

            # Send acknowledgement
            self.send_file_ack(addr[0], file_name, "success")
            
            if self.on_file_received:
                # Create file data dictionary
                file_data = {
                    "type": "file_transfer",
                    "file_name": file_name,
                    "file_size": len(received_data),
                    "sender_ip": addr[0],
                    "file_data": received_data  # Raw binary data
                }
                self.on_file_received(file_data, addr)

        except Exception as e:
            print(f" Error receiving file: {e}")
            # Try to send a failure acknowledgement
            try:
                self.send_file_ack(addr[0], "unknown", f"failed: {str(e)}")
            except:
                pass
        finally:
            conn.close()

    def send_file(self, file_path, peer_ip):
        """Send a file to a specific peer via TCP"""
        try:
            file_name = os.path.basename(file_path)
            with open(file_path, 'rb') as file:
                file_data = file.read()
                file_size = len(file_data)

            print(f" Connecting to {peer_ip}:{self.file_port} to send {file_name}...")
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(10)  # Set timeout for connection
            peer_socket.connect((peer_ip, self.file_port))

            # Send metadata header as JSON followed by newline
            header = json.dumps({
                'file_name': file_name,
                'file_size': file_size,
                'timestamp': time.time()
            })
            peer_socket.sendall(header.encode('utf-8') + b'\n')

            # Send file data
            peer_socket.sendall(file_data)
            peer_socket.close()
            print(f" File sent to {peer_ip}: {file_name} ({file_size} bytes)")
            return True
        except Exception as e:
            print(f" Error sending file to {peer_ip}: {e}")
            return False
