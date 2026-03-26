# YouTube网红曝光合作系统

一个基于 AI-Agent 的 YouTube 网红营销自动化系统。帮助游戏厂商（网络游戏/手机游戏/米哈游游戏等）高效找到合适的 YouTube 创作者，基于其历史数据形成可解释报价，并完成从邮件触达、谈判推进、Brief 对接、排期到上线验收的全流程自动化管理。

## 核心功能

- 🔍 **创作者搜索**: 基于 YouTube API 搜索符合条件的游戏创作者
- 📊 **数据采集**: 自动采集频道数据、视频表现、受众画像
- 💰 **智能报价**: 基于历史数据生成可解释的报价卡（Anchor/Target/Floor）
- 📧 **邮件工具**: 内置 12 套英文邮件话术模板，支持一键发送和跟进序列
- 🤖 **AI 谈判**: 自动分析创作者回复并生成应对话术
- 📋 **流程管理**: Pipeline 状态机驱动，支持全流程追踪

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentOrchestrator                        │
│                         (总控编排器)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Pipeline     │    │   7个Agent    │    │    Tools      │
│  状态机引擎    │    │  (子任务Agent) │    │  (工具接口)    │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        ↓                     ↓                     ↓
• PipelineStage        • DataCollection      • WebFetch
• PipelineContext      • Pricing             • YouTubeAPI
• PipelineEngine       • ContactFinding      • Email
                       • Outreach            • CRM
                       • Negotiation         • Storage
                       • Brief
                       • DailyReport
```

## Pipeline状态流转

```
LEAD_COLLECTED → DATA_COLLECTING → DATA_READY → PRICING_DRAFTED 
→ CONTACT_FINDING → OUTREACH_SENT → NEGOTIATING → BRIEF_SENT 
→ SCHEDULE_CONFIRMED → DELIVERABLE_LIVE → WRAP_UP → CLOSED_WON/LOST
                              ↓
                        NEED_HUMAN_APPROVAL
```

## 快速开始

```python
from src import AgentOrchestrator

# 1. 初始化编排器
orchestrator = AgentOrchestrator()

# 2. 创建新线索
context = orchestrator.create_lead(
    channel_url="https://www.youtube.com/@example",
    creator_name="Example Creator"
)

# 3. 运行Pipeline（自动执行到需要人工干预）
result = orchestrator.run_pipeline(
    channel_url="https://www.youtube.com/@example",
    auto_run=True
)

# 4. 处理收到的回复
result = orchestrator.handle_incoming_reply(
    channel_url="https://www.youtube.com/@example",
    email_content="对方邮件内容..."
)

# 5. 人工审批后继续
result = orchestrator.approve_and_continue(
    channel_url="https://www.youtube.com/@example",
    approval_notes="已确认报价"
)

# 6. 生成日报
report = orchestrator.generate_daily_report(date="2026-03-25")
```

## 项目结构

```
.
├── src/
│   ├── __init__.py              # 主入口
│   ├── core/                    # 核心模块
│   │   ├── __init__.py
│   │   ├── pipeline.py          # Pipeline状态机
│   │   ├── agent.py             # Agent基类和7个子Agent
│   │   └── orchestrator.py      # 总控编排器
│   └── tools/                   # 工具接口
│       ├── __init__.py
│       ├── web_fetch.py         # 网页抓取
│       ├── youtube_api.py       # YouTube API
│       ├── email.py             # 邮件发送
│       ├── crm.py               # CRM存储
│       └── storage.py           # 文件存储
├── data/                        # 数据目录
│   ├── artifacts/               # 生成的工件
│   └── crm_records.json         # CRM记录
├── YouTube游戏曝光合作_英文邮件话术库.md
├── YouTube网红曝光合作_AI-Agent提示词与状态机.md
└── README.md
```

## 核心概念

### 1. PipelineContext
贯穿整个流程的数据容器，包含：
- 创作者基础信息
- 当前Pipeline状态
- 采集的数据和画像
- 报价信息
- 联系方式
- 邮件历史
- 谈判记录

### 2. Agent
7个专门的子任务Agent：
- **DataCollectionAgent**: 数据采集与画像
- **PricingAgent**: 报价计算
- **ContactFindingAgent**: 查找联系方式
- **OutreachAgent**: 首封邮件生成
- **NegotiationAgent**: 谈判处理
- **BriefAgent**: Brief生成
- **DailyReportAgent**: 日报汇总

### 3. Tools
工具接口层：
- **WebFetchTool**: 网页抓取
- **YouTubeAPITool**: YouTube Data API
- **EmailTool**: 邮件发送
- **CRMStorage**: CRM记录存储
- **StorageTool**: 文件存储

## 配置

### YouTube API Key（可选）
```python
from src.tools import YouTubeAPITool

