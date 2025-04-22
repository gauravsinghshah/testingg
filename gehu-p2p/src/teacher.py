
import asyncio
import threading
from core.network import NetworkManager
from core.file_handler import FileManager
from gui.main_window import MainWindow
from config import PSK

class TeacherNode:
    def __init__(self):
        self.network = NetworkManager('teacher')
        self.file_manager = FileManager()
        self.gui = MainWindow('teacher', on_share=self.share_file)
        self.shared_chunks = []

    async def async_start(self):
        await self.network.start_service()
        asyncio.create_task(self.network.discover_peers())

        while True:
            # Update the peers in the GUI
            self.gui.update_peers(self.network.peers)
            await asyncio.sleep(1)

    def share_file(self, file_path):
        """Handle file sharing by chunking the file."""
        chunks = self.file_manager.chunk_file(file_path)
        self.shared_chunks = chunks
        print(f"[+] Shared {len(chunks)} chunks from: {file_path}")
        # You can implement logic here to distribute the chunks to peers

    def run(self):
        # Run the async task in a separate thread to keep GUI responsive
        threading.Thread(target=lambda: asyncio.run(self.async_start()), daemon=True).start()
        self.gui.root.mainloop()

if __name__ == "__main__":
    node = TeacherNode()
    node.run()
