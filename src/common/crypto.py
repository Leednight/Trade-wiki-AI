"""本地敏感数据加密工具"""

from pathlib import Path

from cryptography.fernet import Fernet


class DataEncryptor:
    """本地敏感数据加密/解密"""

    def __init__(self, key: bytes | None = None, key_path: str | None = None):
        if key:
            self.cipher = Fernet(key)
        elif key_path:
            path = Path(key_path)
            if path.exists():
                self.cipher = Fernet(path.read_bytes())
            else:
                key = Fernet.generate_key()
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(key)
                path.chmod(0o600)
                self.cipher = Fernet(key)
        else:
            raise ValueError("Must provide either key or key_path")

    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """解密数据"""
        return self.cipher.decrypt(encrypted.encode()).decode()
