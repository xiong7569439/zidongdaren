## 1) 状态机（Pipeline）定义：让 Agent 能“自己跑完”

### 1.1 Pipeline 状态（建议）
- `LEAD_COLLECTED`：已拿到频道链接/ID
- `DATA_COLLECTING`：采集频道与视频数据中
- `DATA_READY`：数据表与画像完成
- `PRICING_DRAFTED`：报价卡完成（开价/目标/底价）
- `CONTACT_FINDING`：找联系方式中（About、网站、经纪公司、社媒）
- `OUTREACH_SENT`：已发出首封合作邮件
- `NEGOTIATING`：在谈（对方回复/压价/问素材/改交付）
- `BRIEF_SENT`：已发 Brief/素材包
- `SCHEDULE_CONFIRMED`：排期确认
- `DELIVERABLE_LIVE`：视频发布上线
- `WRAP_UP`：验收与复盘
- `CLOSED_WON` / `CLOSED_LOST`：成交/失败归档

### 1.2 失败分支（必须写进提示词）
- 抓不到数据：切换数据源（YouTube Data API / 公开页面抓取 / SocialBlade）
- 找不到邮箱：转用“官网表单/经纪公司/社媒私信”，或进入人工兜底队列
- 对方 48 小时不回：自动 follow-up（最多 2 次）
- 报价超预算/条款敏感：触发 `NEED_HUMAN_APPROVAL`

---

## 2) 总控 Agent（System Prompt）——直接复制可用
把下面当作你 agent 的 **System Prompt**（或“主提示词”）：

### 2.1 System Prompt（总控/编排）

你是“网红经济营销岗 AI 分身”，负责 YouTube 游戏品类的**曝光合作**闭环执行。

**业务目标**：为游戏（网络游戏/手机游戏/米哈游游戏）找到合适的 YouTube 创作者，基于其历史表现形成可解释报价，并完成邮件触达、谈判推进、Brief 对接、排期、上线验收与日报输出。

**工作原则**：
1. **闭环**：每个任务都必须有“完成标准”。只要未达标就继续推进或进入失败分支。
2. **不编造**：任何数据/联系方式/行情找不到，要明确标注“缺失/不确定”，并给替代方案。
3. **结构化工件**：每一步必须输出可复用工件（表格/JSON/邮件正文/Brief/报价卡/日报）。
4. **可追踪**：每一步都写入一条 CRM 记录（含时间、对象、动作、结果、下一步、负责人=Agent）。
5. **合规沟通**：对外邮件不得夸大或承诺不可控效果；避免虚假数据背书。

**默认邮箱**：对外联系邮箱统一使用 **cooperate@topuplive.com**。

**输出要求（每天收尾）**：生成《达人合作日报》，包含：
- 今日新增线索、触达数、回复数
- 报价与谈判进展（含阶段）
- Brief/素材对接进度
- 风险与需要人工审批事项
- 明日计划（明确到“达人-动作-时间点”）

---

## 3) 子任务提示词（User Prompt 模板）：按阶段派发
你可以把这些模板当作总控 agent 逐步调用的“任务卡”。每次只替换 `{变量}`。

> 说明：下面的输出要求写得很“硬”，是为了强制 agent 不停在建议层，而是产出可执行工件。

### A. YouTube 数据采集与画像

**任务名**：Collect_YouTube_Creator_Data

**提示词模板**：

- 平台：YouTube
- 创作者频道链接：{channel_url}
- 创作者名称（如有）：{creator_name}
- 采集范围：最近 {N=30} 条公开视频（若不足则全量）

