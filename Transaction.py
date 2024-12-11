import hashlib
import ecdsa
import json
import base64  # 用于编码字节类型数据

class UTXO:
    def __init__(self, tx_hash, output_index, amount, recipient_address):
        self.tx_hash = tx_hash  # 交易的哈希
        self.output_index = output_index  # 输出在交易中的索引
        self.amount = amount  # 金额
        self.recipient_address = recipient_address  # 接收者的地址

    def to_json(self):
        return {
            "tx_hash": self.tx_hash,
            "output_index": self.output_index,
            "amount": self.amount,
            "recipient_address": self.recipient_address
        }

    @classmethod
    def from_json(cls, json_data):
        return cls(
            tx_hash=json_data["tx_hash"],
            output_index=json_data["output_index"],
            amount=json_data["amount"],
            recipient_address=json_data["recipient_address"]
        )

    def __repr__(self):
        return f"UTXO(tx_hash={self.tx_hash}, output_index={self.output_index}, amount={self.amount}, recipient={self.recipient_address})"

class Transaction:
    def __init__(self):
        self.inputs = []  # 交易输入
        self.outputs = []  # 交易输出
        self.tx_hash = None  # 交易哈希
        self.signature = None  # 交易签名
        self.sender_public_key = None  # 发送者的公钥
        self.block_index = None  # 区块索引

    def to_json(self):
        return {
            "inputs": [utxo.to_json() for utxo in self.inputs],
            "outputs": [utxo.to_json() for utxo in self.outputs],
            "tx_hash": self.tx_hash,
            "signature": base64.b64encode(self.signature).decode('utf-8') if self.signature else None,
            "sender_public_key": base64.b64encode(self.sender_public_key).decode('utf-8') if self.sender_public_key else None,
            "block_index": self.block_index
        }

    @classmethod
    def from_json(cls, json_data):
        tx = cls()
        tx.inputs = [UTXO.from_json(utxo_data) for utxo_data in json_data["inputs"]]
        tx.outputs = [UTXO.from_json(utxo_data) for utxo_data in json_data["outputs"]]
        tx.tx_hash = json_data["tx_hash"]
        tx.signature = base64.b64decode(json_data["signature"]) if json_data["signature"] else None
        tx.sender_public_key = base64.b64decode(json_data["sender_public_key"]) if json_data["sender_public_key"] else None
        tx.block_index = json_data["block_index"]
        return tx

    def add_input(self, utxo):
        self.inputs.append(utxo)

    def add_output(self, amount, recipient_address):
        output = UTXO(tx_hash=self.tx_hash, output_index=len(self.outputs), amount=amount, recipient_address=recipient_address)
        self.outputs.append(output)

    def calculate_hash(self):
        # 计算交易的哈希值
        tx_content = self.get_tx_content()
        sha = hashlib.sha256()
        sha.update(tx_content.encode('utf-8'))
        self.tx_hash = sha.hexdigest()
        return self.tx_hash

    def sign(self, private_key):
        # 使用私钥对交易进行签名
        sk = ecdsa.SigningKey.from_string(private_key, curve=ecdsa.SECP256k1)
        message_hash = hashlib.sha256(self.tx_hash.encode('utf-8')).digest()
        self.signature = sk.sign(message_hash)
        self.sender_public_key = b'\x04' + sk.verifying_key.to_string()  # 存储发送者的公钥

    def verify_signature(self):
        try:
            vk = ecdsa.VerifyingKey.from_string(self.sender_public_key[1:], curve=ecdsa.SECP256k1)
            message_hash = hashlib.sha256(self.tx_hash.encode('utf-8')).digest()
            return vk.verify(self.signature, message_hash)
        except ecdsa.BadSignatureError:
            return False

    def get_tx_content(self):
        # 返回交易内容的字符串表示
        return "".join([
            f"{utxo.tx_hash}:{utxo.output_index}" for utxo in self.inputs
        ]) + "".join([
            f"{output.amount}:{output.recipient_address}" for output in self.outputs
        ]) + f"{self.block_index}"

    def __repr__(self):
        return f"Transaction(inputs={self.inputs}, outputs={self.outputs}, tx_hash={self.tx_hash})"

if __name__ == "__main__":  
    mining_reward = Transaction()
    reward_output = UTXO(
        tx_hash=None,  # 这里会在calculate_hash后被更新
        output_index=0,
        amount=50,
        recipient_address="0x123"
    )
    mining_reward.outputs.append(reward_output)
    mining_reward.tx_hash = mining_reward.calculate_hash()
    print(mining_reward)
    print(mining_reward.to_json())
    print(Transaction.from_json(mining_reward.to_json()))
#     tx = Transaction()
#     tx.add_input(UTXO(tx_hash="123", output_index=0, amount=100, recipient_address="0x123"))
#     tx.add_output(amount=100, recipient_address="0x123")
#     tx.calculate_hash()
#     tx.sign(private_key=b'\x01' * 32)
#     print(tx)
#     print("-"*100)
#     print(tx.to_json())
#     print("-"*100)
#     print(Transaction.from_json(tx.to_json()))

