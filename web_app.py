"""
YouTube网红曝光合作系统 - Web界面
使用Flask构建的可视化操作界面

运行方式:
    python web_app.py
    
然后访问: http://localhost:5000
"""
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List

# 加载.env文件
from pathlib import Path
env_path = Path('.') / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# 导入系统组件
from src.config import get_config, reload_config
from src.core import (
    AgentOrchestrator, PipelineContext, PipelineStage,
    DataCollectionAgent, PricingAgent, ContactFindingAgent,
    OutreachAgent, NegotiationAgent, BriefAgent,
    ContactRefreshAgent, EmailSequenceManager
)
from src.tools import YouTubeAPITool, EmailTool, CRMStorage
from src.tools.email_validator import EmailValidator

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)

# 全局状态
orchestrator = AgentOrchestrator()
active_leads: Dict[str, PipelineContext] = {}
config = get_config()
email_sequence_manager = EmailSequenceManager()
email_validator = EmailValidator()

# 初始化工具
youtube_api = None
email_tool = None
llm_tool = None

if config.youtube_api.api_key:
    youtube_api = YouTubeAPITool(config.youtube_api.api_key)

# 邮件工具初始化 - 优先使用环境变量
email_sender = os.getenv("EMAIL_SENDER")
email_password = os.getenv("EMAIL_PASSWORD")
email_smtp_host = os.getenv("EMAIL_SMTP_HOST")
email_smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
sendgrid_api_key = os.getenv("SENDGRID_API_KEY")

# 调试日志
print(f"[Email Config] SENDGRID_API_KEY: {'已设置' if sendgrid_api_key else '未设置'}")
print(f"[Email Config] EMAIL_SENDER: {email_sender or '未设置'}")

if sendgrid_api_key and email_sender:
    # 优先使用 SendGrid（避免Railway端口限制）
    email_tool = EmailTool(
        sendgrid_api_key=sendgrid_api_key,
        mock_mode=False
    )
    print(f"✓ 邮件工具: SendGrid 已配置 ({email_sender})")
elif email_sender and email_password and email_smtp_host:
    # 使用 SMTP 配置
    email_tool = EmailTool(
        smtp_host=email_smtp_host,
        smtp_port=email_smtp_port,
        smtp_user=email_sender,
        smtp_password=email_password,
        mock_mode=False
    )
    print(f"✓ 邮件工具: SMTP 已配置 ({email_sender})")
elif config.email.mode == "smtp" and config.email.smtp.user:
    email_tool = EmailTool(
        smtp_host=config.email.smtp.host,
        smtp_port=config.email.smtp.port,
        smtp_user=config.email.smtp.user,
        smtp_password=config.email.smtp.password,
        mock_mode=False
    )
    print(f"✓ 邮件工具: SMTP 已配置 ({config.email.smtp.user})")
else:
    email_tool = EmailTool(mock_mode=True)
    print("✓ 邮件工具: 模拟模式")

# 初始化LLM
from src.tools.llm import LLMTool

