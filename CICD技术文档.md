# CI/CD 持续集成与持续部署 — 完整技术文档

## 一、什么是 CI/CD

### 1.1 传统软件开发的问题

在没有 CI/CD 之前，代码上线是手动的：

1. 开发者在本地写代码
2. 手动 FTP/SCP 上传到服务器
3. 手动 SSH 登录服务器
4. 手动停服务、替换文件、重启服务
5. 祈祷不出问题

问题很明显：**慢、容易出错、不可重复、无法追溯。**

### 1.2 CI/CD 解决什么

| 缩写 | 全称 | 含义 | 做什么 |
|------|------|------|--------|
| **CI** | Continuous Integration | 持续集成 | 每次提交代码，自动拉取 → 构建 → 测试，确保代码质量 |
| **CD** | Continuous Deployment | 持续部署 | CI 通过后，自动把代码部署到服务器，无需人工干预 |

**核心价值：你 push 代码，等两分钟，线上自动更新。中间没有任何手动操作。**

### 1.3 本项目的 CI/CD 架构

```
开发者本地 git push
       │
       ▼
┌──────────────────────────────────┐
│         GitHub Actions           │
│                                  │
│  ┌────────┐     ┌────────────┐   │
│  │   CI   │────→│    CD      │   │
│  │ 测试代码 │ 通过 │  部署到服务器 │   │
│  └────────┘     └────────────┘   │
└──────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│       腾讯云服务器 (Ubuntu)        │
│                                  │
│  Nginx (:80) → Gunicorn (:8000)  │
│                     ↓            │
│               Flask app.py       │
└──────────────────────────────────┘
       │
       ▼
   用户浏览器访问 http://124.221.3.229
```

---

## 二、项目文件结构

```
CICD/
├── app.py                          # Flask Web 应用（14行代码）
├── requirements.txt                # Python 依赖清单
├── README.md                       # 项目说明
└── .github/workflows/
    ├── ci.yml                      # CI 工作流：自动化测试
    └── deploy.yml                  # CD 工作流：自动化部署
```

---

## 三、应用代码详解（app.py）

```python
from flask import Flask      # Flask：Python 轻量级 Web 框架
import socket                # 用于获取服务器主机名

app = Flask(__name__)        # 创建 Flask 应用实例

@app.route("/")              # 路由装饰器：访问根路径 "/" 时触发
def index():
    return f"""
    <h1>CICD Test App</h1>
    <p>Server: {socket.gethostname()}</p>
    <p>Status: Running</p>
    """
```

**功能：** 浏览器访问网站时，返回一个包含服务器主机名和运行状态的 HTML 页面。

**代码量这么少的原因：** 本项目的目的是验证 CI/CD 流水线是否正常运转，而非展示业务逻辑。你可以随时扩展此应用，CI/CD 流水线会自动处理部署。

### 依赖说明（requirements.txt）

```
flask==3.1.2          # Web 框架：处理 HTTP 请求和响应
gunicorn==23.0.0      # WSGI 生产级服务器：运行 Flask 应用
```

为什么需要 Gunicorn？Flask 内置的开发服务器是单线程、单进程的，仅适合本地开发调试。生产环境必须使用 Gunicorn 这类生产级 WSGI 服务器，它能：
- 启动多个工作进程，处理并发请求
- 管理进程生命周期（崩溃自动重启子进程）
- 提供生产级的稳定性和性能

---

## 四、CI 工作流详解（ci.yml）

### 4.1 整体结构

```yaml
name: CI                           # 工作流名称，在 GitHub Actions 页面显示

on:                                # 触发条件
  push:
    branches: [main]               # push 到 main 分支时触发
  pull_request:
    branches: [main]               # 创建 PR 到 main 分支时也触发

jobs:                              # 任务列表
  test:                            # 任务名称为 "test"
    runs-on: ubuntu-latest         # 运行在 GitHub 提供的最新 Ubuntu 虚拟机上
    steps:                         # 执行步骤
      - ...                        # 4 个步骤，见下文
```

### 4.2 触发条件

| 触发事件 | 场景 |
|----------|------|
| `push` 到 main | 你本地 `git push` 后自动触发 |
| `pull_request` 到 main | 团队成员提 PR 时自动触发 |

### 4.3 执行步骤

**Step 1 — 拉取代码：**

```yaml
- uses: actions/checkout@v4
```

