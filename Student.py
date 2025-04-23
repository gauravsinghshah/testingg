import sys
import threading
import json
import os
import base64
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QTreeWidget, QTreeWidgetItem, 
                             QPushButton, QLabel, QFileDialog, QMessageBox, QGroupBox)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, Qt
from network import PeerNetwork

class SignalHandler(QObject):
    message_received = pyqtSignal(str)
    file_received = pyqtSignal(str, str, str, int)
    peer_discovered = pyqtSignal(str)
    show_message_box = pyqtSignal(str, str, int)

class StudentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEHU P2P - Student")
        self.resize(800, 600)

        self.signal_handler = SignalHandler()
        self.signal_handler.message_received.connect(self.update_messages)
        self.signal_handler.file_received.connect(self.add_file_to_list)
        self.signal_handler.peer_discovered.connect(self.update_messages)
        self.signal_handler.show_message_box.connect(self.display_message_box)

        self.received_chunks = {}
        self.expected_chunks = {}
        self.received_files = {}
        self.chunk_registry = {}

        self.network = PeerNetwork(
            on_file_received=self.handle_file_chunk,
            on_peer_discovered=self.handle_peer_discovery,
            on_message_received=self.handle_peer_message
        )

        self.init_ui()
        self.start_listening()
        self.join_session()

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)

        messages_group = QGroupBox("Received Messages")
        messages_layout = QVBoxLayout(messages_group)
        self.messages_text = QTextEdit()
        self.messages_text.setReadOnly(True)
        messages_layout.addWidget(self.messages_text)
        main_layout.addWidget(messages_group)

        files_group = QGroupBox("Shared Files")
        files_layout = QVBoxLayout(files_group)
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["Name", "Size", "Shared By"])
        self.files_tree.setColumnWidth(0, 250)
        self.files_tree.setColumnWidth(1, 100)
        self.files_tree.setColumnWidth(2, 150)
        files_layout.addWidget(self.files_tree)

        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(self.download_file)
        download_btn.setStyleSheet("background-color: #6C63FF; color: white;")
        files_layout.addWidget(download_btn)
        main_layout.addWidget(files_group)

        self.setCentralWidget(central_widget)

    @pyqtSlot(str, str, int)
    def display_message_box(self, title, message, icon_type=QMessageBox.Information):
        if icon_type == QMessageBox.Warning:
            QMessageBox.warning(self, title, message)
        else:
            QMessageBox.information(self, title, message)

    def handle_peer_discovery(self, message, addr):
        self.signal_handler.peer_discovered.emit(f"Discovered peer: {addr[0]}")

    def handle_peer_message(self, message, sender_address):
        ip = sender_address[0]
        try:
            if message.startswith("CHUNK_ANNOUNCE"):
                _, filename, chunk_idx = message.split("|")
                chunk_idx = int(chunk_idx)
                self.chunk_registry.setdefault(filename, {}).setdefault(chunk_idx, []).append(ip)
                self.signal_handler.message_received.emit(f"📣 {ip} has chunk {chunk_idx} of {filename}")

            elif message.startswith("REQUEST_CHUNK"):
                _, filename, chunk_idx = message.split("|")
                chunk_idx = int(chunk_idx)
                if filename in self.received_chunks and chunk_idx in self.received_chunks[filename]:
                    chunk_data = base64.b64encode(self.received_chunks[filename][chunk_idx]).decode('utf-8')
                    reply = f"CHUNK_DATA|{filename}|{chunk_idx}|{chunk_data}"
                    self.network.send_message(ip, reply)

            elif message.startswith("CHUNK_DATA"):
                _, filename, chunk_idx, chunk_data_b64 = message.split("|", 3)
                chunk_idx = int(chunk_idx)
                chunk_data = base64.b64decode(chunk_data_b64)
                if filename not in self.received_chunks:
                    self.received_chunks[filename] = {}
                self.received_chunks[filename][chunk_idx] = chunk_data
                self.signal_handler.message_received.emit(f"📥 Received missing chunk {chunk_idx} of {filename} from {ip}")
                if filename in self.expected_chunks and len(self.received_chunks[filename]) == self.expected_chunks[filename]:
                    self.assemble_file(filename, ip)
            else:
                self.signal_handler.message_received.emit(f" Message from {ip}: {message}")
        except Exception as e:
            self.signal_handler.message_received.emit(f"❌ Error handling peer message: {e}")

    def handle_file_chunk(self, chunk_info, sender_address):
        try:
            required_keys = ['file_name', 'chunk_index', 'total_chunks', 'data']
            for key in required_keys:
                if key not in chunk_info:
                    self.signal_handler.message_received.emit(f"❌ Missing key in chunk_info: {key}")
                    return

            file_name = chunk_info['file_name']
            index = chunk_info['chunk_index']
            total = chunk_info['total_chunks']
            data = chunk_info['data']
            sender_ip = sender_address[0]

            if file_name not in self.received_chunks:
                self.received_chunks[file_name] = {}
                self.expected_chunks[file_name] = total

            self.received_chunks[file_name][index] = data
            self.chunk_registry.setdefault(file_name, {}).setdefault(index, []).append(sender_ip)

            self.signal_handler.message_received.emit(f" Received chunk {index + 1}/{total} of {file_name} from {sender_ip}")

            for peer in self.network.peers:
                peer_ip = peer[0] if isinstance(peer, tuple) else peer
                if peer_ip != sender_ip:
                    self.network.send_message(peer_ip, f"CHUNK_ANNOUNCE|{file_name}|{index}")

            if len(self.received_chunks[file_name]) < total:
                missing = [i for i in range(total) if i not in self.received_chunks[file_name]]
                for m in missing:
                    if m in self.chunk_registry.get(file_name, {}):
                        for peer_ip in self.chunk_registry[file_name][m]:
                            self.network.send_message(peer_ip, f"REQUEST_CHUNK|{file_name}|{m}")

            if len(self.received_chunks[file_name]) == total:
                self.assemble_file(file_name, sender_ip)

        except Exception as e:
            self.signal_handler.message_received.emit(f"❌ Error handling chunk: {e}")

    def assemble_file(self, file_name, sender_ip):
        chunks = self.received_chunks[file_name]
        if len(chunks) != self.expected_chunks[file_name]:
            return

        save_dir = Path.home() / "Downloads" / "GEHU_P2P_Received"
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / file_name

        with open(file_path, 'wb') as f:
            for i in range(len(chunks)):
                f.write(chunks[i])

        file_size = os.path.getsize(file_path)
        self.received_files[file_name] = {
            'path': str(file_path),
            'size': file_size,
            'sender': sender_ip
        }

        size_str = f"{file_size // 1024} KB" if file_size >= 1024 else f"{file_size} bytes"
        self.signal_handler.file_received.emit(file_name, size_str, sender_ip, file_size)

        self.signal_handler.show_message_box.emit(
            "File Reconstructed",
            f"Successfully reconstructed {file_name} ({size_str}) from chunks.\nSaved at {file_path}",
            QMessageBox.Information
        )

    @pyqtSlot(str)
    def update_messages(self, msg):
        self.messages_text.append(msg)
        scrollbar = self.messages_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    @pyqtSlot(str, str, str, int)
    def add_file_to_list(self, name, size, sender, raw_size):
        item = QTreeWidgetItem([name, size, sender])
        item.setData(0, Qt.UserRole, raw_size)
        self.files_tree.addTopLevelItem(item)

    def download_file(self):
        selected_items = self.files_tree.selectedItems()
        if not selected_items:
            self.signal_handler.show_message_box.emit("Warning", "Please select a file to download", QMessageBox.Warning)
            return

        selected_item = selected_items[0]
        file_name = selected_item.text(0)

        if file_name not in self.received_files:
            self.signal_handler.show_message_box.emit("Error", "File information not found", QMessageBox.Warning)
            return

        source_path = self.received_files[file_name]['path']
        if not os.path.exists(source_path):
            self.signal_handler.show_message_box.emit("Error", f"Source file not found at {source_path}", QMessageBox.Warning)
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save File", file_name, "All Files (*.*)")

        if file_path:
            try:
                with open(source_path, 'rb') as src, open(file_path, 'wb') as dest:
                    dest.write(src.read())
                self.signal_handler.show_message_box.emit("Success", f"File {file_name} saved to {file_path}", QMessageBox.Information)
            except Exception as e:
                self.signal_handler.show_message_box.emit("Error", f"Failed to save file: {e}", QMessageBox.Warning)

    def start_listening(self):
        threading.Thread(target=self.network.listen_for_peers, daemon=True).start()
        threading.Thread(target=self.network.listen_for_files, daemon=True).start()
        threading.Thread(target=self.network.listen_for_messages, daemon=True).start()
        try:
            threading.Thread(target=self.network.listen_for_acks, daemon=True).start()
        except Exception as e:
            self.signal_handler.message_received.emit(f"⚠️ Could not start ACK listener: {e}")

    def join_session(self):
        self.network.discover_peers()
        QApplication.instance().processEvents()
        self.signal_handler.show_message_box.emit("Success", "Connected to the session", QMessageBox.Information)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StudentWindow()
    window.show()
    sys.exit(app.exec_())
