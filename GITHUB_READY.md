# PortPier GitHub 发布清单

## ✅ 已准备完成

### 📁 项目结构
```
PortPier/
├── .github/workflows/build.yml
├── server/
├── client/
├── docs/
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── QUICKSTART.md
├── RELEASE.md
└── README.md
```

### 📄 文档说明
- **README.md**: 项目主页
- **QUICKSTART.md**: 快速开始指南
- **CONTRIBUTING.md**: 贡献指南
- **CHANGELOG.md**: 版本更新日志
- **RELEASE.md**: 发布流程指南
- **LICENSE**: MIT 开源许可证

---

## 🚀 发布步骤

### 1. 初始化 Git 仓库
```bash
cd project/PortPier
git init
git add .
git commit -m "Initial commit: PortPier v1.1.0"
```

### 2. 创建 GitHub 仓库
- 访问 https://github.com/new
- 仓库名：`PortPier`
- 描述：`A lightweight TCP port mapping tool with GUI`

### 3. 推送到 GitHub
```bash
git remote add origin https://github.com/FatFatYoung/PortPier.git
git branch -M main
git push -u origin main
```

### 4. 创建 Release
```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

### 5. 上传 EXE 文件
- 访问 https://github.com/FatFatYoung/PortPier/releases
- 创建新 Release
- 上传 `portpier_server.exe` 和 `portpier_client.exe`

---

## 📦 需要上传的文件

| 文件 | 路径 | 大小 |
|------|------|------|
| portpier_server.exe | `server/dist/portpier_server.exe` | ~11.8 MB |
| portpier_client.exe | `client/dist/portpier_client.exe` | ~11.7 MB |

---

## 📊 项目亮点

1. **轻量级 Python 实现** - 易于理解和修改
2. **GUI 界面** - 对新手友好
3. **中英双语支持** - 完整的界面国际化
4. **专注端口映射** - 功能简单明确
5. **Windows 优先** - 针对 Windows 用户优化
6. **自动重连** - 网络波动时自动恢复
7. **IP 访问控制** - 安全性保障

---

## 📧 联系方式

- GitHub：[@FatFatYoung](https://github.com/FatFatYoung)
- 邮箱：fafafat@qq.com
