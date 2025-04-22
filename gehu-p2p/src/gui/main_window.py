import tkinter as tk
from tkinter import filedialog, ttk

class MainWindow:
    def __init__(self, role, on_share=None):  
        self.root = tk.Tk()
        self.role = role
        self.on_share = on_share
        self.setup_ui()
        
    def setup_ui(self):
        self.root.title(f"GEHU P2P - {self.role.capitalize()}")
        
        if self.role == 'teacher':
            self.btn_share = ttk.Button(
                text="Share File", command=self.share_file)
            self.btn_share.pack(padx=20, pady=10)
            
        self.progress = ttk.Progressbar(self.root, length=200)
        self.progress.pack(pady=10)
        
        self.peer_list = tk.Listbox(self.root)
        self.peer_list.pack(fill=tk.BOTH, expand=True)
        
    def share_file(self):
        file_path = filedialog.askopenfilename()
        if file_path and self.on_share:
            self.on_share(file_path)  

    def update_peers(self, peers):
        self.peer_list.delete(0, tk.END)
        for peer in peers:
            self.peer_list.insert(tk.END, peer)