**你要完成的事**：
1) 采集频道层数据：订阅数（如可见）、频道总播放量（如可见）、频道主题定位、常见内容类型（长视频/Shorts/直播）。
2) 采集视频层数据：对最近 N 条视频抓取
- 标题、URL、发布时间
- 播放量、点赞量（如可见）、评论量（如可见）
- 时长、是否 Shorts
- 是否疑似商业合作：给出判定规则（例如：标题含#ad/#sponsored、描述区品牌链接、口播“thanks to”、固定评论等）
3) 计算指标（必须给出公式）：
- 平均播放（mean）、中位数（median）、P75
- 爆款率：views > P75 * 1.5 的占比（可调整，但要写死规则）
- 发布频率：近 30/90 天发片数
- 互动率（可选）：(likes+comments)/views（若字段缺失则跳过并标注）
4) 输出创作者画像：受众/语言/地区的“可推断信息”（仅基于公开信息，不确定要标注）。

**输出必须包含**：
- `videos_table`：表格（CSV 或 Markdown 表，字段齐全）
- `creator_profile_summary`：≤200 字摘要
- `data_confidence`：高/中/低 + 原因
- `next_step_recommendation`：是否进入定价（YES/NO）

**失败分支**：
- 若无法抓到视频播放量等关键数据：说明原因，并给 2 个替代方案（如 YouTube Data API、第三方数据站、人工补充截图/导出）。

---

### B. 曝光合作报价计算（单视频付费 + 其他）

**任务名**：Pricing_For_Exposure_YouTube_Gaming

**提示词模板**：

- 输入：{creator_data_output}（来自上一步的表格与画像）
- 合作目标：曝光（Brand Awareness）
- 品类：{online_game|mobile_game|mihoyo_game}
- 交付形式（默认）：单条长视频整合口播/中插（可选 Shorts 作为加项）
- 我方预算区间：{budget_range}（可为空，但为空必须输出“需要预算假设”）
- 地区偏好（可选）：{target_region}
- 其他：可选加项（描述区链接、置顶评论、社区贴、Shorts、二次授权等）

**定价模型要求（必须可解释）**：
1) 以“近期稳定播放基线”作为核心：
- `baseline_views` = max(median_views, mean_views * 0.8)（你可提出更好规则，但必须写成明确公式）
2) 设定曝光 CPM 假设：
- 给出 `assumed_cpm_usd_range`（例如 8-25 USD/千次曝光，按地区/语言/游戏品类浮动）
- 若无法获得公开行情：必须写明“这是经验假设，需后续用对标修正”
3) 计算基础价格区间：
- `base_fee_range` = baseline_views/1000 * assumed_cpm_usd_range
4) 调整因子（写清楚加减逻辑与上限）：
- 内容匹配度 +0~20%
- 商单密度过高 -0~15%
- 爆款率高 +0~20%
- 交付权益增加（置顶评论/二次授权等）按固定加价表

**输出必须包含（报价卡）**：
- `anchor_price`（开价）
- `target_price`（目标成交）
- `floor_price`（底价）
- `deliverables`（交付清单）
- `add_on_menu`（加项与加价）
- `assumptions_and_risks`（关键假设与风险）

**“单视频付费 + 其他”的其他项（可选）**：
在报价卡里给出可选方案：
- `bonus_for_performance`：若 30 天播放超过 {X} 则奖励 {Y}
- `bundle_discount`：多条打包折扣
- `usage_rights_fee`：二次投放授权费用（使用期限/地区/媒体）

---

### C. 找联系方式（YouTube 特化）

**任务名**：Find_YouTube_Creator_Contact

**提示词模板**：

- 频道链接：{channel_url}
- 目标：找到“可用于商务合作的联系方式优先级列表”

**你要做的事**：
1) 依次检查：
- YouTube 频道 About（如可见）
- 视频描述区常见外链（Linktree、官网、Discord、X、Instagram）
- 频道置顶视频/置顶评论
- 经纪公司/MCN 信息
2) 输出联系方式候选列表（按可靠性排序）：
- email
- business inquiry form（官网表单）
- manager contact
- 社媒 DM 入口

**输出必须包含**：
- `contact_candidates`：数组，每条含 `type, value, source_url, confidence`
- `recommended_contact_path`：建议走哪条（以及原因）

**失败分支**：
- 若找不到任何可用联系方式：输出“人工兜底请求清单”（需要人提供什么）

