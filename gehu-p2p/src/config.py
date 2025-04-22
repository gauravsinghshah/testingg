import hashlib

# Network config
SERVICE_TYPE = "_gehu-p2p._tcp.local."
PORT = 53530
CHUNK_SIZE = 1024 * 1024  # 1MB chunks
MAX_PEERS = 50

# Security
PSK = b'REPLACE_THIS_WITH_A_REAL_FERNET_KEY_32BYTES=='  # Use Fernet.generate_key()
HASH_FUNC = hashlib.sha256
