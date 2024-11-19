from Crypto.PublicKey import ECC
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
import os

class Sender:
    def __init__(self):
        # 生成发送方的密钥对
        self.private_key = ECC.generate(curve='P-384')
        self.public_key = self.private_key.public_key()
        
    def encrypt_message(self, message: str, receiver_public_key: ECC.EccKey) -> dict:
        # 生成一次性密钥对
        ephemeral_key = ECC.generate(curve='P-384')
        
        # 计算共享密钥
        shared_point = self.private_key.d * receiver_public_key.pointQ
        shared_key = shared_point.x.to_bytes()
        
        # 生成salt并保存
        salt = os.urandom(16)
        
        # 使用HKDF导出AES密钥
        aes_key = HKDF(
            master=shared_key,
            key_len=32,
            salt=salt,
            hashmod=SHA256,
            context=b'encryption'
        )
        
        # 生成随机IV
        iv = os.urandom(16)
        
        # 使用AES-GCM加密
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(message.encode())
        
        return {
            'ephemeral_public_key': ephemeral_key.public_key(),
            'iv': iv,
            'ciphertext': ciphertext,
            'tag': tag,
            'salt': salt
        }
    
    def get_public_key(self):
        return self.public_key

class Receiver:
    def __init__(self):
        # 生成接收方的密钥对
        self.private_key = ECC.generate(curve='P-384')
        self.public_key = self.private_key.public_key()
        
    def decrypt_message(self, encrypted_data: dict, sender_public_key: ECC.EccKey) -> str:
        # 计算共享密钥
        shared_point = self.private_key.d * sender_public_key.pointQ
        shared_key = shared_point.x.to_bytes()
        
        # 使用发送方提供的salt
        aes_key = HKDF(
            master=shared_key,
            key_len=32,
            salt=encrypted_data['salt'],
            hashmod=SHA256,
            context=b'encryption'
        )
        
        # 使用AES-GCM解密
        cipher = AES.new(aes_key, AES.MODE_GCM, nonce=encrypted_data['iv'])
        plaintext = cipher.decrypt_and_verify(
            encrypted_data['ciphertext'],
            encrypted_data['tag']
        )
        
        return plaintext.decode()
    
    def get_public_key(self):
        return self.public_key

def main():
    # 创建发送方和接收方
    sender = Sender()
    receiver = Receiver()
    
    # 要发送的消息
    message = "hello ecc"
    print(f"原始消息: {message}")
    
    try:
        # 发送方加密消息
        encrypted_data = sender.encrypt_message(
            message,
            receiver.get_public_key()
        )
        print(f"加密后的数据: {encrypted_data['ciphertext'].hex()}")
        
        # 接收方解密消息
        decrypted_message = receiver.decrypt_message(
            encrypted_data,
            sender.get_public_key()
        )
        print(f"解密后的消息: {decrypted_message}")
        
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main()