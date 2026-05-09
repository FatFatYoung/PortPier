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

CONFIG_FILE = 'config.json'
ALLOWED_CLIENTS_FILE = 'allowed_clients.json'

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
def load_config():
    if not os.path.exists(CONFIG_FILE):
        salt, pwd_hash = hash_secret("admin")
        default = {
            "username": "admin",
            "salt": salt,
            "password_hash": pwd_hash,
            "global_allowed_ports": "1000-20000"
        }
        save_config(default)
        return default
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

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

# ---------- ClientHandler ----------
class ClientHandler:
    def __init__(self, reader, writer, client_id):
        self.reader = reader
        self.writer = writer
        self.client_id = client_id
        self.next_stream_id = 1
        self.stream_queues = {}
        self.read_task = None
        self.rules = []
        self.logger = logger.getChild(f"ClientHandler-{client_id}")

    async def start(self):
        self.read_task = asyncio.create_task(self._read_loop())
        self.logger.info(f"客户端 {self.client_id} 已连接")

    async def _read_loop(self):
        buffer = b''
        try:
            while True:
                data = await self.reader.read(4096)
                if not data:
                    break
                buffer += data
                while True:
                    stream_id, packet_data, remaining = decode_packet(buffer)
                    if stream_id is None:
                        break
                    if stream_id == 0:
                        await self._handle_control(packet_data)
                    else:
                        q = self.stream_queues.get(stream_id)
                        if q:
                            await q.put(packet_data)
                        else:
                            self.logger.warning(f"未知 stream_id {stream_id}")
                    buffer = remaining
        except (ConnectionResetError, BrokenPipeError):
            self.logger.warning(f"客户端 {self.client_id} 连接被重置")
        except Exception as e:
            self.logger.exception(f"读取循环异常: {e}")
        finally:
            await self._remove_all_proxy_ports()
            for q in self.stream_queues.values():
                await q.put(None)
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
            self.logger.info(f"客户端 {self.client_id} 断开")

    async def _handle_control(self, data):
        # 忽略空数据（客户端心跳包）
        if not data:
            return
        try:
            msg = json.loads(data.decode())
            action = msg.get("action")
            if action == "sync":
                allowed_range = get_client_allowed_ports(self.client_id)
                for rule in msg.get("rules", []):
                    if not is_port_allowed(rule["public_port"], allowed_range):
                        await self._send_error(f"端口 {rule['public_port']} 不在允许范围内")
                        return
                self.rules = msg.get("rules", [])
                await self._apply_rules()
            elif action == "add":
                rule = msg["rule"]
                allowed_range = get_client_allowed_ports(self.client_id)
                if not is_port_allowed(rule["public_port"], allowed_range):
                    await self._send_error(f"端口 {rule['public_port']} 不在允许范围内")
                    return
                self.rules.append(rule)
                await self._apply_rule(rule, add=True)
            elif action == "remove":
                public_port = msg["public_port"]
                self.rules = [r for r in self.rules if r["public_port"] != public_port]
                await self._remove_proxy_port(public_port)
        except Exception as e:
            self.logger.exception(f"处理控制消息失败: {e}")

    async def _send_error(self, error_msg):
        msg = json.dumps({"error": error_msg}).encode()
        packet = encode_packet(0, msg)
        self.writer.write(packet)
        await self.writer.drain()

    async def _apply_rules(self):
        current_ports = set(app['proxy_servers'].keys())
        needed_ports = {r["public_port"] for r in self.rules}
        for port in list(current_ports):
            if port not in needed_ports:
                await self._remove_proxy_port(port)
        for rule in self.rules:
            await self._apply_rule(rule, add=True)

    async def _apply_rule(self, rule, add=True):
        public_port = rule["public_port"]
        target_host = rule["target_host"]
        target_port = rule["target_port"]
        if add:
            if public_port not in app['proxy_servers']:
                server = await asyncio.start_server(
                    lambda r, w, cid=self.client_id, th=target_host, tp=target_port: handle_user(r, w, cid, th, tp),
                    '0.0.0.0', public_port
                )
                app['proxy_servers'][public_port] = server
                logger.info(f"代理端口 {public_port} -> 客户端 {self.client_id} -> {target_host}:{target_port}")
        else:
            await self._remove_proxy_port(public_port)

    async def _remove_proxy_port(self, public_port):
        server = app['proxy_servers'].pop(public_port, None)
        if server:
            server.close()
            await server.wait_closed()
            logger.info(f"停止代理端口 {public_port}")

    async def _remove_all_proxy_ports(self):
        for port in list(app['proxy_servers'].keys()):
            await self._remove_proxy_port(port)

    async def open_stream(self):
        stream_id = self.next_stream_id
        self.next_stream_id += 1
        q = asyncio.Queue()
        self.stream_queues[stream_id] = q
        return stream_id, q

    async def send_data(self, stream_id, data):
        packet = encode_packet(stream_id, data)
        self.writer.write(packet)
        await self.writer.drain()

    async def close_stream(self, stream_id):
        await self.send_data(stream_id, b'')
        self.stream_queues.pop(stream_id, None)