使用 GitHub 官方 Action，将当前仓库的代码克隆到虚拟机的工作目录中。

**Step 2 — 安装 Python：**

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
```

使用 GitHub 官方 Action，在虚拟机中安装 Python 3.12 运行环境。

**Step 3 — 安装依赖：**

```yaml
- run: pip install -r requirements.txt
```

在虚拟机中安装 Flask 和 Gunicorn。

**Step 4 — 运行测试：**

```python
from app import app                    # 导入我们的 Flask 应用
client = app.test_client()             # 创建 Flask 内置测试客户端（无需真实启动服务器）
r = client.get('/')                    # 模拟 HTTP GET 请求访问 "/"
assert r.status_code == 200            # 断言：HTTP 状态码必须是 200
assert b'Running' in r.data            # 断言：返回内容中必须包含 "Running"
```

使用 Python 的 `assert` 语句进行自动化验证：
- 如果所有断言通过 → CI 标记为 **绿色（成功）**
- 如果任一断言失败 → CI 标记为 **红色（失败）**，CD 不会触发

**CI 的核心价值：**

1. **门禁作用：** 代码有问题（如语法错误、逻辑错误）在部署前就被发现
2. **防止回退：** 新代码不会破坏已有功能
3. **自动化执行：** 无需人工审查，push 即触发
4. **环境一致性：** GitHub Ubuntu 虚拟机与腾讯云 Ubuntu 服务器环境几乎一致

---

## 五、CD 工作流详解（deploy.yml）

### 5.1 整体结构

```yaml
name: CD - Deploy to Server

on:                                # 触发条件：监听 CI 工作流
  workflow_run:
    workflows: ["CI"]              # 当名为 "CI" 的工作流完成时触发
    types: [completed]
    branches: [main]

jobs:
  deploy:
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
                                   # 仅当 CI 成功时才执行
    runs-on: ubuntu-latest
    steps:
      - ...                        # 3 个步骤
```

### 5.2 触发条件与门禁

CD 不是直接由 `push` 触发的，而是监听 CI 完成事件：

```
push → CI 自动运行 → CI 成功 → CD 自动运行
                  → CI 失败 → CD 不运行（阻止有问题的代码上线）
```

```yaml
if: ${{ github.event.workflow_run.conclusion == 'success' }}
```

这行是关键：**只有 CI 标记为 success，CD 才会执行。** 这是 CI/CD 流水线的核心纪律。

### 5.3 执行步骤

**Step 1 — 拉取代码：**

```yaml
- uses: actions/checkout@v4
```

与 CI 相同，将最新代码拉到 GitHub Actions 虚拟机。

**Step 2 — SCP 传输文件到服务器：**

```yaml
- uses: appleboy/scp-action@v0.1.7
  with:
    host: ${{ secrets.SERVER_HOST }}      # 服务器公网 IP
    username: ${{ secrets.SERVER_USER }}   # SSH 用户名
    key: ${{ secrets.SSH_PRIVATE_KEY }}   # SSH 私钥
    source: "app.py,requirements.txt"     # 要传输的文件
    target: /home/ubuntu/app              # 服务器目标路径
```

SCP（Secure Copy）是一种基于 SSH 协议的安全文件传输方式。`${{ secrets.XXX }}` 是 GitHub Secrets 机制，敏感信息存储在仓库设置中，运行时注入但不会在日志中暴露。

**Step 3 — SSH 远程部署：**

通过 SSH 在服务器上执行以下一系列命令：

**3.1 安装基础软件：**

```bash
sudo apt-get update -qq                  # 更新软件包索引
sudo apt-get install -y -qq \            # 安装必要软件
    python3-pip \                         # Python 包管理器
    python3-venv \                        # Python 虚拟环境模块
    nginx                                 # 反向代理服务器
```

首次部署时需要安装，后续部署这些命令会跳过已安装的包。

**3.2 创建 Python 虚拟环境并安装依赖：**

```bash
python3 -m venv /home/ubuntu/app/venv   # 创建虚拟环境（一个独立文件夹）
/home/ubuntu/app/venv/bin/pip install \ # 使用虚拟环境的 pip 安装依赖
    -r /home/ubuntu/app/requirements.txt
```

**3.3 注册 systemd 系统服务：**

```ini
[Unit]
Description=CICD Test App               # 服务描述
After=network.target                     # 在网络就绪后启动

