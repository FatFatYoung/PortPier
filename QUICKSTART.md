# PortPier 快速开始指南

## 📥 下载

从 [Releases](https://github.com/FatFatYoung/PortPier/releases) 页面下载最新版本：

- `portpier_server.exe` - 服务端程序
- `portpier_client.exe` - 客户端程序

## 🖥️ 服务端部署

### 1. 启动服务端

双击 `portpier_server.exe` 启动服务端。

### 2. 登录

- 默认用户名：`admin`
- 默认密码：`admin`

### 3. 配置服务端

在「系统设置」选项卡中：

1. **控制端口**：客户端连接的端口（默认 8024）
2. **全局默认端口范围**：允许客户端映射的端口

### 4. 配置防火墙

如果服务器有防火墙，需要开放端口：

```powershell
New-NetFirewallRule -DisplayName "PortPier" -Direction Inbound -Protocol TCP -LocalPort 8024,10000-20000 -Action Allow
```

## 💻 客户端配置

### 1. 启动客户端

双击 `portpier_client.exe` 启动客户端。

### 2. 登录

- 默认密码：`admin`

### 3. 配置服务器连接

点击「设置」按钮，填写：

- **服务器地址**：服务端的公网 IP 或域名
- **服务器端口**：8024
- **客户端 ID**：唯一标识
- **Token**：认证令牌

### 4. 添加端口映射规则

点击「规则」按钮，添加映射：

```
公网端口：80
目标地址：127.0.0.1
目标端口：80
```

### 5. 连接服务器

点击「连接」按钮，等待连接成功。

## 🌐 语言切换

点击界面右上角的语言切换按钮，即可在中文和英文之间切换。

## ❓ 常见问题

### Q: 连接失败？

- 检查服务器地址和端口是否正确
- 检查服务器防火墙是否开放端口
- 检查 Token 是否正确

### Q: 端口映射不工作？

- 检查本地服务是否正在运行
- 检查远程端口是否在允许范围内

### Q: 连接断开？

客户端会自动重连，等待即可。

## 📞 技术支持

如有问题，请提交 [Issue](https://github.com/FatFatYoung/PortPier/issues)
