from Crypto.PublicKey import ECC
from Crypto.Cipher import AES
import os

def encrypt(message: str, public_key: ECC.EccKey) -> tuple:
    """
    简单的ECC加密
    """
    # 生成一次性密钥对
    ephemeral_key = ECC.generate(curve='P-256')
    
    # 计算共享密钥点
    shared_point = ephemeral_key.d * public_key.pointQ
    # 使用x坐标作为AES密钥
    shared_key = shared_point.x.to_bytes(32, byteorder='big')
    
    # 使用AES加密消息
    cipher = AES.new(shared_key, AES.MODE_CBC)
    # 对消息进行填充
    padded_message = message.encode('utf-8')
    padded_message += b' ' * (16 - len(padded_message) % 16)
    
    # 返回临时公钥、IV和密文
    return (ephemeral_key.public_key(), cipher.iv, cipher.encrypt(padded_message))

def decrypt(encrypted_data: tuple, private_key: ECC.EccKey) -> str:
    """
    简单的ECC解密
    """
    ephemeral_public_key, iv, ciphertext = encrypted_data
    
    # 计算共享密钥点
    shared_point = private_key.d * ephemeral_public_key.pointQ
    # 使用x坐标作为AES密钥
    shared_key = shared_point.x.to_bytes(32, byteorder='big')
    
    # 使用AES解密
    cipher = AES.new(shared_key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)
    
    # 去除填充并返回
    return decrypted.strip().decode('utf-8')

def main():
    # 生成密钥对
    private_key = ECC.generate(curve='P-256')
    public_key = private_key.public_key()
    
    # 测试消息
    message = "hello ecc"
    print(f"原始消息: {message}")
    
    # 加密
    encrypted = encrypt(message, public_key)
    print(f"加密后的数据: {encrypted[2].hex()}")
    
    # 解密
    decrypted = decrypt(encrypted, private_key)
    print(f"解密后的消息: {decrypted}")

if __name__ == "__main__":
    main()