# File: teacher.py
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from network import PeerNetwork

class TeacherWindow:
    def _init_(self, root):
        self.root = root
        self.root.title("GEHU P2P - Teacher")
        self.colors = {
            'primary': '#6C63FF',
            'secondary': '#F0F0F7',
            'text': '#2D3748',
            'white': '#FFFFFF'
        }
        self.network = PeerNetwork(port=8081)  # Use the same port as the student
        self.setup_ui()
        self.start_listening()
        
    def setup_ui(self):
        self.main_frame = tk.Frame(self.root, bg=self.colors['secondary'], padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Message frame
        message_frame = tk.LabelFrame(self.main_frame, text="Broadcast Message", 
                                    font=('Helvetica', 12, 'bold'), bg=self.colors['secondary'])
        message_frame.pack(fill=tk.X, pady=10)
        
        self.message_entry = tk.Text(message_frame, height=5)
        self.message_entry.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        send_msg_btn = tk.Button(message_frame, text="Broadcast Message", 
                                bg=self.colors['primary'], fg='white',
                                command=self.broadcast_message)
        send_msg_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # File sharing frame
        file_frame = tk.LabelFrame(self.main_frame, text="Share File", 
                                 font=('Helvetica', 12, 'bold'), bg=self.colors['secondary'])
        file_frame.pack(fill=tk.X, pady=10)
        
        self.file_path = tk.StringVar()
        file_entry = tk.Entry(file_frame, textvariable=self.file_path, width=50)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_btn = tk.Button(file_frame, text="Browse", 
                              command=self.browse_file)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        send_file_btn = tk.Button(file_frame, text="Send File", 
                               bg=self.colors['primary'], fg='white',
                               command=self.send_file)
        send_file_btn.pack(side=tk.LEFT, padx=5)
        
    def start_listening(self):
        """Start listening for incoming connections"""
        listen_thread = threading.Thread(target=self.network.listen_for_peers)
        listen_thread.daemon = True
        listen_thread.start()
        
    def browse_file(self):
        """Browse for file to share"""
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path.set(file_path)
            
    def broadcast_message(self):
        """Broadcast message to all peers"""
        message = self.message_entry.get("1.0", tk.END)
        if message.strip():
            self.network.broadcast(message)
            messagebox.showinfo("Success", "Message sent to all peers")
            
    def send_file(self):
        """Send selected file to all peers"""
        file_path = self.file_path.get()
        if not file_path:
            messagebox.showwarning("Warning", "Please select a file to send")
            return
            
        file_name = os.path.basename(file_path)
        # Implement file chunking and sending logic here
        # For now, we'll just send the file path as a message
        self.network.broadcast(f"file:{file_name}:{file_path}")
        messagebox.showinfo("Success", "File sent successfully")

if _name_ == "_main_":
    root = tk.Tk()
    TeacherWindow(root)
    root.mainloop()