# 检测LLM配置优先级：环境变量 > config.yaml
llm_provider = os.getenv("LLM_PROVIDER", "openai")  # 默认openai
llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("ALIBABA_BAILIAN_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
llm_model = os.getenv("LLM_MODEL")
llm_base_url = os.getenv("LLM_BASE_URL")

if llm_api_key:
    llm_tool = LLMTool(
        provider=llm_provider,
        api_key=llm_api_key,
        model=llm_model,
        base_url=llm_base_url
    )
else:
    llm_tool = LLMTool()  # 尝试从环境变量自动检测


# ============================================
# 路由定义
# ============================================

@app.route("/")
def index():
    """首页 - Dashboard"""
    # 统计信息
    stats = {
        "total_leads": len(active_leads),
        "by_stage": {},
        "api_configured": youtube_api is not None and youtube_api.is_available(),
        "email_configured": email_tool is not None,
        "llm_configured": llm_tool is not None and llm_tool.is_available()
    }
    
    # 按阶段统计
    for stage in PipelineStage:
        stats["by_stage"][stage.value] = 0
    
    for ctx in active_leads.values():
        stage = ctx.current_stage.value
        stats["by_stage"][stage] = stats["by_stage"].get(stage, 0) + 1
    
    return render_template("index.html", stats=stats, config=config)


@app.route("/leads")
def leads():
    """线索列表页 - 卡片式展示"""
    leads_list = []
    
    for url, ctx in active_leads.items():
        # 从creator_profile提取更多信息
        profile = ctx.creator_profile or {}
        
        # 格式化订阅数显示
        sub_count = profile.get('subscriber_count', 0)
        if sub_count >= 10000:
            sub_display = f"{sub_count/10000:.1f}万"
        else:
            sub_display = f"{sub_count:,}" if sub_count else None
        
        # 格式化视频数
        video_count = profile.get('video_count', 0)
        video_display = f"{video_count:,}" if video_count else None
        
        # 格式化平均播放量
        baseline = profile.get('baseline_views', 0)
        if baseline >= 10000:
            avg_display = f"{baseline/10000:.1f}万"
        else:
            avg_display = f"{baseline:,}" if baseline else None
        
        # 构建社交链接列表
        social_links = []
        
        # YouTube主链接
        social_links.append({
            "type": "youtube",
            "label": "YouTube",
            "url": ctx.channel_url
        })
        
        # 优先使用About页面的链接
        about_links = profile.get('about_links', [])
        for link in about_links[:4]:  # 最多显示4个About链接
            link_type = link.get('type', 'website')
            link_url = link.get('url', '')
            link_title = link.get('title', '')
            
            # 根据类型设置标签
            if link_type == 'twitter':
                label = "X"
            elif link_type == 'instagram':
                label = "Instagram"
            elif link_type == 'twitch':
                label = "Twitch"
            elif link_type == 'discord':
                label = "Discord"
            elif link_type == 'tiktok':
                label = "TikTok"
            elif link_type == 'linktree':
                label = "Linktree"
            else:
                # 使用标题或简化URL
                label = link_title[:15] if link_title else link_url.split('/')[2][:15] if '/' in link_url else "链接"
            
            social_links.append({
                "type": link_type,
                "label": label,
                "url": link_url
            })
        
        # 从contact_candidates补充其他社交链接
        for contact in ctx.contact_candidates:
            contact_type = contact.get('type', '')
            contact_value = contact.get('value', '')
            
            if contact_type == 'social_dm':
                if 'twitter.com' in contact_value or 'x.com' in contact_value:
                    # 检查是否已存在
                    if not any(s['type'] == 'twitter' for s in social_links):
                        social_links.append({
                            "type": "twitter",
                            "label": "X",
                            "url": contact_value
                        })
                elif 'twitch.tv' in contact_value:
                    if not any(s['type'] == 'twitch' for s in social_links):
                        social_links.append({
                            "type": "twitch",
                            "label": "Twitch",
                            "url": contact_value
                        })
                elif 'discord' in contact_value:
                    if not any(s['type'] == 'discord' for s in social_links):
                        social_links.append({
                            "type": "discord",
                            "label": "Discord",
                            "url": contact_value
                        })
            elif contact_type in ['business_email', 'email']:
                if not any(s['type'] == 'email' for s in social_links):
                    social_links.append({
                        "type": "email",
                        "label": "邮箱",
                        "url": f"mailto:{contact_value}"
                    })
        
        # 游戏焦点标签
        game_focus = []
        content_focus = profile.get('content_focus', [])
        if content_focus:
            game_focus = content_focus[:3]
        
        leads_list.append({
            "channel_url": url,
            "creator_name": ctx.creator_name,
            "custom_url": profile.get('custom_url', ''),
            "thumbnail": profile.get('thumbnail'),
            "current_stage": ctx.current_stage.value,
            "stage_display": get_stage_display(ctx.current_stage),
            "data_confidence": ctx.data_confidence,
            "created_at": ctx.created_at.strftime("%Y-%m-%d %H:%M"),
            "has_pricing": ctx.pricing_card is not None,
            "has_contact": ctx.recommended_contact is not None,
            # 新增字段
            "subscriber_display": sub_display,
            "video_count_display": video_display,
            "avg_views_display": avg_display,
            "country": profile.get('country'),
            "game_focus": game_focus,
            "sponsor_status": "合作达人" if ctx.pricing_card else None,
            "social_links": social_links
        })
    
    # 按创建时间倒序
    leads_list.sort(key=lambda x: x["created_at"], reverse=True)
    
    return render_template("leads.html", leads=leads_list, stages=PipelineStage)


@app.route("/leads/new", methods=["GET", "POST"])
def new_lead():
    """创建新线索"""
    if request.method == "POST":
        channel_url = request.form.get("channel_url", "").strip()
        creator_name = request.form.get("creator_name", "").strip()
        
        if not channel_url:
            flash("请输入频道URL", "error")
            return redirect(url_for("new_lead"))
        
        if not channel_url.startswith("https://www.youtube.com/"):
            flash("请输入有效的YouTube频道URL", "error")
            return redirect(url_for("new_lead"))
        
        # 创建线索
        ctx = orchestrator.create_lead(channel_url, creator_name)
        active_leads[channel_url] = ctx
        
        flash(f"线索已创建: {ctx.creator_name}", "success")
        
        # 如果配置了API，自动执行数据采集
        if youtube_api and youtube_api.is_available():
            return redirect(url_for("collect_data", channel_url=channel_url))
        
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    return render_template("new_lead.html")


@app.route("/leads/<path:channel_url>")
def lead_detail(channel_url):
    """线索详情页"""
    ctx = active_leads.get(channel_url)
    
    if not ctx:
        flash("线索不存在", "error")
        return redirect(url_for("leads"))
    
    # 获取邮件工具状态
    email_mock_mode = True
    if email_tool:
        stats = email_tool.get_stats()
        email_mock_mode = stats.get("mock_mode", True)
    
    # 准备展示数据
    data = {
        "context": ctx,
        "stage_display": get_stage_display(ctx.current_stage),
        "stage_history": ctx.stage_history,
        "creator_profile": ctx.creator_profile or {},
        "pricing_card": ctx.pricing_card or {},
        "contact_candidates": ctx.contact_candidates or [],
        "recommended_contact": ctx.recommended_contact or None,
        "email_history": ctx.email_history or [],
        "negotiation_log": ctx.negotiation_log or [],
        "brief_data": ctx.brief_data or {},
        "available_actions": get_available_actions(ctx),
        "email_mock_mode": email_mock_mode
    }
    
    return render_template("lead_detail.html", **data)


@app.route("/leads/<path:channel_url>/collect", methods=["POST"])
def collect_data(channel_url):
    """执行数据采集"""
    ctx = active_leads.get(channel_url)
    
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    if not youtube_api or not youtube_api.is_available():
        flash("YouTube API未配置", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    # 执行数据采集
    agent = DataCollectionAgent(config.youtube_api.api_key)
    result = agent.execute(ctx, video_count=30)
    
    if result["status"] == "success":
        flash(f"数据采集完成: {result.get('data_confidence')} 置信度", "success")
    else:
        flash(f"数据采集失败: {result.get('message')}", "error")
    
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/price", methods=["POST"])
def calculate_price(channel_url):
    """计算报价"""
    ctx = active_leads.get(channel_url)
    
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    if not ctx.creator_profile:
        flash("请先执行数据采集", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    game_category = request.form.get("game_category", "mobile_game")
    
    # 执行报价计算
    agent = PricingAgent()
    result = agent.execute(ctx, game_category=game_category)
    
    if result["status"] == "success":
        flash(f"报价计算完成: ${result['pricing_card']['target_price']}", "success")
    else:
        flash(f"报价计算失败: {result.get('message')}", "error")
    
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/find_contact", methods=["POST"])
def find_contact(channel_url):
    """查找联系方式"""
    ctx = active_leads.get(channel_url)
    
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    # 执行联系方式查找
    agent = ContactFindingAgent()
    result = agent.execute(ctx)
    
    if result["status"] == "success":
        contact = result.get("recommended_contact", {})
        flash(f"找到联系方式: {contact.get('value', 'Unknown')}", "success")
    else:
        flash(f"查找联系方式失败: {result.get('message')}", "error")
    
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/compose_email", methods=["GET", "POST"])
def compose_email(channel_url):
    """撰写邮件 - 预览和编辑页面"""
    ctx = active_leads.get(channel_url)
    
    if not ctx:
        flash("线索不存在", "error")
        return redirect(url_for("leads"))
    
    if not ctx.recommended_contact:
        flash("请先查找联系方式", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    if not email_tool:
        flash("邮件工具未配置", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    # 检查邮件工具是否处于模拟模式
    email_stats = email_tool.get_stats()
    is_mock_mode = email_stats.get("mock_mode", True)
    
    if request.method == "POST":
        # 实际发送邮件
        subject = request.form.get("subject", "")
        body = request.form.get("body", "")
        to_addr = ctx.recommended_contact.get("value")
        
        if not subject or not body:
            flash("邮件主题和正文不能为空", "error")
            return redirect(url_for("compose_email", channel_url=channel_url))
        
        send_result = email_tool.send_outreach_email(
            to_addr=to_addr,
            creator_name=ctx.creator_name,
            subject=subject,
            body=body
        )
        
        if send_result["status"] == "success":
            # 更新状态（如果当前状态允许流转到 OUTREACH_SENT）
            from src.core.pipeline import PipelineEngine, PipelineStage
            engine = PipelineEngine(ctx)
            if engine.can_transition_to(PipelineStage.OUTREACH_SENT):
                engine.transition(PipelineStage.OUTREACH_SENT, "已发送首封合作邮件")
            else:
                # 记录邮件历史但不改变状态（允许重复发送）
                ctx.email_history.append({
                    "type": "outbound",
                    "to": to_addr,
                    "subject": subject,
                    "sent_at": datetime.now().isoformat(),
                    "note": "重复发送或跟进邮件"
                })
            
            if send_result.get("mock"):
                flash(f"【模拟模式】邮件已记录（未实际发送）。请在控制台查看邮件内容。", "success")
            else:
                flash(f"邮件发送成功! ID: {send_result.get('message_id')}", "success")
        else:
            flash(f"邮件发送失败: {send_result.get('error')}", "error")
        
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    # GET 请求：显示邮件撰写页面
    game_name = request.args.get("game_name", "Our Game")
    template = request.args.get("template", "standard")
    
    # 生成邮件草稿
    agent = OutreachAgent()
    result = agent.execute(ctx, game_name=game_name, template_type=template)
    
    if result["status"] != "success":
        flash(f"邮件生成失败: {result.get('message')}", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    email_draft = result.get("email_draft", {})
    
    return render_template("compose_email.html",
                         context=ctx,
                         email_draft=email_draft,
                         recipient=ctx.recommended_contact,
                         is_mock_mode=is_mock_mode,
                         email_stats=email_stats)


@app.route("/leads/<path:channel_url>/send_email", methods=["POST"])
def send_email(channel_url):
    """发送合作邮件（旧接口，重定向到新页面）"""
    game_name = request.form.get("game_name", "Our Game")
    use_email = request.form.get("use_email", "")
    
    # 如果指定了邮箱，先设置为推荐联系方式
    if use_email:
        ctx = active_leads.get(channel_url)
        if ctx:
            # 检查是否已存在该联系方式
            existing = [c for c in ctx.contact_candidates if c.get("value") == use_email]
            if not existing:
                ctx.contact_candidates.append({
                    "type": "business_email",
                    "value": use_email,
                    "source": "about_page",
                    "confidence": 0.9,
                    "notes": "From channel About section"
                })
            # 设置为推荐联系方式
            ctx.recommended_contact = {
                "type": "business_email",
                "value": use_email,
                "source": "about_page",
                "confidence": 0.9
            }
    
    return redirect(url_for("compose_email", channel_url=channel_url, game_name=game_name))


@app.route("/leads/<path:channel_url>/handle_reply", methods=["POST"])
def handle_reply(channel_url):
    """处理收到的回复"""
    ctx = active_leads.get(channel_url)
    
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    raw_reply = request.form.get("raw_reply", "").strip()
    
    if not raw_reply:
        flash("请输入回复内容", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    # 执行谈判处理
    agent = NegotiationAgent()
    result = agent.execute(ctx, raw_reply=raw_reply)
    
    if result["status"] == "success":
        reply_type = result.get("reply_type", "unknown")
        flash(f"回复处理完成: {reply_type}", "success")
    else:
        flash(f"回复处理失败: {result.get('message')}", "error")
    
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/record_attempt", methods=["POST"])
def record_contact_attempt(channel_url):
    """记录一次联系尝试"""
    ctx = active_leads.get(channel_url)
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    channel = request.form.get("channel", "")  # email / twitter / discord 等
    to_value = request.form.get("to_value", "")
    content_note = request.form.get("content_note", "")
    
    if not channel or not to_value:
        flash("请填写联系渠道和联系方式", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    # 如果是邮箱类型，自动添加到 contact_candidates 并设为推荐联系方式
    if channel == "email" and "@" in to_value:
        # 检查是否已存在
        existing = [c for c in ctx.contact_candidates if c.get("value") == to_value]
        if not existing:
            ctx.contact_candidates.append({
                "type": "business_email",
                "value": to_value,
                "source": "manual_record",
                "confidence": 0.85,
                "notes": content_note or "Manually recorded"
            })
        # 设置为推荐联系方式
        ctx.recommended_contact = {
            "type": "business_email",
            "value": to_value,
            "source": "manual_record",
            "confidence": 0.85
        }
    
    attempt = {
        "id": f"attempt_{len(ctx.contact_attempts) + 1}",
        "channel": channel,
        "to": to_value,
        "content_note": content_note,
        "sent_at": datetime.now().isoformat(),
        "status": "sent",   # sent / opened / replied / failed
        "reply_received": False
    }
    ctx.contact_attempts.append(attempt)
    ctx.updated_at = datetime.now()
    
    flash(f"已记录联系尝试: {channel} → {to_value}", "success")
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/update_attempt_status", methods=["POST"])
def update_attempt_status(channel_url):
    """更新联系尝试状态（已回复/已读等）"""
    ctx = active_leads.get(channel_url)
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    attempt_id = request.form.get("attempt_id", "")
    new_status = request.form.get("status", "")
    
    for attempt in ctx.contact_attempts:
        if attempt.get("id") == attempt_id:
            attempt["status"] = new_status
            attempt["updated_at"] = datetime.now().isoformat()
            if new_status == "replied":
                attempt["reply_received"] = True
                attempt["replied_at"] = datetime.now().isoformat()
                # 自动停止邮件序列
                email_sequence_manager.stop_sequence(ctx, "收到回复，序列停止")
            break
    
    return jsonify({"status": "success", "message": "状态已更新"})


@app.route("/api/validate_email", methods=["POST"])
def api_validate_email():
    """API: 验证邮箱有效性"""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    deep = data.get("deep", False)
    
    if not email:
        return jsonify({"status": "error", "message": "请提供邮箱地址"})
    
    result = email_validator.validate(email, deep=deep)
    return jsonify({"status": "success", "result": result})


@app.route("/leads/<path:channel_url>/validate_contacts", methods=["POST"])
def validate_contacts(channel_url):
    """验证线索的所有邮箱联系方式"""
    ctx = active_leads.get(channel_url)
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    validated_count = 0
    for contact in ctx.contact_candidates:
        if contact.get("type") in ["email", "business_email"]:
            email = contact.get("value", "")
            if email:
                val_result = email_validator.validate(email)
                contact["validation"] = val_result
                contact["confidence"] = min(
                    contact.get("confidence", 0.5) * 0.5 + val_result["score"] * 0.5, 1.0
                )
                validated_count += 1
    
    # 记录验证时间
    if not ctx.contact_verification:
        ctx.contact_verification = {}
    ctx.contact_verification["last_email_validation"] = datetime.now().isoformat()
    ctx.contact_verification["validated_count"] = validated_count
    
    flash(f"已验证 {validated_count} 个邮箱地址", "success")
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/refresh_contacts", methods=["POST"])
def refresh_contacts(channel_url):
    """刷新联系方式"""
    ctx = active_leads.get(channel_url)
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    force = request.form.get("force", "false").lower() == "true"
    agent = ContactRefreshAgent()
    result = agent.execute(ctx, force=force, validate_emails=True)
    
    if result["status"] == "success":
        changes = result.get("changes", {})
        added = len(changes.get("added", []))
        removed = len(changes.get("removed", []))
        flash(f"联系方式已刷新: 新增{added}个, 移除{removed}个", "success")
    elif result["status"] == "skipped":
        flash(result.get("message", "联系方式无需刷新"), "info")
    else:
        flash(f"刷新失败: {result.get('message')}", "error")
    
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/start_sequence", methods=["POST"])
def start_email_sequence(channel_url):
    """启动邮件跟进序列"""
    ctx = active_leads.get(channel_url)
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    game_name = request.form.get("game_name", "Our Game")
    anchor_price = int(request.form.get("anchor_price", 1000))
    
    result = email_sequence_manager.start_sequence(ctx, game_name, anchor_price)
    flash(f"邮件跟进序列已启动，将在3天/7天/14天自动跟进", "success")
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/leads/<path:channel_url>/send_followup", methods=["POST"])
def send_followup_email(channel_url):
    """发送跟进邮件"""
    ctx = active_leads.get(channel_url)
    if not ctx:
        return jsonify({"status": "error", "message": "线索不存在"})
    
    if not ctx.email_sequence:
        flash("请先启动邮件序列", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    # 检查是否有手动输入的邮箱
    manual_email = request.form.get("manual_email", "").strip()
    if manual_email:
        # 使用手动输入的邮箱作为推荐联系方式
        ctx.recommended_contact = {
            "type": "business_email",
            "value": manual_email,
            "source": "manual_input",
            "confidence": 0.8
        }
        # 同时添加到联系候选人列表
        existing = [c for c in ctx.contact_candidates if c.get("value") == manual_email]
        if not existing:
            ctx.contact_candidates.append({
                "type": "business_email",
                "value": manual_email,
                "source": "manual_input",
                "confidence": 0.8,
                "notes": "Manually entered for follow-up"
            })
    
    if not ctx.recommended_contact:
        flash("未找到联系方式，请手动输入邮箱", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    seq = ctx.email_sequence
    current_step_idx = seq.get("current_step", 0)
    
    if current_step_idx >= len(email_sequence_manager.SEQUENCE_STEPS):
        flash("邮件序列已全部发送完毕", "info")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    step_info = email_sequence_manager.SEQUENCE_STEPS[current_step_idx]
    email_result = email_sequence_manager.generate_follow_up_email(
        ctx, step_info,
        game_name=seq.get("game_name", "Our Game"),
        anchor_price=seq.get("anchor_price", 1000)
    )
    
    if email_result.get("status") != "success":
        flash("跟进邮件生成失败", "error")
        return redirect(url_for("lead_detail", channel_url=channel_url))
    
    email_draft = email_result.get("email_draft", {})
    
    # 发送邮件
    to_addr = ctx.recommended_contact.get("value", "")
    if email_tool and to_addr:
        send_result = email_tool.send_outreach_email(
            to_addr=to_addr,
            creator_name=ctx.creator_name,
            subject=email_draft.get("subject", ""),
            body=email_draft.get("body", "")
        )
        
        if send_result.get("status") == "success":
            # 记录到邮件历史
            ctx.email_history.append({
                "type": "follow_up",
                "step": step_info["name"],
                "description": step_info["description"],
                "subject": email_draft.get("subject", ""),
                "to_addr": to_addr,
                "sent_at": datetime.now().isoformat()
            })
            # 记录联系尝试
            ctx.contact_attempts.append({
                "id": f"attempt_{len(ctx.contact_attempts) + 1}",
                "channel": "email",
                "to": to_addr,
                "content_note": f"跟进邮件: {step_info['description']}",
                "sent_at": datetime.now().isoformat(),
                "status": "sent",
                "reply_received": False
            })
            # 推进序列
            email_sequence_manager.advance_sequence(ctx)
            flash(f"跟进邮件已发送: {step_info['description']}", "success")
        else:
            flash(f"邮件发送失败: {send_result.get('error')}", "error")
    else:
        flash("邮件工具未配置或联系方式无效", "error")
    
    return redirect(url_for("lead_detail", channel_url=channel_url))


@app.route("/api/contact_stats")
def api_contact_stats():
    """API: 联系成功率统计"""
    stats = {
        "total_leads": len(active_leads),
        "total_attempts": 0,
        "by_channel": {},
        "reply_rate_overall": 0.0,
        "leads_with_contact": 0,
        "leads_replied": 0,
        "top_performing_stage": None,
        "avg_attempts_before_reply": 0.0
    }
    
    all_attempts = []
    replied_leads = 0
    leads_with_contact = 0
    
    for ctx in active_leads.values():
        attempts = ctx.contact_attempts or []
        all_attempts.extend(attempts)
        
        if ctx.contact_candidates:
            leads_with_contact += 1
        
        has_reply = any(a.get("reply_received") for a in attempts)
        if has_reply:
            replied_leads += 1
    
    stats["total_attempts"] = len(all_attempts)
    stats["leads_with_contact"] = leads_with_contact
    stats["leads_replied"] = replied_leads
    
    if leads_with_contact > 0:
        stats["reply_rate_overall"] = round(replied_leads / leads_with_contact, 3)
    
    # 按渠道统计
    channel_data = {}
    for attempt in all_attempts:
        ch = attempt.get("channel", "unknown")
        if ch not in channel_data:
            channel_data[ch] = {"sent": 0, "replied": 0}
        channel_data[ch]["sent"] += 1
        if attempt.get("reply_received"):
            channel_data[ch]["replied"] += 1
    
    for ch, data in channel_data.items():
        data["reply_rate"] = round(data["replied"] / data["sent"], 3) if data["sent"] > 0 else 0
    
    stats["by_channel"] = channel_data
    
    # 最佳渠道
    if channel_data:
        best_channel = max(channel_data, key=lambda c: channel_data[c].get("reply_rate", 0))
        stats["top_channel"] = best_channel
    
    return jsonify({"status": "success", "data": stats})


@app.route("/api/followup_queue")
def api_followup_queue():
    """API: 获取待跟进的线索队列"""
    pending = email_sequence_manager.get_pending_follow_ups(list(active_leads.values()))
    
    queue = []
    for item in pending:
        ctx = item["context"]
        queue.append({
            "creator_name": ctx.creator_name,
            "channel_url": ctx.channel_url,
            "step": item["step"]["description"],
            "step_name": item["step"]["name"],
            "game_name": item["game_name"],
            "overdue_hours": round(item["overdue_hours"], 1),
            "send_url": f"/leads/{ctx.channel_url}/send_followup"
        })
    
    return jsonify({"status": "success", "data": queue, "count": len(queue)})


@app.route("/search", methods=["GET", "POST"])
def search_creators():
    """YouTube创作者搜索 - 支持筛选和排序"""
    results = []
    query = ""
    min_subscribers = 0
    max_results = 20
    country = ""
    language = ""
    
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        min_subs = request.form.get("min_subscribers", "0")
        max_res = request.form.get("max_results", "20")
        country = request.form.get("country", "")
        language = request.form.get("language", "")
        
        if not query:
            flash("请输入搜索关键词", "error")
            return redirect(url_for("search_creators"))
        
        if not youtube_api or not youtube_api.is_available():
            flash("YouTube API未配置，无法搜索", "error")
            return redirect(url_for("search_creators"))
        
        try:
            min_subscriber_count = int(min_subs) if min_subs else 0
            max_results_count = int(max_res) if max_res else 20
            # 限制在20-50范围内
            max_results_count = max(20, min(50, max_results_count))
            
            min_subscribers = min_subscriber_count
            max_results = max_results_count
            
            # 调用API搜索
            results = youtube_api.search_creators(
                query=query,
                max_results=max_results_count,
                min_subscriber_count=min_subscriber_count if min_subscriber_count > 0 else None
            )
            
            # 按订阅数从高到低排序
            results.sort(key=lambda x: x.get("subscriber_count", 0), reverse=True)
            
            # 根据国家筛选
            if country:
                if country == "OTHER":
                    # 排除主要国家
                    major_countries = ["US", "GB", "CA", "AU", "DE", "FR", "JP", "KR", "CN", "TW", "HK", "SG", "IN", "BR", "MX", "ES", "IT", "NL", "RU"]
                    results = [r for r in results if r.get("country") not in major_countries]
                else:
                    results = [r for r in results if r.get("country") == country]
            
            # 根据语言筛选（通过关键词匹配）
            if language:
                lang_keywords = {
                    "en": ["english", "eng"],
                    "zh": ["chinese", "中文", "china"],
                    "ja": ["japanese", "日本語", "japan"],
                    "ko": ["korean", "한국어", "korea"],
                    "es": ["spanish", "español", "spain"],
                    "fr": ["french", "français", "france"],
                    "de": ["german", "deutsch", "germany"],
                    "pt": ["portuguese", "português", "brazil"],
                    "ru": ["russian", "русский", "russia"],
                    "it": ["italian", "italiano", "italy"],
                    "ar": ["arabic", "العربية"],
                    "hi": ["hindi", "हिन्दी", "india"]
                }
                keywords = lang_keywords.get(language, [language])
                # 这里简化处理，实际应该分析频道内容
                # 目前通过标题和描述中的关键词判断
            
            # 格式化订阅数显示
            for creator in results:
                sub_count = creator.get("subscriber_count", 0)
                if sub_count >= 10000:
                    creator["subscriber_display"] = f"{sub_count/10000:.1f}万"
                else:
                    creator["subscriber_display"] = f"{sub_count:,}"
            
            flash(f"找到 {len(results)} 个创作者", "success")
        except Exception as e:
            flash(f"搜索失败: {str(e)}", "error")
    
    return render_template("search.html", results=results, query=query, 
                          min_subscribers=min_subscribers, max_results=max_results,
                          country=country, language=language)


@app.route("/search/add/<channel_id>", methods=["POST"])
def add_from_search(channel_id):
    """从搜索结果添加单个线索"""
    channel_url = request.form.get("channel_url", "")
    channel_title = request.form.get("channel_title", "")
    
    if not channel_url:
        flash("无效的频道信息", "error")
        return redirect(url_for("search_creators"))
    
    # 创建线索
    ctx = orchestrator.create_lead(channel_url, channel_title)
    active_leads[channel_url] = ctx
    
    flash(f"已添加: {channel_title}", "success")
    
    # 如果配置了API，自动执行数据采集
    if youtube_api and youtube_api.is_available():
        return redirect(url_for("collect_data", channel_url=channel_url))
    
    return redirect(url_for("search_creators"))


@app.route("/search/batch_add", methods=["POST"])
def batch_add_from_search():
    """批量添加搜索结果为线索"""
    selected_creators = request.form.getlist("selected_creators")
    
    if not selected_creators:
        flash("请先选择要添加的创作者", "error")
        return redirect(url_for("search_creators"))
    
    added_count = 0
    failed_count = 0
    
    for channel_id in selected_creators:
        channel_url = request.form.get(f"creator_data_{channel_id}_url", "")
        channel_title = request.form.get(f"creator_data_{channel_id}_title", "")
        
        if not channel_url:
            failed_count += 1
            continue
        
        try:
            # 创建线索
            ctx = orchestrator.create_lead(channel_url, channel_title)
            active_leads[channel_url] = ctx
            added_count += 1
            
            # 异步执行数据采集（不阻塞页面）
            if youtube_api and youtube_api.is_available():
                # 使用线程池异步执行
                import threading
                def auto_collect():
                    try:
                        orchestrator.run_pipeline(ctx, until_stage=PipelineStage.CONTACT_FINDING)
                    except Exception:
                        pass
                
                thread = threading.Thread(target=auto_collect)
                thread.daemon = True
                thread.start()
                
        except Exception as e:
            failed_count += 1
            print(f"添加 {channel_title} 失败: {e}")
    
    if added_count > 0:
        flash(f"成功添加 {added_count} 个创作者到线索", "success")
    if failed_count > 0:
        flash(f"{failed_count} 个创作者添加失败", "error")
    
    return redirect(url_for("leads"))


@app.route("/api/leads")
def api_leads():
    """API: 获取线索列表"""
    leads_list = []
    
    for url, ctx in active_leads.items():
        leads_list.append({
            "channel_url": url,
            "creator_name": ctx.creator_name,
            "current_stage": ctx.current_stage.value,
            "data_confidence": ctx.data_confidence,
            "created_at": ctx.created_at.isoformat()
        })
    
    return jsonify({"status": "success", "data": leads_list})


@app.route("/api/stats")
def api_stats():
    """API: 获取统计数据"""
    stats = {
        "total_leads": len(active_leads),
        "by_stage": {},
        "api_status": {
            "youtube": youtube_api is not None and youtube_api.is_available(),
            "email": email_tool is not None
        }
    }
    
    for stage in PipelineStage:
        stats["by_stage"][stage.value] = 0
    
    for ctx in active_leads.values():
        stage = ctx.current_stage.value
        stats["by_stage"][stage] = stats["by_stage"].get(stage, 0) + 1
    
    return jsonify({"status": "success", "data": stats})


@app.route("/email-tools")
def email_tools():
    """邮件工具页面 - 邮件话术模板库"""
    return render_template("email_tools.html")


@app.route("/settings")
def settings():
    """设置页面"""
    return render_template("settings.html", 
                         config=config,
                         llm_available=llm_tool.is_available() if llm_tool else False,
                         llm_provider=llm_tool.provider if llm_tool else "N/A",
                         llm_model=llm_tool.model if llm_tool else "N/A")


# ============================================
# 辅助函数
# ============================================

def get_stage_display(stage: PipelineStage) -> str:
    """获取阶段显示名称"""
    stage_names = {
        PipelineStage.LEAD_COLLECTED: "📝 已收集",
        PipelineStage.DATA_COLLECTING: "📊 采集中",
        PipelineStage.DATA_READY: "✅ 数据就绪",
        PipelineStage.PRICING_DRAFTED: "💰 报价完成",
        PipelineStage.CONTACT_FINDING: "🔍 查找联系",
        PipelineStage.OUTREACH_SENT: "📧 已发送",
        PipelineStage.NEGOTIATING: "🤝 谈判中",
        PipelineStage.BRIEF_SENT: "📦 Brief已发",
        PipelineStage.SCHEDULE_CONFIRMED: "📅 排期确认",
        PipelineStage.DELIVERABLE_LIVE: "🎬 已上线",
        PipelineStage.WRAP_UP: "📋 验收中",
        PipelineStage.CLOSED_WON: "✨ 成交",
        PipelineStage.CLOSED_LOST: "❌ 未成交",
        PipelineStage.NEED_HUMAN_APPROVAL: "👤 需审批"
    }
    return stage_names.get(stage, stage.value)


def get_available_actions(ctx: PipelineContext) -> List[Dict]:
    """获取当前可用的操作"""
    actions = []
    stage = ctx.current_stage
    
    if stage == PipelineStage.LEAD_COLLECTED:
        if youtube_api and youtube_api.is_available():
            actions.append({
                "name": "collect_data",
                "label": "📊 数据采集",
                "url": f"/leads/{ctx.channel_url}/collect",
                "method": "POST"
            })
    
    elif stage == PipelineStage.DATA_READY:
        actions.append({
            "name": "calculate_price",
            "label": "💰 计算报价",
            "url": f"/leads/{ctx.channel_url}/price",
            "method": "POST"
        })
    
    elif stage == PipelineStage.PRICING_DRAFTED:
        actions.append({
            "name": "find_contact",
            "label": "🔍 查找联系方式",
            "url": f"/leads/{ctx.channel_url}/find_contact",
            "method": "POST"
        })
    
    elif stage == PipelineStage.CONTACT_FINDING:
        if ctx.recommended_contact and email_tool:
            actions.append({
                "name": "send_email",
                "label": "📧 发送邮件",
                "url": f"/leads/{ctx.channel_url}/send_email",
                "method": "POST"
            })
    
    # 如果已有联系方式，始终显示邮件发送选项（便于重新发送或测试）
    if ctx.recommended_contact and email_tool and stage.value not in ['outreach_sent', 'negotiating', 'brief_sent', 'schedule_confirmed', 'deliverable_live', 'wrap_up', 'closed_won', 'closed_lost']:
        # 检查是否已存在发送邮件操作
        existing_send = [a for a in actions if a['name'] == 'send_email']
        if not existing_send:
            actions.append({
                "name": "send_email",
                "label": "📧 发送合作邮件",
                "url": f"/leads/{ctx.channel_url}/send_email",
                "method": "POST"
            })

    if stage in [PipelineStage.OUTREACH_SENT, PipelineStage.NEGOTIATING]:
        actions.append({
            "name": "handle_reply",
            "label": "💬 处理回复",
            "url": f"/leads/{ctx.channel_url}/handle_reply",
            "method": "POST"
        })
    
    return actions


# ============================================
# 启动应用
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("YouTube网红曝光合作系统 - Web界面")
    print("=" * 80)
    print(f"\n访问地址: http://localhost:5000")
    print(f"按 Ctrl+C 停止服务\n")
    
    # 检查配置
    if youtube_api and youtube_api.is_available():
        print(f"✓ YouTube API: 已配置")
    else:
        print(f"⚠ YouTube API: 未配置")
    
    if email_tool:
        print(f"✓ 邮件工具: 已配置 ({config.email.mode})")
    else:
        print(f"⚠ 邮件工具: 未配置")
    
    print("=" * 80)
    
    app.run(host="0.0.0.0", port=5000, debug=True)
