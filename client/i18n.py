"""
PortPier 国际化支持模块
支持中英双语切换
"""
import os
import json

# 获取配置文件路径
def _get_config_path():
    """获取配置文件所在目录"""
    import sys
    if getattr(sys, 'frozen', False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

# 语言包
TRANSLATIONS = {
    "zh": {
        # 窗口标题
        "window_title": "PortPier 客户端",
        "login_title": "PortPier 客户端 - 登录",
        "settings_title": "服务器设置",
        "rules_title": "端口映射规则",
        "password_title": "修改密码",
        
        # 登录界面
        "login_username": "用户名:",
        "login_password": "密码:",
        "login_button": "登录",
        "login_failed": "登录失败",
        "login_wrong_password": "用户名或密码错误",
        
        # 主界面 - 左侧面板
        "config_panel_title": "配置信息",
        "config_server": "服务器地址:",
        "config_port": "服务器端口:",
        "config_client_id": "客户端 ID:",
        "config_token": "Token:",
        "config_status": "连接状态:",
        "config_rules_count": "规则数量:",
        "config_rules_title": "--- 端口映射规则 ---",
        
        # 主界面 - 右侧面板
        "log_panel_title": "连接日志",
        
        # 主界面 - 按钮
        "btn_connect": "连接",
        "btn_disconnect": "断开",
        "btn_settings": "设置",
        "btn_rules": "规则",
        "btn_password": "密码",
        "btn_clear_log": "清空日志",
        "btn_auto_scroll": "自动滚动",
        
        # 状态栏
        "status_ready": "就绪",
        "status_connecting": "正在连接...",
        "status_connected": "已连接",
        "status_disconnected": "已断开",
        "status_reconnecting": "正在重连...",
        "status_connection_failed": "连接失败",
        "status_streams": "流数量",
        
        # 设置界面
        "settings_server_host": "服务器地址:",
        "settings_server_port": "服务器端口:",
        "settings_client_id": "客户端 ID:",
        "settings_token": "Token:",
        "settings_save": "保存",
        "settings_cancel": "取消",
        "settings_saved": "配置已保存",
        
        # 规则界面
        "rules_local_port": "本地端口",
        "rules_remote_host": "远程地址",
        "rules_remote_port": "远程端口",
        "rules_add": "添加",
        "rules_edit": "编辑",
        "rules_delete": "删除",
        "rules_save": "保存",
        "rules_close": "关闭",
        "rules_saved": "规则已保存",
        "rules_confirm_delete": "确定要删除选中的规则吗？",
        "rules_no_selection": "请先选择一条规则",
        "rules_invalid_port": "端口号无效",
        "rules_invalid_input": "请填写所有字段",
        
        # 密码界面
        "password_current": "当前密码:",
        "password_new": "新密码:",
        "password_confirm": "确认新密码:",
        "password_change": "修改",
        "password_cancel": "取消",
        "password_changed": "密码修改成功",
        "password_mismatch": "两次输入的新密码不一致",
        "password_wrong_current": "当前密码错误",
        "password_empty": "密码不能为空",
        
        # 日志消息
        "log_program_start": "程序启动",
        "log_waiting": "等待连接...",
        "log_connecting": "正在连接服务器 {host}:{port}...",
        "log_connected": "已连接到服务器",
        "log_auth_success": "认证成功",
        "log_auth_failed": "认证失败",
        "log_rules_sent": "已发送 {count} 条规则",
        "log_disconnected": "连接已断开",
        "log_reconnecting": "连接断开，{delay}秒后重连...",
        "log_reconnect_attempt": "尝试重连 ({attempt}/{max})...",
        "log_reconnect_success": "重连成功",
        "log_reconnect_failed": "重连失败",
        "log_heartbeat": "心跳包发送中...",
        "log_error": "错误: {error}",
        "log_stream_open": "新连接 #{stream_id} ({addr})",
        "log_stream_close": "连接 #{stream_id} 关闭",
        "log_local_connect": "连接本地 {host}:{port}",
        "log_local_failed": "连接本地失败: {error}",
        "log_user_disconnect": "用户手动断开",
        "log_connect_server": "连接服务端 {host}:{port} ...",
        "log_auth_denied": "认证失败：服务端拒绝连接（客户端ID或Token无效）",
        "log_auth_unknown": "认证失败：服务端返回未知响应 '{resp}'",
        "log_auth_ok": "认证成功！连接成功",
        "log_sync_rule": "  规则: 公网端口 {port} -> {host}:{target_port}",
        "log_sync_done": "已同步规则到服务端",
        "log_connect_error": "连接异常: {error}",
        "log_reconnect_wait": "[重连] {delay} 秒后尝试重连...",
        "log_reconnect_trying": "[重连] 正在尝试重新连接...",
        "log_reconnect_ok": "[重连] 重新连接成功！",
        "log_reconnect_fail": "[重连] 重新连接失败，将继续重试...",
        "log_reconnect_cancelled": "[重连] 重连任务被取消",
        "log_reconnect_error": "[重连] 重连异常: {error}",
        "log_reconnect_auth_denied": "[重连] 认证失败：服务端拒绝连接",
        "log_reconnect_auth_unknown": "[重连] 认证失败：服务端返回未知响应 '{resp}'",
        "log_reconnect_timeout": "[重连] 连接超时 (10秒)",
        "log_reconnect_cancel": "[重连] 连接被取消",
        "log_reconnect_failed2": "[重连] 连接失败: {error}",
        "log_add_rule": "添加规则: {rule}",
        "log_del_rule": "删除规则: 公网端口 {port}",
        "log_heartbeat_fail": "[心跳] 发送失败，连接已断开",
        "log_heartbeat_error": "[心跳] 异常: {error}",
        "log_server_disconnected": "服务端已断开连接",
        "log_rule_confirmed": "[规则] 服务端确认: {msg}",
        "log_rule_denied": "[规则] 服务端拒绝: {msg}",
        "log_stream_data": "[流] #{stream_id} 收到 {size} 字节",
        "log_stream_end": "[流] #{stream_id} 服务端关闭",
        "log_stream_queue": "[流] #{stream_id} 队列收到 None，关闭本地连接",
        "log_local_closed": "[本地] #{stream_id} 本地连接已关闭",
        "log_stream_error": "[流] #{stream_id} 转发异常: {error}",
        "log_read_error": "[读取] 异常: {error}",
        "log_cleanup": "[清理] 资源已释放",
        "log_auto_reconnect": "[自动重连] 连接被动断开，启动重连",
        "log_settings_changed": "[设置] 服务器地址已更新，重新连接",
        
        # 语言切换
        "language": "语言",
        "lang_chinese": "中文",
        "lang_english": "English",
        "switch_lang": "English",
        
        # 服务端专用
        "server_title": "PortPier 服务端 - 可视化管理",
        "btn_start": "启动服务",
        "btn_stop": "停止服务",
        "status_stopped": "服务未启动",
        "status_running": "服务运行中",
        "online_clients": "在线客户端",
        "tab_clients": "客户端管理",
        "tab_rules": "规则管理",
        "tab_settings": "系统设置",
        "tab_firewall": "防火墙日志",
        "tab_logs": "连接日志",
        "btn_clear_log": "清空日志",
        "client_id": "客户端 ID",
        "client_ip": "客户端 IP",
        "client_status": "状态",
        "client_rules": "规则数",
        "client_action": "操作",
        "btn_kick": "踢出",
        "btn_view": "查看",
        "settings_control_port": "控制端口:",
        "settings_port_range": "端口范围:",
        "settings_save": "保存设置",
        "settings_saved": "设置已保存",
        "firewall_refresh": "刷新日志",
        "firewall_clear": "清空日志",
        "firewall_enable": "启用日志",
        "firewall_blocked": "拦截",
        "firewall_allowed": "放行",
    },
    
    "en": {
        # Window titles
        "window_title": "PortPier Client",
        "login_title": "PortPier Client - Login",
        "settings_title": "Server Settings",
        "rules_title": "Port Mapping Rules",
        "password_title": "Change Password",
        
        # Login
        "login_username": "Username:",
        "login_password": "Password:",
        "login_button": "Login",
        "login_failed": "Login Failed",
        "login_wrong_password": "Invalid username or password",
        
        # Main - Left panel
        "config_panel_title": "Configuration",
        "config_server": "Server Address:",
        "config_port": "Server Port:",
        "config_client_id": "Client ID:",
        "config_token": "Token:",
        "config_status": "Status:",
        "config_rules_count": "Rules:",
        "config_rules_title": "--- Port Mapping Rules ---",
        
        # Main - Right panel
        "log_panel_title": "Connection Log",
        
        # Main - Buttons
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "btn_settings": "Settings",
        "btn_rules": "Rules",
        "btn_password": "Password",
        "btn_clear_log": "Clear Log",
        "btn_auto_scroll": "Auto Scroll",
        
        # Status bar
        "status_ready": "Ready",
        "status_connecting": "Connecting...",
        "status_connected": "Connected",
        "status_disconnected": "Disconnected",
        "status_reconnecting": "Reconnecting...",
        "status_connection_failed": "Connection Failed",
        "status_streams": "Streams",
        
        # Settings
        "settings_server_host": "Server Address:",
        "settings_server_port": "Server Port:",
        "settings_client_id": "Client ID:",
        "settings_token": "Token:",
        "settings_save": "Save",
        "settings_cancel": "Cancel",
        "settings_saved": "Settings saved",
        
        # Rules
        "rules_local_port": "Local Port",
        "rules_remote_host": "Remote Host",
        "rules_remote_port": "Remote Port",
        "rules_add": "Add",
        "rules_edit": "Edit",
        "rules_delete": "Delete",
        "rules_save": "Save",
        "rules_close": "Close",
        "rules_saved": "Rules saved",
        "rules_confirm_delete": "Are you sure to delete the selected rule?",
        "rules_no_selection": "Please select a rule first",
        "rules_invalid_port": "Invalid port number",
        "rules_invalid_input": "Please fill in all fields",
        
        # Password
        "password_current": "Current Password:",
        "password_new": "New Password:",
        "password_confirm": "Confirm Password:",
        "password_change": "Change",
        "password_cancel": "Cancel",
        "password_changed": "Password changed successfully",
        "password_mismatch": "New passwords do not match",
        "password_wrong_current": "Current password is incorrect",
        "password_empty": "Password cannot be empty",
        
        # Log messages
        "log_program_start": "Program started",
        "log_waiting": "Waiting for connection...",
        "log_connecting": "Connecting to server {host}:{port}...",
        "log_connected": "Connected to server",
        "log_auth_success": "Authentication successful",
        "log_auth_failed": "Authentication failed",
        "log_rules_sent": "Sent {count} rules",
        "log_disconnected": "Disconnected",
        "log_reconnecting": "Disconnected, reconnecting in {delay}s...",
        "log_reconnect_attempt": "Reconnect attempt ({attempt}/{max})...",
        "log_reconnect_success": "Reconnected successfully",
        "log_reconnect_failed": "Reconnect failed",
        "log_heartbeat": "Sending heartbeat...",
        "log_error": "Error: {error}",
        "log_stream_open": "New connection #{stream_id} ({addr})",
        "log_stream_close": "Connection #{stream_id} closed",
        "log_local_connect": "Connecting to local {host}:{port}",
        "log_local_failed": "Failed to connect locally: {error}",
        "log_user_disconnect": "User disconnected",
        "log_connect_server": "Connecting to server {host}:{port}...",
        "log_auth_denied": "Auth failed: Server rejected (invalid Client ID or Token)",
        "log_auth_unknown": "Auth failed: Unknown response '{resp}'",
        "log_auth_ok": "Auth successful! Connected",
        "log_sync_rule": "  Rule: Public port {port} -> {host}:{target_port}",
        "log_sync_done": "Rules synced to server",
        "log_connect_error": "Connection error: {error}",
        "log_reconnect_wait": "[Reconnect] Reconnecting in {delay}s...",
        "log_reconnect_trying": "[Reconnect] Trying to reconnect...",
        "log_reconnect_ok": "[Reconnect] Reconnected successfully!",
        "log_reconnect_fail": "[Reconnect] Reconnect failed, will retry...",
        "log_reconnect_cancelled": "[Reconnect] Reconnect task cancelled",
        "log_reconnect_error": "[Reconnect] Error: {error}",
        "log_reconnect_auth_denied": "[Reconnect] Auth failed: Server rejected",
        "log_reconnect_auth_unknown": "[Reconnect] Auth failed: Unknown response '{resp}'",
        "log_reconnect_timeout": "[Reconnect] Connection timeout (10s)",
        "log_reconnect_cancel": "[Reconnect] Connection cancelled",
        "log_reconnect_failed2": "[Reconnect] Connection failed: {error}",
        "log_add_rule": "Add rule: {rule}",
        "log_del_rule": "Delete rule: Public port {port}",
        "log_heartbeat_fail": "[Heartbeat] Send failed, disconnected",
        "log_heartbeat_error": "[Heartbeat] Error: {error}",
        "log_server_disconnected": "Server disconnected",
        "log_rule_confirmed": "[Rule] Server confirmed: {msg}",
        "log_rule_denied": "[Rule] Server denied: {msg}",
        "log_stream_data": "[Stream] #{stream_id} received {size} bytes",
        "log_stream_end": "[Stream] #{stream_id} server closed",
        "log_stream_queue": "[Stream] #{stream_id} queue got None, closing local",
        "log_local_closed": "[Local] #{stream_id} local connection closed",
        "log_stream_error": "[Stream] #{stream_id} forward error: {error}",
        "log_read_error": "[Read] Error: {error}",
        "log_cleanup": "[Cleanup] Resources released",
        "log_auto_reconnect": "[Auto-reconnect] Passive disconnect, starting reconnect",
        "log_settings_changed": "[Settings] Server address changed, reconnecting",
        
        # Language
        "language": "Language",
        "lang_chinese": "中文",
        "lang_english": "English",
        "switch_lang": "简体中文",
        
        # Server specific
        "server_title": "PortPier Server - Visual Management",
        "btn_start": "Start Server",
        "btn_stop": "Stop Server",
        "status_stopped": "Server Stopped",
        "status_running": "Server Running",
        "online_clients": "Online Clients",
        "tab_clients": "Client Management",
        "tab_rules": "Rules Management",
        "tab_settings": "System Settings",
        "tab_firewall": "Firewall Log",
        "tab_logs": "Connection Log",
        "btn_clear_log": "Clear Log",
        "client_id": "Client ID",
        "client_ip": "Client IP",
        "client_status": "Status",
        "client_rules": "Rules",
        "client_action": "Action",
        "btn_kick": "Kick",
        "btn_view": "View",
        "settings_control_port": "Control Port:",
        "settings_port_range": "Port Range:",
        "settings_save": "Save Settings",
        "settings_saved": "Settings saved",
        "firewall_refresh": "Refresh Log",
        "firewall_clear": "Clear Log",
        "firewall_enable": "Enable Logging",
        "firewall_blocked": "Blocked",
        "firewall_allowed": "Allowed",
    }
}

class I18n:
    """国际化管理类"""
    
    def __init__(self, lang="zh"):
        self.lang = lang
        self.translations = TRANSLATIONS.get(lang, TRANSLATIONS["zh"])
    
    def t(self, key, **kwargs):
        """获取翻译文本，支持格式化参数"""
        text = self.translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except:
                return text
        return text
    
    def set_lang(self, lang):
        """切换语言"""
        if lang in TRANSLATIONS:
            self.lang = lang
            self.translations = TRANSLATIONS[lang]
            return True
        return False
    
    def get_lang(self):
        """获取当前语言"""
        return self.lang
    
    def get_available_langs(self):
        """获取可用语言列表"""
        return list(TRANSLATIONS.keys())

# 全局实例
i18n = I18n()

def get_i18n():
    """获取全局 i18n 实例"""
    return i18n

def load_lang_config():
    """加载语言配置"""
    config_file = os.path.join(_get_config_path(), 'lang_config.json')
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                lang = config.get('lang', 'zh')
                i18n.set_lang(lang)
                return lang
    except Exception as e:
        print(f"[i18n] 加载语言配置失败: {e}")
    return 'zh'

def save_lang_config(lang):
    """保存语言配置"""
    config_file = os.path.join(_get_config_path(), 'lang_config.json')
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump({'lang': lang}, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[i18n] 保存语言配置失败: {e}")
        return False
