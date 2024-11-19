import hashlib
import time
import json
from MerkleTree import MerkleTree, merkle_tree_from_json


class Block:
    def __init__(
        self, index, merkle_tree: MerkleTree, previous_hash, nonce, timestamp=None
    ):
        self.index = index
        self.timestamp = time.time() if timestamp is None else timestamp  # 当前时间戳
        self.merkle_tree = merkle_tree
        self.merkle_root = merkle_tree.get_root_hash()
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        # 计算区块的hash值
        # 这里我们使用sha256算法
        sha = hashlib.sha256()
        sha.update(
            str(self.index).encode("utf-8")
            + str(self.timestamp).encode("utf-8")
            + str(self.merkle_root).encode("utf-8")
            + str(self.previous_hash).encode("utf-8")
            + str(self.nonce).encode("utf-8")
        )
        return sha.hexdigest()
    
    def to_json(self):
        # 自定义序列化过程
        block_dict = {
            'index': self.index,
            'timestamp': self.timestamp,
            'merkle_tree': self.merkle_tree.to_json(),
            'previous_hash': self.previous_hash,
            'nonce': self.nonce,
            'hash': self.hash
        }
        return json.dumps(block_dict, ensure_ascii=False)

    def __str__(self, show_merkle_tree=False):
        if show_merkle_tree:
            return f"Block(index={self.index},\n timestamp={self.timestamp},\n merkle_root={self.merkle_root},\n previous_hash={self.previous_hash},\n hash={self.hash}) \n merkle tree: \n{self.merkle_tree.__str__()}"
        else:
            return f"Block(index={self.index},\n timestamp={self.timestamp},\n merkle_root={self.merkle_root},\n previous_hash={self.previous_hash},\n hash={self.hash})"

    def draw_svg(self):
        # 设置基本参数
        node_height = 50  # 节点高度
        level_height = 120  # 层间距

        # 计算Merkle树的层数和叶子节点数
        def get_tree_height(node):
            if not node:
                return 0
            return 1 + max(get_tree_height(node.left), get_tree_height(node.right))

        def count_leaves(node):
            if not node:
                return 0
            if not node.left and not node.right:
                return 1
            return count_leaves(node.left) + count_leaves(node.right)

        # 计算叶子节点宽度
        def get_node_width(node):
            if not node:
                return 120  # 默认宽度
            if node.data is not None:
                # 根据数据长度调整宽度,最小120
                return max(120, len(str(node.data)) * 15)
            return 120  # 非叶子节点使用默认宽度

        tree_height = get_tree_height(self.merkle_tree.root)
        leaf_count = count_leaves(self.merkle_tree.root)

        # 计算画布尺寸
        max_leaf_width = max(get_node_width(leaf) for leaf in self.merkle_tree.leaves)
        width = max(1200, leaf_count * max_leaf_width * 1.5)
        height = max(
            800, (tree_height + 3) * level_height * 1.5
        )  # 增加高度以容纳区块头

        # 生成SVG头部
        svg = [f'<?xml version="1.0" encoding="UTF-8"?>']
        svg.append(
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        )

        # 绘制区块头
        header_height = 150
        header_width = 400
        header_x = (width - header_width) / 2
        svg.append(
            f'<rect x="{header_x}" y="20" width="{header_width}" height="{header_height}" fill="none" stroke="black"/>'
        )

        # 居中对齐的区块头文本
        text_x = header_x + 20
        svg.append(
            f'<text x="{text_x}" y="50" font-size="16">Block Index: {self.index}</text>'
        )
        svg.append(
            f'<text x="{text_x}" y="75" font-size="16">Timestamp: {self.timestamp}</text>'
        )
        svg.append(
            f'<text x="{text_x}" y="100" font-size="16">Previous Hash: {self.previous_hash[:10]}...</text>'
        )
        svg.append(
            f'<text x="{text_x}" y="125" font-size="16">Block Hash: {self.hash[:10]}...</text>'
        )
        svg.append(
            f'<text x="{text_x}" y="150" font-size="16">Merkle Root: {self.merkle_root[:10]}...</text>'
        )

        # 递归绘制Merkle树节点和连线
        def draw_node(node, x, y, level, x_offset):
            if not node:
                return

            # 获取当前节点宽度
            node_width = get_node_width(node)

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
                draw_node(node.left, left_x, next_y, level + 1, next_x_offset)

            # 递归绘制右子节点
            if node.right:
                right_x = x + x_offset
                svg.append(
                    f'<line x1="{x}" y1="{y+node_height}" x2="{right_x}" y2="{next_y}" stroke="black"/>'
                )
                draw_node(node.right, right_x, next_y, level + 1, next_x_offset)

        # 从Merkle根开始绘制树
        initial_x_offset = width / 4
        # 添加从区块头到Merkle根的连接线
        svg.append(
            f'<line x1="{width/2}" y1="{header_height+20}" x2="{width/2}" y2="{header_height+50}" stroke="black"/>'
        )
        draw_node(
            self.merkle_tree.root, width / 2, header_height + 50, 0, initial_x_offset
        )

        # 关闭SVG标签
        svg.append("</svg>")

        return "\n".join(svg)

    def save_svg(self, filename):
        svg_content = self.draw_svg()
        with open(filename, "w") as f:
            f.write(svg_content)

def block_from_json(block_json):
    # 将JSON字符串解析为字典
    block_data = json.loads(block_json)
    
    # 从字典中提取构造Block对象所需的参数
    index = block_data['index']
    previous_hash = block_data['previous_hash']
    nonce = block_data['nonce']
    timestamp = block_data.get('timestamp', None)
    
    # 反序列化MerkleTree
    merkle_tree_data = block_data['merkle_tree']
    merkle_tree = merkle_tree_from_json(merkle_tree_data)
    
    # 创建并返回Block对象
    block = Block(index, merkle_tree, previous_hash, nonce, timestamp)
    block.hash = block_data['hash']  # 直接使用已保存的哈希值
    return block


if __name__ == "__main__":
    block = Block(0, MerkleTree(["a", "b", "c"]), "0", 0)
    print(block)
    print(block.merkle_tree)
    print("--------------------------------")
    block = block_from_json(block.to_json())
    print(block)
    print(block.merkle_tree)
    print([leaf.data for leaf in block.merkle_tree.leaves])
