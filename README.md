# YouTube网红曝光合作系统

为游戏（网络游戏/手机游戏/米哈游游戏）找到合适的 YouTube 创作者，基于其历史表现形成可解释报价，并完成邮件触达、谈判推进、Brief 对接、排期、上线验收与日报输出。

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

## 开发计划

- [x] 搭建系统框架
- [ ] 实现DataCollectionAgent（数据采集）
- [ ] 实现PricingAgent（报价计算）
- [ ] 实现ContactFindingAgent（联系方式查找）
- [ ] 实现OutreachAgent（邮件生成）
- [ ] 实现NegotiationAgent（谈判处理）
- [ ] 实现BriefAgent（Brief生成）
- [ ] 实现DailyReportAgent（日报汇总）
- [ ] 集成邮件话术库
- [ ] 添加Web界面