[Service]
User=ubuntu                              # 以 ubuntu 用户身份运行
WorkingDirectory=/home/ubuntu/app        # 工作目录
ExecStart=/home/ubuntu/app/venv/bin/gunicorn \  # 启动命令
    -w 2 \                               # 2 个工作进程
    -b 127.0.0.1:8000 \                  # 监听本机 8000 端口
    app:app                              # 模块名:Flask实例名
Restart=always                           # 进程崩溃自动重启

[Install]
WantedBy=multi-user.target               # 系统启动时自动运行
```

```bash
sudo systemctl daemon-reload             # 重新加载服务配置
sudo systemctl enable cicd-test          # 设置开机自启动
sudo systemctl restart cicd-test         # 重启服务（应用新代码）
```

**3.4 配置 Nginx 反向代理：**

```nginx
server {
    listen 80;                           # 监听 HTTP 标准端口 80
    server_name _;                       # 匹配所有域名

    location / {
        proxy_pass http://127.0.0.1:8000;        # 转发请求到 Gunicorn
        proxy_set_header Host $host;              # 传递原始 Host 头
        proxy_set_header X-Real-IP $remote_addr;  # 传递客户端真实 IP
    }
}
```

```bash
sudo ln -sf /etc/nginx/sites-available/cicd-test \
    /etc/nginx/sites-enabled/              # 启用站点配置
sudo rm -f /etc/nginx/sites-enabled/default # 删除默认站点
sudo nginx -t && sudo systemctl restart nginx  # 测试配置并重启 Nginx
```

---

## 六、关键技术概念

### 6.1 GitHub Actions 虚拟机

GitHub Actions 在每次触发时免费提供一台**临时的 Ubuntu 虚拟机**：

- 配置：2 核 CPU、7GB 内存、14GB SSD
- 特点：用完即销毁，不保存任何状态
- 用途：运行测试（CI）、执行部署脚本（CD）
- **不能用来运行长期在线的应用**——这就是需要云服务器的原因

### 6.2 Python 虚拟环境（venv）

虚拟环境是 Python 的依赖隔离机制，本质是**一个文件夹**：

```
/home/ubuntu/app/venv/
├── bin/
│   ├── python       ← 此环境专属的 Python 解释器
│   ├── pip          ← 此环境专属的包管理器
│   └── gunicorn     ← 安装在此环境中的命令
└── lib/
    └── python3.12/
        └── site-packages/
            ├── flask/
            └── gunicorn/
```

**为什么需要虚拟环境？**

- **隔离性：** 项目 A 需要 Flask 1.0，项目 B 需要 Flask 2.0，两个虚拟环境互不影响
- **可复现：** `requirements.txt` 锁定版本，任何人部署结果一致
- **安全性：** 不影响系统 Python，不污染全局环境
- **清洁性：** 不需要时直接删除文件夹即可

**对比：**

| | 无虚拟环境 | 有虚拟环境 |
|---|----------|----------|
| 安装位置 | 系统全局 `/usr/lib/python3/` | 项目目录 `app/venv/` |
| 版本冲突 | 多项目共享，易冲突 | 每个项目隔离，不冲突 |
| 权限 | 需要 sudo | 不需要 sudo |
| 删除清理 | 难以彻底清理 | 删除文件夹即可 |

### 6.3 Nginx 反向代理

Nginx 是高性能的 HTTP 服务器和反向代理，在部署架构中扮演"前台接待员"的角色：

```
用户浏览器 → Nginx (公网 :80) → Gunicorn (内网 :8000) → Flask app.py
```

**完整的请求处理流程：**

1. 用户在浏览器输入 `http://124.221.3.229`（浏览器默认使用 80 端口）
2. 请求到达服务器，Nginx 监听 80 端口接收请求
3. Nginx 根据配置规则 `proxy_pass http://127.0.0.1:8000`，将请求转发给 Gunicorn
4. Gunicorn（监听 127.0.0.1:8000）调用 Flask 应用的 `index()` 函数处理请求
5. Flask 返回 HTML → Gunicorn → Nginx → 用户浏览器

**为什么不能直接把 Gunicorn 暴露到公网？**