clients = {}
app = None
config = load_config()

async def handle_user(user_reader, user_writer, client_id, target_host, target_port):
    client = clients.get(client_id)
    if not client:
        user_writer.write(b'No such client\r\n')
        await user_writer.drain()
        user_writer.close()
        return
    stream_id, recv_queue = await client.open_stream()
    addr_info = f"{target_host}:{target_port}\n".encode()
    await client.send_data(stream_id, addr_info)

    async def forward_user_to_client():
        try:
            while True:
                data = await user_reader.read(8192)
                if not data:
                    break
                await client.send_data(stream_id, data)
        except:
            pass
        finally:
            await client.close_stream(stream_id)
            user_writer.close()

    async def forward_client_to_user():
        try:
            while True:
                data = await recv_queue.get()
                if data is None:
                    break
                user_writer.write(data)
                await user_writer.drain()
        except:
            pass

    await asyncio.gather(forward_user_to_client(), forward_client_to_user())

async def control_handler(reader, writer):
    try:
        client_id_line = await reader.readline()
        client_id = client_id_line.decode().strip()
        token_line = await reader.readline()
        token = token_line.decode().strip()
    except:
        writer.close()
        return
    if not client_id or not token:
        writer.write(b'NOID\n')
        await writer.drain()
        writer.close()
        return
    allowed = load_allowed_clients()
    client_info = allowed.get(client_id)
    if not client_info:
        writer.write(b'DENIED\n')
        await writer.drain()
        writer.close()
        logger.warning(f"客户端 {client_id} 未注册")
        return
    salt_b64 = client_info.get('salt')
    token_hash = client_info.get('token_hash')
    if not salt_b64 or not token_hash or not verify_secret(token, salt_b64, token_hash):
        writer.write(b'DENIED\n')
        await writer.drain()
        writer.close()
        logger.warning(f"客户端 {client_id} Token 错误")
        return
    writer.write(b'OK\n')
    await writer.drain()
    client = ClientHandler(reader, writer, client_id)
    clients[client_id] = client
    await client.start()
    await client.read_task
    clients.pop(client_id, None)

