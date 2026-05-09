# PortPier 发布指南

## 准备工作

### 1. 更新版本号

在以下文件中更新版本号：
- `CHANGELOG.md` - 添加新版本的更新日志
- `README.md` - 更新版本信息

### 2. 构建 EXE 文件

```bash
cd server
build.bat

cd ../client
build.bat
```

### 3. 测试

在发布前，请确保：
- [ ] 服务端能正常启动
- [ ] 客户端能正常启动
- [ ] 客户端能连接到服务端
- [ ] 端口映射功能正常
- [ ] 中英文切换功能正常

## 发布步骤

### 1. 创建 Git 标签

```bash
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

### 2. 在 GitHub 上创建 Release

1. 访问 https://github.com/FatFatYoung/PortPier/releases
2. 点击 "Draft a new release"
3. 选择标签
4. 填写标题和描述
5. 上传 EXE 文件
6. 点击 "Publish release"

## 版本命名规范

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)：

- **主版本号**：不兼容的 API 修改
- **次版本号**：向下兼容的功能性新增
- **修订号**：向下兼容的问题修正

## 发布检查清单

### 发布前
- [ ] 更新版本号
- [ ] 更新 CHANGELOG.md
- [ ] 构建 EXE 文件
- [ ] 测试所有功能

### 发布时
- [ ] 创建 Git 标签
- [ ] 创建 GitHub Release
- [ ] 上传 EXE 文件

### 发布后
- [ ] 验证下载链接
- [ ] 测试下载的 EXE 文件
