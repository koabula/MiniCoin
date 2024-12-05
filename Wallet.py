import random
import ecdsa
import hashlib
import base58

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
    address = "0x" + address.hex()
    return address

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

class Wallet:
    def __init__(self):
        self.private_key = random.randbytes(32) # 256位私钥
        self.public_key = generate_public_key(self.private_key)
        self.address = generate_btc_address(self.public_key)

    def get_address(self):
        return self.address

    # 签名消息
    def sign_message(self, message):
        sk = ecdsa.SigningKey.from_string(self.private_key, curve=ecdsa.SECP256k1)
        # 首先对消息进行哈希处理
        message_hash = hashlib.sha256(message.encode()).digest()
        signature = sk.sign(message_hash)
        return signature

if __name__ == "__main__":
    wallet = Wallet()
    print("private_key: ", wallet.private_key.hex())
    print("public_key: ", wallet.public_key.hex())
    print("address: ", wallet.get_address())
    signature = wallet.sign_message("Hello, world!")
    print("signature: ", signature.hex())
    print("verify_signature: ", verify_signature(wallet.public_key, "Hello, world!", signature))