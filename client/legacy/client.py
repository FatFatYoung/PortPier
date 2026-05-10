import asyncio
import sys
import json
import os
import hashlib
import base64
from aiohttp import web
from common import encode_packet, decode_packet, logger

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

CLIENT_CONFIG_FILE = 'client_config.json'
CLIENT_RULES_FILE = 'client_rules.json'
CLIENT_AUTH_FILE = 'client_auth.json'

# 密码哈希
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
            "server_host": "127.0.0.1",  # 默认本地测试，正式使用时修改
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

class Client:
    def __init__(self, config, rules):
        self.config = config
        self.rules = rules
        self.reader = None
        self.writer = None
        self.stream_queues = {}
        self.stream_tasks = {}
        self.running = True
        self.heartbeat_interval = 15  # 缩短到15秒，保持连接活跃
        self.logger = logger.getChild("Client")

    async def connect(self):
        host = self.config['server_host']
        port = self.config['server_port']
        self.logger.info(f"连接服务端 {host}:{port} ...")
        self.reader, self.writer = await asyncio.open_connection(host, port)
        self.writer.write(f"{self.config['client_id']}\n".encode())
        await self.writer.drain()
        self.writer.write(f"{self.config['token']}\n".encode())
        await self.writer.drain()
        resp = await self.reader.readline()
        resp = resp.decode().strip()
        if resp == 'DENIED':
            raise Exception("服务端拒绝连接：客户端ID或Token无效")
        elif resp != 'OK':
            raise Exception(f"服务端返回未知响应: {resp}")
        self.logger.info("连接成功")
        await self._sync_rules()
        asyncio.create_task(self._heartbeat())
        asyncio.create_task(self._read_loop())

    async def _sync_rules(self):
        msg = {"action": "sync", "rules": self.rules}
        await self._send_control(json.dumps(msg).encode())

    async def add_rule(self, rule):
        self.rules.append(rule)
        save_client_rules(self.rules)
        msg = {"action": "add", "rule": rule}
        await self._send_control(json.dumps(msg).encode())
        self.logger.info(f"添加规则: {rule}")

    async def remove_rule(self, public_port):
        self.rules = [r for r in self.rules if r["public_port"] != public_port]
        save_client_rules(self.rules)
        msg = {"action": "remove", "public_port": public_port}
        await self._send_control(json.dumps(msg).encode())
        self.logger.info(f"删除规则: 公网端口 {public_port}")

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
                self.logger.debug("发送心跳")
            except (ConnectionResetError, BrokenPipeError):
                self.logger.warning("心跳发送失败，连接已断开")
                break
            except Exception as e:
                self.logger.warning(f"心跳发送异常: {e}")
                break

    async def _read_loop(self):
        buffer = b''
        try:
            while self.running:
                data = await self.reader.read(4096)
                if not data:
                    self.logger.info("服务端已断开连接（读取到空数据）")
                    break
                buffer += data
                while True:
                    stream_id, packet_data, remaining = decode_packet(buffer)
                    if stream_id is None:
                        break
                    if stream_id == 0:
                        # 忽略服务端发来的控制消息（本版本不需要处理）
                        buffer = remaining
                        continue
                    q = self.stream_queues.get(stream_id)
                    if q is None:
                        q = asyncio.Queue()
                        self.stream_queues[stream_id] = q
                        task = asyncio.create_task(self._handle_stream(stream_id, q))
                        self.stream_tasks[stream_id] = task
                    await q.put(packet_data)
                    buffer = remaining
        except (ConnectionResetError, BrokenPipeError):
            self.logger.warning("服务端连接被重置")
        except asyncio.CancelledError:
            self.logger.info("读取循环被取消")
        except Exception as e:
            self.logger.exception(f"读取循环异常: {e}")
        finally:
            # 清理所有流
            for task in self.stream_tasks.values():
                task.cancel()
            if self.writer:
                try:
                    self.writer.close()
                    await self.writer.wait_closed()
                except:
                    pass
            self.logger.info("客户端连接已关闭")
            self.running = False

    async def _handle_stream(self, stream_id, queue):
        try:
            addr_data = await queue.get()
            if not addr_data:
                return
            addr_line = addr_data.decode().strip()
            target_host, target_port = addr_line.split(':')
            target_port = int(target_port)
            self.logger.info(f"新流 {stream_id} -> {target_host}:{target_port}")

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
                    self.logger.warning(f"本地转发异常: {e}")
                finally:
                    local_writer.close()

            async def forward_to_server():
                try:
                    while True:
                        data = await local_reader.read(8192)
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
                    self.logger.warning(f"流 {stream_id} 服务端转发连接被重置")
                except Exception as e:
                    self.logger.exception(f"流 {stream_id} 服务端转发异常: {e}")

            await asyncio.gather(forward_to_local(), forward_to_server())
        except Exception as e:
            self.logger.exception(f"流处理异常: {e}")
        finally:
            self.stream_queues.pop(stream_id, None)
            self.stream_tasks.pop(stream_id, None)
            self.logger.info(f"流 {stream_id} 结束")

    async def run(self):
        """主循环，自动重连"""
        while self.running:
            try:
                await self.connect()
                # 等待连接断开（_read_loop 会设置 self.running = False）
                while self.running:
                    await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"连接失败: {e}")
                if self.running:
                    self.logger.info("5秒后重连...")
                    await asyncio.sleep(5)

