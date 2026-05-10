"""
PortPier Client - Visual Version
TCP port mapping client with GUI interface
Supports Chinese and English languages
"""
import asyncio
import sys
import json
import os
import socket
import hashlib
import base64
import threading
import traceback
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext

# 导入国际化模块
from i18n import get_i18n, load_lang_config, save_lang_config
i18n = get_i18n()

# 全局异常捕获：防止 --windowed 模式下崩溃无提示
def global_exception_handler(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "error.log")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("=== TCP Client Crash Log ===\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
    except Exception:
        pass

sys.excepthook = global_exception_handler

# Windows 事件循环策略
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 获取程序所在目录（打包后使用 exe 所在目录）
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    # 开发环境
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 导入通用模块
from common import encode_packet, decode_packet

# ==================== 配置管理 ====================

CLIENT_CONFIG_FILE = os.path.join(BASE_DIR, 'client_config.json')
CLIENT_RULES_FILE = os.path.join(BASE_DIR, 'client_rules.json')
CLIENT_AUTH_FILE = os.path.join(BASE_DIR, 'client_auth.json')

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

def load_client_auth():
    if not os.path.exists(CLIENT_AUTH_FILE):
        salt, pwd_hash = hash_secret("admin")
        default = {"username": "admin", "salt": salt, "password_hash": pwd_hash}
        save_client_auth(default)
        return default
    with open(CLIENT_AUTH_FILE, 'r') as f:
        return json.load(f)

def save_client_auth(auth):
    with open(CLIENT_AUTH_FILE, 'w') as f:
        json.dump(auth, f, indent=2)

def load_client_config():
    if not os.path.exists(CLIENT_CONFIG_FILE):
        default = {
            "server_host": "127.0.0.1",
            "server_port": 8024,
            "client_id": "mypc",
            "token": "your_token_here"
        }
        save_client_config(default)
        return default
    with open(CLIENT_CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_client_config(config):
    with open(CLIENT_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def load_client_rules():
    if not os.path.exists(CLIENT_RULES_FILE):
        save_client_rules([])
        return []
    with open(CLIENT_RULES_FILE, 'r') as f:
        return json.load(f)

def save_client_rules(rules):
    with open(CLIENT_RULES_FILE, 'w') as f:
        json.dump(rules, f, indent=2)


# ==================== TCP 客户端 (完全按原逻辑) ====================

class Client:
    def __init__(self, config, rules, log_callback=None, reconnect_callback=None):
        self.config = config
        self.rules = rules
        self.reader = None
        self.writer = None
        self.stream_queues = {}
        self.stream_tasks = {}
        self.running = True
        self.heartbeat_interval = 15  # 保持与原版一致
        self.reconnect_interval = 15  # 重连间隔
        self.log_callback = log_callback or (lambda msg: None)
        self.reconnect_callback = reconnect_callback or (lambda status: None)
        self.connected = False
        self.user_disconnected = False  # 是否用户主动断开
        self.reconnecting = False  # 是否正在重连
        self.reconnect_task = None  # 重连任务

    def log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_callback(f"[{timestamp}] {msg}")

    async def connect(self):
        host = self.config['server_host']
        port = self.config['server_port']
        self.log(i18n.t("log_connect_server", host=host, port=port))
        try:
            # 添加连接超时（30秒）
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=30
            )
            
            # 开启 TCP Keepalive，防止云平台 NAT 网关超时断开
            sock = self.writer.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 60)   # 空闲 60 秒后开始探测
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 15)  # 每 15 秒探测一次
                sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 5)     # 连续 5 次失败后断开
            
            # 原逻辑：分两行发送 client_id 和 token
            self.writer.write(f"{self.config['client_id']}\n".encode())
            await self.writer.drain()
            self.writer.write(f"{self.config['token']}\n".encode())
            await self.writer.drain()
            
            resp = await self.reader.readline()
            resp = resp.decode().strip()
            
            if resp == 'DENIED':
                self.log(i18n.t("log_auth_denied"))
                raise Exception(i18n.t("log_auth_denied"))
            elif resp != 'OK':
                self.log(i18n.t("log_auth_unknown", resp=resp))
                raise Exception(i18n.t("log_auth_unknown", resp=resp))
            
            self.log(i18n.t("log_auth_ok"))
            self.connected = True
            
            # 原逻辑：同步规则到服务端
            await self._sync_rules()
            
            # 显示规则
            for rule in self.rules:
                pub_port = rule.get('public_port', '')
                target_host = rule.get('target_host', '')
                target_port = rule.get('target_port', '')
                self.log(i18n.t("log_sync_rule", port=pub_port, host=target_host, target_port=target_port))
            
            asyncio.create_task(self._heartbeat())
            asyncio.create_task(self._read_loop())
            return True
        except Exception as e:
            self.log(i18n.t("log_connect_error", error=str(e)))
            self.connected = False
            return False

    async def _sync_rules(self):
        msg = {"action": "sync", "rules": self.rules}
        await self._send_control(json.dumps(msg).encode())
        self.log(i18n.t("log_sync_done"))

    def _start_reconnect(self):
        """启动重连任务（如果尚未启动）"""
        if not self.reconnecting and self.running and not self.user_disconnected:
            self.reconnecting = True
            self.reconnect_callback("reconnecting")
            # 在事件循环中创建重连任务
            loop = asyncio.get_event_loop()
            self.reconnect_task = loop.create_task(self._reconnect_loop())

    async def _reconnect_loop(self):
        """重连循环：每15秒尝试重连一次（支持快速响应用户断开）"""
        try:
            while self.running and not self.user_disconnected and not self.connected:
                self.log(i18n.t("log_reconnect_wait", delay=self.reconnect_interval))
                self.reconnect_callback("reconnecting")
                
                # 分段等待，每秒检查一次用户是否主动断开
                for _ in range(self.reconnect_interval):
                    if not self.running or self.user_disconnected:
                        return
                    await asyncio.sleep(1)
                
                # 再次检查是否应该继续重连
                if not self.running or self.user_disconnected:
                    return
                
                self.log(i18n.t("log_reconnect_trying"))
                
                # 清理旧连接
                if self.writer:
                    try:
                        self.writer.close()
                        await self.writer.wait_closed()
                    except:
                        pass
                
                # 尝试重新连接
                success = await self._try_reconnect()
                
                if success:
                    self.log(i18n.t("log_reconnect_ok"))
                    self.reconnecting = False
                    self.reconnect_callback("connected")
                    # 重新启动心跳和读取循环
                    asyncio.create_task(self._heartbeat())
                    asyncio.create_task(self._read_loop())
                    return
                else:
                    self.log(i18n.t("log_reconnect_fail"))
        except asyncio.CancelledError:
            self.log(i18n.t("log_reconnect_cancelled"))
        except Exception as e:
            self.log(i18n.t("log_reconnect_error", error=str(e)))
        finally:
            self.reconnecting = False
            # 区分用户主动断开和重连失败
            if self.user_disconnected:
                self.reconnect_callback("disconnected")
            elif not self.connected:
                self.reconnect_callback("failed")

    async def _try_reconnect(self):
        """尝试单次重连（带超时，支持取消）"""
        try:
            host = self.config['server_host']
            port = self.config['server_port']
            
            # 使用 wait_for 添加超时，支持取消
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=10  # 10秒连接超时
            )
            
            # 检查是否已取消
            if self.user_disconnected:
                if self.writer:
                    self.writer.close()
                return False
            
            # 原逻辑：分两行发送 client_id 和 token
            self.writer.write(f"{self.config['client_id']}\n".encode())
            await self.writer.drain()
            self.writer.write(f"{self.config['token']}\n".encode())
            await self.writer.drain()
            
            resp = await self.reader.readline()
            resp = resp.decode().strip()
            
            if resp == 'DENIED':
                self.log(i18n.t("log_reconnect_auth_denied"))
                return False
            elif resp != 'OK':
                self.log(i18n.t("log_reconnect_auth_unknown", resp=resp))
                return False
            
            self.connected = True
            
            # 重新同步规则
            await self._sync_rules()
            
            return True
        except asyncio.TimeoutError:
            self.log(i18n.t("log_reconnect_timeout"))
            return False
        except asyncio.CancelledError:
            self.log(i18n.t("log_reconnect_cancel"))
            raise  # 重新抛出取消异常
        except Exception as e:
            self.log(i18n.t("log_reconnect_failed2", error=str(e)))
            return False

    async def add_rule(self, rule):
        self.rules.append(rule)
        save_client_rules(self.rules)
        msg = {"action": "add", "rule": rule}
        await self._send_control(json.dumps(msg).encode())
        self.log(i18n.t("log_add_rule", rule=str(rule)))

    async def remove_rule(self, public_port):
        self.rules = [r for r in self.rules if r["public_port"] != public_port]
        save_client_rules(self.rules)
        msg = {"action": "remove", "public_port": public_port}
        await self._send_control(json.dumps(msg).encode())
        self.log(i18n.t("log_del_rule", port=public_port))

    async def _send_control(self, data):
        if self.writer and not self.writer.is_closing():
            packet = encode_packet(0, data)
            self.writer.write(packet)
            await self.writer.drain()

    async def _heartbeat(self):
        """定期发送空包（ping）保持连接，并检测连接状态"""
        while self.running and self.writer and not self.writer.is_closing():
            await asyncio.sleep(self.heartbeat_interval)
            try:
                await self._send_control(b'')
                # 心跳包不显示日志，避免刷屏
            except (ConnectionResetError, BrokenPipeError):
                self.log(i18n.t("log_heartbeat_fail"))
                self.connected = False
                # 被动断开，触发重连
                if not self.user_disconnected:
                    self._start_reconnect()
                break
            except Exception as e:
                self.log(i18n.t("log_heartbeat_error", error=str(e)))
                self.connected = False
                # 被动断开，触发重连
                if not self.user_disconnected:
                    self._start_reconnect()
                break

    async def _read_loop(self):
        buffer = b''
        try:
            while self.running:
                data = await self.reader.read(65536)
                if not data:
                    self.log(i18n.t("log_server_disconnected"))
                    self.connected = False
                    # 被动断开，触发重连
                    if not self.user_disconnected:
                        self._start_reconnect()
                    break
                buffer += data
                while True:
                    stream_id, packet_data, remaining = decode_packet(buffer)
                    if stream_id is None:
                        break
                    if stream_id == 0:
                        # 控制消息，处理心跳响应
                        try:
                            if packet_data:
                                msg = json.loads(packet_data.decode())
                                action = msg.get('action')
                                if action == 'pong':
                                    pass  # 心跳响应，静默处理
                                elif action == 'rule_added':
                                    self.log(i18n.t("log_rule_confirmed", msg=f"已添加规则 {msg.get('public_port')}"))
                                elif action == 'rule_removed':
                                    self.log(i18n.t("log_rule_confirmed", msg=f"已删除规则 {msg.get('public_port')}"))
                        except:
                            pass  # 空数据包（心跳）忽略
                        buffer = remaining
                        continue
                    q = self.stream_queues.get(stream_id)
                    if q is None:
                        q = asyncio.Queue()
                        self.stream_queues[stream_id] = q
                        task = asyncio.create_task(self._handle_stream(stream_id, q))
                        self.stream_tasks[stream_id] = task
                    # 空数据包表示流结束，发送 None 通知
                    if packet_data:
                        await q.put(packet_data)
                    else:
                        await q.put(None)
                    buffer = remaining
        except (ConnectionResetError, BrokenPipeError):
            self.log(i18n.t("log_server_disconnected"))
            self.connected = False
            # 被动断开，触发重连
            if not self.user_disconnected:
                self._start_reconnect()
        except asyncio.CancelledError:
            pass  # 取消时不输出日志
        except Exception as e:
            self.log(i18n.t("log_read_error", error=str(e)))
            self.connected = False
            # 被动断开，触发重连
            if not self.user_disconnected:
                self._start_reconnect()
        finally:
            for task in self.stream_tasks.values():
                task.cancel()
            if self.writer:
                try:
                    self.writer.close()
                    await self.writer.wait_closed()
                except:
                    pass
            self.log(i18n.t("log_cleanup"))
            self.connected = False

    async def _handle_stream(self, stream_id, queue):
        try:
            addr_data = await queue.get()
            if not addr_data:
                return
            addr_line = addr_data.decode().strip()
            target_host, target_port = addr_line.split(':')
            target_port = int(target_port)
            self.log(i18n.t("log_stream_open", stream_id=stream_id, addr=f"{target_host}:{target_port}"))

            local_reader, local_writer = await asyncio.open_connection(target_host, target_port)

            async def forward_to_local():
                try:
                    while True:
                        data = await queue.get()
                        if data is None:
                            break
                        local_writer.write(data)
                        await local_writer.drain()
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    self.log(i18n.t("log_stream_error", stream_id=stream_id, error=str(e)))
                finally:
                    local_writer.close()
                    await local_writer.wait_closed()

            async def forward_to_server():
                try:
                    while True:
                        data = await local_reader.read(65536)
                        if not data:
                            break
                        packet = encode_packet(stream_id, data)
                        self.writer.write(packet)
                        await self.writer.drain()
                    self.writer.write(encode_packet(stream_id, b''))
                    await self.writer.drain()
                except asyncio.CancelledError:
                    pass
                except (ConnectionResetError, BrokenPipeError):
                    self.log(i18n.t("log_stream_error", stream_id=stream_id, error="Connection reset"))
                except Exception as e:
                    self.log(i18n.t("log_stream_error", stream_id=stream_id, error=str(e)))

            await asyncio.gather(forward_to_local(), forward_to_server())
        except Exception as e:
            self.log(i18n.t("log_stream_error", stream_id=stream_id, error=str(e)))
        finally:
            self.stream_queues.pop(stream_id, None)
            self.stream_tasks.pop(stream_id, None)
            self.log(i18n.t("log_stream_close", stream_id=stream_id))

    async def disconnect(self):
        self.user_disconnected = True  # 标记为用户主动断开
        self.running = False
        self.connected = False
        self.reconnecting = False
        
        # 取消重连任务
        if self.reconnect_task and not self.reconnect_task.done():
            self.reconnect_task.cancel()
            try:
                await self.reconnect_task
            except asyncio.CancelledError:
                pass
        
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
        self.log(i18n.t("log_user_disconnect"))


