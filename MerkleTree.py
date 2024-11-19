import hashlib
import json
class MerkleNode:
    def __init__(self, left=None, right=None, data=None):
        self.left = left
        self.right = right
        self.data = data
        self.hash = self.calculate_hash()


    def calculate_hash(self):
        if self.data is not None:
            sha = hashlib.sha256()
            sha.update(str(self.data).encode("utf-8"))
            return sha.hexdigest()
        else:
            sha = hashlib.sha256()
            sha.update(str(self.left.hash).encode("utf-8") + str(self.right.hash).encode("utf-8"))
            return sha.hexdigest()

    def to_dict(self):
        return {
            'left': self.left.to_dict() if self.left else None,
            'right': self.right.to_dict() if self.right else None,
            'data': self.data,
            'hash': self.hash
        }

class MerkleTree:
    def __init__(self, data):
        self.leaves = [MerkleNode(data=d) for d in data]
        self.root = self.build_tree(self.leaves)

    def to_json(self):
        def node_to_dict(node):
            if not node:
                return None
            return {
                'left': node_to_dict(node.left),
                'right': node_to_dict(node.right),
                'data': node.data,
                'hash': node.hash
            }
        
        tree_dict = {
            'root': node_to_dict(self.root)
        }
        return json.dumps(tree_dict, ensure_ascii=False)

    def __str__(self):
        def print_node(node, level=0):
            if not node:
                return []
            result = [" " * (level * 4) + f"Hash: {node.hash}"]
            if node.data is not None:
                result.append(" " * (level * 4) + f"Data: {node.data}")
            if node.left:
                result.extend(print_node(node.left, level + 1))
            if node.right:
                result.extend(print_node(node.right, level + 1))
            return result
            
        return "\n".join(print_node(self.root))

    def get_root_hash(self):
        return self.root.hash

    def build_tree(self, nodes):
        while len(nodes) > 1:
            temp_nodes = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                right = nodes[i + 1] if i + 1 < len(nodes) else nodes[i]
                parent = MerkleNode(left=left, right=right)
                temp_nodes.append(parent)
            nodes = temp_nodes
        return nodes[0] if nodes else None
    
    def save_svg(self,filename):
        # 设置基本参数
        node_width = 120  # 节点宽度
        node_height = 50  # 节点高
        level_height = 120  # 层间距
        
        # 计算树的层数和叶子节点数
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
        
        tree_height = get_tree_height(self.root)
        leaf_count = count_leaves(self.root)
        
        # 根据树的大小动态计算画布尺寸,减小宽度
        width = max(1200, leaf_count * node_width * 1.5)  # 减小宽度倍数
        height = max(800, (tree_height + 1) * level_height * 1.5)
        
        # 生成SVG头部
        svg = [f'<?xml version="1.0" encoding="UTF-8"?>']
        svg.append(f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">')
        
        # 递归绘制节点和连线
        def draw_node(node, x, y, level, x_offset):
            if not node:
                return
                
            # 绘制节点矩形
            svg.append(f'<rect x="{x-node_width/2}" y="{y}" width="{node_width}" height="{node_height}" fill="none" stroke="black"/>')
            
            # 绘制节点文本
            if node.data is not None:
                # 叶子节点显示数据和哈希值
                svg.append(f'<text x="{x}" y="{y+20}" text-anchor="middle">Data: {node.data}</text>')
                svg.append(f'<text x="{x}" y="{y+40}" text-anchor="middle">Hash: {node.hash[:6]}...</text>')
            else:
                # 非叶子节点只显示哈希值
                svg.append(f'<text x="{x}" y="{y+30}" text-anchor="middle">Hash: {node.hash[:6]}...</text>')
            
            # 计算子节点位置
            next_y = y + level_height
            next_x_offset = x_offset / 2
            
            # 递归绘制左子节点
            if node.left:
                left_x = x - x_offset
                svg.append(f'<line x1="{x}" y1="{y+node_height}" x2="{left_x}" y2="{next_y}" stroke="black"/>')
                draw_node(node.left, left_x, next_y, level+1, next_x_offset)
            
            # 递归绘制右子节点
            if node.right:
                right_x = x + x_offset
                svg.append(f'<line x1="{x}" y1="{y+node_height}" x2="{right_x}" y2="{next_y}" stroke="black"/>')
                draw_node(node.right, right_x, next_y, level+1, next_x_offset)
        
        # 从根节点开始绘制,减小初始x偏移量
        initial_x_offset = width / 4  # 减小初始x偏移量
        draw_node(self.root, width/2, 50, 0, initial_x_offset)
        
        # 关闭SVG标签
        svg.append('</svg>')
        
        # 将SVG内容写入文件
        with open(filename, 'w') as f:
            f.write('\n'.join(svg))
        
def merkle_tree_from_json(json_data):
    def dict_to_node(node_dict):
        if not node_dict:
            return None
        node = MerkleNode(
            left=dict_to_node(node_dict['left']),
            right=dict_to_node(node_dict['right']),
            data=node_dict['data']
        )
        node.hash = node_dict['hash']
        return node
    
    data = json.loads(json_data)
    tree = MerkleTree([])  # 初始化一个空的 MerkleTree
    tree.root = dict_to_node(data['root'])
    
    # 初始化 leaves
    def collect_leaves(node):
        if not node:
            return []
        if not node.left and not node.right:
            return [node]
        return collect_leaves(node.left) + collect_leaves(node.right)
    
    tree.leaves = collect_leaves(tree.root)
    
    return tree

if __name__ == "__main__":
    data = ["a", "b", "c","d","e","f",]
    tree = MerkleTree(data)
    # print(tree)
    # print(tree.to_json())
    tree = merkle_tree_from_json(tree.to_json())
    print(tree)
    # tree.save_svg("merkle_tree.svg")
