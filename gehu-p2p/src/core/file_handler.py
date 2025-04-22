import os
import hashlib
from config import CHUNK_SIZE, HASH_FUNC

class FileManager:
    @staticmethod
    def chunk_file(file_path):
        chunks = []
        file_size = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            chunk_id = 0
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                chunks.append({
                    'id': chunk_id,
                    'data': data,
                    'hash': HASH_FUNC(data).hexdigest(),
                    'total_chunks': (file_size // CHUNK_SIZE) + 1
                })
                chunk_id += 1
        return chunks

    @staticmethod
    def reassemble_file(chunks, output_path):
        with open(output_path, 'wb') as f:
            for chunk in sorted(chunks, key=lambda x: x['id']):
                f.write(chunk['data'])