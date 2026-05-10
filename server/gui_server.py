"""
PortPier Server - Visual Management Interface
TCP port mapping server with GUI interface
Supports Chinese and English languages
"""
import asyncio
import sys
import json
import os
import hashlib
import base64
import struct
import threading
import time
import socket
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext

# 导入国际化模块
from i18n import get_i18n, load_lang_config, save_lang_config
i18n = get_i18n()

# Windows 编码兼容
if sys.platform == 'win32':
    import ctypes
    try:
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except:
        pass
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 全局异常处理
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=== TCP Server Crash Log ===\n")
            import traceback
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass

sys.excepthook = global_exception_handler

# 协议常量
HEADER_FORMAT = '!II'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

def encode_packet(stream_id: int, data: bytes) -> bytes:
    return struct.pack(HEADER_FORMAT, stream_id, len(data)) + data

def decode_packet(data: bytes):
    if len(data) < HEADER_SIZE:
        return None, None, data
    stream_id, data_len = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    if len(data) < HEADER_SIZE + data_len:
        return None, None, data
    packet_data = data[HEADER_SIZE:HEADER_SIZE+data_len]
    remaining = data[HEADER_SIZE+data_len:]
    return stream_id, packet_data, remaining

# 路径处理
# 获取程序所在目录（打包后使用 exe 所在目录）
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 开发环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')
ALLOWED_CLIENTS_FILE = os.path.join(BASE_DIR, 'allowed_clients.json')

# ---------- 密码/Token 哈希工具 ----------
def hash_secret(secret: str, salt: bytes = None) -> tuple:
    if salt is None:
        salt = os.urandom(32)
    else:
        salt = base64.b64decode(salt)
    key = hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt).decode(), base64.b64encode(key).decode()

def verify_secret(secret: str, salt_b64: str, hash_b64: str) -> bool:
    salt = base64.b64decode(salt_b64)
    stored_hash = base64.b64decode(hash_b64)
    key = hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), salt, 100000)
    return key == stored_hash

# ---------- 配置文件加载 ----------
def is_ip_allowed(ip: str, whitelist: str, blacklist: str) -> bool:
    """检查 IP 是否在白名单中且不在黑名单中
    
    Args:
        ip: 要检查的 IP 地址
        whitelist: 白名单，逗号分隔的 IP 或 IP 段（如 "192.168.1.0/24,10.0.0.1"），空表示允许所有
        blacklist: 黑名单，逗号分隔的 IP 或 IP 段，空表示不阻止任何
    
    Returns:
        True 表示允许，False 表示拒绝
    """
    if not ip:
        return False
    
    # 先检查黑名单（黑名单优先）
    if blacklist:
        for item in blacklist.replace(' ', '').split(','):
            if item and _match_ip(ip, item):
                return False
    
    # 再检查白名单（白名单为空表示允许所有）
    if not whitelist:
        return True
    
    for item in whitelist.replace(' ', '').split(','):
        if item and _match_ip(ip, item):
            return True
    
    return False

def _match_ip(ip: str, pattern: str) -> bool:
    """检查 IP 是否匹配模式（支持单个 IP、CIDR、IP 段、IP 范围）
    
    Args:
        ip: 要检查的 IP 地址
        pattern: 模式，可以是：
            - 单个 IP: "192.168.1.100"
            - CIDR: "192.168.1.0/24"
            - IP 通配符: "192.168.1.*"
            - IP 范围: "192.168.1.1-192.168.1.255"
    
    Returns:
        True 表示匹配
    """
    if not pattern:
        return False
    
    # IP 范围格式 (如 113.82.193.1-113.82.193.255)
    if '-' in pattern and '/' not in pattern and '*' not in pattern:
        try:
            start_ip, end_ip = pattern.split('-')
            ip_int = _ip_to_int(ip.strip())
            start_int = _ip_to_int(start_ip.strip())
            end_int = _ip_to_int(end_ip.strip())
            return start_int <= ip_int <= end_int
        except:
            return False
    
    # 单个 IP 精确匹配
    if '/' not in pattern and '*' not in pattern:
        return ip == pattern
    
    # CIDR 格式
    if '/' in pattern:
        try:
            network, prefix_len = pattern.split('/')
            prefix_len = int(prefix_len)
            # 将 IP 转换为整数
            ip_int = _ip_to_int(ip)
            network_int = _ip_to_int(network)
            # 计算掩码
            mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
            return (ip_int & mask) == (network_int & mask)
        except:
            return False
    
    # 通配符格式 (如 192.168.1.*)
    if '*' in pattern:
        pattern_parts = pattern.split('.')
        ip_parts = ip.split('.')
        if len(pattern_parts) != 4 or len(ip_parts) != 4:
            return False
        for p, i in zip(pattern_parts, ip_parts):
            if p != '*' and p != i:
                return False
        return True
    
    return False

def _ip_to_int(ip: str) -> int:
    """将 IP 地址转换为整数"""
    parts = ip.split('.')
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])

def load_config():
    if not os.path.exists(CONFIG_FILE):
        salt, pwd_hash = hash_secret("admin")
        default = {
            "username": "admin",
            "salt": salt,
            "password_hash": pwd_hash,
            "global_allowed_ports": "1000-20000",
            "client_ip_whitelist": "",      # 客户端IP白名单，空表示允许所有
            "client_ip_blacklist": "",      # 客户端IP黑名单
            "visitor_ip_whitelist": "",     # 访客IP白名单，空表示允许所有
            "visitor_ip_blacklist": "",     # 访客IP黑名单
            "visitor_redirect_url": ""      # 被拒绝访客的跳转URL
        }
        save_config(default)
        return default
    with open(CONFIG_FILE, 'r') as f:
        cfg = json.load(f)
        # 确保新字段存在
        cfg.setdefault("client_ip_whitelist", "")
        cfg.setdefault("client_ip_blacklist", "")
        cfg.setdefault("visitor_ip_whitelist", "")
        cfg.setdefault("visitor_ip_blacklist", "")
        cfg.setdefault("visitor_redirect_url", "")
        return cfg

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def is_port_allowed(port: int, range_str: str) -> bool:
    if not range_str:
        return True
    parts = range_str.replace(' ', '').split(',')
    for part in parts:
        if '-' in part:
            start, end = map(int, part.split('-'))
            if start <= port <= end:
                return True
        else:
            if int(part) == port:
                return True
    return False

def load_allowed_clients():
    if not os.path.exists(ALLOWED_CLIENTS_FILE):
        save_allowed_clients({})
        return {}
    with open(ALLOWED_CLIENTS_FILE, 'r') as f:
        return json.load(f)

def save_allowed_clients(clients):
    with open(ALLOWED_CLIENTS_FILE, 'w') as f:
        json.dump(clients, f, indent=2)

def get_client_allowed_ports(client_id):
    clients = load_allowed_clients()
    client_info = clients.get(client_id, {})
    return client_info.get('allowed_ports') or config.get('global_allowed_ports', '')

# 全局配置
config = {}

