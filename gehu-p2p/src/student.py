import asyncio
import threading
from core.network import NetworkManager
from gui.main_window import MainWindow
from config import PSK

class StudentNode:
    def __init__(self):
        self.network = NetworkManager('student')
        self.gui = MainWindow('student')

    async def async_start(self):
        await self.network.discover_peers()
        while True:
            self.gui.update_peers(self.network.peers)
            await asyncio.sleep(1)

    def run(self):
        def wrapper():
            asyncio.run(self.async_start())
        
        threading.Thread(target=wrapper, daemon=True).start()
        self.gui.root.mainloop()

if __name__ == "__main__":
    node = StudentNode()
    node.run()
