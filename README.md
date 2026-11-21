# PortPier - TCP 端口映射工具

一个基于 Python 的轻量级 TCP 端口映射/内网穿透工具，支持将本地服务暴露到公网。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()
[![GitHub Stars](https://img.shields.io/github/stars/FatFatYoung/PortPier.svg)](https://github.com/FatFatYoung/PortPier/stargazers)

## ✨ 功能特性

### 服务端
- 🖥️ 可视化管理界面（tkinter GUI）
- 👥 多客户端同时连接
- 🔐 客户端认证机制（用户名/密码）
- 📊 实时连接日志
- 🔥 防火墙日志查看
- 🛡️ IP 白名单/黑名单访问控制
- ⚙️ 灵活的端口映射规则配置
- 🌐 **中英双语支持**（一键切换）

### 客户端
- 🖥️ 可视化配置界面
- 🔄 自动重连机制
- 📝 实时连接日志
- 🔐 密码保护
- 💾 配置文件持久化
- 🌐 **中英双语支持**（一键切换）

## 📁 项目结构

```
PortPier/
├── server/                        # 服务端 (GUI 版本)
│   ├── gui_server.py             # GUI 管理界面 (推荐)
│   ├── i18n.py                   # 国际化模块
│   ├── build.bat                 # 打包脚本
│   └── legacy/                   # 旧版 Web 管理端 (仅供参考)
│       ├── server.py
│       └── common.py
├── client/                        # 客户端 (GUI 版本)
│   ├── gui_client.py             # GUI 客户端 (推荐)
│   ├── i18n.py                   # 国际化模块
│   ├── build.bat                 # 打包脚本
│   └── legacy/                   # 旧版命令行客户端 (仅供参考)
│       ├── client.py
│       └── common.py
├── docs/                          # 文档
...
```

## 🚀 快速开始

### 方式一：使用预编译 EXE（推荐）

1. 从 [Releases](https://github.com/FatFatYoung/PortPier/releases) 下载最新版本
2. 解压后双击运行 `portpier_server.exe` 或 `portpier_client.exe`
3. **无需安装 Python 环境**

### 方式二：从源码运行

#### 环境要求
- Python 3.10+
- Windows 10/11

#### 运行服务端
```bash
cd server
python gui_server.py
```

#### 运行客户端
```bash
cd client
python gui_client.py
```

## 📖 使用说明

### 服务端配置

1. **启动服务端** - 双击 `portpier_server.exe`
2. **默认账号** - admin / admin
3. **配置监听端口** - 默认 8024
4. **添加客户端** - 在「客户端管理」选项卡中操作

### 客户端配置

1. **启动客户端** - 双击 `portpier_client.exe`
2. **默认密码** - admin
3. **配置服务器** - 点击「设置」填写服务器信息
4. **添加映射规则** - 点击「规则」添加端口映射
5. **连接服务器** - 点击「连接」

### 语言切换

点击界面右上角的语言切换按钮，即可在中文和英文之间切换。语言设置会自动保存。

## 🛡️ 安全说明

- 所有密码使用 PBKDF2 算法加密存储
- 支持 IP 白名单/黑名单访问控制
- 支持 TCP Keepalive 防止连接超时
- 支持 TLS 加密（`tls_enabled`，保护口令与隧道数据）
- 客户端口令仅存 PBKDF2 哈希，历史明文加载时自动清除
- X-Forwarded-For / X-Real-Ip 仅在来源为 `trusted_proxies` 时采信，防止伪造绕过 IP 名单
- 单包长度上限 + 流队列有界，防恶意声明超大包耗尽内存

**TLS 配置（两端 config.json）：**

- 服务端：`tls_enabled: true` + `tls_certfile` / `tls_keyfile`（PEM）；缺证书时拒绝启动，绝不降级明文
- 客户端：`tls_enabled: true` + 可选 `tls_ca_file`（留空用系统 CA）；`tls_insecure_skip_verify: true` 为显式跳过校验（仍加密不认证）
- 反向代理部署：`trusted_proxies` 填代理 IP/CIDR/范围，只有这些来源的 XFF 头才可信；留空永不采信

## 📝 更新日志

### v1.2.0 (2026-05-10)
- ✨ **体验优化**: 语言切换时保留历史日志，不再清空
- ✨ **体验优化**: 自动刷新防火墙日志状态

### v1.1.0 (2026-05-08)
- 🌐 中英双语支持（完整界面国际化）
- 📝 日志消息国际化
- 🐛 修复语言切换按钮显示逻辑

### v1.0.0 (2026-05-04)
- ✨ 初始版本发布

详见 [CHANGELOG.md](CHANGELOG.md)

## 🆚 与同类工具对比

| 特性 | PortPier | frp | ngrok | natpass |
|------|----------|-----|-------|---------|
| **语言** | Python | Go | Go | Go |
| **GUI 界面** | ✅ | ❌ | ❌ | ❌ |
| **中英双语** | ✅ | ❌ | ✅ | ❌ |
| **上手难度** | ⭐ 简单 | ⭐⭐ 中等 | ⭐ 简单 | ⭐⭐⭐ 复杂 |
| **适合人群** | 新手/Windows | 开发者 | 开发者 | 运维 |
| **私有化部署** | ✅ | ✅ | ❌ | ✅ |

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

详见 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

第三方开源组件声明请参见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 📧 联系方式

- GitHub：[@FatFatYoung](https://github.com/FatFatYoung)
- 邮箱：fafafat@qq.com

---

⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