| 维度 | 直接暴露 Gunicorn | 通过 Nginx 代理 |
|------|-------------------|----------------|
| **安全** | Gunicorn 直面公网所有流量，攻击面大 | Gunicorn 只监听本机回环地址（127.0.0.1），外网无法直接访问 |
| **性能** | 慢客户端会长时间占用 Gunicorn 工作进程 | Nginx 作为缓冲区，高效管理所有客户端连接 |
| **静态文件** | Python 进程处理图片/CSS/JS 请求，浪费资源 | Nginx 直接返回静态文件，不经过 Python |
| **功能** | 无 | Nginx 提供限流、压缩、SSL 终端、负载均衡等高级功能 |
| **稳定性** | Gunicorn 崩溃则服务中断 | Nginx 可缓存响应，Gunicorn 短暂不可用时提供降级服务 |

**这被称为"反向代理"模式，是所有 Web 后端（Python/Java/Go/Node.js）部署的标准架构。**

### 6.4 systemd 服务管理

systemd 是 Linux 的初始化系统和服务管理器，负责管理后台进程：

| 操作 | systemd 命令 |
|------|-------------|
| 启动服务 | `sudo systemctl start cicd-test` |
| 停止服务 | `sudo systemctl stop cicd-test` |
| 重启服务 | `sudo systemctl restart cicd-test` |
| 查看状态 | `sudo systemctl status cicd-test` |
| 开机自启 | `sudo systemctl enable cicd-test` |
| 查看日志 | `sudo journalctl -u cicd-test -f` |

通过 systemd 管理的好处：
- **自动重启：** 进程崩溃后 systemd 会自动拉起新进程
- **开机自启：** 服务器重启后应用自动恢复
- **日志管理：** 所有输出自动收集，可通过 journalctl 查看

### 6.5 GitHub Secrets

敏感信息（IP、密码、私钥）不能写在代码里，GitHub Secrets 提供了安全的存储机制：

- 存储在仓库 Settings → Secrets and variables → Actions 中
- 运行时注入为环境变量或 `${{ secrets.XXX }}`
- 在日志中自动遮蔽为 `***`
- 即使仓库公开，Secrets 也不会泄露

本项目使用的三个 Secrets：

| Secret 名称 | 存储内容 | 用途 |
|------------|---------|------|
| `SERVER_HOST` | `124.221.3.229` | 服务器公网 IP 地址 |
| `SERVER_USER` | `ubuntu` | SSH 登录用户名 |
| `SSH_PRIVATE_KEY` | PEM 私钥全文 | GitHub Actions 通过 SSH 连接服务器的凭证 |

---

## 七、CI/CD 完整执行流程

### 7.1 一次完整部署的时间线

```
T+0s    开发者执行 git push
T+5s    GitHub 检测到 main 分支有新提交
T+6s    CI 工作流启动，分配 Ubuntu 虚拟机
T+10s   拉取代码完成
T+15s   Python 3.12 安装完成
T+25s   pip install 依赖安装完成
T+30s   自动化测试执行完成，全部通过 ✓
        ↓
T+31s   CI 标记为 success，触发 CD 工作流
T+32s   CD 工作流启动，分配 Ubuntu 虚拟机
T+36s   拉取代码完成
T+40s   SCP 文件传输到服务器完成
T+45s   SSH 连接服务器，执行部署脚本
T+50s   pip install 依赖更新完成
T+52s   systemd 服务重启完成
T+55s   Nginx 配置重载完成
T+60s   部署完成，线上生效 ✓
```

### 7.2 流程可视化

```
开发者本地                          GitHub Actions                      腾讯云服务器
   │                                    │                                  │
   │  git push ───────────────────────→ │                                  │
   │                                    │                                  │
   │                      ┌─ CI 虚拟机启动 ─┐                              │
   │                      │  1. 拉取代码    │                              │
   │                      │  2. 安装 Python │                              │
   │                      │  3. 安装依赖    │                              │
   │                      │  4. 运行测试    │                              │
   │                      └─── 测试通过 ✓ ──┘                              │
   │                                    │                                  │
   │                      ┌─ CD 虚拟机启动 ─┐                              │
   │                      │  1. 拉取代码    │                              │
   │                      │  2. SCP 传文件  │──── app.py ──────────────→ │
   │                      │                 │  requirements.txt            │
   │                      │  3. SSH 执行脚本│──── 部署命令 ─────────────→ │
   │                      │                 │                              │
   │                      │                 │              ┌─ 安装依赖 ─┐  │
   │                      │                 │              │  重启服务   │  │
   │                      │                 │              │  重载 Nginx │  │
   │                      │                 │              └─ 部署完成 ✓ ┘  │
   │                      └─────────────────┘                              │
   │                                    │                                  │
   │  浏览器访问 ──────────────────────────────────────────────────────→  http://124.221.3.229
   │  ←────────────────────────────────────────────────────── 返回 HTML 页面
```