# ---------- Web 管理界面 ----------
async def admin_index(request):
    html = '''<!DOCTYPE html>
<html><head><title>服务端管理</title>
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
<h1>服务端管理</h1>
<div><a href="/api/logout">退出登录</a></div>
<h2>允许连接的客户端</h2>
<table id="clients-table">
    <tr><th>客户端ID</th><th>Token哈希</th><th>允许端口范围</th><th>操作</th></tr>
</table>
<h2>添加/修改客户端</h2>
<div>客户端ID: <input id="client_id"></div>
<div>Token: <input id="token" type="password"></div>
<div>允许端口范围 (例如 1000-20000, 80, 443): <input id="allowed_ports" style="width:300px"></div>
<button onclick="addOrUpdateClient()">添加/更新</button>
<h2>全局默认端口范围</h2>
<div>全局默认: <input id="global_allowed_ports" style="width:300px"></div>
<button onclick="updateGlobalPorts()">更新全局默认</button>
<h2>修改Web登录密码</h2>
<div>原密码: <input id="old_pwd" type="password"></div>
<div>新密码: <input id="new_pwd" type="password"></div>
<div>确认新密码: <input id="confirm_pwd" type="password"></div>
<button onclick="changePassword()">修改密码</button>
<h2>在线客户端及规则</h2>
<div id="online_clients"></div>
<script>
async function loadClients() {
    const res = await fetch('/api/allowed_clients');
    const data = await res.json();
    const tbody = document.querySelector('#clients-table');
    tbody.innerHTML = '<tr><th>客户端ID</th><th>Token哈希</th><th>允许端口范围</th><th>操作</th></tr>';
    for (const [cid, info] of Object.entries(data)) {
        const row = tbody.insertRow();
        row.insertCell().innerText = cid;
        row.insertCell().innerText = info.token_hash.substring(0,16)+'...';
        row.insertCell().innerText = info.allowed_ports || '(使用全局默认)';
        const btn = document.createElement('button');
        btn.innerText = '删除';
        btn.onclick = (function(id) { return function() { deleteClient(id); }; })(cid);
        const cell = row.insertCell();
        cell.appendChild(btn);
    }
}
async function addOrUpdateClient() {
    const client_id = document.getElementById('client_id').value;
    const token = document.getElementById('token').value;
    const allowed_ports = document.getElementById('allowed_ports').value;
    if (!client_id || !token) { alert('请填写客户端ID和Token'); return; }
    const res = await fetch('/api/allowed_clients', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({client_id, token, allowed_ports})
    });
    if (res.ok) { alert('保存成功'); loadClients(); }
    else alert('保存失败');
}
async function deleteClient(client_id) {
    if (!confirm(`确定删除客户端 ${client_id} 吗？`)) return;
    const res = await fetch(`/api/allowed_clients/${client_id}`, {method: 'DELETE'});
    if (res.ok) { alert('删除成功'); loadClients(); }
    else alert('删除失败');
}
async function loadGlobalPorts() {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    document.getElementById('global_allowed_ports').value = cfg.global_allowed_ports || '';
}
async function updateGlobalPorts() {
    const global_allowed_ports = document.getElementById('global_allowed_ports').value;
    const res = await fetch('/api/config', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({global_allowed_ports})
    });
    if (res.ok) { alert('全局默认端口范围已更新'); loadGlobalPorts(); }
    else alert('更新失败');
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
async function loadOnlineClients() {
    const res = await fetch('/api/online_clients');
    const data = await res.json();
    let html = '';
    for (const [cid, rules] of Object.entries(data)) {
        html += `<h3>客户端 ${cid}</h3><ul>`;
        for (const r of rules) html += `<li>公网端口 ${r.public_port} -> ${r.target_host}:${r.target_port}</li>`;
        html += `</ul>`;
    }
    document.getElementById('online_clients').innerHTML = html || '<p>暂无在线客户端</p>';
}
setInterval(loadOnlineClients, 3000);
loadClients();
loadGlobalPorts();
loadOnlineClients();
</script>
</body></html>'''
    return web.Response(text=html, content_type='text/html')

