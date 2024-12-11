import tkinter as tk
from tkinter import ttk, messagebox
import socket
from Node import Node
import threading

class BlockchainApp:
    def __init__(self, root,ip):
        self.root = root
        self.root.title("Koala Wallet")
        
        # 添加线程列表用于跟踪
        self.threads = []
        
        # 添加关闭窗口的处理
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 标记程序是否正在运行
        self.running = True
        
        # 获取本机IP
        self.ip = ip
        
        # 创建节点
        self.node = None
        self.init_node()
        
        # 创建界面
        self.create_widgets()
        
        # 定期更新余额
        self.update_balance()
        
    def init_node(self):
        # 在新线程中初始化节点
        def node_thread():
            self.node = Node(self.ip)
        
        thread = threading.Thread(target=node_thread)
        thread.daemon = True  # 设置为守护线程
        self.threads.append(thread)  # 添加到线程列表
        thread.start()
        
    def create_widgets(self):
        # IP地址显示
        ttk.Label(self.root, text="节点IP地址:").pack(pady=5)
        ttk.Label(self.root, text=self.ip).pack()
        
        # 钱包地址显示框架
        wallet_frame = ttk.Frame(self.root)
        wallet_frame.pack(pady=5, fill="x", padx=10)
        
        ttk.Label(wallet_frame, text="钱包地址:").pack(side="left", padx=(0,5))
        self.wallet_label = ttk.Entry(wallet_frame, state='readonly')
        self.wallet_label.pack(side="left", fill="x", expand=True)
        
        copy_btn = ttk.Button(wallet_frame, text="复制", 
                            command=lambda: self.copy_to_clipboard(self.wallet_label.get()))
        copy_btn.pack(side="left", padx=(5,0))
        
        # 余额显示
        ttk.Label(self.root, text="当前余额:").pack(pady=5)
        self.balance_label = ttk.Label(self.root, text="等待节点初始化...")
        self.balance_label.pack()
        
        # 转账框架
        transfer_frame = ttk.LabelFrame(self.root, text="转账", padding=10)
        transfer_frame.pack(pady=10, padx=10, fill="x")
        
        # 接收地址输入
        ttk.Label(transfer_frame, text="接收地址:").pack()
        self.address_entry = ttk.Entry(transfer_frame, width=50)
        self.address_entry.pack(pady=5)
        
        # 金额输入
        ttk.Label(transfer_frame, text="转账金额:").pack()
        self.amount_entry = ttk.Entry(transfer_frame)
        self.amount_entry.pack(pady=5)
        
        # 转账按钮
        self.transfer_btn = ttk.Button(transfer_frame, text="转账", command=self.transfer)
        self.transfer_btn.pack(pady=5)
        
    def on_closing(self):
        """处理窗口关闭事件"""
        self.running = False
        
        # 关闭节点的socket连接
        if self.node and hasattr(self.node, 'socket'):
            try:
                self.node.socket.close()
            except:
                pass
        
        # 等待所有线程结束
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=1.0)  # 等待最多1秒
        
        # 销毁窗口
        self.root.destroy()
        
    def copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        
    def update_balance(self):
        if not self.running:
            return
            
        if self.node and self.node.wallet:
            # 更新钱包地址
            self.wallet_label.configure(state='normal')
            self.wallet_label.delete(0, tk.END)
            self.wallet_label.insert(0, self.node.wallet.address)
            self.wallet_label.configure(state='readonly')
            
            # 计算并更新余额
            total_balance = sum(utxo.amount for utxo in self.node.wallet.utxo_pool)
            self.balance_label.config(text=f"{total_balance} coins")
            
        if self.running:
            self.root.after(1000, self.update_balance)
        
    def transfer(self):
        if not self.node:
            messagebox.showerror("错误", "节点尚未初始化完成")
            return
            
        try:
            recipient = self.address_entry.get()
            amount = float(self.amount_entry.get())
            
            if not recipient or amount <= 0:
                messagebox.showerror("错误", "请输入有效的接收地址和转账金额")
                return
                
            # 创建交易
            transaction = self.node.wallet.create_transaction(recipient, amount)
            
            # 广播交易
            self.node.send_transaction(transaction)
            
            messagebox.showinfo("成功", "转账交易已发送")
            
            # 清空输入框
            self.address_entry.delete(0, tk.END)
            self.amount_entry.delete(0, tk.END)
            
        except ValueError as e:
            messagebox.showerror("错误", str(e))
        except Exception as e:
            messagebox.showerror("错误", f"转账失败: {str(e)}")

if __name__ == "__main__":
    ip = input("请输入节点IP地址:")
    root = tk.Tk()
    app = BlockchainApp(root,ip)
    root.mainloop()