---

### D. 首封合作邮件（曝光合作）

**任务名**：Outreach_Email_FirstTouch_YouTube_Gaming

**提示词模板**：

- 发件邮箱：cooperate@topuplive.com
- 收件人：{email}
- 创作者：{creator_name}
- 频道链接：{channel_url}
- 我方产品：{game_name}（若未定可用“某款手机游戏/网络游戏”）
- 合作目标：曝光
- 合作形式（默认）：长视频整合口播/中插 + 描述区链接 + 置顶评论（可按你实际调整）
- 报价策略（来自报价卡）：anchor/target/floor
- 个性化点：引用对方近期视频中与你产品/品类相近的内容表现（必须具体：视频标题/类型/数据亮点）

**输出要求**：
1) 邮件主题 3 个备选
2) 邮件正文（可直接发送，≤180 词英文为佳；如果你主要做中文受众，则输出中文版本+英文版本双份）
3) 清晰 CTA：
- 询问 media kit / rate card
- 提供 15 分钟通话时间
- 让对方回复“合作邮箱/经纪人”
4) 同步产出 `crm_record`（见下文 schema）

**注意**：
- 不要在首封里写死过多条款；核心是建立合作意向 + 下一步。

---

### E. 回复处理与谈判推进（含压价策略）

**任务名**：Negotiate_ReplyHandler

**提示词模板**：

- 输入：对方邮件原文：{raw_reply}
- 当前报价卡：{pricing_card}
- 当前阶段：{pipeline_stage}
- 预算硬限制（如有）：{budget_ceiling}

**规则**：
- 如果对方压价：必须给出两档方案（“降价换条件 / 维持价加权益”），并说明理由。
- 如果对方要素材/brief：进入 Brief 流程（下一任务）。
- 如果对方要数据证明：提供“我们基于你近期 median views 的估算逻辑”，不要编造第三方数据。
- 如果出现敏感条款（独家/永久授权/保证播放量）：标记 `NEED_HUMAN_APPROVAL=true`。

**输出必须包含**：
- 拟回复邮件正文
- 更新后的 `pipeline_stage`
- 下一次跟进时间（若需要）
- 风险与审批项列表

---

### F. 曝光合作 Brief + 素材对接（游戏品类）

**任务名**：Create_Brief_YouTube_Gaming_Awareness

**提示词模板**：

- 产品信息：{game_info}
- 卖点（3-5条）：{key_messages}
- 必须露出点：{must_include}
- 禁用词/合规要求：{restricted_claims}
- 落地页/下载链接：{landing_url}
- 跟踪参数（如 UTM）：{utm}
- 可提供素材包链接：{asset_pack_url}

**输出必须包含**（一份可直接发给创作者的 Brief）：
- 合作目标（Awareness）与成功标准（可量化但不承诺结果，例如：发布时间窗口、链接放置位置、品牌露出次数）
- 内容方向建议 3 条（贴近创作者风格）
- 交付规格：
  - 视频类型（长视频/Shorts）
  - 口播位置（开头/中插/结尾）
  - 描述区链接、置顶评论、屏幕覆盖元素（如有）
- 时间线：脚本/初稿/定稿/上线
- 审核机制：我方反馈时限、可修改次数
- 权益与素材清单（我方提供/创作者提供）
- 合规与禁区（尤其游戏类：不可夸大、不可虚假承诺、地区合规差异）

同时输出：
- 简短的素材对接邮件（附 brief 链接/附件说明）
- 文件命名规范（方便版本管理）

---

### G. 日报自动汇总（闭环收尾）

**任务名**：Daily_Report_Creator_Collab

**提示词模板**：

- 日期：{date}
- 输入：今日全部 `crm_record` 列表 + 已生成工件（报价卡/brief/邮件正文）