# ---------- 客户端 Web 界面 ----------
async def client_index(request):
    html = '''<!DOCTYPE html>
<html><head><title>客户端配置</title>
<style>
    body { font-family: Arial; margin: 20px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #ddd; padding: 8px; }
    th { background-color: #f2f2f2; }
    div { margin-bottom: 10px; }
    label { display: inline-block; width: 150px; }
    input { width: 200px; }
    button { margin-top: 10px; }
</style>
</head>
<body>
<h1>客户端配置</h1>
<div><a href="/api/logout">退出登录</a></div>
<h2>端口映射规则</h2>
<table id="rules-table"><tr><th>公网端口</th><th>内网地址</th><th>内网端口</th><th>操作</th></tr>
<h2>添加规则</h2>
<div>公网端口: <input type="number" id="pub_port"></div>
<div>内网地址: <input id="target_host" value="127.0.0.1"></div>
<div>内网端口: <input type="number" id="target_port"></div>
<button onclick="addRule()">添加</button>
<h2>服务端设置</h2>
<div>服务端地址: <input id="server_host"></div>
<div>服务端端口: <input id="server_port" type="number"></div>
<div>客户端ID: <input id="client_id"></div>
<div>Token: <input id="token" type="password"></div>
<button onclick="saveServerConfig()">保存并重连</button>
<h2>修改Web登录密码</h2>
<div>原密码: <input id="old_pwd" type="password"></div>
<div>新密码: <input id="new_pwd" type="password"></div>
<div>确认新密码: <input id="confirm_pwd" type="password"></div>
<button onclick="changePassword()">修改密码</button>
<div id="status"></div>
<script>
let currentRules = [];
async function loadRules() {
    const res = await fetch('/api/rules');
    currentRules = await res.json();
    const tbody = document.querySelector('#rules-table');
    tbody.innerHTML = '<tr><th>公网端口</th><th>内网地址</th><th>内网端口</th><th>操作</th></tr>';
    for (let r of currentRules) {
        const row = tbody.insertRow();
        row.insertCell().innerText = r.public_port;
        row.insertCell().innerText = r.target_host;
        row.insertCell().innerText = r.target_port;
        const btn = document.createElement('button');
        btn.innerText = '删除';
        btn.onclick = (function(port) { return function() { deleteRule(port); }; })(r.public_port);
        const cell = row.insertCell();
        cell.appendChild(btn);
    }
}
async function addRule() {
    const pub_port = document.getElementById('pub_port').value;
    const target_host = document.getElementById('target_host').value;
    const target_port = document.getElementById('target_port').value;
    const res = await fetch('/api/rules', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({public_port: parseInt(pub_port), target_host, target_port: parseInt(target_port)})
    });
    if (res.ok) { alert('添加成功'); loadRules(); }
    else alert('添加失败');
}
async function deleteRule(port) {
    const res = await fetch(`/api/rules/${port}`, {method: 'DELETE'});
    if (res.ok) { alert('删除成功'); loadRules(); }
    else alert('删除失败');
}
async function loadServerConfig() {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    document.getElementById('server_host').value = cfg.server_host;
    document.getElementById('server_port').value = cfg.server_port;
    document.getElementById('client_id').value = cfg.client_id;
    document.getElementById('token').value = cfg.token;
}
async function saveServerConfig() {
    const newCfg = {
        server_host: document.getElementById('server_host').value,
        server_port: parseInt(document.getElementById('server_port').value),
        client_id: document.getElementById('client_id').value,
        token: document.getElementById('token').value
    };
    const res = await fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(newCfg)
    });
    if (res.ok) {
        document.getElementById('status').innerText = '配置已保存，客户端将重连...';
        setTimeout(() => location.reload(), 1500);
    } else {
        document.getElementById('status').innerText = '保存失败';
    }
}
async function changePassword() {
    const old_pwd = document.getElementById('old_pwd').value;
    const new_pwd = document.getElementById('new_pwd').value;
    const confirm_pwd = document.getElementById('confirm_pwd').value;
    if (!old_pwd || !new_pwd) { alert('请填写原密码和新密码'); return; }
    if (new_pwd !== confirm_pwd) { alert('两次输入的新密码不一致'); return; }
    const res = await fetch('/api/password', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({old_password: old_pwd, new_password: new_pwd})
    });
    if (res.ok) {
        alert('密码修改成功，请重新登录');
        location.href = '/login';
    } else {
        alert('修改失败，原密码错误');
    }
}
loadRules();
loadServerConfig();
</script>
</body></html>'''
    return web.Response(text=html, content_type='text/html')