youtube_api = YouTubeAPITool(api_key="YOUR_API_KEY")
```

### SMTP配置（可选）
```python
from src.tools import EmailTool

email_tool = EmailTool(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    smtp_user="your_email@gmail.com",
    smtp_password="your_password"
)
```

### 测试模式
```python
# 使用模拟邮件发送
email_tool = EmailTool(mock_mode=True)
```

## 工作原则

1. **闭环**: 每个任务都必须有"完成标准"
2. **不编造**: 数据找不到明确标注"缺失/不确定"
3. **结构化工件**: 输出可复用的表格/JSON/邮件/Brief
4. **可追踪**: 每一步写入CRM记录
5. **合规沟通**: 不夸大或承诺不可控效果

## 失败分支处理

- **抓不到数据**: 切换数据源或进入人工审批
- **找不到邮箱**: 转用官网表单/社媒私信或人工兜底
- **48小时不回**: 自动follow-up（最多2次）
- **报价超预算/条款敏感**: 触发NEED_HUMAN_APPROVAL

---

## Vercel 部署指南

本项目可以部署到 Vercel，但需要注意以下限制和配置：

### ⚠️ 重要限制

Vercel 是 **Serverless 平台**，有以下限制：
1. **无状态**: 每次请求后容器会被销毁，内存中的数据会丢失
2. **超时限制**: 免费版函数执行时间限制为 10 秒（Hobby 版）
3. **文件系统**: 只读文件系统，无法持久化存储

### 推荐的部署方案

#### 方案一：简化版 Web 界面（推荐）

仅部署 Web 界面，数据存储使用外部数据库（如 MongoDB Atlas、Supabase）。

**1. 创建 `vercel.json`**

```json
{
  "version": 2,
  "builds": [
    {
      "src": "web_app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "web_app.py"
    }
  ],
  "env": {
    "PYTHONPATH": "."
  }
}
```

**2. 修改 `web_app.py` 适配 Vercel**

```python
# 在文件末尾添加
import os

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # Vercel 生产环境
    app.debug = False
```

**3. 环境变量配置**

在 Vercel Dashboard 中设置以下环境变量：

| 变量名 | 说明 | 必需 |
|-------|------|------|
| `YOUTUBE_API_KEY` | YouTube Data API Key | 是 |
| `EMAIL_SMTP_HOST` | SMTP 服务器地址 | 否 |
| `EMAIL_SMTP_PORT` | SMTP 端口（默认 587） | 否 |
| `EMAIL_SENDER` | 发件人邮箱 | 否 |
| `EMAIL_PASSWORD` | 邮箱密码/授权码 | 否 |
| `LLM_PROVIDER` | LLM 提供商（openai/deepseek） | 否 |
| `LLM_API_KEY` | LLM API Key | 否 |

**4. 部署步骤**

```bash
# 安装 Vercel CLI
npm i -g vercel

# 登录
vercel login