async def login_page(request):
    html = '''<!DOCTYPE html><html><head><title>服务端登录</title></head><body>
    <h2>服务端管理登录</h2>
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
    cfg = load_config()
    if username == cfg.get('username'):
        salt = cfg.get('salt')
        pwd_hash = cfg.get('password_hash')
        if salt and pwd_hash and verify_secret(password, salt, pwd_hash):
            response = web.HTTPFound('/')
            response.set_cookie('auth', 'logged_in', max_age=3600*24, httponly=True)
            return response
    return web.Response(text='Invalid credentials', status=401)

async def api_logout(request):
    response = web.HTTPFound('/login')
    response.del_cookie('auth')
    return response

async def api_change_password(request):
    data = await request.json()
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not old_password or not new_password:
        return web.Response(status=400, text='Missing fields')
    cfg = load_config()
    if not verify_secret(old_password, cfg['salt'], cfg['password_hash']):
        return web.Response(status=401, text='Invalid old password')
    salt, pwd_hash = hash_secret(new_password)
    cfg['salt'] = salt
    cfg['password_hash'] = pwd_hash
    save_config(cfg)
    return web.Response(status=200)

async def api_config_get(request):
    cfg = load_config()
    return web.json_response({"global_allowed_ports": cfg.get("global_allowed_ports", "")})

async def api_config_set(request):
    data = await request.json()
    global_allowed_ports = data.get('global_allowed_ports')
    cfg = load_config()
    cfg['global_allowed_ports'] = global_allowed_ports
    save_config(cfg)
    for client in clients.values():
        allowed_range = get_client_allowed_ports(client.client_id)
        new_rules = []
        for rule in client.rules:
            if is_port_allowed(rule["public_port"], allowed_range):
                new_rules.append(rule)
            else:
                await client._remove_proxy_port(rule["public_port"])
                logger.warning(f"客户端 {client.client_id} 的端口 {rule['public_port']} 不再允许，已删除")
        client.rules = new_rules
        await client._apply_rules()
    return web.Response(status=200)

async def api_allowed_clients(request):
    return web.json_response(load_allowed_clients())

async def api_add_allowed_client(request):
    data = await request.json()
    client_id = data.get('client_id')
    token = data.get('token')
    allowed_ports = data.get('allowed_ports', '')
    if not client_id or not token:
        return web.Response(status=400, text='Missing fields')
    salt, token_hash = hash_secret(token)
    allowed = load_allowed_clients()
    allowed[client_id] = {"salt": salt, "token_hash": token_hash, "allowed_ports": allowed_ports}
    save_allowed_clients(allowed)
    return web.Response(status=200)

async def api_delete_allowed_client(request):
    client_id = request.match_info['client_id']
    allowed = load_allowed_clients()
    if client_id in allowed:
        del allowed[client_id]
        save_allowed_clients(allowed)
        if client_id in clients:
            clients[client_id].writer.close()
        return web.Response(status=200)
    return web.Response(status=404)

async def api_online_clients(request):
    data = {cid: handler.rules for cid, handler in clients.items()}
    return web.json_response(data)

@web.middleware
async def auth_middleware(request, handler):
    if request.path in ('/login', '/api/login'):
        return await handler(request)
    if request.cookies.get('auth') != 'logged_in':
        if request.path.startswith('/api'):
            return web.Response(status=401, text='Unauthorized')
        else:
            return web.HTTPFound('/login')
    return await handler(request)

async def main():
    global app
    control_server = await asyncio.start_server(control_handler, '0.0.0.0', 8024)
    logger.info("控制端口 0.0.0.0:8024 已启动")
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get('/', admin_index)
    app.router.add_get('/login', login_page)
    app.router.add_post('/api/login', api_login)
    app.router.add_get('/api/logout', api_logout)
    app.router.add_post('/api/password', api_change_password)
    app.router.add_get('/api/config', api_config_get)
    app.router.add_post('/api/config', api_config_set)
    app.router.add_get('/api/allowed_clients', api_allowed_clients)
    app.router.add_post('/api/allowed_clients', api_add_allowed_client)
    app.router.add_delete('/api/allowed_clients/{client_id}', api_delete_allowed_client)
    app.router.add_get('/api/online_clients', api_online_clients)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 9000)
    await site.start()
    logger.info("服务端管理界面 http://127.0.0.1:9000 (需要登录)")
    app['proxy_servers'] = {}
    await asyncio.Future()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("服务端停止")
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("按回车键退出...")