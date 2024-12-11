import random
import ecdsa
import hashlib
import base58
from Transaction import Transaction, UTXO

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
        self.private_key = random.randbytes(32)  # 256位私钥
        self.public_key = generate_public_key(self.private_key)
        self.address = generate_btc_address(self.public_key)
        self.utxo_pool = []  # 钱包中的UTXO集合

    def get_address(self):
        return self.address

    # 签名消息
    def sign_message(self, message):
        sk = ecdsa.SigningKey.from_string(self.private_key, curve=ecdsa.SECP256k1)
        # 首先对消息进行哈希处理
        message_hash = hashlib.sha256(message.encode()).digest()
        signature = sk.sign(message_hash)
        return signature

    def create_transaction(self, recipient_address, amount):
        # 1. 选择足够的UTXO
        selected_utxos = []
        total_amount = 0
        for utxo in self.utxo_pool:
            selected_utxos.append(utxo)
            total_amount += utxo.amount
            if total_amount >= amount:
                break

        if total_amount < amount:
            raise ValueError("Don't have enough coins")

        # 2. 创建交易
        tx = Transaction()
        for utxo in selected_utxos:
            tx.add_input(utxo)

        # 3. 创建交易输出
        tx.add_output(amount, recipient_address)

        # 4. 找零
        change = total_amount - amount
        if change > 0:
            tx.add_output(change, self.address)

        # 5. 计算交易哈希
        tx.calculate_hash()

        # 6. 签名交易
        tx.sign(self.private_key)

        # 7. 更新UTXO池
        # self.utxo_pool = [utxo for utxo in self.utxo_pool if utxo not in selected_utxos]

        return tx

    def receive_transaction(self, transaction: Transaction):
        # 1. 验证交易签名
        if not transaction.verify_signature():
            raise ValueError("Invalid transaction signature")

        # 2. 更新UTXO池
        for output in transaction.outputs:
            if output.recipient_address == self.address:
                new_utxo = UTXO(transaction.tx_hash, transaction.outputs.index(output), output.amount, output.recipient_address)
                self.utxo_pool.append(new_utxo)

    def add_utxo(self, utxo):
        self.utxo_pool.append(utxo)

    def remove_utxo(self, utxo):
        self.utxo_pool.remove(utxo)

    def __repr__(self):
        return f"Wallet(address={self.address}, utxo_pool={self.utxo_pool})"

if __name__ == "__main__":
    # 创建发送方钱包
    sender_wallet = Wallet()
    recipient_wallet = Wallet()
    recipient_private_key, recipient_public_key = recipient_wallet.private_key, recipient_wallet.public_key
    recipient_address = recipient_wallet.address

    # 添加UTXO到发送方钱包
    utxo = UTXO(tx_hash="previous_tx_hash", output_index=0, amount=20, recipient_address=sender_wallet.address)
    sender_wallet.add_utxo(utxo)
    utxo = UTXO(tx_hash="previous_tx_hash", output_index=0, amount=20, recipient_address=sender_wallet.address)
    sender_wallet.add_utxo(utxo)

    # 验证接收方钱包的UTXO池
    print(f"Recipient Wallet UTXO Pool: {recipient_wallet.utxo_pool}")
    print(f"Sender Wallet UTXO Pool: {sender_wallet.utxo_pool}")

    # 创建交易
    tx = sender_wallet.create_transaction(recipient_address, 30)

    # 创建接收方钱包
    recipient_wallet = Wallet()
    recipient_wallet.address = recipient_address  # 设置接收方地址

    # 接收交易
    recipient_wallet.receive_transaction(tx)
    sender_wallet.receive_transaction(tx)

    print("转账后")
    print("--------------------------------")

    # 验证接收方钱包的UTXO池
    print(f"Recipient Wallet UTXO Pool: {recipient_wallet.utxo_pool}")
    print(f"Sender Wallet UTXO Pool: {sender_wallet.utxo_pool}")