# 部署
vercel --prod
```

#### 方案二：使用外部数据库

如果需要数据持久化，建议：

1. **使用 MongoDB Atlas** 存储线索数据
2. **使用 Redis** 缓存会话状态
3. **使用 AWS S3** 存储生成的文件

修改 `src/tools/storage.py` 使用云存储：

```python
# 示例：使用 MongoDB
from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGODB_URI"))
db = client["youtube_kol"]
```

### 本地开发 vs Vercel 部署对比

| 功能 | 本地开发 | Vercel 部署 |
|-----|---------|------------|
| 内存数据存储 | ✅ 支持 | ⚠️ 每次请求重置 |
| 文件持久化 | ✅ 支持 | ❌ 不支持 |
| 长时间任务 | ✅ 支持 | ❌ 10秒超时 |
| 邮件发送 | ✅ 支持 | ✅ 支持 |
| YouTube API | ✅ 支持 | ✅ 支持 |

### 推荐的替代部署方案

如果需要在生产环境稳定运行，建议使用：

1. **Railway** (https://railway.app) - 支持持久化存储
2. **Render** (https://render.com) - 支持 Web 服务和后台任务
3. **AWS EC2 / DigitalOcean** - 完整的 VPS 控制

## Railway 部署指南（推荐）

[Railway](https://railway.app) 是一个更适合本项目的部署平台，支持：
- ✅ 持久化磁盘存储（数据不会丢失）
- ✅ 长时间运行的服务（无 10 秒超时限制）
- ✅ 简单的 CLI 部署流程
- ✅ 免费额度足够个人使用

### 方式一：使用 Railway CLI（推荐）

#### 1. 准备工作

确保项目已提交到 Git 仓库（GitHub/GitLab）：

```bash
# 初始化 Git 仓库（如果还没有）
git init
git add .
git commit -m "Initial commit"

# 推送到 GitHub
git remote add origin https://github.com/yourusername/your-repo.git
git push -u origin main
```

#### 2. 安装 Railway CLI

```bash
# macOS/Linux
curl -fsSL https://railway.app/install.sh | sh

# Windows (PowerShell)
npm i -g @railway/cli

# 或者使用 npm（跨平台）
npm i -g @railway/cli
```

#### 3. 登录 Railway

```bash
railway login
```

会打开浏览器进行授权登录。

#### 4. 初始化项目

```bash
# 在项目根目录执行
cd d:\coding\zidongyingxiao

# 创建新项目或关联现有项目
railway init

# 选择：
# - "Create a new project" 创建新项目
# - 或选择已有项目
```

#### 5. 配置环境变量

```bash
# 必需：YouTube API Key
railway variables set YOUTUBE_API_KEY="your_youtube_api_key"

# 可选：SMTP 邮件配置（阿里云企业邮箱示例）
railway variables set EMAIL_SMTP_HOST="smtp.qiye.aliyun.com"
railway variables set EMAIL_SMTP_PORT="465"
railway variables set EMAIL_SENDER="cooperate@topuplive.com"
railway variables set EMAIL_PASSWORD="your_email_password"

# 可选：LLM 配置（DeepSeek 示例）
railway variables set LLM_PROVIDER="deepseek"
railway variables set DEEPSEEK_API_KEY="your_deepseek_api_key"

# 可选：其他配置
railway variables set FLASK_ENV="production"
railway variables set PYTHONUNBUFFERED="1"
```

查看所有已设置的环境变量：
```bash
railway variables
```

#### 6. 创建启动脚本

确保项目根目录有 `Procfile` 文件（告诉 Railway 如何启动应用）：

```bash
# 创建 Procfile
echo "web: python web_app.py" > Procfile
```

内容如下：
```
web: python web_app.py
```

#### 7. 部署

```bash
# 部署到 Railway
railway up

# 查看部署日志
railway logs

# 查看部署状态
railway status
```

部署成功后会显示访问 URL，类似：
```
🚀 Deployed to https://your-project.up.railway.app
```

#### 8. 后续更新

当代码有更新时，重新部署：

```bash
# 提交代码变更
git add .
git commit -m "Update features"
git push

