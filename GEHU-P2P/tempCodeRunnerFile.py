import threading
from tkinter import ttk, filedialog
import os
from pathlib import Path
import json
from network import PeerNetwork
import tkinter.messagebox as messagebox  # Ensure correct import for messagebox
import tkinter as tk

class StudentWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("GEHU P2P - Student")
        self.colors = {
            'primary': '#6C63FF',
            'secondary': '#F0F0F7',
            'text': '#2D3748',
            'white': '#FFFFFF'
        }

        self.network = PeerNetwork(
            on_file_received=self.handle_file_received,
            on_peer_discovered=self.handle_peer_discovery
        )

        self.setup_ui()
        self.start_listening()
        self.join_session()

    def setup_ui(self):
        self.main_frame = tk.Frame(self.root, bg=self.colors['secondary'], padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Messages frame
        messages_frame = tk.LabelFrame(self.main_frame, text="Received Messages", 
                                       font=('Helvetica', 12, 'bold'), bg=self.colors['secondary'])
        messages_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        self.messages_text = tk.Text(messages_frame, height=10)
        self.messages_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Files frame
        files_frame = tk.LabelFrame(self.main_frame, text="Shared Files", 
                                    font=('Helvetica', 12, 'bold'), bg=self.colors['secondary'])
        files_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        columns = ('Name', 'Size', 'Shared By')
        self.files_tree = ttk.Treeview(files_frame, columns=columns, show='headings')

        for col in columns:
            self.files_tree.heading(col, text=col)
            self.files_tree.column(col, width=150)

        self.files_tree.pack(fill=tk.BOTH, expand=True)

        download_btn = tk.Button(files_frame, text="Download Selected", 
                                 bg=self.colors['primary'], fg='white',
                                 command=self.download_file)
        download_btn.pack(fill=tk.X, padx=5, pady=5)

    def handle_file_received(self, file_name, file_data, sender_ip):
        """Callback for when a file is received via TCP."""
        try:
            # Save file
            save_dir = Path.home() / "Downloads" / "GEHU_P2P_Received"
            save_dir.mkdir(parents=True, exist_ok=True)
            file_path = save_dir / file_name
            with open(file_path, 'wb') as f:
                f.write(file_data)

            # Update UI
            self.root.after(0, self.update_ui, f"✅ Received file: {file_name} from {sender_ip}\n")
            self.root.after(0, lambda: self.files_tree.insert("", tk.END, values=(
                file_name, f"{len(file_data)//1024} KB", sender_ip)))
        except Exception as e:
            self.root.after(0, self.update_ui, f"❌ Error handling file: {str(e)}\n")

    def handle_peer_discovery(self, message, addr):
        """Handle discovered peers and update the UI."""
        peer_info = f"🔍 Discovered peer: {addr[0]}\n"
        self.root.after(0, self.update_ui, peer_info)

    def update_ui(self, msg):
        self.messages_text.insert(tk.END, msg)
        self.messages_text.yview(tk.END)

    def download_file(self):
        selected_item = self.files_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a file to download")
            return

        file_name = self.files_tree.item(selected_item)['values'][0]
        save_path = filedialog.asksaveasfilename(defaultextension=os.path.splitext(file_name)[1],
                                                 initialfile=file_name)

        if save_path:
            # For now, simulate that the file was downloaded.
            messagebox.showinfo("Download Complete", f"{file_name} downloaded successfully!")

    def start_listening(self):
        threading.Thread(target=self.network.listen_for_peers, daemon=True).start()
        threading.Thread(target=self.network.listen_for_files, daemon=True).start()

    def join_session(self):
        """Simulate joining the lab session"""
        messagebox.showinfo("Welcome", "Welcome to the GEHU P2P session!")
        self.network.discover_peers()
