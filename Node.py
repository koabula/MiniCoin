import socket
import threading
import time
from BlockChain import BlockChain, block_chain_from_json
from Block import Block, block_from_json
from MerkleTree import MerkleTree, merkle_tree_from_json
import json
from Wallet import Wallet

class Node:
    def __init__(self, ip):
        self.wallet = Wallet()
        self.address = ip
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

    def send_msg(self, msg):
        for peer in list(self.peers):
            if peer == self.address:
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
        self.send_msg(f"@HELLO{self.address}")

    def send_join(self):
        self.send_msg(f"@JOIN{self.address}")

    def send_intro(self,addr):
        self.send_msg(f"#INTRO{addr}")

    def send_block(self,block:Block):
        self.send_msg(f"@ONEBLOCK{block.to_json()}")
    
    def parse_block(self, block_json):
        if not block_json.strip():  # 检查 block_json 是否为空
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
            valid_addr = block.merkle_tree.leaves[0].data.split()[-1]  # 假设IP地址在数据的最后
            self.send_blockchain_request(valid_addr)
            print(f"Request blockchain from {valid_addr}")
        else:
            with self.blockchain_lock:  # 使用锁保护区块链访问
                if self.blockchain.is_block_valid(block):
                    with self.signal_lock:
                        self.getBlock = True
                    self.blockchain.append_block(block)
                    print(f"Accepted block {block.index} :{block.hash},from {block.merkle_tree.leaves[0].data}")

    def send_blockchain_request(self,addr):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((addr, 5000))
                s.sendall(f"@BLOCKCHAIN{self.address}".encode("utf-8"))
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
                    print(f"Failed to decode blockchain JSON from {addr}: {e}")
                    print(f"Received JSON: {blockchain_json}")
                    continue
                if len(new_blockchain.chain) > len(self.blockchain.chain) and new_blockchain.is_chain_valid():
                    with self.blockchain_lock:
                        self.blockchain = new_blockchain
                    print(f"Synchronized blockchain from {addr}")

            conn.close()

    def mainloop(self):
        while True:
            self.send_data(f"This is {self.address}")
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
            self.data_queue = [f"Created by {self.address}",]
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
            self.mine()
            with self.signal_lock:
                self.getBlock=False

    def send_data_thread(self):
        while True:
            data=input()
            self.send_data(data)
            self.data_queue.append(data)
            print(f"Sent data: {data}")

if __name__ == "__main__":
    ip = input("Enter IP address: ")
    node = Node(ip)