# ---------- 登录窗口 ----------
class LoginDialog:
    def __init__(self, parent):
        self.result = False
        self.dialog = Toplevel(parent)
        self.dialog.title(i18n.t("login_title"))
        self.dialog.geometry("400x280")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # 居中显示
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - 400) // 2
        y = (self.dialog.winfo_screenheight() - 280) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        # 界面
        self._create_widgets()
        
        # 绑定回车键
        self.dialog.bind('<Return>', lambda e: self._do_login())
        
    def _create_widgets(self):
        # 主框架
        main_frame = Frame(self.dialog, padx=30, pady=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        Label(main_frame, text=i18n.t("window_title"), 
              font=('Microsoft YaHei UI', 16, 'bold'),
              fg='#2c3e50').pack(pady=(0, 20))
        
        # 用户名
        Label(main_frame, text=i18n.t("login_username"), font=('Microsoft YaHei UI', 10),
              anchor=W).pack(fill=X)
        self.username_var = StringVar(value="admin")
        Entry(main_frame, textvariable=self.username_var, 
              font=('Microsoft YaHei UI', 11)).pack(fill=X, pady=(0, 10))
        
        # 密码
        Label(main_frame, text=i18n.t("login_password"), font=('Microsoft YaHei UI', 10),
              anchor=W).pack(fill=X)
        self.password_var = StringVar()
        Entry(main_frame, textvariable=self.password_var, show='*',
              font=('Microsoft YaHei UI', 11)).pack(fill=X, pady=(0, 10))
        
        # 错误提示
        self.error_var = StringVar()
        Label(main_frame, textvariable=self.error_var, fg='red',
              font=('Microsoft YaHei UI', 9)).pack(pady=(0, 10))
        
        # 按钮
        btn_frame = Frame(main_frame)
        btn_frame.pack(fill=X)
        
        Button(btn_frame, text=i18n.t("login_button"), bg='#27ae60', fg='white',
               font=('Microsoft YaHei UI', 11, 'bold'),
               command=self._do_login).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        Button(btn_frame, text=i18n.t("settings_cancel"), bg='#95a5a6', fg='white',
               font=('Microsoft YaHei UI', 11, 'bold'),
               command=self._cancel).pack(side=LEFT, fill=X, expand=True)
        
    def _do_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            self.error_var.set(i18n.t("login_wrong_password"))
            return
            
        if username != config.get('username', 'admin'):
            self.error_var.set(i18n.t("login_wrong_password"))
            return
            
        if not verify_secret(password, config.get('salt', ''), config.get('password_hash', '')):
            self.error_var.set(i18n.t("login_wrong_password"))
            return
            
        self.result = True
        self.dialog.destroy()
        
    def _cancel(self):
        self.result = False
        self.dialog.destroy()

# ---------- ClientHandler ----------
class ClientHandler:
    def __init__(self, reader, writer, client_id, log_callback=None, refresh_callback=None):
        self.reader = reader
        self.writer = writer
        self.client_id = client_id
        self.next_stream_id = 1
        self.stream_queues = {}
        self.read_task = None
        self.rules = []
        self.servers = []  # 保存所有子服务器
        self.log_callback = log_callback or (lambda msg: None)
        self.refresh_callback = refresh_callback or (lambda: None)
        self.connected = True

    async def start(self):
        self.read_task = asyncio.create_task(self._read_loop())
        self.log_callback(i18n.t("log_client_connected", client_id=self.client_id), 'success')
        self.refresh_callback()

    async def stop(self):
        """停止所有子服务器"""
        self.connected = False
        if self.read_task:
            self.read_task.cancel()
        
        # 关闭所有子服务器（不等待活跃连接，直接关 socket）
        for server in self.servers:
            try:
                server.close()
                # 直接关闭底层 socket，不等待活跃连接结束
                for sock in server.sockets:
                    try:
                        sock.close()
                    except:
                        pass
            except:
                pass
        self.servers.clear()
        
        try:
            if not self.writer.is_closing():
                self.writer.close()
        except:
            pass
        self.refresh_callback()

    async def sync_rules(self, rules):
        self.rules = rules
        for rule in rules:
            self.next_stream_id += 1
            stream_id = self.next_stream_id
            addr = f"{rule['target_host']}:{rule['target_port']}".encode()
            self.writer.write(encode_packet(stream_id, addr))
            await self.writer.drain()
            q = asyncio.Queue()
            self.stream_queues[stream_id] = q
            asyncio.create_task(self._handle_local(rule, stream_id, q))
            self.log_callback(i18n.t("log_rule_added", port=rule['public_port'], host=rule['target_host'], target_port=rule['target_port']))

    async def add_rule(self, rule):
        self.rules.append(rule)
        # 不发送地址包！地址包只在真实连接进来时发送（参照原始 server.py 的 start_proxy）
        self.next_stream_id += 1
        rule['_server'] = None
        asyncio.create_task(self._handle_local(rule))
        self.log_callback(i18n.t("log_rule_added", port=rule['public_port'], host=rule['target_host'], target_port=rule['target_port']))
        self.refresh_callback()

    async def remove_rule(self, rule):
        match = next((r for r in self.rules if r['public_port'] == rule['public_port']), None)
        if match:
            self.rules.remove(match)
            # 关闭对应的服务器
            server = match.get('_server')
            if server:
                try:
                    server.close()
                    self.servers.remove(server)
                except:
                    pass
            self.log_callback(i18n.t("log_rule_removed", port=rule['public_port']))
            self.refresh_callback()

    async def _handle_local(self, rule):
        """处理本地端口监听，为每个新连接分配独立的 stream_id"""
        try:
            pub_port = rule['public_port']
            bind = rule.get('bind', '0.0.0.0')
            
            # 创建 socket 并设置 SO_REUSEADDR
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((bind, pub_port))
            sock.listen(100)
            
            # 使用自定义处理函数为每个连接分配独立 stream_id
            async def handle_new_conn(reader, writer):
                # 获取访客 IP（先用 peername，后面会从 HTTP 头部获取真实 IP）
                addr = writer.get_extra_info('peername')
                visitor_ip = addr[0] if addr else 'unknown'
                visitor_port = addr[1] if addr else 0
                
                # 读取第一个数据包，解析 HTTP 头部获取真实 IP
                first_data = await reader.read(8192)
                if not first_data:
                    writer.close()
                    return
                
                # 尝试从 HTTP 头部获取真实 IP
                real_ip = visitor_ip
                try:
                    text = first_data.decode('utf-8', errors='ignore')
                    if text.startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ')):
                        for line in text.split('\r\n'):
                            ll = line.lower()
                            if ll.startswith('x-real-ip:'):
                                real_ip = line.split(':', 1)[1].strip()
                            elif ll.startswith('x-forwarded-for:'):
                                real_ip = line.split(':', 1)[1].strip().split(',')[0].strip()
                except:
                    pass
                
                # 使用真实 IP 进行检查
                if real_ip != visitor_ip:
                    visitor_ip = real_ip
                
                # 检查访客 IP 白名单/黑名单
                current_config = load_config()
                visitor_whitelist = current_config.get('visitor_ip_whitelist', '')
                visitor_blacklist = current_config.get('visitor_ip_blacklist', '')
                
                if not is_ip_allowed(visitor_ip, visitor_whitelist, visitor_blacklist):
                    self.log_callback(i18n.t("log_visitor_denied", ip=visitor_ip, port=rule['public_port']))
                    # 发送 HTTP 重定向响应
                    redirect_url = current_config.get('visitor_redirect_url', '')
                    if redirect_url:
                        response = (
                            f"HTTP/1.1 302 Found\r\n"
                            f"Location: {redirect_url}\r\n"
                            f"Connection: close\r\n"
                            f"\r\n"
                        )
                    else:
                        response = (
                            "HTTP/1.1 403 Forbidden\r\n"
                            "Content-Type: text/html; charset=utf-8\r\n"
                            "Connection: close\r\n"
                            "\r\n"
                            "<html><body><h1>403 Forbidden</h1>"
                            "<p>Your IP address is not allowed to access this resource.</p>"
                            "</body></html>"
                        )
                    try:
                        writer.write(response.encode())
                        await writer.drain()
                    except:
                        pass
                    writer.close()
                    return
                
                # 为每个新连接分配独立的 stream_id
                self.next_stream_id += 1
                conn_stream_id = self.next_stream_id
                
                # 创建独立的队列
                conn_queue = asyncio.Queue()
                self.stream_queues[conn_stream_id] = conn_queue
                
                # 发送连接地址给客户端
                addr_data = f"{rule['target_host']}:{rule['target_port']}".encode()
                self.writer.write(encode_packet(conn_stream_id, addr_data))
                await self.writer.drain()
                
                # 处理连接（传递第一个数据包）
                await self._handle_conn(reader, writer, conn_stream_id, conn_queue, rule, first_data)
            
            server = await asyncio.start_server(handle_new_conn, sock=sock)
            self.servers.append(server)  # 保存服务器引用
            rule['_server'] = server  # 保存到规则中，便于删除时关闭
            self.log_callback(i18n.t("log_listener_started", port=pub_port))
            await server.wait_closed()
        except Exception as e:
            self.log_callback(i18n.t("log_listener_error", port=rule['public_port'], error=str(e)), 'error')

    async def _handle_conn(self, reader, writer, stream_id, queue, rule, first_data=None):
        addr = writer.get_extra_info('peername')
        client_ip = addr[0] if addr else 'unknown'
        client_port = addr[1] if addr else 0
        
        # 解析第一个数据包获取真实 IP 和 HTTP 信息
        real_ip = client_ip
        http_method = ''
        http_path = ''
        http_host = ''
        
        if first_data:
            # 先发送第一个数据包给客户端
            self.writer.write(encode_packet(stream_id, first_data))
            await self.writer.drain()
            
            # 解析 HTTP 头部
            try:
                text = first_data.decode('utf-8', errors='ignore')
                if text.startswith(('GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ')):
                    first_line = text.split('\r\n')[0]
                    parts = first_line.split(' ')
                    if len(parts) >= 2:
                        http_method, http_path = parts[0], parts[1]
                    for line in text.split('\r\n'):
                        ll = line.lower()
                        if ll.startswith('host:'):
                            http_host = line.split(':', 1)[1].strip()
                        elif ll.startswith('x-real-ip:'):
                            real_ip = line.split(':', 1)[1].strip()
                        elif ll.startswith('x-forwarded-for:'):
                            real_ip = line.split(':', 1)[1].strip().split(',')[0].strip()
            except:
                pass
        
        if real_ip != client_ip:
            self.log_callback(i18n.t("log_visitor", ip=real_ip, port=client_port, public_port=rule['public_port']))
            if http_method:
                self.log_callback(i18n.t("log_http_request", ip=real_ip, method=http_method, host=http_host, path=http_path))
        else:
            self.log_callback(i18n.t("log_visitor", ip=client_ip, port=client_port, public_port=rule['public_port']))
            if http_method:
                self.log_callback(i18n.t("log_http_request", ip=client_ip, method=http_method, host=http_host, path=http_path))

        async def forward_user_to_client():
            # 第一个数据包已在上面发送，这里继续读取后续数据
            try:
                while True:
                    data = await reader.read(8192)
                    if not data:
                        break
                    self.writer.write(encode_packet(stream_id, data))
                    await self.writer.drain()
            except:
                pass
            finally:
                # 通知客户端流结束
                try:
                    self.writer.write(encode_packet(stream_id, b''))
                    await self.writer.drain()
                except:
                    pass
                # 通知 forward_client_to_user 退出（不要 pop stream_queues！）
                await queue.put(None)
                writer.close()

        async def forward_client_to_user():
            try:
                while True:
                    data = await queue.get()
                    if data is None:
                        break
                    writer.write(data)
                    await writer.drain()
            except:
                pass

        await asyncio.gather(forward_user_to_client(), forward_client_to_user())
        # 两个协程都结束后再清理队列
        self.stream_queues.pop(stream_id, None)

    async def _read_loop(self):
        buffer = b''
        try:
            while True:
                data = await self.reader.read(65536)
                if not data:
                    self.log_callback(i18n.t("log_client_disconnected", client_id=self.client_id), 'warning')
                    break
                buffer += data
                while True:
                    stream_id, packet_data, remaining = decode_packet(buffer)
                    if stream_id is None:
                        break
                    buffer = remaining
                    if stream_id == 0:
                        try:
                            msg = json.loads(packet_data.decode())
                            action = msg.get('action')
                            if action == 'pong':
                                self.log_callback(i18n.t("log_heartbeat", client_id=self.client_id))
                            elif action == 'add':
                                # 处理添加规则
                                rule = msg.get('rule')
                                if rule:
                                    allowed_ports = get_client_allowed_ports(self.client_id)
                                    if is_port_allowed(rule['public_port'], allowed_ports):
                                        await self.add_rule(rule)
                                        self.log_callback(i18n.t("log_client_add_rule", client_id=self.client_id, port=rule['public_port']))
                                    else:
                                        self.log_callback(i18n.t("log_port_denied", port=rule['public_port']), 'warning')
                            elif action == 'remove':
                                # 处理删除规则
                                pub_port = msg.get('public_port')
                                rule = next((r for r in self.rules if r['public_port'] == pub_port), None)
                                if rule:
                                    await self.remove_rule(rule)
                                    self.log_callback(i18n.t("log_client_delete_rule", client_id=self.client_id, port=pub_port))
                        except:
                            pass
                        continue
                    q = self.stream_queues.get(stream_id)
                    if q:
                        if packet_data:
                            await q.put(packet_data)
                        else:
                            await q.put(None)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.log_callback(i18n.t("log_read_error", error=str(e)), 'error')
        finally:
            self.connected = False
            for q in self.stream_queues.values():
                await q.put(None)
            try:
                if not self.writer.is_closing():
                    self.writer.close()
            except:
                pass
            self.log_callback(i18n.t("log_cleanup", client_id=self.client_id), 'warning')
            self.refresh_callback()

# ---------- 全局状态 ----------
online_clients = {}
control_server = None

# ---------- GUI 服务器类 ----------
class ServerGUI:
    def __init__(self):
        # 创建主窗口
        self.root = Tk()
        
        # 加载语言配置
        lang = load_lang_config()
        i18n.set_lang(lang)
        
        self.root.title(i18n.t("window_title"))
        self.root.geometry("400x280")
        self.root.resizable(False, False)
        
        # 加载配置（如果不存在会自动创建默认配置）
        global config
        config = load_config()
        
        # 确保配置文件已创建（首次运行时）
        if not os.path.exists(CONFIG_FILE):
            save_config(config)
        
        # 配色
        self.colors = {
            'bg': '#f5f6fa',
            'sidebar': '#2c3e50',
            'primary': '#3498db',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'text': '#2c3e50',
            'light': '#ecf0f1',
            'white': '#ffffff'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # 服务器状态
        self.server_running = False
        self.server_thread = None
        self.loop = None
        self.server = None
        self.stop_event = threading.Event()  # 停止信号
        self._login_success = False
        
        # 显示登录界面
        self._create_login_widgets()
    
    def _create_login_widgets(self):
        """创建登录界面"""
        # 清空窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 主框架
        main_frame = Frame(self.root, padx=30, pady=20)
        main_frame.pack(fill=BOTH, expand=True)
        
        # 标题
        Label(main_frame, text=i18n.t("window_title"), 
              font=('Microsoft YaHei UI', 16, 'bold'),
              fg='#2c3e50').pack(pady=(0, 20))
        
        # 用户名
        Label(main_frame, text=i18n.t("login_username"), font=('Microsoft YaHei UI', 10),
              anchor=W).pack(fill=X)
        self.username_var = StringVar(value="admin")
        Entry(main_frame, textvariable=self.username_var, 
              font=('Microsoft YaHei UI', 11)).pack(fill=X, pady=(0, 10))
        
        # 密码
        Label(main_frame, text=i18n.t("login_password"), font=('Microsoft YaHei UI', 10),
              anchor=W).pack(fill=X)
        self.password_var = StringVar()
        self.password_entry = Entry(main_frame, textvariable=self.password_var, show='*',
              font=('Microsoft YaHei UI', 11))
        self.password_entry.pack(fill=X, pady=(0, 10))
        
        # 错误提示
        self.login_error_var = StringVar()
        Label(main_frame, textvariable=self.login_error_var, fg='red',
              font=('Microsoft YaHei UI', 9)).pack(pady=(0, 10))
        
        # 按钮
        btn_frame = Frame(main_frame)
        btn_frame.pack(fill=X)
        
        Button(btn_frame, text=i18n.t("login_button"), bg='#27ae60', fg='white',
               font=('Microsoft YaHei UI', 11, 'bold'),
               command=self._do_login).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        
        Button(btn_frame, text=i18n.t("login_cancel"), bg='#95a5a6', fg='white',
               font=('Microsoft YaHei UI', 11, 'bold'),
               command=self._cancel_login).pack(side=LEFT, fill=X, expand=True)
        
        # 绑定回车键
        self.root.bind('<Return>', lambda e: self._do_login())
        
        # 聚焦密码输入框
        self.password_entry.focus_set()
    
    def _do_login(self):
        """执行登录"""
        username = self.username_var.get().strip()
        password = self.password_var.get()
        
        if not username or not password:
            self.login_error_var.set(i18n.t("login_wrong_password"))
            return
            
        if username != config.get('username', 'admin'):
            self.login_error_var.set(i18n.t("login_wrong_password"))
            return
            
        if not verify_secret(password, config.get('salt', ''), config.get('password_hash', '')):
            self.login_error_var.set(i18n.t("login_wrong_password"))
            return
        
        # 登录成功
        self._login_success = True
        self._init_main_gui()
    
    def _cancel_login(self):
        """取消登录"""
        self.root.destroy()
    
    def _init_main_gui(self):
        """初始化主界面"""
        # 解绑回车键
        self.root.unbind('<Return>')
        
        # 清空所有旧控件（登录界面）
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 设置主窗口
        self.root.title(i18n.t("server_title"))
        self.root.geometry("1200x750")
        self.root.minsize(1000, 600)
        self.root.resizable(True, True)
        
        # 创建界面
        self._create_widgets()
        
        # 加载数据
        self._load_data()
        
        # 启动定时刷新
        self._auto_refresh()
        
    def _create_widgets(self):
        # 主容器
        main_container = Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 左侧管理面板（固定宽度）
        left_panel = Frame(main_container, bg=self.colors['white'], relief=RAISED, bd=1, width=480)
        left_panel.pack(side=LEFT, fill=Y, padx=(0, 5))
        left_panel.pack_propagate(False)  # 保持固定宽度
        
        # 右侧日志面板（占据剩余空间）
        right_panel = Frame(main_container, bg=self.colors['white'], relief=RAISED, bd=1)
        right_panel.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))
        
        # 创建左侧内容
        self._create_left_panel(left_panel)
        
        # 创建右侧内容
        self._create_right_panel(right_panel)
        
    def _create_left_panel(self, parent):
        # 顶部标题栏
        header = Frame(parent, bg=self.colors['primary'], height=50)
        header.pack(fill=X)
        header.pack_propagate(False)
        
        # 保存标题标签引用，用于语言切换时更新
        self.header_title_label = Label(header, text=i18n.t("window_title"), 
              font=('Microsoft YaHei UI', 14, 'bold'),
              bg=self.colors['primary'], fg='white')
        self.header_title_label.pack(side=LEFT, padx=15, pady=10)
        
        # 服务器控制按钮
        self.btn_start = Button(header, text=i18n.t("btn_start"), 
                               bg=self.colors['success'], fg='white',
                               font=('Microsoft YaHei UI', 10, 'bold'),
                               command=self._toggle_server, relief=FLAT, padx=20)
        self.btn_start.pack(side=RIGHT, padx=15, pady=10)
        
        # 状态标签
        self.status_var = StringVar(value=i18n.t("status_stopped"))
        Label(header, textvariable=self.status_var,
              font=('Microsoft YaHei UI', 10),
              bg=self.colors['primary'], fg='white').pack(side=RIGHT, padx=10)
        
        # 在线客户端数量
        self.online_count_var = StringVar(value=f"{i18n.t('online_clients')}: 0")
        Label(header, textvariable=self.online_count_var,
              font=('Microsoft YaHei UI', 10, 'bold'),
              bg=self.colors['primary'], fg='#f1c40f').pack(side=RIGHT, padx=10)
        
        # 选项卡
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # 设置样式
        style = ttk.Style()
        style.configure('TNotebook.Tab', font=('Microsoft YaHei UI', 10))
        
        # 创建选项卡
        self._create_clients_tab()
        self._create_online_tab()
        self._create_settings_tab()
        self._create_firewall_tab()
        
        # 防火墙日志读取状态
        self.firewall_log_path = r"C:\Windows\System32\LogFiles\Firewall\pfirewall.log"
        self.firewall_last_pos = 0
        
    def _create_clients_tab(self):
        """客户端管理选项卡"""
        tab = Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab, text=i18n.t("tab_clients"))
        
        # 工具栏
        toolbar = Frame(tab, bg=self.colors['white'])
        toolbar.pack(fill=X, padx=10, pady=10)
        
        Button(toolbar, text=i18n.t("btn_add_client"), bg=self.colors['success'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._add_client,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        Button(toolbar, text=i18n.t("btn_refresh"), bg=self.colors['primary'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._refresh_clients,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        Button(toolbar, text=i18n.t("btn_delete"), bg=self.colors['danger'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._delete_client,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        # 客户端列表
        list_frame = Frame(tab, bg=self.colors['white'])
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 创建 Treeview
        columns = ('client_id', 'allowed_ports')
        self.clients_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        self.clients_tree.heading('client_id', text=i18n.t("client_id"))
        self.clients_tree.heading('allowed_ports', text=i18n.t("allowed_ports"))
        
        self.clients_tree.column('client_id', width=150)
        self.clients_tree.column('allowed_ports', width=350)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=scrollbar.set)
        
        self.clients_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # 双击编辑
        self.clients_tree.bind('<Double-1>', self._edit_client)
        
    def _create_online_tab(self):
        """在线客户端选项卡"""
        tab = Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab, text=i18n.t("tab_online"))
        
        # 工具栏
        toolbar = Frame(tab, bg=self.colors['white'])
        toolbar.pack(fill=X, padx=10, pady=10)
        
        Button(toolbar, text=i18n.t("btn_refresh"), bg=self.colors['primary'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._refresh_online,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        # 在线客户端列表
        list_frame = Frame(tab, bg=self.colors['white'])
        list_frame.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        
        columns = ('client_id', 'rules_count', 'status')
        self.online_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        self.online_tree.heading('client_id', text=i18n.t("client_id"))
        self.online_tree.heading('rules_count', text=i18n.t("client_rules"))
        self.online_tree.heading('status', text=i18n.t("client_status"))
        
        self.online_tree.column('client_id', width=200)
        self.online_tree.column('rules_count', width=150)
        self.online_tree.column('status', width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.online_tree.yview)
        self.online_tree.configure(yscrollcommand=scrollbar.set)
        
        self.online_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
    def _create_settings_tab(self):
        """设置选项卡"""
        tab = Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab, text=i18n.t("tab_settings"))
        
        # 设置内容 - 使用 Canvas + Scrollbar 实现滚动
        canvas = Canvas(tab, bg=self.colors['white'], highlightthickness=0)
        scrollbar = Scrollbar(tab, orient=VERTICAL, command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.colors['white'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 绑定鼠标滚轮
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        
        content = Frame(scrollable_frame, bg=self.colors['white'])
        content.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        # 服务器端口设置
        Label(content, text=i18n.t("settings_title"), font=('Microsoft YaHei UI', 12, 'bold'),
              bg=self.colors['white'], fg=self.colors['text']).grid(row=0, column=0, columnspan=2, sticky=W, pady=(0, 15))
        
        Label(content, text=i18n.t("control_port"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=1, column=0, sticky=W, pady=5)
        self.control_port_var = StringVar(value="8024")
        Entry(content, textvariable=self.control_port_var, font=('Microsoft YaHei UI', 10),
              width=20).grid(row=1, column=1, sticky=W, padx=10)
        
        Label(content, text=i18n.t("global_port_range"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=2, column=0, sticky=W, pady=5)
        self.global_ports_var = StringVar()
        Entry(content, textvariable=self.global_ports_var, font=('Microsoft YaHei UI', 10),
              width=30).grid(row=2, column=1, sticky=W, padx=10)
        
        # 修改密码
        Label(content, text="", bg=self.colors['white']).grid(row=3, column=0, pady=10)
        
        Label(content, text=i18n.t("change_password"), font=('Microsoft YaHei UI', 12, 'bold'),
              bg=self.colors['white'], fg=self.colors['text']).grid(row=4, column=0, columnspan=2, sticky=W, pady=(0, 15))
        
        Label(content, text=i18n.t("current_password"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=5, column=0, sticky=W, pady=5)
        self.current_password_var = StringVar()
        Entry(content, textvariable=self.current_password_var, font=('Microsoft YaHei UI', 10),
              width=30, show='*').grid(row=5, column=1, sticky=W, padx=10)
        
        Label(content, text=i18n.t("new_password"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=6, column=0, sticky=W, pady=5)
        self.new_password_var = StringVar()
        Entry(content, textvariable=self.new_password_var, font=('Microsoft YaHei UI', 10),
              width=30, show='*').grid(row=6, column=1, sticky=W, padx=10)
        
        Label(content, text=i18n.t("confirm_password"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=7, column=0, sticky=W, pady=5)
        self.confirm_password_var = StringVar()
        Entry(content, textvariable=self.confirm_password_var, font=('Microsoft YaHei UI', 10),
              width=30, show='*').grid(row=7, column=1, sticky=W, padx=10)
        
        # IP 访问控制
        Label(content, text="", bg=self.colors['white']).grid(row=9, column=0, pady=5)
        Label(content, text=i18n.t("ip_control_title"), font=('Microsoft YaHei UI', 12, 'bold'),
              bg=self.colors['white'], fg=self.colors['text']).grid(row=10, column=0, columnspan=2, sticky=W, pady=(0, 5))
        
        # 客户端IP白名单
        Label(content, text=i18n.t("client_ip_whitelist"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=11, column=0, sticky=W, pady=5)
        self.client_ip_whitelist_var = StringVar()
        Entry(content, textvariable=self.client_ip_whitelist_var, font=('Microsoft YaHei UI', 10),
              width=40).grid(row=11, column=1, sticky=W, padx=10)
        Label(content, text=i18n.t("ip_whitelist_hint"), font=('Microsoft YaHei UI', 8),
              bg=self.colors['white'], fg='#999').grid(row=12, column=1, sticky=W, padx=10)
        
        # 客户端IP黑名单
        Label(content, text=i18n.t("client_ip_blacklist"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=13, column=0, sticky=W, pady=5)
        self.client_ip_blacklist_var = StringVar()
        Entry(content, textvariable=self.client_ip_blacklist_var, font=('Microsoft YaHei UI', 10),
              width=40).grid(row=13, column=1, sticky=W, padx=10)
        Label(content, text=i18n.t("ip_blacklist_hint"), font=('Microsoft YaHei UI', 8),
              bg=self.colors['white'], fg='#999').grid(row=14, column=1, sticky=W, padx=10)
        
        # 访客IP白名单
        Label(content, text=i18n.t("visitor_ip_whitelist"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=15, column=0, sticky=W, pady=5)
        self.visitor_ip_whitelist_var = StringVar()
        Entry(content, textvariable=self.visitor_ip_whitelist_var, font=('Microsoft YaHei UI', 10),
              width=40).grid(row=15, column=1, sticky=W, padx=10)
        Label(content, text=i18n.t("ip_whitelist_hint"), font=('Microsoft YaHei UI', 8),
              bg=self.colors['white'], fg='#999').grid(row=16, column=1, sticky=W, padx=10)
        
        # 访客IP黑名单
        Label(content, text=i18n.t("visitor_ip_blacklist"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=17, column=0, sticky=W, pady=5)
        self.visitor_ip_blacklist_var = StringVar()
        Entry(content, textvariable=self.visitor_ip_blacklist_var, font=('Microsoft YaHei UI', 10),
              width=40).grid(row=17, column=1, sticky=W, padx=10)
        Label(content, text=i18n.t("ip_blacklist_hint"), font=('Microsoft YaHei UI', 8),
              bg=self.colors['white'], fg='#999').grid(row=18, column=1, sticky=W, padx=10)
        
        # 访客拒绝跳转URL
        Label(content, text=i18n.t("visitor_redirect_url"), font=('Microsoft YaHei UI', 10),
              bg=self.colors['white']).grid(row=19, column=0, sticky=W, pady=5)
        self.visitor_redirect_url_var = StringVar()
        Entry(content, textvariable=self.visitor_redirect_url_var, font=('Microsoft YaHei UI', 10),
              width=40).grid(row=19, column=1, sticky=W, padx=10)
        Label(content, text=i18n.t("redirect_hint"), font=('Microsoft YaHei UI', 8),
              bg=self.colors['white'], fg='#999').grid(row=20, column=1, sticky=W, padx=10)
        
        # 保存按钮
        btn_frame = Frame(content, bg=self.colors['white'])
        btn_frame.grid(row=21, column=0, columnspan=2, pady=20)
        
        Button(btn_frame, text=i18n.t("btn_save_settings"), bg=self.colors['success'], fg='white',
               font=('Microsoft YaHei UI', 10, 'bold'), command=self._save_settings,
               relief=FLAT, padx=20).pack(side=LEFT, padx=10)
        
        Button(btn_frame, text=i18n.t("btn_change_password"), bg=self.colors['primary'], fg='white',
               font=('Microsoft YaHei UI', 10, 'bold'), command=self._change_password,
               relief=FLAT, padx=20).pack(side=LEFT, padx=10)
        
    def _create_firewall_tab(self):
        """防火墙日志选项卡"""
        tab = Frame(self.notebook, bg=self.colors['white'])
        self.notebook.add(tab, text=i18n.t("tab_firewall"))
        
        # 工具栏
        toolbar = Frame(tab, bg=self.colors['white'])
        toolbar.pack(fill=X, padx=10, pady=(10, 5))
        
        Button(toolbar, text=i18n.t("firewall_refresh"), bg=self.colors['primary'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._refresh_firewall_logs,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        Button(toolbar, text=i18n.t("firewall_enable"), bg=self.colors['warning'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._enable_firewall_logging,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        Button(toolbar, text=i18n.t("firewall_clear"), bg=self.colors['danger'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._clear_firewall_logs,
               relief=FLAT, padx=15).pack(side=LEFT, padx=5)
        
        # 统计信息（单独一行，在按钮下方）
        stats_frame = Frame(tab, bg=self.colors['white'])
        stats_frame.pack(fill=X, padx=10, pady=(0, 5))
        
        self.firewall_stats_var = StringVar(value=i18n.t("firewall_stats", blocked=0, allowed=0))
        Label(stats_frame, textvariable=self.firewall_stats_var,
              font=('Microsoft YaHei UI', 10),
              bg=self.colors['white'], fg=self.colors['text']).pack(side=LEFT, padx=5)
        
        # 日志显示区域 - 使用 Notebook 分开显示拦截和放行
        log_notebook = ttk.Notebook(tab)
        log_notebook.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        
        # 拦截记录选项卡
        blocked_tab = Frame(log_notebook, bg=self.colors['white'])
        log_notebook.add(blocked_tab, text=f"{i18n.t('firewall_blocked')} (0)")
        
        self.firewall_blocked_text = scrolledtext.ScrolledText(blocked_tab, font=('Consolas', 10),
                                                               wrap=WORD, state=DISABLED)
        self.firewall_blocked_text.pack(fill=BOTH, expand=True)
        self.firewall_blocked_text.tag_config('blocked', foreground='#e74c3c')
        self.firewall_blocked_text.tag_config('timestamp', foreground='#7f8c8d')
        
        # 放行记录选项卡
        allowed_tab = Frame(log_notebook, bg=self.colors['white'])
        log_notebook.add(allowed_tab, text=f"{i18n.t('firewall_allowed')} (0)")
        
        self.firewall_allowed_text = scrolledtext.ScrolledText(allowed_tab, font=('Consolas', 10),
                                                               wrap=WORD, state=DISABLED)
        self.firewall_allowed_text.pack(fill=BOTH, expand=True)
        self.firewall_allowed_text.tag_config('allowed', foreground='#27ae60')
        self.firewall_allowed_text.tag_config('timestamp', foreground='#7f8c8d')
        
        # 保存 notebook 引用，用于更新标签文字
        self.firewall_log_notebook = log_notebook
        
    def _enable_firewall_logging(self):
        """启用 Windows 防火墙日志"""
        import subprocess
        try:
            # 启用丢弃和允许连接的日志
            subprocess.run(['netsh', 'advfirewall', 'set', 'allprofiles', 'logging', 'droppedconnections', 'enable'], 
                          capture_output=True, text=True, check=True)
            subprocess.run(['netsh', 'advfirewall', 'set', 'allprofiles', 'logging', 'allowedconnections', 'enable'], 
                          capture_output=True, text=True, check=True)
            # 设置日志文件路径和大小
            subprocess.run(['netsh', 'advfirewall', 'set', 'allprofiles', 'logging', 'filename', self.firewall_log_path], 
                          capture_output=True, text=True, check=True)
            subprocess.run(['netsh', 'advfirewall', 'set', 'allprofiles', 'logging', 'maxfilesize', '32767'], 
                          capture_output=True, text=True, check=True)
            
            self.log(i18n.t("log_firewall_enabled"), 'success')
            self.log(i18n.t("log_firewall_path", path=self.firewall_log_path), 'info')
        except subprocess.CalledProcessError as e:
            self.log(i18n.t("log_firewall_enable_failed", error=str(e.stderr)), 'error')
        except Exception as e:
            self.log(i18n.t("log_firewall_enable_failed", error=str(e)), 'error')
    
    def _refresh_firewall_logs(self):
        """读取并显示防火墙日志"""
        import subprocess
        try:
            # 检查日志文件是否存在
            if not os.path.exists(self.firewall_log_path):
                self.log(i18n.t("log_firewall_file_not_found"), 'warning')
                return
            
            # 读取日志文件
            with open(self.firewall_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # 统计
            blocked_count = 0
            allowed_count = 0
            
            # 清空显示
            self.firewall_blocked_text.configure(state=NORMAL)
            self.firewall_blocked_text.delete(1.0, END)
            self.firewall_allowed_text.configure(state=NORMAL)
            self.firewall_allowed_text.delete(1.0, END)
            
            # 解析并显示日志
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) < 8:
                    continue
                
                # 解析字段: date time action protocol src-ip dst-ip src-port dst-port ...
                date_str = parts[0]
                time_str = parts[1]
                action = parts[2]
                protocol = parts[3]
                src_ip = parts[4]
                dst_ip = parts[5]
                src_port = parts[6]
                dst_port = parts[7]
                
                # 格式化显示
                timestamp = f"{date_str} {time_str}"
                log_entry = f"[{timestamp}] {protocol} {src_ip}:{src_port} -> {dst_ip}:{dst_port}\n"
                
                if action == 'DROP':
                    blocked_count += 1
                    self.firewall_blocked_text.insert(END, f"[{timestamp}] ", 'timestamp')
                    self.firewall_blocked_text.insert(END, f"[拦截] {protocol} ", 'blocked')
                    self.firewall_blocked_text.insert(END, f"{src_ip}:{src_port} -> {dst_ip}:{dst_port}\n", 'blocked')
                elif action == 'ALLOW':
                    allowed_count += 1
                    self.firewall_allowed_text.insert(END, f"[{timestamp}] ", 'timestamp')
                    self.firewall_allowed_text.insert(END, f"[放行] {protocol} ", 'allowed')
                    self.firewall_allowed_text.insert(END, f"{src_ip}:{src_port} -> {dst_ip}:{dst_port}\n", 'allowed')
            
            self.firewall_blocked_text.configure(state=DISABLED)
            self.firewall_allowed_text.configure(state=DISABLED)
            
            # 自动聚焦到最后一行最新记录
            self.firewall_blocked_text.see(END)
            self.firewall_allowed_text.see(END)
            
            # 更新统计
            self.firewall_stats_var.set(i18n.t("firewall_stats", blocked=blocked_count, allowed=allowed_count))
            
            # 更新选项卡标题显示数量
            self.firewall_log_notebook.tab(0, text=f"{i18n.t('firewall_blocked')} ({blocked_count})")
            self.firewall_log_notebook.tab(1, text=f"{i18n.t('firewall_allowed')} ({allowed_count})")
            
        except Exception as e:
            self.log(i18n.t("log_firewall_read_failed", error=str(e)), 'error')
    
    def _clear_firewall_logs(self):
        """清空防火墙日志显示"""
        self.firewall_blocked_text.configure(state=NORMAL)
        self.firewall_blocked_text.delete(1.0, END)
        self.firewall_blocked_text.configure(state=DISABLED)
        
        self.firewall_allowed_text.configure(state=NORMAL)
        self.firewall_allowed_text.delete(1.0, END)
        self.firewall_allowed_text.configure(state=DISABLED)
        
        # 重置选项卡标题
        self.firewall_log_notebook.tab(0, text=f"{i18n.t('firewall_blocked')} (0)")
        self.firewall_log_notebook.tab(1, text=f"{i18n.t('firewall_allowed')} (0)")
        
        # 重置统计
        self.firewall_stats_var.set(i18n.t("firewall_stats", blocked=0, allowed=0))
        
    def _toggle_language(self):
        """切换语言"""
        new_lang = "en" if i18n.get_lang() == "zh" else "zh"
        i18n.set_lang(new_lang)
        
        # 保存语言配置
        lang_config_path = os.path.join(BASE_DIR, "lang_config.json")
        with open(lang_config_path, 'w', encoding='utf-8') as f:
            json.dump({"lang": new_lang}, f, ensure_ascii=False, indent=2)
        
        # 重建界面
        self._rebuild_ui()
        
    def _rebuild_ui(self):
        """重建界面（语言切换后）"""
        # 保存当前状态
        was_running = self.server_running
        
        # 1. 保存日志内容
        saved_logs = ""
        if hasattr(self, 'log_text'):
            self.log_text.configure(state=NORMAL)
            saved_logs = self.log_text.get("1.0", END)
            self.log_text.configure(state=DISABLED)
        
        # 清空界面
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 更新窗口标题
        self.root.title(i18n.t("server_title"))
        
        # 重新创建界面
        self._create_widgets()
        
        # 恢复状态
        if was_running:
            self.btn_start.configure(text=i18n.t("btn_stop"), bg='#e74c3c')
            self.status_var.set(i18n.t("status_running"))
        
        # 刷新数据
        self._load_data()
        
        # 2. 恢复日志内容
        if hasattr(self, 'log_text') and saved_logs:
            self.log_text.configure(state=NORMAL)
            self.log_text.insert("1.0", saved_logs)
            self.log_text.see(END) # 滚动到底部
            self.log_text.configure(state=DISABLED)
            
        # 3. 刷新防火墙日志（因为读取的是系统文件，刷新能保证最新）
        if hasattr(self, '_refresh_firewall_logs'):
            self._refresh_firewall_logs()
        
    def _create_right_panel(self, parent):
        # 标题栏
        header = Frame(parent, bg=self.colors['sidebar'], height=50)
        header.pack(fill=X)
        header.pack_propagate(False)
        
        # 保存日志标题标签引用
        self.log_header_label = Label(header, text=i18n.t("tab_logs"), 
              font=('Microsoft YaHei UI', 14, 'bold'),
              bg=self.colors['sidebar'], fg='white')
        self.log_header_label.pack(side=LEFT, padx=15, pady=10)
        
        # 语言切换按钮
        lang_btn = Button(header, text=i18n.t("switch_lang"), bg='#1abc9c', fg='white',
               font=('Microsoft YaHei UI', 10), command=self._toggle_language,
               relief=FLAT, padx=15)
        lang_btn.pack(side=RIGHT, padx=15, pady=10)
        
        Button(header, text=i18n.t("btn_clear_log"), bg=self.colors['warning'], fg='white',
               font=('Microsoft YaHei UI', 10), command=self._clear_logs,
               relief=FLAT, padx=15).pack(side=RIGHT, padx=5, pady=10)
        
        # 日志显示区域
        log_frame = Frame(parent, bg=self.colors['white'])
        log_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas', 10),
                                                  wrap=WORD, state=DISABLED)
        self.log_text.pack(fill=BOTH, expand=True)
        
        # 配置日志标签颜色
        self.log_text.tag_config('info', foreground='#2c3e50')
        self.log_text.tag_config('success', foreground='#27ae60')
        self.log_text.tag_config('error', foreground='#e74c3c')
        self.log_text.tag_config('warning', foreground='#f39c12')
        self.log_text.tag_config('timestamp', foreground='#7f8c8d')
        
    def log(self, message, tag='info'):
        """添加日志（线程安全）"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        def _update():
            self.log_text.configure(state=NORMAL)
            self.log_text.insert(END, f"[{timestamp}] ", 'timestamp')
            self.log_text.insert(END, f"{message}\n", tag)
            self.log_text.see(END)
            self.log_text.configure(state=DISABLED)
        self.root.after(0, _update)
        
    def _clear_logs(self):
        """清空日志"""
        self.log_text.configure(state=NORMAL)
        self.log_text.delete(1.0, END)
        self.log_text.configure(state=DISABLED)
        
    def _load_data(self):
        """加载配置数据"""
        self.global_ports_var.set(config.get('global_allowed_ports', '1000-20000'))
        # 加载 IP 访问控制配置
        self.client_ip_whitelist_var.set(config.get('client_ip_whitelist', ''))
        self.client_ip_blacklist_var.set(config.get('client_ip_blacklist', ''))
        self.visitor_ip_whitelist_var.set(config.get('visitor_ip_whitelist', ''))
        self.visitor_ip_blacklist_var.set(config.get('visitor_ip_blacklist', ''))
        self.visitor_redirect_url_var.set(config.get('visitor_redirect_url', ''))
        self._refresh_clients()
        self.log(i18n.t("log_config_loaded"))
        
    def _refresh_clients(self):
        """刷新客户端列表"""
        # 清空列表
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
            
        # 加载数据
        clients = load_allowed_clients()
        for client_id, info in clients.items():
            allowed_ports = info.get('allowed_ports', '') or config.get('global_allowed_ports', '')
            self.clients_tree.insert('', END, values=(client_id, allowed_ports))
            
        self.log(i18n.t("log_clients_refreshed", count=len(clients)))
        
    def _refresh_online(self):
        """刷新在线客户端列表"""
        # 清空列表
        for item in self.online_tree.get_children():
            self.online_tree.delete(item)
            
        # 添加在线客户端（只显示仍然连接的）
        count = 0
        for client_id, handler in list(online_clients.items()):
            if handler.connected:
                rules_count = len(handler.rules)
                self.online_tree.insert('', END, values=(client_id, rules_count, i18n.t("status_online")))
                count += 1
                
        # 更新在线数量
        self.online_count_var.set(i18n.t("online_count", count=count))
        
    def _auto_refresh(self):
        """定时自动刷新在线客户端和防火墙日志"""
        self._refresh_online()
        # 每 30 秒刷新一次防火墙日志
        if not hasattr(self, '_firewall_refresh_counter'):
            self._firewall_refresh_counter = 0
        self._firewall_refresh_counter += 1
        if self._firewall_refresh_counter >= 10:  # 3秒 * 10 = 30秒
            self._firewall_refresh_counter = 0
            self._refresh_firewall_logs()
        self.root.after(3000, self._auto_refresh)  # 每 3 秒刷新一次
        
    def _add_client(self):
        """添加客户端对话框"""
        dialog = Toplevel(self.root)
        dialog.title(i18n.t("add_client_title"))
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 400) // 2
        y = (dialog.winfo_screenheight() - 300) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = Frame(dialog, padx=20, pady=20)
        content.pack(fill=BOTH, expand=True)
        
        Label(content, text=i18n.t("client_id_label"), font=('Microsoft YaHei UI', 10)).pack(anchor=W)
        client_id_var = StringVar()
        Entry(content, textvariable=client_id_var, font=('Microsoft YaHei UI', 10)).pack(fill=X, pady=(0, 10))
        
        Label(content, text=i18n.t("token_label"), font=('Microsoft YaHei UI', 10)).pack(anchor=W)
        token_var = StringVar()
        Entry(content, textvariable=token_var, font=('Microsoft YaHei UI', 10)).pack(fill=X, pady=(0, 10))
        
        Label(content, text=i18n.t("allowed_ports_label"), font=('Microsoft YaHei UI', 10)).pack(anchor=W)
        ports_var = StringVar()
        Entry(content, textvariable=ports_var, font=('Microsoft YaHei UI', 10)).pack(fill=X, pady=(0, 10))
        
        def save():
            client_id = client_id_var.get().strip()
            token = token_var.get().strip()
            allowed_ports = ports_var.get().strip()
            
            if not client_id or not token:
                messagebox.showerror(i18n.t("login_failed"), i18n.t("login_wrong_password"))
                return
                
            clients = load_allowed_clients()
            if client_id in clients:
                messagebox.showerror(i18n.t("login_failed"), i18n.t("client_id") + " " + i18n.t("login_wrong_password"))
                return
                
            salt, token_hash = hash_secret(token)
            clients[client_id] = {
                'salt': salt,
                'token_hash': token_hash,
                'token': token,
                'allowed_ports': allowed_ports
            }
            save_allowed_clients(clients)
            
            self.log(i18n.t("log_client_added", client_id=client_id), 'success')
            self._refresh_clients()
            dialog.destroy()
            
        btn_frame = Frame(content)
        btn_frame.pack(fill=X, pady=10)
        
        Button(btn_frame, text=i18n.t("settings_save"), bg='#27ae60', fg='white',
               font=('Microsoft YaHei UI', 10), command=save).pack(side=LEFT, padx=5)
        Button(btn_frame, text=i18n.t("settings_cancel"), bg='#95a5a6', fg='white',
               font=('Microsoft YaHei UI', 10), command=dialog.destroy).pack(side=LEFT, padx=5)
        
    def _edit_client(self, event):
        """编辑客户端"""
        selected = self.clients_tree.selection()
        if not selected:
            return
            
        item = self.clients_tree.item(selected[0])
        client_id = item['values'][0]
        
        clients = load_allowed_clients()
        if client_id not in clients:
            messagebox.showerror(i18n.t("login_failed"), i18n.t("client_id") + " " + i18n.t("status_offline"))
            return
            
        client_info = clients[client_id]
        
        dialog = Toplevel(self.root)
        dialog.title(f"{i18n.t('edit_client_title')} - {client_id}")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - 400) // 2
        y = (dialog.winfo_screenheight() - 250) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = Frame(dialog, padx=20, pady=20)
        content.pack(fill=BOTH, expand=True)
        
        Label(content, text=f"{i18n.t('client_id')}: {client_id}", font=('Microsoft YaHei UI', 10, 'bold')).pack(anchor=W)
        
        Label(content, text=i18n.t("allowed_ports") + ":", font=('Microsoft YaHei UI', 10)).pack(anchor=W, pady=(10, 0))
        ports_var = StringVar(value=client_info.get('allowed_ports', ''))
        Entry(content, textvariable=ports_var, font=('Microsoft YaHei UI', 10)).pack(fill=X, pady=(0, 10))
        
        def save():
            allowed_ports = ports_var.get().strip()
            clients[client_id]['allowed_ports'] = allowed_ports
            save_allowed_clients(clients)
            
            self.log(i18n.t("log_client_updated", client_id=client_id), 'success')
            self._refresh_clients()
            dialog.destroy()
            
        btn_frame = Frame(content)
        btn_frame.pack(fill=X, pady=10)
        
        Button(btn_frame, text=i18n.t("settings_save"), bg='#27ae60', fg='white',
               font=('Microsoft YaHei UI', 10), command=save).pack(side=LEFT, padx=5)
        Button(btn_frame, text=i18n.t("settings_cancel"), bg='#95a5a6', fg='white',
               font=('Microsoft YaHei UI', 10), command=dialog.destroy).pack(side=LEFT, padx=5)
        
    def _delete_client(self):
        """删除客户端"""
        selected = self.clients_tree.selection()
        if not selected:
            messagebox.showwarning(i18n.t("login_failed"), i18n.t("rules_no_selection"))
            return
            
        item = self.clients_tree.item(selected[0])
        client_id = item['values'][0]
        
        if messagebox.askyesno(i18n.t("confirm_title"), i18n.t("confirm_delete_client", client_id=client_id)):
            clients = load_allowed_clients()
            if client_id in clients:
                del clients[client_id]
                save_allowed_clients(clients)
                self.log(i18n.t("log_client_deleted", client_id=client_id), 'warning')
                self._refresh_clients()
                
    def _save_settings(self):
        """保存设置"""
        config['global_allowed_ports'] = self.global_ports_var.get().strip()
        # 保存 IP 访问控制配置
        config['client_ip_whitelist'] = self.client_ip_whitelist_var.get().strip()
        config['client_ip_blacklist'] = self.client_ip_blacklist_var.get().strip()
        config['visitor_ip_whitelist'] = self.visitor_ip_whitelist_var.get().strip()
        config['visitor_ip_blacklist'] = self.visitor_ip_blacklist_var.get().strip()
        config['visitor_redirect_url'] = self.visitor_redirect_url_var.get().strip()
        save_config(config)
        self.log(i18n.t("log_settings_saved"), 'success')
        self.log(i18n.t("log_ip_settings_saved"), 'success')
        messagebox.showinfo(i18n.t("status_running"), i18n.t("settings_saved"))
        
    def _change_password(self):
        """修改密码"""
        current_password = self.current_password_var.get()
        new_password = self.new_password_var.get()
        confirm_password = self.confirm_password_var.get()
        
        if not current_password:
            messagebox.showerror(i18n.t("login_failed"), i18n.t("current_password"))
            return
            
        if not verify_secret(current_password, config.get('salt', ''), config.get('password_hash', '')):
            messagebox.showerror(i18n.t("login_failed"), i18n.t("password_wrong"))
            return
            
        if not new_password:
            messagebox.showerror(i18n.t("login_failed"), i18n.t("new_password"))
            return
            
        if new_password != confirm_password:
            messagebox.showerror(i18n.t("login_failed"), i18n.t("password_mismatch"))
            return
            
        salt, pwd_hash = hash_secret(new_password)
        config['salt'] = salt
        config['password_hash'] = pwd_hash
        save_config(config)
        
        self.current_password_var.set('')
        self.new_password_var.set('')
        self.confirm_password_var.set('')
        
        self.log(i18n.t("log_password_changed"), 'success')
        messagebox.showinfo(i18n.t("status_running"), i18n.t("password_changed"))
        
    def _toggle_server(self):
        """切换服务器状态"""
        if not self.server_running:
            self._start_server()
        else:
            self._stop_server()
            
    def _start_server(self):
        """启动服务器"""
        try:
            port = int(self.control_port_var.get())
        except ValueError:
            messagebox.showerror(i18n.t("login_failed"), i18n.t("control_port"))
            return
            
        self.server_running = True
        self.stop_event.clear()
        self.btn_start.configure(text=i18n.t("btn_stop"), bg='#e74c3c')
        self.status_var.set(i18n.t("status_running"))
        
        # 在新线程中启动服务器
        self.server_thread = threading.Thread(target=self._run_server, args=(port,), daemon=True)
        self.server_thread.start()
        
        self.log(i18n.t("log_server_started", port=port), 'success')
        
    def _stop_server(self):
        """停止服务器"""
        self.server_running = False
        self.stop_event.set()  # 发送停止信号
        self.btn_start.configure(text=i18n.t("btn_start"), bg='#27ae60')
        self.status_var.set(i18n.t("status_stopped"))
        
        # 关闭所有客户端的子服务器
        for client_id, handler in list(online_clients.items()):
            try:
                # 关闭子服务器
                for server in handler.servers:
                    try:
                        server.close()
                    except:
                        pass
                handler.servers.clear()
                
                # 关闭读取任务
                if handler.read_task:
                    handler.read_task.cancel()
                    
                # 关闭连接
                if handler.writer:
                    try:
                        handler.writer.close()
                    except:
                        pass
            except:
                pass
        
        # 关闭主服务器 socket
        if self.server:
            try:
                self.server.close()
            except:
                pass
        
        # 停止事件循环
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
            
        # 等待线程结束
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=5)
            
        # 清空在线客户端
        online_clients.clear()
        self._refresh_online()
        
        self.server = None
        self.loop = None
        
        self.log(i18n.t("log_server_stopped"), 'warning')
        
    def _force_release_port(self, port):
        """强制释放端口"""
        try:
            # 尝试绑定端口来测试是否已释放
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('0.0.0.0', port))
            test_socket.close()
        except:
            # 端口仍被占用，等待一下
            time.sleep(1)
        
    def _run_server(self, port):
        """运行服务器事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._start_control_server(port))
        except Exception as e:
            self.log(i18n.t("log_server_error", error=str(e)), 'error')
        finally:
            self.loop.close()
            
    async def _start_control_server(self, port):
        """启动控制服务器"""
        async def handle_client(reader, writer):
            try:
                # 获取客户端 IP
                peername = writer.get_extra_info('peername')
                client_ip = peername[0] if peername else 'unknown'
                
                # 读取 client_id
                raw = await reader.readline()
                if not raw:
                    writer.close()
                    return
                client_id = raw.decode('utf-8', errors='replace').strip()
                if not client_id:
                    writer.close()
                    return
                    
                # 读取 token
                raw = await reader.readline()
                token = raw.decode('utf-8', errors='replace').strip() if raw else ''
                
                # 检查客户端 IP 白名单/黑名单（每次重新加载配置）
                current_config = load_config()
                client_whitelist = current_config.get('client_ip_whitelist', '')
                client_blacklist = current_config.get('client_ip_blacklist', '')
                if not is_ip_allowed(client_ip, client_whitelist, client_blacklist):
                    writer.write(b'DENIED\n')
                    await writer.drain()
                    writer.close()
                    self.log(i18n.t("log_client_ip_denied", client_id=client_id, ip=client_ip), 'warning')
                    return
                
                # 验证客户端
                clients = load_allowed_clients()
                client_info = clients.get(client_id)
                
                if not client_info:
                    writer.write(b'DENIED\n')
                    await writer.drain()
                    writer.close()
                    self.log(i18n.t("log_unknown_client", client_id=client_id), 'error')
                    return
                    
                if not verify_secret(token, client_info['salt'], client_info['token_hash']):
                    writer.write(b'DENIED\n')
                    await writer.drain()
                    writer.close()
                    self.log(i18n.t("log_token_error", client_id=client_id), 'error')
                    return
                    
                writer.write(b'OK\n')
                await writer.drain()
                
                # 开启 TCP Keepalive，防止云平台 NAT 网关超时断开
                sock = writer.get_extra_info('socket')
                if sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 15)
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)
                
                # 如果同一客户端已在线，拒绝新连接（独占模式）
                old_handler = online_clients.get(client_id)
                if old_handler:
                    writer.write(b'DENIED\n')
                    await writer.drain()
                    writer.close()
                    self.log(i18n.t("log_client_already_online", client_id=client_id), 'warning')
                    return
                
                # 创建处理器
                handler = ClientHandler(reader, writer, client_id, 
                                       log_callback=self.log,
                                       refresh_callback=lambda: self.root.after(0, self._refresh_online))
                online_clients[client_id] = handler
                
                # 先读取同步规则（在启动 _read_loop 之前）
                initial_buffer = b''
                data = await reader.read(65536)
                if data:
                    initial_buffer = data
                    # 处理所有数据包
                    while initial_buffer:
                        stream_id, packet_data, remaining = decode_packet(initial_buffer)
                        if stream_id is None:
                            break
                        initial_buffer = remaining
                        if stream_id == 0 and packet_data:
                            try:
                                msg = json.loads(packet_data.decode())
                                if msg.get('action') == 'sync':
                                    rules = msg.get('rules', [])
                                    allowed_ports = get_client_allowed_ports(client_id)
                                    for rule in rules:
                                        if is_port_allowed(rule['public_port'], allowed_ports):
                                            await handler.add_rule(rule)
                                        else:
                                            self.log(i18n.t("log_port_denied", port=rule['public_port']), 'warning')
                            except Exception as e:
                                self.log(i18n.t("log_parse_rule_error", error=str(e)), 'error')
                
                # 启动读取循环（在读取同步规则之后）
                await handler.start()
                
                # 等待读取任务完成（保持连接），参照原始 server.py
                if handler.read_task:
                    await handler.read_task
                
            except Exception as e:
                self.log(i18n.t("log_handle_client_error", error=str(e)), 'error')
            finally:
                # 客户端断开时，从在线列表中移除，允许后续重连
                if client_id in online_clients and online_clients[client_id] is handler:
                    del online_clients[client_id]
                    self.log(i18n.t("log_client_offline", client_id=client_id), 'warning')
                # 停止 handler，释放资源
                await handler.stop()
        
        # 创建 socket 并设置 SO_REUSEADDR
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('0.0.0.0', port))
        sock.listen(100)
        
        self.server = await asyncio.start_server(handle_client, sock=sock)
        self.log(i18n.t("log_control_port_open", port=port))
        
        async with self.server:
            await self.server.serve_forever()
            
    def run(self):
        """运行 GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        
    def _on_close(self):
        """关闭窗口"""
        if self.server_running:
            if messagebox.askyesno(i18n.t("confirm_title"), i18n.t("confirm_close_server")):
                self._stop_server()
                self.root.destroy()
        else:
            self.root.destroy()

# ---------- 主程序入口 ----------
if __name__ == '__main__':
    try:
        app = ServerGUI()
        # 检查窗口是否仍然存在（用户可能在登录时关闭了窗口）
        if app.root and app.root.winfo_exists():
            app.run()
    except Exception as e:
        # 忽略窗口关闭后的错误
        pass
