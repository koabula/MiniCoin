from Block import Block,block_from_json
import time
from MerkleTree import MerkleTree
import json

class BlockChain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]
        self.height = 1
        self.difficulty = 5

    def create_genesis_block(self):
        return Block(0, MerkleTree(["Genesis Block"]), "0", 0, timestamp=0)

    def get_latest_block(self):
        return self.chain[-1]

    def add_block(self, data: list):
        previous_block = self.get_latest_block()
        new_block = Block(self.height, MerkleTree(data), previous_block.hash,0)
        self.chain.append(new_block)
        self.height += 1

    def append_block(self,block:Block):
        self.chain.append(block)
        self.height += 1

    def is_chain_valid(self):
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            if current_block.hash != current_block.calculate_hash():
                return (
                    False,
                    f"The hash of the {current_block.index} block is not equal to the calculated hash",
                )
            if current_block.previous_hash != previous_block.hash:
                return (
                    False,
                    f"The previous hash of the {current_block.index} block is not equal to the hash of the {previous_block.index} block",
                )
            if not current_block.hash.startswith("0" * self.difficulty):
                return (
                    False,
                    f"The hash of the {current_block.index} block does not start with {self.difficulty} zeros",
                )
        return True
    
    def is_block_valid(self,block:Block):
        if block.index != self.height:
            return False
        if not block.hash.startswith("0" * self.difficulty):
            return False
        if block.previous_hash != self.chain[-1].hash:
            return False
        if block.hash != block.calculate_hash():
            return False
        return True
    
    def to_json(self):
        return json.dumps([block.to_json() for block in self.chain[1:]], ensure_ascii=False)

    def draw_svg(self):
        # 设置基本参数
        block_width = 400  # 区块宽度
        block_height = 150  # 区块头高度
        arrow_size = 20  # 箭头大小
        node_height = 50  # Merkle树节点高度
        level_height = 120  # Merkle树层间距

        # 计算每个区块的Merkle树高度
        def calculate_tree_height(node):
            if not node:
                return 0
            return 1 + max(
                calculate_tree_height(node.left), calculate_tree_height(node.right)
            )

        # 计算每个区块的间隔
        block_spacings = []
        for block in self.chain:
            tree_height = calculate_tree_height(block.merkle_tree.root)
            block_spacing = max(200, tree_height * level_height)
            block_spacings.append(block_spacing)

        # 计算总宽度和高度
        total_width = sum(block_width + spacing for spacing in block_spacings)
        total_height = block_height + 800  # 额外高度用于显示Merkle树

        # 生成SVG头部
        svg = ['<?xml version="1.0" encoding="UTF-8"?>']
        svg.append(
            f'<svg width="{total_width}" height="{total_height}" xmlns="http://www.w3.org/2000/svg">'
        )

        # 绘制每个区块
        current_x = 0
        for i, block in enumerate(self.chain):
            x = current_x
            block_spacing = block_spacings[i]

            # 绘制区块头
            svg.append(
                f'<rect x="{x}" y="20" width="{block_width}" height="{block_height}" fill="none" stroke="black"/>'
            )

            # 区块头文本
            text_x = x + 20
            svg.append(
                f'<text x="{text_x}" y="50" font-size="16">Block Index: {block.index}</text>'
            )
            svg.append(
                f'<text x="{text_x}" y="75" font-size="16">Timestamp: {block.timestamp}</text>'
            )
            svg.append(
                f'<text x="{text_x}" y="100" font-size="16">Previous Hash: {block.previous_hash[:10]}...</text>'
            )
            svg.append(
                f'<text x="{text_x}" y="125" font-size="16">Block Hash: {block.hash[:10]}...</text>'
            )
            svg.append(
                f'<text x="{text_x}" y="150" font-size="16">Merkle Root: {block.merkle_root[:10]}...</text>'
            )

            # 如果不是最后一个区块，绘制箭头
            if i < len(self.chain) - 1:
                # 箭头起点和终点
                start_x = x + block_width
                start_y = block_height / 2 + 20
                end_x = x + block_width + block_spacing
                end_y = start_y

                # 绘制箭头主体
                svg.append(
                    f'<line x1="{start_x}" y1="{start_y}" x2="{end_x}" y2="{end_y}" stroke="black" stroke-width="2"/>'
                )

                # 绘制箭头头部
                svg.append(
                    f'<polygon points="{end_x-arrow_size},{end_y-arrow_size/2} {end_x},{end_y} {end_x-arrow_size},{end_y+arrow_size/2}" fill="black"/>'
                )

            # 绘制Merkle树
            def draw_merkle_tree(node, x, y, x_offset):
                if not node:
                    return

                # 获取当前节点宽度
                node_width = max(120, len(str(node.data)) * 15 if node.data else 120)

                # 绘制节点矩形
                svg.append(
                    f'<rect x="{x-node_width/2}" y="{y}" width="{node_width}" height="{node_height}" fill="none" stroke="black"/>'
                )

                # 绘制节点文本
                if node.data is not None:
                    # 叶子节点显示数据和哈希值
                    svg.append(
                        f'<text x="{x}" y="{y+20}" text-anchor="middle">Data: {node.data}</text>'
                    )
                    svg.append(
                        f'<text x="{x}" y="{y+40}" text-anchor="middle">Hash: {node.hash[:6]}...</text>'
                    )
                else:
                    # 非叶子节点只显示哈希值
                    svg.append(
                        f'<text x="{x}" y="{y+30}" text-anchor="middle">Hash: {node.hash[:6]}...</text>'
                    )

                # 计算子节点位置
                next_y = y + level_height
                next_x_offset = x_offset / 2

                # 递归绘制左子节点
                if node.left:
                    left_x = x - x_offset
                    svg.append(
                        f'<line x1="{x}" y1="{y+node_height}" x2="{left_x}" y2="{next_y}" stroke="black"/>'
                    )
                    draw_merkle_tree(node.left, left_x, next_y, next_x_offset)

                # 递归绘制右子节点
                if node.right:
                    right_x = x + x_offset
                    svg.append(
                        f'<line x1="{x}" y1="{y+node_height}" x2="{right_x}" y2="{next_y}" stroke="black"/>'
                    )
                    draw_merkle_tree(node.right, right_x, next_y, next_x_offset)

            # 从Merkle根开始绘制树
            initial_x_offset = block_width / 2
            tree_y = block_height + 40
            draw_merkle_tree(
                block.merkle_tree.root, x + block_width / 2, tree_y, initial_x_offset
            )

            # 更新当前x位置
            current_x += block_width + block_spacing

        svg.append("</svg>")  # 确保SVG标签闭合
        return "\n".join(svg)

    def save_svg(self, filename):
        svg_content = self.draw_svg()
        with open(filename, "w") as f:
            f.write(svg_content)

def block_chain_from_json(block_chain_json):
    block_chain_dict = json.loads(block_chain_json)
    block_chain = BlockChain()
    for block in block_chain_dict:
        block_chain.append_block(block_from_json(block))
    return block_chain

if __name__ == "__main__":
    blockchain = BlockChain()
    time.sleep(1)
    blockchain.add_block(["First Block", "hello world", "yes"])
    time.sleep(1)
    blockchain.add_block(["Second Block", "BlockChain", "I like money"])
    # blockchain.save_svg("blockchain.svg")
    print(blockchain.to_json())
    print([blockchain.chain[i].hash for i in range(len(blockchain.chain))])
    print([block_chain_from_json(blockchain.to_json()).chain[i].hash for i in range(len(block_chain_from_json(blockchain.to_json()).chain))])