# ==================== 登录窗口 ====================

# ==================== GUI 应用程序 ====================

class ClientGUI:
    def __init__(self):
        self.root = Tk()
        
        # 加载语言配置
        lang = load_lang_config()
        i18n.set_lang(lang)
        
        self.root.title(i18n.t("window_title"))
        self.root.geometry("350x280")
        self.root.resizable(False, False)
        
        # 加载配置
        self.config = load_client_config()
        self.rules = load_client_rules()
        self.auth = load_client_auth()
        
        # 客户端实例
        self.client = None
        self.loop = None
        self.thread = None
        
        # 显示登录界面
        self._create_login_widgets()
        
    def _create_login_widgets(self):
        """创建登录界面"""
        frame = Frame(self.root, padx=20, pady=20)
        frame.pack(fill=BOTH, expand=True)
        
        Label(frame, text=i18n.t("window_title"), font=('Microsoft YaHei UI', 12, 'bold')).pack(pady=(0, 15))
        
        Label(frame, text=i18n.t("login_username"), anchor=W).pack(fill=X)
        self.login_username_var = StringVar(value=self.auth.get('username', 'admin'))
        Entry(frame, textvariable=self.login_username_var, font=('Microsoft YaHei UI', 10)).pack(fill=X, pady=(0, 5))
        
        Label(frame, text=i18n.t("login_password"), anchor=W).pack(fill=X)
        self.login_password_var = StringVar()
        self.login_password_entry = Entry(frame, textvariable=self.login_password_var, show='*', font=('Microsoft YaHei UI', 10))
        self.login_password_entry.pack(fill=X, pady=(0, 10))
        
        self.login_error_var = StringVar()
        Label(frame, textvariable=self.login_error_var, fg='red', font=('Microsoft YaHei UI', 9)).pack(pady=(0, 5))
        
        btn_frame = Frame(frame)
        btn_frame.pack(fill=X, pady=(10, 0))
        Button(btn_frame, text=i18n.t("login_button"), bg='#27ae60', fg='white', font=('Microsoft YaHei UI', 10, 'bold'), command=self._do_login).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        Button(btn_frame, text=i18n.t("settings_cancel"), bg='#95a5a6', fg='white', font=('Microsoft YaHei UI', 10, 'bold'), command=self._cancel_login).pack(side=LEFT, fill=X, expand=True)
        
        self.root.bind('<Return>', lambda e: self._do_login())
        self.login_password_entry.focus_set()
        
    def _do_login(self):
        """执行登录验证"""
        username = self.login_username_var.get()
        password = self.login_password_var.get()
        
        if not username or not password:
            self.login_error_var.set(i18n.t("login_wrong_password"))
            return
            
        if username != self.auth.get('username'):
            self.login_error_var.set(i18n.t("login_wrong_password"))
            return
            
        if not verify_secret(password, self.auth['salt'], self.auth['password_hash']):
            self.login_error_var.set(i18n.t("login_wrong_password"))
            return
            
        # 登录成功，清空登录界面
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 解绑回车键
        self.root.unbind('<Return>')
        
        # 切换到主界面
        self.root.title(i18n.t("window_title"))
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        
        self._create_ui()
        self._log_initial_messages()
        
    def _cancel_login(self):
        """取消登录，退出程序"""
        self.root.destroy()
        
    def _create_ui(self):
        """创建主界面"""
        # 顶部工具栏
        toolbar = Frame(self.root, bg='#2c3e50', height=40)
        toolbar.pack(fill=X, side=TOP)
        
        # 连接状态指示器
        self.status_var = StringVar(value=i18n.t("status_disconnected"))
        self.status_label = Label(
            toolbar, 
            textvariable=self.status_var,
            bg='#2c3e50',
            fg='#ecf0f1',
            font=('Microsoft YaHei UI', 10, 'bold')
        )
        self.status_label.pack(side=LEFT, padx=10)
        
        # 连接/断开按钮
        self.connect_btn = Button(
            toolbar,
            text=i18n.t("btn_connect"),
            bg='#27ae60',
            fg='white',
            font=('Microsoft YaHei UI', 10, 'bold'),
            relief=FLAT,
            padx=15,
            pady=5,
            command=self._toggle_connection
        )
        self.connect_btn.pack(side=LEFT, padx=5)
        
        # 设置按钮
        settings_btn = Button(
            toolbar,
            text=i18n.t("btn_settings"),
            bg='#3498db',
            fg='white',
            font=('Microsoft YaHei UI', 10),
            relief=FLAT,
            padx=15,
            pady=5,
            command=self._show_settings
        )
        settings_btn.pack(side=LEFT, padx=5)
        
        # 规则按钮
        rules_btn = Button(
            toolbar,
            text=i18n.t("btn_rules"),
            bg='#e67e22',
            fg='white',
            font=('Microsoft YaHei UI', 10),
            relief=FLAT,
            padx=15,
            pady=5,
            command=self._show_rules
        )
        rules_btn.pack(side=LEFT, padx=5)
        
        # 修改密码按钮
        password_btn = Button(
            toolbar,
            text=i18n.t("btn_password"),
            bg='#9b59b6',
            fg='white',
            font=('Microsoft YaHei UI', 10),
            relief=FLAT,
            padx=15,
            pady=5,
            command=self._change_password
        )
        password_btn.pack(side=LEFT, padx=5)
        
        # 语言切换按钮
        lang_btn = Button(
            toolbar,
            text=i18n.t("switch_lang"),
            bg='#1abc9c',
            fg='white',
            font=('Microsoft YaHei UI', 10),
            relief=FLAT,
            padx=15,
            pady=5,
            command=self._toggle_language
        )
        lang_btn.pack(side=RIGHT, padx=10)
        
        # 主内容区域 - 左右分栏
        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, side=TOP)
        
        # 左侧面板 - 配置信息
        left_frame = Frame(main_frame, bg='#ecf0f1')
        left_frame.pack(side=LEFT, fill=BOTH, expand=False, padx=5, pady=5)
        
        # 左侧标题
        left_title = Label(
            left_frame,
            text=i18n.t("config_panel_title"),
            bg='#34495e',
            fg='white',
            font=('Microsoft YaHei UI', 12, 'bold')
        )
        left_title.pack(fill=X)
        
        # 左侧内容 - 使用 Treeview
        self.config_tree = ttk.Treeview(
            left_frame,
            columns=('key', 'value'),
            show='headings',
            height=20
        )
        self.config_tree.heading('key', text='Key')
        self.config_tree.heading('value', text='Value')
        self.config_tree.column('key', width=150)
        self.config_tree.column('value', width=300)
        self.config_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 刷新配置信息
        self._refresh_config_display()
        
        # 右侧面板 - 连接日志
        right_frame = Frame(main_frame, bg='#ecf0f1')
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=5, pady=5)
        
        # 右侧标题
        right_title = Label(
            right_frame,
            text=i18n.t("log_panel_title"),
            bg='#34495e',
            fg='white',
            font=('Microsoft YaHei UI', 12, 'bold')
        )
        right_title.pack(fill=X)
        
        # 日志控制按钮
        log_controls = Frame(right_frame, bg='#ecf0f1')
        log_controls.pack(fill=X, padx=5, pady=2)
        
        clear_btn = Button(
            log_controls,
            text=i18n.t("btn_clear_log"),
            bg='#e74c3c',
            fg='white',
            font=('Microsoft YaHei UI', 9),
            relief=FLAT,
            padx=10,
            pady=3,
            command=self._clear_log
        )
        clear_btn.pack(side=LEFT, padx=2)
        
        auto_scroll_var = BooleanVar(value=True)
        auto_scroll_cb = Checkbutton(
            log_controls,
            text=i18n.t("btn_auto_scroll"),
            variable=auto_scroll_var,
            bg='#ecf0f1',
            font=('Microsoft YaHei UI', 9),
            command=lambda: setattr(self, 'auto_scroll', auto_scroll_var.get())
        )
        auto_scroll_cb.pack(side=LEFT, padx=5)
        self.auto_scroll = True
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(
            right_frame,
            bg='#1e1e1e',
            fg='#d4d4d4',
            font=('Consolas', 9),
            wrap=WORD
        )
        self.log_text.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        # 底部状态栏
        status_bar = Frame(self.root, bg='#2c3e50', height=25)
        status_bar.pack(fill=X, side=BOTTOM)
        
        self.info_var = StringVar(value=i18n.t("status_ready"))
        info_label = Label(
            status_bar,
            textvariable=self.info_var,
            bg='#2c3e50',
            fg='#bdc3c7',
            font=('Microsoft YaHei UI', 9)
        )
        info_label.pack(side=LEFT, padx=10)
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _refresh_config_display(self):
        """刷新配置信息显示"""
        for item in self.config_tree.get_children():
            self.config_tree.delete(item)
        
        # 根据语言选择配置项名称
        if i18n.get_lang() == "zh":
            configs = [
                ("服务器地址", self.config.get('server_host', '')),
                ("服务器端口", str(self.config.get('server_port', ''))),
                ("客户端 ID", self.config.get('client_id', '')),
                ("Token", self.config.get('token', '')[:10] + '...' if len(self.config.get('token', '')) > 10 else self.config.get('token', '')),
                ("连接状态", self._get_connection_status()),
                ("规则数量", str(len(self.rules))),
                ("自动重连", "已启用" if self.client and not self.client.user_disconnected else "未启用"),
            ]
        else:
            configs = [
                ("Server Address", self.config.get('server_host', '')),
                ("Server Port", str(self.config.get('server_port', ''))),
                ("Client ID", self.config.get('client_id', '')),
                ("Token", self.config.get('token', '')[:10] + '...' if len(self.config.get('token', '')) > 10 else self.config.get('token', '')),
                ("Status", self._get_connection_status()),
                ("Rules Count", str(len(self.rules))),
                ("Auto Reconnect", "Enabled" if self.client and not self.client.user_disconnected else "Disabled"),
            ]
        
        for key, value in configs:
            self.config_tree.insert('', END, values=(key, value))
        
        if self.rules:
            self.config_tree.insert('', END, values=("", ""))
            self.config_tree.insert('', END, values=(i18n.t("config_rules_title"), ""))
            for i, rule in enumerate(self.rules, 1):
                pub_port = rule.get('public_port', '')
                target_host = rule.get('target_host', '')
                target_port = rule.get('target_port', '')
                self.config_tree.insert('', END, values=(
                    f"{i18n.t('rules_local_port')} {i}",
                    f"Public:{pub_port} -> {target_host}:{target_port}"
                ))
    
    def _log_message(self, msg):
        """添加日志消息"""
        self.log_text.insert(END, msg + '\n')
        if self.auto_scroll:
            self.log_text.see(END)
    
    def _clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, END)
    
    def _toggle_connection(self):
        """切换连接状态"""
        # 检查是否已连接或正在重连
        if self.client and (self.client.connected or self.client.reconnecting):
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """连接到服务器"""
        if self.client and self.client.connected:
            messagebox.showwarning("Warning", i18n.t("status_connected"))
            return
        
        self.connect_btn.config(state=DISABLED)
        self.info_var.set(i18n.t("status_connecting"))
        
        def run_asyncio_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            self.client = Client(
                self.config,
                self.rules,
                log_callback=self._log_message,
                reconnect_callback=self._on_reconnect_status
            )
            
            async def do_connect():
                success = await self.client.connect()
                if success:
                    self.root.after(0, self._on_connected)
                else:
                    self.root.after(0, self._on_connect_failed)
                
                # 等待直到用户断开或连接结束
                while self.client.running or self.client.reconnecting:
                    await asyncio.sleep(0.1)
                    # 检查用户是否主动断开
                    if self.client.user_disconnected:
                        break
                    self.root.after(0, self._update_status)
            
            self.loop.run_until_complete(do_connect())
            self.loop.close()
            self.loop = None
            # 只有在非用户主动断开时才调用 _on_disconnected
            if self.client and not self.client.user_disconnected:
                self.root.after(0, self._on_disconnected)
        
        self.thread = threading.Thread(target=run_asyncio_loop, daemon=True)
        self.thread.start()
    
    def _disconnect(self):
        """断开连接（支持强制停止重连）"""
        # 保存引用
        client = self.client
        
        if not client:
            return
        
        # 1. 立即设置标志，阻止重连循环继续
        client.user_disconnected = True
        client.running = False
        client.connected = False
        
        # 2. 立即取消重连任务
        if client.reconnect_task and not client.reconnect_task.done():
            if self.loop and self.loop.is_running():
                self.loop.call_soon_threadsafe(client.reconnect_task.cancel)
        
        # 3. 立即关闭 writer（强制中断连接）
        if client.writer and not client.writer.is_closing():
            try:
                # 直接关闭底层 socket
                transport = client.writer.transport
                if transport:
                    if self.loop and self.loop.is_running():
                        self.loop.call_soon_threadsafe(transport.close)
            except:
                pass
        
        # 4. 立即更新 GUI 状态
        self.connect_btn.config(state=NORMAL, text="连接", bg='#27ae60')
        self.status_var.set("未连接")
        self.info_var.set("已断开")
        self.client = None
        
        # 5. 异步执行完整清理
        async def do_cleanup():
            try:
                await client.disconnect()
            except:
                pass
        
        if self.loop and self.loop.is_running():
            asyncio.run_coroutine_threadsafe(do_cleanup(), self.loop)
    
    def _on_connected(self):
        """连接成功回调"""
        self.connect_btn.config(state=NORMAL, text=i18n.t("btn_disconnect"), bg='#e74c3c')
        self.status_var.set(i18n.t("status_connected"))
        self.info_var.set(i18n.t("status_connected"))
        self._refresh_config_display()
    
    def _on_connect_failed(self):
        """连接失败回调"""
        self.connect_btn.config(state=NORMAL, text=i18n.t("btn_connect"), bg='#27ae60')
        self.status_var.set(i18n.t("status_connection_failed"))
        self.info_var.set(i18n.t("status_connection_failed"))
        self._refresh_config_display()
    
    def _on_disconnected(self):
        """断开连接回调"""
        # 不立即清除 self.client，保留引用以便取消重连
        self.connect_btn.config(state=NORMAL, text=i18n.t("btn_connect"), bg='#27ae60')
        self.status_var.set(i18n.t("status_disconnected"))
        self.info_var.set(i18n.t("status_disconnected"))
        # 延迟清除 client 引用
        if self.client and not self.client.reconnecting:
            self.client = None
        self._refresh_config_display()
    
    def _on_reconnect_status(self, status):
        """重连状态回调"""
        if status == "reconnecting":
            self.status_var.set(i18n.t("status_reconnecting"))
            self.info_var.set(i18n.t("status_reconnecting"))
            self.connect_btn.config(text=i18n.t("btn_disconnect"), bg='#e74c3c')
        elif status == "connected":
            self.status_var.set(i18n.t("status_connected"))
            self.info_var.set(i18n.t("log_reconnect_success"))
            self.connect_btn.config(text=i18n.t("btn_disconnect"), bg='#e74c3c')
            self._refresh_config_display()
        elif status == "disconnected":
            # 用户主动断开
            self.status_var.set(i18n.t("status_disconnected"))
            self.info_var.set(i18n.t("log_user_disconnect"))
            self.connect_btn.config(text=i18n.t("btn_connect"), bg='#27ae60')
            self.client = None
        elif status == "failed":
            self.status_var.set(i18n.t("status_connection_failed"))
            self.info_var.set(i18n.t("log_reconnect_failed"))
            self.connect_btn.config(text=i18n.t("btn_connect"), bg='#27ae60')
            self.client = None
    
    def _get_connection_status(self):
        """获取连接状态文本"""
        if not self.client:
            return i18n.t("status_disconnected")
        if self.client.connected:
            return i18n.t("status_connected")
        if self.client.reconnecting:
            return i18n.t("status_reconnecting")
        return i18n.t("status_disconnected")
    
    def _update_status(self):
        """更新状态"""
        if self.client:
            if self.client.reconnecting:
                self.info_var.set(f"{i18n.t('status_reconnecting')} | {i18n.t('status_streams')}: {len(self.client.stream_queues)}")
            elif self.client.connected:
                self.info_var.set(f"{i18n.t('status_connected')} | {i18n.t('status_streams')}: {len(self.client.stream_queues)}")
    
    def _show_settings(self):
        """显示设置对话框"""
        dialog = Toplevel(self.root)
        dialog.title(i18n.t("settings_title"))
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        Label(dialog, text=i18n.t("settings_server_host"), font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky=W, padx=10, pady=10)
        host_var = StringVar(value=self.config.get('server_host', ''))
        Entry(dialog, textvariable=host_var, width=30, font=('Microsoft YaHei UI', 10)).grid(row=0, column=1, padx=10, pady=10)
        
        Label(dialog, text=i18n.t("settings_server_port"), font=('Microsoft YaHei UI', 10)).grid(row=1, column=0, sticky=W, padx=10, pady=10)
        port_var = StringVar(value=str(self.config.get('server_port', '')))
        Entry(dialog, textvariable=port_var, width=30, font=('Microsoft YaHei UI', 10)).grid(row=1, column=1, padx=10, pady=10)
        
        Label(dialog, text=i18n.t("settings_client_id"), font=('Microsoft YaHei UI', 10)).grid(row=2, column=0, sticky=W, padx=10, pady=10)
        id_var = StringVar(value=self.config.get('client_id', ''))
        Entry(dialog, textvariable=id_var, width=30, font=('Microsoft YaHei UI', 10)).grid(row=2, column=1, padx=10, pady=10)
        
        Label(dialog, text=i18n.t("settings_token"), font=('Microsoft YaHei UI', 10)).grid(row=3, column=0, sticky=W, padx=10, pady=10)
        token_var = StringVar(value=self.config.get('token', ''))
        Entry(dialog, textvariable=token_var, width=30, font=('Microsoft YaHei UI', 10)).grid(row=3, column=1, padx=10, pady=10)
        
        def save():
            self.config['server_host'] = host_var.get()
            self.config['server_port'] = int(port_var.get())
            self.config['client_id'] = id_var.get()
            self.config['token'] = token_var.get()
            save_client_config(self.config)
            self._refresh_config_display()
            messagebox.showinfo("Success", i18n.t("settings_saved"))
            dialog.destroy()
        
        Button(dialog, text=i18n.t("settings_save"), bg='#27ae60', fg='white', font=('Microsoft YaHei UI', 10), command=save).grid(row=4, column=0, columnspan=2, pady=20)
    
    def _show_rules(self):
        """显示规则管理对话框"""
        dialog = Toplevel(self.root)
        dialog.title(i18n.t("rules_title"))
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        columns = ('public_port', 'target_host', 'target_port')
        rule_tree = ttk.Treeview(dialog, columns=columns, show='headings', height=10)
        rule_tree.heading('public_port', text=i18n.t("rules_local_port"))
        rule_tree.heading('target_host', text=i18n.t("rules_remote_host"))
        rule_tree.heading('target_port', text=i18n.t("rules_remote_port"))
        rule_tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        def refresh_rules():
            for item in rule_tree.get_children():
                rule_tree.delete(item)
            for rule in self.rules:
                rule_tree.insert('', END, values=(
                    rule.get('public_port', ''),
                    rule.get('target_host', ''),
                    rule.get('target_port', '')
                ))
        
        refresh_rules()
        
        form_frame = Frame(dialog)
        form_frame.pack(fill=X, padx=10, pady=5)
        
        Label(form_frame, text=i18n.t("rules_local_port") + ":").grid(row=0, column=0, sticky=W, padx=5)
        pub_port_var = StringVar()
        Entry(form_frame, textvariable=pub_port_var, width=10).grid(row=0, column=1, padx=5)
        
        Label(form_frame, text=i18n.t("rules_remote_host") + ":").grid(row=0, column=2, sticky=W, padx=5)
        target_host_var = StringVar(value="127.0.0.1")
        Entry(form_frame, textvariable=target_host_var, width=15).grid(row=0, column=3, padx=5)
        
        Label(form_frame, text=i18n.t("rules_remote_port") + ":").grid(row=0, column=4, sticky=W, padx=5)
        target_port_var = StringVar()
        Entry(form_frame, textvariable=target_port_var, width=10).grid(row=0, column=5, padx=5)
        
        def add_rule():
            try:
                rule = {
                    'public_port': int(pub_port_var.get()),
                    'target_host': target_host_var.get(),
                    'target_port': int(target_port_var.get())
                }
                self.rules.append(rule)
                save_client_rules(self.rules)
                refresh_rules()
                self._refresh_config_display()
                if self.client and self.client.connected:
                    asyncio.run_coroutine_threadsafe(
                        self.client.add_rule(rule),
                        self.loop
                    )
                pub_port_var.set('')
                target_host_var.set('127.0.0.1')
                target_port_var.set('')
            except Exception as e:
                messagebox.showerror(i18n.t("login_failed"), str(e))
        
        def delete_rule():
            selection = rule_tree.selection()
            if not selection:
                messagebox.showwarning("Warning", i18n.t("rules_no_selection"))
                return
            if messagebox.askyesno("Confirm", i18n.t("rules_confirm_delete")):
                idx = rule_tree.index(selection[0])
                if 0 <= idx < len(self.rules):
                    port = self.rules[idx].get('public_port')
                    self.rules.pop(idx)
                    save_client_rules(self.rules)
                    refresh_rules()
                    self._refresh_config_display()
                    if self.client and self.client.connected:
                        asyncio.run_coroutine_threadsafe(
                            self.client.remove_rule(port),
                            self.loop
                        )
        
        btn_frame = Frame(dialog)
        btn_frame.pack(fill=X, padx=10, pady=5)
        
        Button(btn_frame, text=i18n.t("rules_add"), bg='#27ae60', fg='white', command=add_rule).pack(side=LEFT, padx=5)
        Button(btn_frame, text=i18n.t("rules_delete"), bg='#e74c3c', fg='white', command=delete_rule).pack(side=LEFT, padx=5)
        Button(btn_frame, text=i18n.t("rules_close"), bg='#95a5a6', fg='white', command=dialog.destroy).pack(side=RIGHT, padx=5)
    
    def _change_password(self):
        """修改密码对话框"""
        dialog = Toplevel(self.root)
        dialog.title(i18n.t("password_title"))
        dialog.geometry("350x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        Label(dialog, text=i18n.t("login_username"), font=('Microsoft YaHei UI', 10)).grid(row=0, column=0, sticky=W, padx=20, pady=10)
        Label(dialog, text=self.auth.get('username', ''), font=('Microsoft YaHei UI', 10)).grid(row=0, column=1, sticky=W, padx=10, pady=10)
        
        Label(dialog, text=i18n.t("password_current"), font=('Microsoft YaHei UI', 10)).grid(row=1, column=0, sticky=W, padx=20, pady=10)
        current_pwd_var = StringVar()
        Entry(dialog, textvariable=current_pwd_var, show='*', width=20).grid(row=1, column=1, padx=10, pady=10)
        
        Label(dialog, text=i18n.t("password_new"), font=('Microsoft YaHei UI', 10)).grid(row=2, column=0, sticky=W, padx=20, pady=10)
        new_pwd_var = StringVar()
        Entry(dialog, textvariable=new_pwd_var, show='*', width=20).grid(row=2, column=1, padx=10, pady=10)
        
        Label(dialog, text=i18n.t("password_confirm"), font=('Microsoft YaHei UI', 10)).grid(row=3, column=0, sticky=W, padx=20, pady=10)
        confirm_pwd_var = StringVar()
        Entry(dialog, textvariable=confirm_pwd_var, show='*', width=20).grid(row=3, column=1, padx=10, pady=10)
        
        def save_password():
            current_pwd = current_pwd_var.get()
            new_pwd = new_pwd_var.get()
            confirm_pwd = confirm_pwd_var.get()
            
            if not verify_secret(current_pwd, self.auth['salt'], self.auth['password_hash']):
                messagebox.showerror(i18n.t("login_failed"), i18n.t("password_wrong_current"))
                return
            
            if new_pwd != confirm_pwd:
                messagebox.showerror(i18n.t("login_failed"), i18n.t("password_mismatch"))
                return
            
            if not new_pwd:
                messagebox.showerror(i18n.t("login_failed"), i18n.t("password_empty"))
                return
            
            salt, pwd_hash = hash_secret(new_pwd)
            self.auth['salt'] = salt
            self.auth['password_hash'] = pwd_hash
            save_client_auth(self.auth)
            messagebox.showinfo("Success", i18n.t("password_changed"))
            dialog.destroy()
        
        Button(dialog, text=i18n.t("settings_save"), bg='#27ae60', fg='white', font=('Microsoft YaHei UI', 10), command=save_password).grid(row=4, column=0, columnspan=2, pady=20)
    
    def _on_closing(self):
        """窗口关闭事件"""
        if self.client and self.client.connected:
            if messagebox.askyesno("Confirm", i18n.t("log_user_disconnect") + "?"):
                if self.loop and self.loop.is_running():
                    async def do_disconnect():
                        await self.client.disconnect()
                    asyncio.run_coroutine_threadsafe(do_disconnect(), self.loop)
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """运行 GUI"""
        # 启动主循环，不在此处打印日志（因为界面还没创建）
        self.root.mainloop()

    def _log_initial_messages(self):
        """登录成功后打印初始日志"""
        self._log_message("=" * 60)
        self._log_message(i18n.t("window_title"))
        self._log_message("=" * 60)
        self._log_message(f"Config: {CLIENT_CONFIG_FILE}")
        self._log_message(f"Rules: {CLIENT_RULES_FILE}")
        self._log_message(f"Auth: {CLIENT_AUTH_FILE}")
        self._log_message(f"Server: {self.config.get('server_host')}:{self.config.get('server_port')}")
        self._log_message(f"Client ID: {self.config.get('client_id')}")
        self._log_message(f"Rules: {len(self.rules)}")
        self._log_message("=" * 60)
        self._log_message(i18n.t("btn_connect") + " -> " + i18n.t("status_ready"))
        self._log_message("=" * 60)
    
    def _toggle_language(self):
        """切换语言"""
        current_lang = i18n.get_lang()
        new_lang = "en" if current_lang == "zh" else "zh"
        
        # 保存语言配置
        save_lang_config(new_lang)
        i18n.set_lang(new_lang)
        
        # 重新创建界面
        self._rebuild_ui()
    
    def _rebuild_ui(self):
        """重建界面（语言切换后）"""
        # 保存当前状态
        was_connected = self.client and self.client.connected if self.client else False
        
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
        self.root.title(i18n.t("window_title"))
        
        # 重新创建界面
        self._create_ui()
        
        # 恢复日志
        if hasattr(self, 'log_text') and saved_logs:
            self.log_text.configure(state=NORMAL)
            self.log_text.insert("1.0", saved_logs)
            self.log_text.see(END)
            self.log_text.configure(state=DISABLED)
            
        # 刷新配置显示
        self._refresh_config_display()
        
        # 如果之前已连接，更新状态
        if was_connected:
            self.status_var.set(i18n.t("status_connected"))
            self.connect_btn.config(text=i18n.t("btn_disconnect"), bg='#e74c3c')


if __name__ == '__main__':
    app = ClientGUI()
    app.run()