async def login_page(request):
    html = '''<!DOCTYPE html><html><head><title>客户端登录</title></head><body>
    <h2>客户端配置界面登录</h2>
    <form method="post" action="/api/login">
        <div>用户名: <input name="username"></div>
        <div>密码: <input type="password" name="password"></div>
        <button type="submit">登录</button>
    </form>
    </body></html>'''
    return web.Response(text=html, content_type='text/html')

async def api_login(request):
    data = await request.post()
    username = data.get('username')
    password = data.get('password')
    auth = load_client_auth()
    if username == auth.get('username'):
        salt = auth.get('salt')
        pwd_hash = auth.get('password_hash')
        if salt and pwd_hash and verify_secret(password, salt, pwd_hash):
            response = web.HTTPFound('/')
            response.set_cookie('client_auth', 'logged_in', max_age=3600*24, httponly=True)
            return response
    return web.Response(text='Invalid credentials', status=401)

async def api_logout(request):
    response = web.HTTPFound('/login')
    response.del_cookie('client_auth')
    return response

async def api_change_password(request):
    data = await request.json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not old_password or not new_password:
        return web.Response(status=400, text='Missing fields')
    auth = load_client_auth()
    if not verify_secret(old_password, auth['salt'], auth['password_hash']):
        return web.Response(status=401, text='Invalid old password')
    salt, pwd_hash = hash_secret(new_password)
    auth['salt'] = salt
    auth['password_hash'] = pwd_hash
    save_client_auth(auth)
    return web.Response(status=200)

async def get_rules(request):
    return web.json_response(load_client_rules())

async def add_rule(request):
    data = await request.json()
    rules = load_client_rules()
    for r in rules:
        if r['public_port'] == data['public_port']:
            return web.Response(status=400, text='Port exists')
    rules.append(data)
    save_client_rules(rules)
    if client_instance:
        await client_instance.add_rule(data)
    return web.Response(status=200)

async def delete_rule(request):
    port = int(request.match_info['port'])
    rules = load_client_rules()
    rules = [r for r in rules if r['public_port'] != port]
    save_client_rules(rules)
    if client_instance:
        await client_instance.remove_rule(port)
    return web.Response(status=200)

async def get_config(request):
    cfg = load_client_config()
    return web.json_response(cfg)

async def set_config(request):
    new_cfg = await request.json()
    save_client_config(new_cfg)
    if client_instance:
        client_instance.running = False
        if client_instance.writer:
            client_instance.writer.close()
    return web.Response(status=200)

@web.middleware
async def auth_middleware(request, handler):
    if request.path in ('/login', '/api/login'):
        return await handler(request)
    if request.cookies.get('client_auth') != 'logged_in':
        if request.path.startswith('/api'):
            return web.Response(status=401, text='Unauthorized')
        else:
            return web.HTTPFound('/login')
    return await handler(request)

client_instance = None

async def start_client_web():
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get('/', client_index)
    app.router.add_get('/login', login_page)
    app.router.add_post('/api/login', api_login)
    app.router.add_get('/api/logout', api_logout)
    app.router.add_post('/api/password', api_change_password)
    app.router.add_get('/api/rules', get_rules)
    app.router.add_post('/api/rules', add_rule)
    app.router.add_delete('/api/rules/{port}', delete_rule)
    app.router.add_get('/api/config', get_config)
    app.router.add_post('/api/config', set_config)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 9001)
    await site.start()
    logger.info("客户端Web配置界面 http://127.0.0.1:9001 (需要登录)")

async def client_main():
    global client_instance
    await start_client_web()
    cfg = load_client_config()
    rules = load_client_rules()
    client_instance = Client(cfg, rules)
    await client_instance.run()

if __name__ == '__main__':
    try:
        asyncio.run(client_main())
    except KeyboardInterrupt:
        logger.info("客户端退出")
    except Exception as e:
        logger.exception("客户端异常退出")
        input("按回车键退出...")