import os
import ecdsa
import hashlib
import base58

# 生成私钥
def generate_private_key():
    return os.urandom(32)

# 生成公钥
def generate_public_key(private_key):
    sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
    vk = sk.verifying_key
    return b'\x04' + vk.to_string()

# 生成比特币地址
def generate_btc_address(public_key):
    # 1. SHA-256哈希
    sha256_bpk = hashlib.sha256(public_key).digest()
    # 2. RIPEMD-160哈希
    ripemd160_bpk = hashlib.new('ripemd160', sha256_bpk).digest()
    # 3. 添加网络字节
    network_byte = b'\x00' + ripemd160_bpk
    # 4. 双SHA-256哈希
    sha256_nbpk = hashlib.sha256(network_byte).digest()
    sha256_sha256_nbpk = hashlib.sha256(sha256_nbpk).digest()
    # 5. 取前4个字节作为校验和
    checksum = sha256_sha256_nbpk[:4]
    # 6. 拼接校验和
    binary_address = network_byte + checksum
    # 7. Base58编码
    address = base58.b58encode(binary_address)
    return address

# 签名消息
def sign_message(private_key, message):
    # 创建签名对象
    sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
    # 对消息进行签名
    # 首先对消息进行哈希处理，这是比特币签名的标准做法
    message_hash = hashlib.sha256(message.encode()).digest()
    signature = sk.sign(message_hash)
    return signature

# 验证签名
def verify_signature(public_key, message, signature):
    try:
        # 从完整公钥中移除前缀0x04
        public_key_bytes = public_key[1:] if public_key[0] == 0x04 else public_key
        # 创建验证密钥对象
        vk = ecdsa.VerifyingKey.from_string(public_key_bytes, curve=ecdsa.SECP256k1)
        # 对消息进行相同的哈希处理
        message_hash = hashlib.sha256(message.encode()).digest()
        # 验证签名
        return vk.verify(signature, message_hash)
    except:
        return False

# 测试代码
def main():
    # 生成密钥对和地址
    private_key = generate_private_key()
    public_key = generate_public_key(private_key)
    btc_address = generate_btc_address(public_key)

    print("私钥:", private_key.hex())
    print("公钥:", public_key.hex())
    print("比特币地址:", btc_address.decode())

    # 签名示例
    message = "Hello, Bitcoin!"
    print("\n原始消息:", message)

    # 签名
    signature = sign_message(private_key, message)
    print("签名:", signature.hex())

    # 验证签名
    is_valid = verify_signature(public_key, message, signature)
    print("签名验证结果:", is_valid)

    # 尝试验证被篡改的消息
    tampered_message = "Hello, Bitcoin!!"
    is_valid_tampered = verify_signature(public_key, tampered_message, signature)
    print("篡改消息后的验证结果:", is_valid_tampered)

if __name__ == "__main__":
    main()