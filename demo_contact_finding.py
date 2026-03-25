"""
联系方式查找Agent演示脚本
"""
from src.core import (
    AgentOrchestrator, PipelineContext, PipelineStage, 
    PipelineEngine, ContactFindingAgent
)


def demo_contact_finding():
    """演示联系方式查找流程"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 联系方式查找演示")
    print("=" * 80)
    
    # ========== 场景1: 成功找到联系方式 ==========
    print("\n" + "📧" * 20)
    print("场景1: 成功找到联系方式")
    print("📧" * 20)
    
    context = PipelineContext(
        channel_url="https://www.youtube.com/@GamingCreatorDemo",
        creator_name="Gaming Creator Demo"
    )
    
    # 设置创作者画像
    context.creator_profile = {
        "creator_name": "Gaming Creator Demo",
        "custom_url": "gamingcreatordemo",
        "language_guess": "en",
        "region_guess": "US"
    }
    
    # 模拟找到多个联系方式
    print("\n模拟找到以下联系方式：")
    
    mock_candidates = [
        {
            "type": "business_email",
            "value": "business@gamingcreatordemo.com",
            "source_url": "https://www.youtube.com/@GamingCreatorDemo/about",
            "confidence": 0.85,
            "notes": "从About页面提取的商务邮箱"
        },
        {
            "type": "linktree",
            "value": "https://linktr.ee/gamingcreatordemo",
            "source_url": "https://www.youtube.com/@GamingCreatorDemo/about",
            "confidence": 0.70,
            "notes": "Linktree链接，可能包含更多联系方式"
        },
        {
            "type": "email",
            "value": "contact@gamingcreatordemo.com",
            "source_url": "https://www.youtube.com/watch?v=video1",
            "confidence": 0.60,
            "notes": "从视频描述提取"
        },
        {
            "type": "social_dm",
            "value": "https://twitter.com/gamingcreatordemo",
            "source_url": "inferred",
            "confidence": 0.40,
            "notes": "基于频道handle推断的Twitter链接（需验证）"
        },
        {
            "type": "social_dm",
            "value": "https://instagram.com/gamingcreatordemo",
            "source_url": "inferred",
            "confidence": 0.40,
            "notes": "基于频道handle推断的Instagram链接（需验证）"
        }
    ]
    
    # 创建Agent并模拟执行
    agent = ContactFindingAgent()
    
    # 手动设置结果（实际使用时会真的去抓取）
    result = {
        "status": "success",
        "contact_candidates": mock_candidates,
        "recommended_contact": mock_candidates[0],  # 推荐商务邮箱
        "recommended_contact_path": "推荐使用商务邮箱联系（置信度85%），这是最直接的合作渠道；如未回复，可尝试linktree",
        "message": "找到5个联系方式"
    }
    
    # 更新Context
    context.contact_candidates = result["contact_candidates"]
    context.recommended_contact = result["recommended_contact"]
    
    print(f"\n✓ 联系方式查找完成")
    print(f"  找到 {len(result['contact_candidates'])} 个联系方式")
    
    print(f"\n📋 联系方式列表（按优先级排序）：")
    for i, contact in enumerate(result["contact_candidates"], 1):
        type_emoji = {
            "business_email": "💼",
            "email": "📧",
            "business_form": "📝",
            "manager_contact": "👔",
            "social_dm": "💬",
            "linktree": "🌲",
            "website": "🌐"
        }.get(contact["type"], "📧")
        
        print(f"\n  {i}. {type_emoji} {contact['type']}")
        print(f"     值: {contact['value']}")
        print(f"     置信度: {contact['confidence']:.0%}")
        print(f"     来源: {contact['source_url']}")
        print(f"     备注: {contact['notes']}")
    
    print(f"\n⭐ 推荐联系方式：")
    rec = result["recommended_contact"]
    print(f"  类型: {rec['type']}")
    print(f"  值: {rec['value']}")
    print(f"  置信度: {rec['confidence']:.0%}")
    
    print(f"\n📍 推荐路径：")
    print(f"  {result['recommended_contact_path']}")
    
    # ========== 场景2: 未找到联系方式 ==========
    print("\n" + "🔍" * 20)
    print("场景2: 未找到联系方式（需要人工介入）")
    print("🔍" * 20)
    
    context2 = PipelineContext(
        channel_url="https://www.youtube.com/@MysteryCreator",
        creator_name="Mystery Creator"
    )
    
    result2 = {
        "status": "success",
        "contact_candidates": [],
        "recommended_contact": None,
        "recommended_contact_path": "未找到可用联系方式",
        "message": "未找到任何联系方式",
        "needs_human_intervention": True,
        "manual_checklist": [
            "访问频道About页面手动查找",
            "检查视频描述区是否有Linktree链接",
            "通过Twitter/X私信联系",
            "通过Instagram DM联系",
            "查找创作者是否签约MCN/经纪公司",
            "使用第三方工具（如SocialBlade）查找联系信息"
        ]
    }
    
    print(f"\n⚠ {result2['message']}")
    print(f"\n需要人工介入，建议检查清单：")
    for i, item in enumerate(result2["manual_checklist"], 1):
        print(f"  {i}. {item}")
    
    # ========== 场景3: 在完整Pipeline中使用 ==========
    print("\n" + "🔄" * 20)
    print("场景3: 在完整Pipeline中使用")
    print("🔄" * 20)
    
    orchestrator = AgentOrchestrator()
    
    # 创建线索并完成数据采集和报价
    channel_url = "https://www.youtube.com/@FullPipelineDemo"
    creator_name = "Full Pipeline Demo"
    
    context3 = orchestrator.create_lead(channel_url, creator_name)
    
    # 模拟完成前面的阶段
    context3.creator_profile = {
        "creator_name": creator_name,
        "custom_url": "fullpipelinedemo",
        "recent_metrics": {"baseline_views": 50000}
    }
    context3.pricing_card = {
        "target_price": 1200,
        "currency": "USD"
    }
    context3.current_stage = PipelineStage.PRICING_DRAFTED
    
    print(f"\n当前Pipeline状态: {context3.current_stage.value}")
    print(f"已获取报价: ${context3.pricing_card['target_price']}")
    
    # 执行联系方式查找
    print(f"\n▶ 执行联系方式查找...")
    
    # 模拟找到联系方式
    context3.contact_candidates = mock_candidates[:3]
    context3.recommended_contact = mock_candidates[0]
    
    engine = PipelineEngine(context3)
    engine.transition(PipelineStage.CONTACT_FINDING, "开始查找联系方式")
    engine.transition(PipelineStage.OUTREACH_SENT, "已获取联系方式，准备发送邮件")
    
    print(f"✓ 找到推荐联系方式: {context3.recommended_contact['value']}")
    print(f"✓ 当前状态: {context3.current_stage.value}")
    
    print(f"\n📧 下一步：生成首封合作邮件")
    print(f"  收件人: {context3.recommended_contact['value']}")
    print(f"  报价参考: ${context3.pricing_card['target_price']}")
    
    # ========== 场景4: 不同类型联系方式对比 ==========
    print("\n" + "📊" * 20)
    print("场景4: 联系方式类型与优先级")
    print("📊" * 20)
    
    contact_types = [
        ("business_email", "商务邮箱", "最高优先级，直接合作渠道", 0.85),
        ("email", "普通邮箱", "次优先级，可能需要筛选", 0.60),
        ("business_form", "官网表单", "适合正式商务合作", 0.70),
        ("manager_contact", "经纪人", "适合高价值合作", 0.75),
        ("linktree", "Linktree", "聚合多种联系方式", 0.65),
        ("social_dm", "社媒私信", "初步接触，需引导至邮件", 0.40),
        ("website", "官网", "可能有联系表单", 0.50),
    ]
    
    print(f"\n{'类型':<20} {'优先级':<8} {'典型置信度':<12} {'说明'}")
    print("-" * 80)
    
    for contact_type, name, desc, confidence in contact_types:
        priority = agent.CONTACT_PRIORITY.get(contact_type, 99)
        print(f"{name:<20} {priority:<8} {confidence:<12.0%} {desc}")
    
    print("\n" + "=" * 80)
    print("联系方式查找演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    demo_contact_finding()
