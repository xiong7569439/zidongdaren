"""
谈判处理Agent演示脚本
"""
from src.core import (
    AgentOrchestrator, PipelineContext, PipelineStage, 
    PipelineEngine, NegotiationAgent
)


def demo_negotiation():
    """演示谈判处理流程"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 谈判处理演示")
    print("=" * 80)
    
    # 准备基础Context
    def create_base_context():
        context = PipelineContext(
            channel_url="https://www.youtube.com/@NegotiationDemo",
            creator_name="Gaming Creator Pro"
        )
        context.creator_profile = {
            "creator_name": "Gaming Creator Pro",
            "recent_metrics": {
                "baseline_views": 80000,
                "median_views": 75000
            }
        }
        context.pricing_card = {
            "anchor_price": 2000,
            "target_price": 1600,
            "floor_price": 1200,
            "baseline_views": 80000
        }
        context.current_stage = PipelineStage.NEGOTIATING
        return context
    
    agent = NegotiationAgent()
    
    # ========== 场景1: 对方压价 ==========
    print("\n" + "💰" * 20)
    print("场景1: 对方压价 - 提供两档方案")
    print("💰" * 20)
    
    context1 = create_base_context()
    
    reply_from_creator = """
    Hi,
    
    Thanks for reaching out! I'm interested in the collaboration, 
    but your budget is a bit too high for me. My usual rate for 
    this type of integration is around $1200-1300. 
    
    Is there any flexibility on the pricing?
    
    Best,
    Gaming Creator Pro
    """
    
    result1 = agent.execute(context1, raw_reply=reply_from_creator)
    
    print(f"\n📧 对方回复：")
    print(f"  意图: {result1['intent_analysis']['intent']}")
    print(f"  置信度: {result1['intent_analysis']['confidence']:.0%}")
    
    if result1['status'] == 'success':
        print(f"\n✓ 处理结果: {result1['message']}")
        print(f"\n📝 拟回复邮件：")
        print("-" * 80)
        print(result1['reply_draft']['body'])
        print("-" * 80)
        
        if 'options' in result1['reply_draft']:
            print(f"\n📊 提供的方案：")
            for opt in result1['reply_draft']['options']:
                print(f"  - {opt['name']}: ${opt['price']} ({opt['scope']})")
    
    # ========== 场景2: 对方要素材/Brief ==========
    print("\n" + "📦" * 20)
    print("场景2: 对方要素材/Brief")
    print("📦" * 20)
    
    context2 = create_base_context()
    
    reply2 = """
    Hi,
    
    Thanks for the offer! Before we proceed, could you send me 
    the campaign brief and any assets you have? I'd like to 
    understand the game better and see what materials are available.
    
    Also, what's the timeline for this campaign?
    
    Thanks,
    Gaming Creator Pro
    """
    
    result2 = agent.execute(context2, raw_reply=reply2)
    
    print(f"\n📧 对方回复意图: {result2['intent_analysis']['intent']}")
    
    if result2['status'] == 'success':
        print(f"\n✓ 处理结果: {result2['message']}")
        print(f"📍 更新后状态: {result2['updated_stage']}")
        print(f"\n📝 拟回复邮件：")
        print("-" * 80)
        print(result2['reply_draft']['body'])
        print("-" * 80)
    
    # ========== 场景3: 对方要数据证明 ==========
    print("\n" + "📊" * 20)
    print("场景3: 对方要数据证明")
    print("📊" * 20)
    
    context3 = create_base_context()
    
    reply3 = """
    Hi,
    
    I'm interested, but I want to understand how you calculated 
    the pricing. Can you share the data or metrics that support 
    this budget? What's the expected ROI or view count?
    
    Thanks,
    Gaming Creator Pro
    """
    
    result3 = agent.execute(context3, raw_reply=reply3)
    
    print(f"\n📧 对方回复意图: {result3['intent_analysis']['intent']}")
    
    if result3['status'] == 'success':
        print(f"\n✓ 处理结果: {result3['message']}")
        print(f"\n📝 拟回复邮件：")
        print("-" * 80)
        print(result3['reply_draft']['body'])
        print("-" * 80)
    
    # ========== 场景4: 敏感条款（需人工审批） ==========
    print("\n" + "⚠️" * 20)
    print("场景4: 敏感条款 - 需人工审批")
    print("⚠️" * 20)
    
    context4 = create_base_context()
    
    reply4 = """
    Hi,
    
    I'm open to the collaboration. However, I have a few requirements:
    
    1. I need a guaranteed minimum of 100,000 views on the video
    2. I want exclusive rights for 6 months (no other gaming sponsors)
    3. The usage rights should be permanent for your marketing
    
    Can you accommodate these terms?
    
    Best,
    Gaming Creator Pro
    """
    
    result4 = agent.execute(context4, raw_reply=reply4)
    
    print(f"\n📧 对方回复意图: {result4['intent_analysis']['intent']}")
    
    if result4['status'] == 'success':
        print(f"\n⚠️ 检测到敏感条款！")
        print(f"  需要人工审批: {result4['need_human_approval']}")
        print(f"  风险项: {result4['risks']}")
        print(f"\n📝 拟回复邮件（婉拒敏感条款）：")
        print("-" * 80)
        print(result4['reply_draft']['body'])
        print("-" * 80)
    
    # ========== 场景5: 对方接受报价 ==========
    print("\n" + "✅" * 20)
    print("场景5: 对方接受报价")
    print("✅" * 20)
    
    context5 = create_base_context()
    
    reply5 = """
    Hi,
    
    This sounds great! I'm interested in working with you on this.
    
    The budget works for me and I like the game. Let's move forward!
    
    What's the next step?
    
    Best,
    Gaming Creator Pro
    """
    
    result5 = agent.execute(context5, raw_reply=reply5)
    
    print(f"\n📧 对方回复意图: {result5['intent_analysis']['intent']}")
    
    if result5['status'] == 'success':
        print(f"\n✓ 处理结果: {result5['message']}")
        print(f"📍 更新后状态: {result5['updated_stage']}")
        print(f"\n📝 拟回复邮件：")
        print("-" * 80)
        print(result5['reply_draft']['body'])
        print("-" * 80)
    
    # ========== 场景6: 对方拒绝 ==========
    print("\n" + "❌" * 20)
    print("场景6: 对方拒绝")
    print("❌" * 20)
    
    context6 = create_base_context()
    
    reply6 = """
    Hi,
    
    Thanks for reaching out, but I'm not interested at this time.
    I'm currently busy with other projects and don't have capacity 
    for new sponsorships.
    
    Maybe next time!
    
    Best,
    Gaming Creator Pro
    """
    
    result6 = agent.execute(context6, raw_reply=reply6)
    
    print(f"\n📧 对方回复意图: {result6['intent_analysis']['intent']}")
    
    if result6['status'] == 'success':
        print(f"\n✓ 处理结果: {result6['message']}")
        print(f"📍 更新后状态: {result6['updated_stage']}")
        print(f"\n📝 拟回复邮件（礼貌留存）：")
        print("-" * 80)
        print(result6['reply_draft']['body'])
        print("-" * 80)
    
    # ========== 场景7: 预算超限 ==========
    print("\n" + "💸" * 20)
    print("场景7: 预算硬限制 - 无法成交")
    print("💸" * 20)
    
    context7 = create_base_context()
    # 设置一个较低的预算限制
    
    reply7 = """
    Hi,
    
    Your offer is way above my budget. I usually charge around 
    $1000-1200 for this type of work. Can you match that?
    """
    
    result7 = agent.execute(context7, raw_reply=reply7, budget_ceiling=1100)
    
    print(f"\n📧 对方期望价格: $1000-1200")
    print(f"   我方底价: ${context7.pricing_card['floor_price']}")
    print(f"   预算限制: $1100")
    
    if result7['status'] == 'success':
        print(f"\n✓ 处理结果: {result7['message']}")
        print(f"📍 更新后状态: {result7['updated_stage']}")
        print(f"\n📝 拟回复邮件（婉拒）：")
        print("-" * 80)
        print(result7['reply_draft']['body'])
        print("-" * 80)
    
    # ========== 场景8: 完整Pipeline中的谈判 ==========
    print("\n" + "🔄" * 20)
    print("场景8: 完整Pipeline中的谈判")
    print("🔄" * 20)
    
    orchestrator = AgentOrchestrator()
    
    channel_url = "https://www.youtube.com/@FullNegotiationDemo"
    creator_name = "Full Negotiation Demo"
    
    context8 = orchestrator.create_lead(channel_url, creator_name)
    
    # 模拟完成前面所有阶段
    context8.creator_profile = {
        "creator_name": creator_name,
        "recent_metrics": {"baseline_views": 70000, "median_views": 65000}
    }
    context8.videos_data = [{"title": "Demo Video", "views": 70000, "is_suspected_sponsored": False}]
    context8.pricing_card = {"anchor_price": 1800, "target_price": 1400, "floor_price": 1000}
    context8.contact_candidates = [{"type": "email", "value": "demo@example.com"}]
    context8.recommended_contact = context8.contact_candidates[0]
    context8.email_history = [{
        "type": "outbound",
        "stage": "first_touch",
        "timestamp": "2026-03-25T10:00:00"
    }]
    
    # 流转到谈判阶段
    engine = PipelineEngine(context8)
    engine.transition(PipelineStage.DATA_COLLECTING, "开始数据采集")
    engine.transition(PipelineStage.DATA_READY, "数据采集完成")
    engine.transition(PipelineStage.PRICING_DRAFTED, "报价计算完成")
    engine.transition(PipelineStage.CONTACT_FINDING, "开始查找联系方式")
    engine.transition(PipelineStage.OUTREACH_SENT, "首封邮件已发送")
    engine.transition(PipelineStage.NEGOTIATING, "进入谈判阶段")
    
    print(f"\n当前Pipeline状态: {context8.current_stage.value}")
    print(f"谈判历史: {len(context8.negotiation_log)} 轮")
    
    # 模拟收到回复
    reply8 = "Thanks for the email! I'm interested but the price is a bit high. Can we discuss?"
    
    result8 = agent.execute(context8, raw_reply=reply8)
    
    print(f"\n📧 收到回复: {reply8[:50]}...")
    print(f"📧 意图分析: {result8['intent_analysis']['intent']}")
    print(f"✓ 处理结果: {result8['message']}")
    
    print(f"\n📊 谈判历史更新:")
    for i, log in enumerate(context8.negotiation_log, 1):
        print(f"  {i}. [{log['timestamp'][:19]}] {log['type']} - {log['intent']}")
    
    print("\n" + "=" * 80)
    print("谈判处理演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    demo_negotiation()
