"""
PortPier 服务端国际化支持模块
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
        "window_title": "PortPier 服务端",
        "server_title": "PortPier 服务端 - 可视化管理",
        "login_title": "PortPier 服务端 - 登录",
        
        # 登录界面
        "login_username": "用户名:",
        "login_password": "密码:",
        "login_button": "登录",
        "login_cancel": "取消",
        "login_failed": "登录失败",
        "login_wrong_password": "用户名或密码错误",
        
        # 服务端控制
        "btn_start": "启动服务",
        "btn_stop": "停止服务",
        "status_stopped": "服务未启动",
        "status_running": "服务运行中",
        "online_clients": "在线客户端",
        "online_count": "在线: {count}",
        
        # 选项卡
        "tab_clients": "客户端管理",
        "tab_online": "在线客户端",
        "tab_rules": "规则管理",
        "tab_settings": "系统设置",
        "tab_firewall": "防火墙日志",
        "tab_logs": "连接日志",
        
        # 客户端管理
        "client_id": "客户端 ID",
        "client_ip": "客户端 IP",
        "client_status": "状态",
        "client_rules": "规则数",
        "client_action": "操作",
        "allowed_ports": "允许的端口范围",
        "btn_add_client": "添加客户端",
        "btn_refresh": "刷新列表",
        "btn_delete": "删除选中",
        "btn_kick": "踢出",
        "btn_view": "查看",
        
        # 添加/编辑客户端
        "add_client_title": "添加客户端",
        "edit_client_title": "编辑客户端",
        "client_id_label": "客户端 ID:",
        "token_label": "Token:",
        "allowed_ports_label": "允许的端口范围 (留空使用全局默认):",
        "settings_save": "保存",
        "settings_cancel": "取消",
        "settings_saved": "设置已保存",
        
        # 系统设置
        "settings_title": "服务器设置",
        "control_port": "控制端口:",
        "global_port_range": "全局默认端口范围:",
        "change_password": "修改密码",
        "current_password": "当前密码:",
        "new_password": "新密码:",
        "confirm_password": "确认新密码:",
        "btn_save_settings": "保存设置",
        "btn_change_password": "修改密码",
        
        # IP 访问控制
        "ip_control_title": "IP 访问控制",
        "client_ip_whitelist": "客户端IP白名单:",
        "client_ip_blacklist": "客户端IP黑名单:",
        "visitor_ip_whitelist": "访客IP白名单:",
        "visitor_ip_blacklist": "访客IP黑名单:",
        "visitor_redirect_url": "拒绝访客跳转URL:",
        "ip_whitelist_hint": "空=允许所有 | 格式: IP/CIDR/范围",
        "ip_blacklist_hint": "空=不阻止 | 格式: IP/范围",
        "redirect_hint": "被拒绝的访客将跳转到此URL",
        
        # 防火墙日志
        "firewall_refresh": "刷新日志",
        "firewall_enable": "启用防火墙日志",
        "firewall_clear": "清空显示",
        "firewall_blocked": "拦截记录",
        "firewall_allowed": "放行记录",
        "firewall_stats": "已拦截: {blocked} | 已放行: {allowed}",
        
        # 日志
        "btn_clear_log": "清空日志",
        "btn_auto_scroll": "自动滚动",
        
        # 状态
        "status_online": "在线",
        "status_offline": "离线",
        
        # 语言
        "language": "语言",
        "lang_chinese": "中文",
        "lang_english": "English",
        "switch_lang": "English",
        
        # 密码修改
        "password_changed": "密码修改成功",
        "password_mismatch": "两次输入的新密码不一致",
        "password_wrong": "当前密码错误",
        
        # 确认对话框
        "confirm_title": "确认",
        "confirm_delete_client": "确定要删除客户端 {client_id} 吗？",
        "confirm_close_server": "服务器正在运行，确定要关闭吗？",
        
        # 日志消息
        "log_config_loaded": "配置文件已加载",
        "log_clients_refreshed": "客户端列表已刷新，共 {count} 个客户端",
        "log_client_added": "客户端 {client_id} 已添加",
        "log_client_updated": "客户端 {client_id} 端口范围已更新",
        "log_client_deleted": "客户端 {client_id} 已删除",
        "log_settings_saved": "全局端口范围已更新",
        "log_ip_settings_saved": "IP 访问控制配置已更新",
        "log_password_changed": "登录密码已修改",
        "log_server_started": "服务器已启动，监听端口 {port}",
        "log_server_stopped": "服务器已停止，端口已释放",
        "log_server_error": "服务器异常: {error}",
        "log_client_ip_denied": "客户端 {client_id} IP {ip} 不在允许范围",
        "log_unknown_client": "未知客户端 {client_id}",
        "log_token_error": "客户端 {client_id} Token 错误",
        "log_client_already_online": "客户端 {client_id} 已在线，拒绝重复连接",
        "log_rule_port_denied": "端口 {port} 不在允许范围",
        "log_parse_rule_error": "解析规则失败: {error}",
        "log_handle_client_error": "处理客户端异常: {error}",
        "log_client_offline": "客户端 {client_id} 已离线",
        "log_control_port_open": "控制端口 {port} 已开启",
        "log_firewall_enabled": "防火墙日志已启用",
        "log_firewall_path": "日志路径: {path}",
        "log_firewall_enable_failed": "启用日志失败: {error}",
        "log_firewall_file_not_found": "日志文件不存在，请先启用防火墙日志",
        "log_firewall_read_failed": "读取日志失败: {error}",
        
        # ClientHandler 日志
        "log_client_connected": "客户端 {client_id} 已连接",
        "log_rule_added": "公网端口 {port} -> {host}:{target_port}",
        "log_rule_removed": "公网端口 {port}",
        "log_visitor_denied": "访客 {ip} 不在允许范围 -> 端口 {port}",
        "log_listener_started": "端口 {port} 已开启",
        "log_listener_error": "监听端口 {port} 失败: {error}",
        "log_visitor": "{ip}:{port} -> 端口 {public_port}",
        "log_http_request": "{ip} {method} {host}{path}",
        "log_client_disconnected": "客户端 {client_id} 连接断开",
        "log_heartbeat": "收到 {client_id} 心跳响应",
        "log_client_add_rule": "客户端 {client_id} 添加规则: {port}",
        "log_port_denied": "端口 {port} 不在允许范围",
        "log_client_delete_rule": "客户端 {client_id} 删除规则: {port}",
        "log_read_error": "读取异常: {error}",
        "log_cleanup": "客户端 {client_id} 资源已释放",
    },
    
    "en": {
        # Window titles
        "window_title": "PortPier Server",
        "server_title": "PortPier Server - Visual Management",
        "login_title": "PortPier Server - Login",
        
        # Login
        "login_username": "Username:",
        "login_password": "Password:",
        "login_button": "Login",
        "login_cancel": "Cancel",
        "login_failed": "Login Failed",
        "login_wrong_password": "Invalid username or password",
        
        # Server control
        "btn_start": "Start Server",
        "btn_stop": "Stop Server",
        "status_stopped": "Server Stopped",
        "status_running": "Server Running",
        "online_clients": "Online Clients",
        "online_count": "Online: {count}",
        
        # Tabs
        "tab_clients": "Client Management",
        "tab_online": "Online Clients",
        "tab_rules": "Rules Management",
        "tab_settings": "System Settings",
        "tab_firewall": "Firewall Log",
        "tab_logs": "Connection Log",
        
        # Client management
        "client_id": "Client ID",
        "client_ip": "Client IP",
        "client_status": "Status",
        "client_rules": "Rules",
        "client_action": "Action",
        "allowed_ports": "Allowed Ports",
        "btn_add_client": "Add Client",
        "btn_refresh": "Refresh",
        "btn_delete": "Delete Selected",
        "btn_kick": "Kick",
        "btn_view": "View",
        
        # Add/Edit client
        "add_client_title": "Add Client",
        "edit_client_title": "Edit Client",
        "client_id_label": "Client ID:",
        "token_label": "Token:",
        "allowed_ports_label": "Allowed Ports (leave empty for global default):",
        "settings_save": "Save",
        "settings_cancel": "Cancel",
        "settings_saved": "Settings saved",
        
        # System settings
        "settings_title": "Server Settings",
        "control_port": "Control Port:",
        "global_port_range": "Global Default Port Range:",
        "change_password": "Change Password",
        "current_password": "Current Password:",
        "new_password": "New Password:",
        "confirm_password": "Confirm Password:",
        "btn_save_settings": "Save Settings",
        "btn_change_password": "Change Password",
        
        # IP access control
        "ip_control_title": "IP Access Control",
        "client_ip_whitelist": "Client IP Whitelist:",
        "client_ip_blacklist": "Client IP Blacklist:",
        "visitor_ip_whitelist": "Visitor IP Whitelist:",
        "visitor_ip_blacklist": "Visitor IP Blacklist:",
        "visitor_redirect_url": "Denied Visitor Redirect URL:",
        "ip_whitelist_hint": "Empty=Allow All | Format: IP/CIDR/Range",
        "ip_blacklist_hint": "Empty=Block None | Format: IP/Range",
        "redirect_hint": "Denied visitors will be redirected to this URL",
        
        # Firewall log
        "firewall_refresh": "Refresh Log",
        "firewall_enable": "Enable Firewall Log",
        "firewall_clear": "Clear Display",
        "firewall_blocked": "Blocked",
        "firewall_allowed": "Allowed",
        "firewall_stats": "Blocked: {blocked} | Allowed: {allowed}",
        
        # Log
        "btn_clear_log": "Clear Log",
        "btn_auto_scroll": "Auto Scroll",
        
        # Status
        "status_online": "Online",
        "status_offline": "Offline",
        
        # Language
        "language": "Language",
        "lang_chinese": "中文",
        "lang_english": "English",
        "switch_lang": "简体中文",
        
        # Password change
        "password_changed": "Password changed successfully",
        "password_mismatch": "Passwords do not match",
        "password_wrong": "Current password is incorrect",
        
        # Confirmation dialogs
        "confirm_title": "Confirm",
        "confirm_delete_client": "Are you sure you want to delete client {client_id}?",
        "confirm_close_server": "Server is running. Are you sure you want to close?",
        
        # Log messages
        "log_config_loaded": "Config file loaded",
        "log_clients_refreshed": "Client list refreshed, {count} clients",
        "log_client_added": "Client {client_id} added",
        "log_client_updated": "Client {client_id} port range updated",
        "log_client_deleted": "Client {client_id} deleted",
        "log_settings_saved": "Global port range updated",
        "log_ip_settings_saved": "IP access control settings saved",
        "log_password_changed": "Login password changed",
        "log_server_started": "Server started, listening on port {port}",
        "log_server_stopped": "Server stopped, ports released",
        "log_server_error": "Server error: {error}",
        "log_client_ip_denied": "Client {client_id} IP {ip} not allowed",
        "log_unknown_client": "Unknown client {client_id}",
        "log_token_error": "Client {client_id} token error",
        "log_client_already_online": "Client {client_id} already online, connection rejected",
        "log_rule_port_denied": "Port {port} not in allowed range",
        "log_parse_rule_error": "Parse rule failed: {error}",
        "log_handle_client_error": "Handle client error: {error}",
        "log_client_offline": "Client {client_id} offline",
        "log_control_port_open": "Control port {port} opened",
        "log_firewall_enabled": "Firewall logging enabled",
        "log_firewall_path": "Log path: {path}",
        "log_firewall_enable_failed": "Enable logging failed: {error}",
        "log_firewall_file_not_found": "Log file not found, please enable firewall logging first",
        "log_firewall_read_failed": "Read log failed: {error}",
        
        # ClientHandler logs
        "log_client_connected": "Client {client_id} connected",
        "log_rule_added": "Public port {port} -> {host}:{target_port}",
        "log_rule_removed": "Public port {port}",
        "log_visitor_denied": "Visitor {ip} not allowed -> port {port}",
        "log_listener_started": "Port {port} opened",
        "log_listener_error": "Listen port {port} failed: {error}",
        "log_visitor": "{ip}:{port} -> port {public_port}",
        "log_http_request": "{ip} {method} {host}{path}",
        "log_client_disconnected": "Client {client_id} disconnected",
        "log_heartbeat": "Heartbeat from {client_id}",
        "log_client_add_rule": "Client {client_id} added rule: {port}",
        "log_port_denied": "Port {port} not in allowed range",
        "log_client_delete_rule": "Client {client_id} deleted rule: {port}",
        "log_read_error": "Read error: {error}",
        "log_cleanup": "Client {client_id} resources released",
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