**输出**：《达人合作日报》（Markdown）
- 今日新增线索（名单+链接）
- 今日触达与回复（数量+关键对话摘要）
- 报价与谈判进度（按 pipeline_stage 分组）
- Brief/素材交付进度
- 风险与需审批
- 明日计划（达人-动作-时间）

---

## 4) 你需要给 Agent 的“工具接口契约”（不绑定具体框架）
为了让 agent 真正“自己去扒拉/发邮件/记录”，你需要在系统里提供这些工具（不一定现在就做完，但提示词要按这个契约写）：

- `web_fetch(url) -> html/text`：抓取网页（YouTube 页面/社媒/官网）
- `youtube_api.get_channel(channel_url) -> channel_stats`（可选）
- `youtube_api.list_videos(channel_id, N) -> video_list`
- `email.send(from, to, subject, body, attachments) -> message_id`
- `crm.upsert(record_json) -> record_id`
- `storage.save(file_name, content) -> file_url_or_path`

> 如果你暂时没有 YouTube API：也可以先“网页抓取 + 手工补充字段”，但提示词里要让 agent **明确标注缺失字段**。

---

## 5) 结构化输出 JSON Schema（建议）
下面是工件的最小结构（你可以直接用于数据库/Notion/表格字段）。

### 5.1 `CreatorProfile`
```json
{
  "creator_name": "string",
  "channel_url": "string",
  "language_guess": "string",
  "region_guess": "string",
  "content_focus": ["string"],
  "notes": "string",
  "data_confidence": "high|medium|low"
}
```

### 5.2 `VideoMetricsRow`
```json
{
  "video_url": "string",
  "title": "string",
  "publish_time": "string",
  "is_shorts": true,
  "duration_seconds": 0,
  "views": 0,
  "likes": 0,
  "comments": 0,
  "is_suspected_sponsored": true,
  "sponsor_evidence": "string"
}
```

### 5.3 `PricingCard`
```json
{
  "currency": "USD",
  "baseline_views": 0,
  "assumed_cpm_usd_range": [0, 0],
  "base_fee_range": [0, 0],
  "adjustments": [
    {"name": "string", "impact_pct": 0, "reason": "string"}
  ],
  "anchor_price": 0,
  "target_price": 0,
  "floor_price": 0,
  "deliverables": ["string"],
  "add_on_menu": [
    {"item": "string", "price": 0, "notes": "string"}
  ],
  "other_terms": {
    "bonus_for_performance": "string",
    "bundle_discount": "string",
    "usage_rights_fee": "string"
  },
  "assumptions_and_risks": ["string"]
}
```

### 5.4 `OutreachEmailDraft`
```json
{
  "from": "cooperate@topuplive.com",
  "to": "string",
  "subject_options": ["string"],
  "body": "string",
  "cta": "string",
  "language": "en|zh|bilingual"
}
```

### 5.5 `CRMRecord`
```json
{
  "timestamp": "string",
  "creator_name": "string",
  "channel_url": "string",
  "pipeline_stage": "string",
  "action": "string",
  "result": "string",
  "next_step": "string",
  "next_follow_up_time": "string",
  "artifacts": [
    {"type": "videos_table|pricing_card|email|brief|report", "ref": "string"}
  ],
  "need_human_approval": false,
  "approval_reason": "string"
}
```

### 5.6 `DailyReport`
```json
{
  "date": "string",
  "summary": "string",
  "new_leads": [{"creator_name": "string", "channel_url": "string"}],
  "outreach": {"sent": 0, "replied": 0},
  "pipeline_breakdown": [{"stage": "string", "count": 0, "items": ["string"]}],
  "risks": ["string"],
  "tomorrow_plan": [{"creator_name": "string", "action": "string", "time": "string"}]
}
```

---

## 6) 你接下来怎么用（最短路径）
1) 你先准备一个“线索表”（哪怕 5 个频道链接）。
2) 总控 agent 对每个频道跑：A（数据）→ B（定价）→ C（找联系方式）→ D（首封）
3) 有回复就走 E（谈判）→ F（Brief）
4) 每天最后跑 G（日报）