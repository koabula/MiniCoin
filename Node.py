import socket
import threading
import time
from BlockChain import BlockChain, block_chain_from_json
from Block import Block, block_from_json
from MerkleTree import MerkleTree, merkle_tree_from_json
import json
from Wallet import Wallet
from Transaction import Transaction,UTXO

class Node:
    def __init__(self, ip):
        self.wallet = Wallet()
        self.node_ip = ip
        self.peers = {"127.0.0.1"}  # 种子节点
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((ip, 5000))    # 监听5000端口
        self.socket.listen(5)
        self.hello_dict = {}
        self.blockchain = BlockChain()
        self.data_queue = [f"Created by {ip}",]
        self.getBlock=False
        self.blockchain_lock = threading.Lock()  # 添加线程锁
        self.signal_lock = threading.Lock()
        self.data_lock = threading.Lock()
        self.mempool = []  # 交易池
        self.mempool_lock = threading.Lock()  # 交易池的锁
        self.global_utxo_pool = {}  # 全局UTXO池，格式: {tx_hash:output_index: UTXO}
        self.utxo_pool_lock = threading.Lock()  # 全局UTXO池的锁
        while True:
            try:
                self.send_join()    # 发送加入消息
                break
            except:
                time.sleep(1)
        self.handle_thread = threading.Thread(target=self.handle_connection)    # 处理连接
        self.handle_thread.start()
        self.helloloop_thread = threading.Thread(target=self.helloloop)    # 心跳检测
        self.helloloop_thread.start()
        self.mine_thread = threading.Thread(target=self.mine_thread)
        self.mine_thread.start()
        self.send_data_thread = threading.Thread(target=self.send_data_thread)
        self.send_data_thread.start()

        # 初始化UTXO池
        self.init_utxo_pool()

        # 启动UTXO同步线程
        self.sync_thread = threading.Thread(target=self.sync_utxo_thread)
        self.sync_thread.daemon = True
        self.sync_thread.start()

    def send_msg(self, msg):
        for peer in list(self.peers):
            if peer == self.node_ip:
                continue
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((peer, 5000))
                    s.sendall(msg.encode("utf-8"))
                except:
                    print(f"Failed to send message to {peer}")

    def send_data(self, data):
        self.send_msg(f"@DATA{data}")

    def send_hello(self):
        self.send_msg(f"@HELLO{self.node_ip}")

    def send_join(self):
        self.send_msg(f"@JOIN{self.node_ip}")

    def send_intro(self,addr):
        self.send_msg(f"#INTRO{addr}")

    def send_block(self,block:Block):
        self.send_msg(f"@ONEBLOCK{block.to_json()}")
    
    def verify_block_transactions(self, block):
        """验证区块中的所有交易，返回(是否全部有效, 无效交易列表)"""
        transactions = []
        invalid_transactions = []
        
        for leaf in block.merkle_tree.leaves:
            try:
                tx = Transaction.from_json(json.loads(leaf.data))
                transactions.append(tx)
            except:
                continue  # 跳过非交易数据

        # 临时存储已使用的UTXO
        used_utxos = set()

        with self.utxo_pool_lock:
            for tx in transactions:
                # 如果是挖矿奖励交易（第一个交易），直接验证通过
                if transactions.index(tx) == 0:
                    if tx.outputs[0].amount != 50:
                        print(f"Invalid mining reward transaction: {tx.tx_hash}")
                        invalid_transactions.append(tx)
                    continue

                try:
                    # 1. 验证交易签名
                    if not tx.verify_signature():
                        print(f"Invalid transaction signature: {tx.tx_hash}")
                        invalid_transactions.append(tx)
                        continue

                    # 2. 验证输入UTXO
                    total_input = 0
                    valid_inputs = True
                    
                    for utxo in tx.inputs:
                        # 检查UTXO是否已被使用（防止双重支付）
                        utxo_key = f"{utxo.tx_hash}:{utxo.output_index}"
                        if utxo_key in used_utxos:
                            print(f"Double spending detected: {utxo_key}")
                            valid_inputs = False
                            break

                        # 在全局UTXO池中查找这个UTXO
                        if utxo_key in self.global_utxo_pool:
                            total_input += self.global_utxo_pool[utxo_key].amount
                            used_utxos.add(utxo_key)
                        else:
                            print(f"UTXO not found in global pool: {utxo_key}")
                            valid_inputs = False
                            break

                    if not valid_inputs:
                        invalid_transactions.append(tx)
                        continue

                    # 3. 验证输入输出金额
                    total_output = sum(output.amount for output in tx.outputs)
                    if total_input != total_output:
                        print(f"Input/output amount mismatch: {tx.tx_hash}")
                        invalid_transactions.append(tx)
                        continue

                except Exception as e:
                    print(f"Error verifying transaction {tx.tx_hash}: {e}")
                    invalid_transactions.append(tx)
                    continue

        return len(invalid_transactions) == 0, invalid_transactions

    def parse_block(self, block_json):
        if not block_json.strip():
            print("Received empty block JSON")
            return
        try:
            block = block_from_json(block_json)
        except json.JSONDecodeError as e:
            print(f"Failed to decode block JSON: {e}")
            return
        if not block.merkle_tree or not block.merkle_tree.leaves:
            print("Merkle tree or leaves are not initialized")
            return
        
        if block.index > self.blockchain.height + 1:
            # 直接使用区块中记录的矿工节点IP地址
            self.send_blockchain_request(block.miner_address)
            print(f"Request blockchain from {block.miner_address}")
        else:
            with self.blockchain_lock:
                if self.blockchain.is_block_valid(block):
                    # 先验证区块的所有交易
                    if not self.verify_block_transactions(block):
                        print(f"Rejected block {block.index}: invalid transactions")
                        return
                    
                    # 如果所有交易都验证通过，接受区块并处理交易
                    with self.signal_lock:
                        self.getBlock = True
                    self.blockchain.append_block(block)
                    # 处理新区块中的交易
                    self.process_block_transactions(block)
                    print(f"Accepted block {block.index} :{block.hash}")

    def send_blockchain_request(self,addr):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((addr, 5000))
                s.sendall(f"@BLOCKCHAIN{self.node_ip}".encode("utf-8"))
            except:
                print(f"Failed to send blockchain request to {addr}")

    def send_blockchain(self, addr):
        blockchain_json = self.blockchain.to_json()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((addr, 5000))
                s.sendall(f"#BLOCKCHAIN{blockchain_json}".encode("utf-8"))
            except:
                print(f"Failed to send blockchain to {addr}")

    def send_transaction(self, transaction):
        # 广播交易
        self.mempool.append(transaction)
        self.send_msg(f"@TRANSACTION{json.dumps(transaction.to_json())}")

    def handle_transaction(self, transaction_json):
        try:
            # 解析交易
            transaction = Transaction.from_json(json.loads(transaction_json))
            
            # 验证交易
            if not transaction.verify_signature():
                print(f"Invalid transaction signature: {transaction.tx_hash}")
                return

            # 添加到交易池
            with self.mempool_lock:
                if transaction not in self.mempool:
                    self.mempool.append(transaction)
                    print(f"Added transaction to mempool: {transaction.tx_hash}")


        except Exception as e:
            print(f"Error handling transaction: {e}")

    def handle_connection(self):
        while True:
            conn, addr = self.socket.accept()
            data = ""
            while True:
                part = conn.recv(1024).decode("utf-8")
                if not part:
                    break
                data += part
            # 处理接收到的数据
            if data.startswith("@DATA"):
                with self.data_lock:
                    self.data_queue.append(data[5:])
                print(f"Received data: {data[5:]}")

            elif data.startswith("@HELLO"):
                formaddr = data[6:]
                self.peers.update([formaddr])
                self.hello_dict[formaddr] = time.time()

            elif data.startswith("@JOIN"):
                formaddr = data[5:]
                self.send_intro(formaddr)
                self.peers.update([formaddr])
                print(f"Join {formaddr}")

            elif data.startswith("#INTRO"):
                formaddr = data[6:]
                self.peers.update([formaddr])
                print(f"Intro {formaddr}")

            elif data.startswith("@ONEBLOCK"):
                self.parse_block(data[9:])

            elif data.startswith("@BLOCKCHAIN"):
                addr = data[11:]
                self.send_blockchain(addr)

            elif data.startswith("#BLOCKCHAIN"):
                blockchain_json = data[11:]
                try:
                    new_blockchain = block_chain_from_json(blockchain_json)
                except json.JSONDecodeError as e:
                    print(f"Failed to decode blockchain JSON: {e}")
                    continue
                
                if len(new_blockchain.chain) > len(self.blockchain.chain):
                    if new_blockchain.is_chain_valid():
                        # 验证区块链中的所有交易
                        if self.verify_blockchain_transactions(new_blockchain):
                            with self.blockchain_lock:
                                self.blockchain = new_blockchain
                                # 重新初始化UTXO池
                            self.init_utxo_pool()
                            print(f"Synchronized blockchain and updated UTXO pool")
                        else:
                            print("Rejected blockchain: invalid transactions")
                    else:
                        print("Rejected blockchain: invalid chain")

            elif data.startswith("@TRANSACTION"):
                # 处理新的交易
                self.handle_transaction(data[12:])

            conn.close()

    def mainloop(self):
        while True:
            self.send_data(f"This is {self.node_ip}")
            time.sleep(1)

    def helloloop(self):
        while True:
            self.send_hello()
            for peer in list(self.hello_dict.keys()):
                if time.time() - self.hello_dict[peer] > 10:
                    self.peers.discard(peer)
                    del self.hello_dict[peer]
                    print(f"Discard {peer}")
            time.sleep(5)

    def mine(self):
        with self.data_lock:
            merkle_tree = MerkleTree(self.data_queue)
            self.data_queue = [f"Created by {self.node_ip}",]
        nonce = 0
        timestamp = time.time()
        while not self.getBlock:
            block = Block(self.blockchain.height, merkle_tree, self.blockchain.get_latest_block().hash, nonce, timestamp)
            if self.blockchain.is_block_valid(block):
                with self.blockchain_lock:
                    self.send_block(block)
                    self.blockchain.append_block(block)
                    if block.index == 5:
                        self.blockchain.save_svg("blockchain.svg")
                print(f"Mined block {block.index} :{block.hash}")
                break
            nonce += 1

    def mine_thread(self):
        while True:
            with self.data_lock:
                # 创建挖矿奖励交易
                mining_reward = Transaction()
                reward_output = UTXO(
                    tx_hash=None,
                    output_index=0,
                    amount=50,
                    recipient_address=self.wallet.address
                )
                mining_reward.outputs.append(reward_output)
                mining_reward.block_index = self.blockchain.height
                mining_reward.tx_hash = mining_reward.calculate_hash()
                reward_output.tx_hash = mining_reward.tx_hash
                
                # 从交易池中选择交易
                selected_transactions = []
                with self.mempool_lock:
                    selected_transactions = self.mempool
                
                # 将挖矿奖励交易放在第一位
                all_transactions = [mining_reward] + selected_transactions
                    
                # 创建merkle树（注意这里需要先将交易转换为JSON字符串）
                merkle_tree = MerkleTree([json.dumps(tx.to_json()) for tx in all_transactions])

            # 创建区块并验证交易
            block = Block(self.blockchain.height, merkle_tree, 
                         self.blockchain.get_latest_block().hash, 
                         0, time.time(), self.node_ip)
            
            # 验证交易并获取无效交易列表
            is_valid, invalid_txs = self.verify_block_transactions(block)
            
            # 如果有无效交易，从交易池和选中的交易中移除它们
            if invalid_txs:
                with self.mempool_lock:
                    self.mempool = [tx for tx in self.mempool if tx not in invalid_txs]
                    selected_transactions = [tx for tx in selected_transactions if tx not in invalid_txs]
                
                # 重新创建merkle树（包含奖励交易和有效交易）
                all_transactions = [mining_reward] + selected_transactions
                merkle_tree = MerkleTree([json.dumps(tx.to_json()) for tx in all_transactions])
                block = Block(self.blockchain.height, merkle_tree, 
                            self.blockchain.get_latest_block().hash, 
                            0, time.time(), self.node_ip)

            # 尝试挖矿
            nonce = 0
            while not self.getBlock:
                block.nonce = nonce
                block.hash = block.calculate_hash()
                if self.blockchain.is_block_valid(block):
                    with self.blockchain_lock:
                        self.send_block(block)
                        self.blockchain.append_block(block)
                        # 处理新区块中的交易
                        self.process_block_transactions(block)
                        # 从交易池中移除已确认的交易
                        with self.mempool_lock:
                            self.mempool = [tx for tx in self.mempool 
                                          if tx not in selected_transactions]
                        # 同步钱包UTXO
                        self.sync_wallet_utxo()
                    print(f"Mined block {block.index} :{block.hash}")
                    
                    # 打印钱包状态
                    self.print_wallet_status()
                    
                    break
                nonce += 1

            with self.signal_lock:
                self.getBlock = False

    def send_data_thread(self):
        while True:
            data=input()
            self.send_data(data)
            self.data_queue.append(data)
            print(f"Sent data: {data}")

    def init_utxo_pool(self):
        """初始化UTXO池，遍历区块链中的所有交易"""
        self.global_utxo_pool = {}
        with self.blockchain_lock:
            for block in self.blockchain.chain:
                self.process_block_transactions(block)

    def process_block_transactions(self, block):
        """处理区块中的所有交易，更新UTXO池"""
        transactions = []
        for leaf in block.merkle_tree.leaves:
            try:
                # 解析JSON字符串
                tx_data = json.loads(leaf.data)
                tx = Transaction.from_json(tx_data)
                transactions.append(tx)
            except Exception as e:
                continue

        with self.utxo_pool_lock:
            for tx in transactions:
                # 如果是挖矿奖励交易（第一个交易），直接添加输出到UTXO池
                if transactions.index(tx) == 0:
                    for i, output in enumerate(tx.outputs):
                        utxo_key = f"{tx.tx_hash}:{i}"
                        self.global_utxo_pool[utxo_key] = output
                        # 确保将奖励交易的输出添加到钱包的UTXO池
                        # if output.recipient_address == self.wallet.address:
                            # self.wallet.add_utxo(output)
                    continue

                # 对于普通交易，直接更新UTXO池
                # 1. 移除已使用的UTXO
                for utxo in tx.inputs:
                    utxo_key = f"{utxo.tx_hash}:{utxo.output_index}"
                    self.global_utxo_pool.pop(utxo_key, None)
                    # if utxo.recipient_address == self.wallet.address:
                    #     self.wallet.remove_utxo(utxo)

                # 2. 添加新的UTXO
                for i, output in enumerate(tx.outputs):
                    utxo_key = f"{tx.tx_hash}:{i}"
                    self.global_utxo_pool[utxo_key] = output
                    # 如果是发给自己的，也添加到钱包的UTXO池
                    # if output.recipient_address == self.wallet.address:
                    #     self.wallet.add_utxo(output)

    def verify_blockchain_transactions(self, blockchain):
        """验证区块链中所有区块的所有交易"""
        print("Verifying all transactions in the blockchain...")
        
        # 保存当前的UTXO池状态
        original_utxo_pool = self.global_utxo_pool.copy()
        self.global_utxo_pool = {}  # 临时清空UTXO池
        
        try:
            # 按顺序验证每个区块
            for block in blockchain.chain:
                is_valid, invalid_txs = self.verify_block_transactions(block)
                if not is_valid:
                    print(f"Invalid transactions found in block {block.index}")
                    return False
                
                # 如果验证通过，处理这个区块的交易（更新UTXO池)
                self.process_block_transactions(block)
            
            print("All transactions in the blockchain are valid")
            return True
            
        except Exception as e:
            print(f"Error during blockchain verification: {e}")
            return False
            
        finally:
            # 恢复原始UTXO池状态
            self.global_utxo_pool = original_utxo_pool

    def print_wallet_status(self):
        """打印钱包状态"""
        total_balance = sum(utxo.amount for utxo in self.wallet.utxo_pool)
        print(f"\n=== Wallet Status for {self.node_ip} ===")
        print(f"Total Balance: {total_balance}")
        print("UTXOs:")
        for utxo in self.wallet.utxo_pool:
            tx_hash_display = utxo.tx_hash[:8] if utxo.tx_hash else "None"
            print(f"  - Amount: {utxo.amount}, From TX: {tx_hash_display}...")
        print("=====================================\n")

    def sync_wallet_utxo(self):
        """与全局UTXO池同步钱包的UTXO"""
        with self.utxo_pool_lock:
            # 清空钱包的UTXO池
            self.wallet.utxo_pool = []
            
            # 从全局UTXO池中找出属于本钱包的UTXO
            for utxo_key, utxo in self.global_utxo_pool.items():
                if utxo.recipient_address == self.wallet.address:
                    self.wallet.add_utxo(utxo)
                
            # 打印同步后的钱包状态
            # self.print_wallet_status()

    def sync_utxo_thread(self):
        """定期同步UTXO的线程"""
        while True:
            time.sleep(1)  # 每1秒同步一次
            self.sync_wallet_utxo()

if __name__ == "__main__":
    ip = input("Enter IP address: ")
    node = Node(ip)