---

## 八、环境配置清单

### 8.1 本地环境

| 组件 | 说明 |
|------|------|
| Git | 版本控制，代码提交工具 |
| SSH Key | 用于 GitHub 认证（HTTPS Token 也可替代） |
| 代码编辑器 | IDE 或文本编辑器 |

### 8.2 GitHub 仓库配置

| 配置项 | 说明 |
|-------|------|
| 仓库可见性 | Public（公开） |
| GitHub Actions | 已启用（公开仓库免费使用） |
| Secrets | 配置 SERVER_HOST、SERVER_USER、SSH_PRIVATE_KEY |

### 8.3 服务器环境

| 组件 | 版本/配置 |
|------|----------|
| 云平台 | 腾讯云 Lighthouse |
| 操作系统 | Ubuntu 22.04 |
| CPU/内存 | 1 核 / 2 GB |
| 公网 IP | 124.221.3.229 |
| Web 服务器 | Nginx（监听 80 端口） |
| 应用服务器 | Gunicorn 2 workers（监听 127.0.0.1:8000） |
| Python | 3.12（虚拟环境） |
| 进程管理 | systemd（服务名：cicd-test） |

---

## 九、常用操作指南

### 9.1 修改并部署代码

```bash
# 1. 修改代码
vim app.py

# 2. 提交并推送
git add app.py
git commit -m "描述你的修改"
git push

# 3. 等待 1-2 分钟，CI/CD 自动完成
# 4. 刷新 http://124.221.3.229 查看结果
```

### 9.2 查看部署状态

- **GitHub Actions 页面：** https://github.com/wt1298562757/CICD_Test/actions
- **服务器登录：** `ssh ubuntu@124.221.3.229`
- **查看服务状态：** `sudo systemctl status cicd-test`
- **查看应用日志：** `sudo journalctl -u cicd-test -f`
- **查看 Nginx 日志：** `sudo tail -f /var/log/nginx/access.log`

### 9.3 手动重启服务（服务器上）

```bash
sudo systemctl restart cicd-test    # 重启 Flask 应用
sudo systemctl restart nginx        # 重启 Nginx
```

### 9.4 故障排查

| 问题 | 检查方法 |
|------|---------|
| 网站打不开 | `sudo systemctl status nginx cicd-test` |
| 部署后没变化 | 检查 GitHub Actions 日志 |
| 应用报 502 错误 | `sudo journalctl -u cicd-test -n 50` |
| 端口被占用 | `sudo netstat -tlnp | grep -E '80|8000'` |

---

## 十、后续扩展建议

本项目的 CI/CD 流水线已具备生产级部署的核心要素，可根据实际需求扩展：

| 扩展方向 | 方案 |
|----------|------|
| 自动构建 Docker 镜像 | 在 CI 中添加 `docker build` 步骤 |
| 多环境部署 | 添加 staging/production 分支对应不同服务器 |
| 数据库集成 | 添加 MySQL/PostgreSQL 连接配置 |
| 域名 + HTTPS | 配置域名解析 + Nginx SSL 证书（Let's Encrypt） |
| 通知 | 添加 Slack/企业微信/钉钉 部署通知 |
| 回滚机制 | 保留历史版本，一键回滚 |

---

## 十一、总结

**这个项目做了什么：**

1. 创建了一个 14 行的 Python Flask Web 应用
2. 配置了 GitHub Actions CI 流水线：push 自动测试
3. 配置了 GitHub Actions CD 流水线：测试通过自动部署
4. 在腾讯云 Ubuntu 服务器上搭建了 Nginx + Gunicorn 生产级部署架构
5. 实现了"一行 git push，两分钟全自动上线"的 CI/CD 流程

**这个项目的教学价值：**

- 麻雀虽小，五脏俱全——代码量少但涵盖了 CI/CD 的全部核心环节
- 所有配置文件（CI/CD 脚本、服务配置、Nginx 配置）都在仓库中可见可读
- 可以在演示中实时修改代码并展示自动部署效果
- 可以复制到任何新建的 GitHub 仓库中快速搭建 CI/CD 环境