# 重新部署
railway up
```

---

### 方式二：使用 Railway Dashboard（图形界面）

如果不习惯命令行，可以使用 Railway 网页界面：

#### 1. 登录 Railway Dashboard

访问 https://railway.app/dashboard

#### 2. 创建新项目

- 点击 "New Project"
- 选择 "Deploy from GitHub repo"
- 授权并选择你的 GitHub 仓库

#### 3. 配置环境变量

- 在项目页面点击 "Variables" 标签
- 点击 "New Variable" 逐个添加：
  - `YOUTUBE_API_KEY`
  - `EMAIL_SMTP_HOST`
  - `EMAIL_SENDER`
  - 等等...

#### 4. 配置启动命令

- 点击 "Settings" 标签
- 找到 "Start Command"
- 输入：`python web_app.py`

#### 5. 部署

- Railway 会自动检测代码变更并部署
- 点击 "Deploy" 标签查看部署状态

---

### 方式三：使用 Docker 部署（高级）

如果需要更精细的控制，可以使用 Docker：

#### 1. 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
copy requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
copy . .

# 暴露端口
EXPOSE 5000

# 启动命令
cmd ["python", "web_app.py"]
```

#### 2. 创建 .dockerignore

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.git/
.gitignore
README.md
```

#### 3. 在 Railway 使用 Docker

- 在 Railway Dashboard 中
- Settings → Build → Builder 选择 "Docker"
- Railway 会自动使用 Dockerfile 构建和部署

---

### Railway 配置参考

#### 必需的环境变量

| 变量名 | 说明 | 示例值 |
|-------|------|--------|
| `YOUTUBE_API_KEY` | YouTube Data API Key | AIzaSy... |

#### 可选的环境变量

| 变量名 | 说明 | 示例值 |
|-------|------|--------|
| `EMAIL_SMTP_HOST` | SMTP 服务器 | smtp.qiye.aliyun.com |
| `EMAIL_SMTP_PORT` | SMTP 端口 | 465 |
| `EMAIL_SENDER` | 发件人邮箱 | cooperate@topuplive.com |
| `EMAIL_PASSWORD` | 邮箱密码/授权码 | your_password |
| `LLM_PROVIDER` | LLM 提供商 | deepseek / openai |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | sk-... |
| `OPENAI_API_KEY` | OpenAI API Key | sk-... |

---

### Railway 常见问题

#### Q: 如何查看日志？
```bash
railway logs
# 或实时查看
railway logs --follow
```

#### Q: 如何重启服务？
```bash
railway up
```

#### Q: 如何添加自定义域名？
1. 在 Railway Dashboard 中点击 "Settings"
2. 找到 "Domains" 部分
3. 点击 "Custom Domain"
4. 按照指引配置 DNS

#### Q: 数据会丢失吗？
默认情况下，Railway 的磁盘是临时的。如需持久化：
1. 在 Dashboard 中点击 "Settings"
2. 找到 "Volumes"
3. 添加 Volume 并挂载到 `/app/data`

#### Q: 免费额度是多少？
- 每月 $5 免费额度
- 足够运行一个小型应用
- 超出后会暂停服务，不会自动扣费

---

### Railway vs Vercel 对比

| 特性 | Railway | Vercel |
|-----|---------|--------|
| 持久化存储 | ✅ 支持 | ❌ 不支持 |
| 执行超时 | ✅ 无限制 | ❌ 10秒 |
| 内存数据 | ✅ 保留 | ❌ 每次请求重置 |
| 文件系统 | ✅ 可写 | ❌ 只读 |
| 免费额度 | $5/月 |  generous |
| 部署难度 | 简单 | 简单 |
| 适合本项目 | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**结论**: 本项目推荐使用 Railway 部署。
