import sys
import threading
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                             QLabel, QFileDialog, QMessageBox, QGroupBox)
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot
from network import PeerNetwork

class TeacherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEHU P2P - Teacher")
        self.resize(700, 400)
        
        # Initialize network
        self.network = PeerNetwork(
            port=8080,
            file_port=8081,
            on_peer_discovered=self.on_peer_discovered
        )
        
        self.init_ui()
        self.start_listening()
    
    def init_ui(self):
        # Main widget and layout
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        
        # Message frame
        message_group = QGroupBox("Broadcast Message")
        message_layout = QVBoxLayout(message_group)
        
        self.message_entry = QTextEdit()
        self.message_entry.setPlaceholderText("Type your message here...")
        message_layout.addWidget(self.message_entry)
        
        send_msg_btn = QPushButton("Broadcast Message")
        send_msg_btn.clicked.connect(self.broadcast_message)
        send_msg_btn.setStyleSheet("background-color: #6C63FF; color: white;")
        message_layout.addWidget(send_msg_btn)
        
        main_layout.addWidget(message_group)
        
        # File sharing frame
        file_group = QGroupBox("Share File")
        file_layout = QHBoxLayout(file_group)
        
        self.file_path_entry = QLineEdit()
        self.file_path_entry.setReadOnly(True)
        file_layout.addWidget(self.file_path_entry, 4)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn, 1)
        
        send_file_btn = QPushButton("Send File")
        send_file_btn.clicked.connect(self.send_file_thread)
        send_file_btn.setStyleSheet("background-color: #6C63FF; color: white;")
        file_layout.addWidget(send_file_btn, 1)
        
        main_layout.addWidget(file_group)
        
        self.setCentralWidget(central_widget)
    
    def start_listening(self):
        """Start listening for incoming peers (UDP) and optionally file transfers (TCP)"""
        threading.Thread(target=self.network.listen_for_peers, daemon=True).start()
        
        # Broadcast presence to find peers
        self.network.discover_peers()
    
    def on_peer_discovered(self, message, address):
        ip_address = address[0]
        if ip_address not in self.network.peers:
            self.network.peers.append(ip_address)
            print(f"👋 New peer joined: {ip_address}")
    
    def browse_file(self):
        """Browse for file to share"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            self.file_path_entry.setText(file_path)
    
    def broadcast_message(self):
        message = self.message_entry.toPlainText().strip()
        if message:
            for peer_ip in self.network.peers:
                self.network.send_message(peer_ip, message)
            QMessageBox.information(self, "Success", "Message broadcasted to all peers")
            self.message_entry.clear()
        else:
            QMessageBox.warning(self, "Empty Message", "Please enter a message to broadcast.")
    
    def send_file_thread(self):
        """Run send_file in a separate thread"""
        threading.Thread(target=self.send_file, daemon=True).start()
    
    def send_file(self):
        """Send selected file to all peers"""
        file_path = self.file_path_entry.text()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "Warning", "Please select a valid file to send")
            return
        
        if not self.network.peers:
            QMessageBox.warning(self, "No Peers", "No peers discovered to send the file to.")
            return
        
        successful_sends, failed_sends = 0, 0
        for peer_ip in self.network.peers:
            try:
                self.network.send_file(file_path, peer_ip)
                successful_sends += 1
            except Exception as e:
                print(f"❌ Error sending file to {peer_ip}: {e}")
                failed_sends += 1
        
        QMessageBox.information(self, "File Sent", 
                               f"File successfully sent to {successful_sends} peer(s), failed for {failed_sends}.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TeacherWindow()
    window.show()
    sys.exit(app.exec_())
