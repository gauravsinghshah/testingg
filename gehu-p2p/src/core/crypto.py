from cryptography.fernet import Fernet
from config import PSK

class CryptoHandler:
    def __init__(self):
        self.cipher = Fernet(PSK)

    def encrypt_chunk(self, chunk):
        return self.cipher.encrypt(chunk['data'])

    def decrypt_chunk(self, encrypted_data):
        return self.cipher.decrypt(encrypted_data)