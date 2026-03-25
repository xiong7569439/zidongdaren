"""
所有Agent综合演示
展示完整的YouTube网红曝光合作系统
"""
from src.core import (
    AgentOrchestrator, PipelineContext, PipelineStage, PipelineEngine,
    DataCollectionAgent, PricingAgent, ContactFindingAgent,
    OutreachAgent, NegotiationAgent, BriefAgent, DailyReportAgent
)


def demo_all_agents():
    """演示所有Agent的完整流程"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 所有Agent综合演示")
    print("=" * 80)
    
    orchestrator = AgentOrchestrator()
    
    # ========== 创建多个线索 ==========
    print("\n📋 创建3个测试线索...")
    
    creators = [
        ("Gaming Pro A", "https://www.youtube.com/@GamingProA"),
        ("RPG Master", "https://www.youtube.com/@RPGMaster"),
        ("Mobile Gamer", "https://www.youtube.com/@MobileGamer"),
    ]
    
    contexts = []
    for name, url in creators:
        ctx = orchestrator.create_lead(url, name)
        contexts.append(ctx)
        print(f"  ✓ {name}: {ctx.current_stage.value}")
    
    # ========== 1. DataCollectionAgent ==========
    print("\n" + "📊" * 30)
    print("1. DataCollectionAgent - 数据采集")
    print("📊" * 30)
    
    data_agent = DataCollectionAgent()
    
    for i, ctx in enumerate(contexts):
        # 模拟采集结果
        ctx.creator_profile = {
            "creator_name": ctx.creator_name,
            "subscriber_count": 100000 + i * 50000,
            "language_guess": "en",
            "region_guess": "US",
            "content_focus": ["Gaming"],
            "recent_metrics": {
                "baseline_views": 50000 + i * 20000,
                "median_views": 45000 + i * 15000,
                "viral_rate": 0.1 + i * 0.05
            }
        }
        ctx.videos_data = [{"title": f"Video {j}", "views": 50000} for j in range(5)]
        ctx.data_confidence = "high"
        
        engine = PipelineEngine(ctx)
        engine.transition(PipelineStage.DATA_COLLECTING, "开始采集")
        engine.transition(PipelineStage.DATA_READY, "采集完成")
        
        print(f"  ✓ {ctx.creator_name}: baseline={ctx.creator_profile['recent_metrics']['baseline_views']:,}")
    
    # ========== 2. PricingAgent ==========
    print("\n" + "💰" * 30)
    print("2. PricingAgent - 报价计算")
    print("💰" * 30)
    
    pricing_agent = PricingAgent()
    
    for ctx in contexts:
        result = pricing_agent.execute(ctx, game_category="mobile_game")
        if result["status"] == "success":
            card = result["pricing_card"]
            ctx.pricing_card = card
            
            engine = PipelineEngine(ctx)
            engine.transition(PipelineStage.PRICING_DRAFTED, "报价完成")
            
            print(f"  ✓ {ctx.creator_name}: ${card['target_price']:,}")
    
    # ========== 3. ContactFindingAgent ==========
    print("\n" + "📧" * 30)
    print("3. ContactFindingAgent - 联系方式查找")
    print("📧" * 30)
    
    for ctx in contexts:
        # 模拟找到联系方式
        ctx.contact_candidates = [
            {"type": "email", "value": f"contact@{ctx.creator_name.replace(' ', '').lower()}.com"}
        ]
        ctx.recommended_contact = ctx.contact_candidates[0]
        
        engine = PipelineEngine(ctx)
        engine.transition(PipelineStage.CONTACT_FINDING, "查找联系方式")
        
        print(f"  ✓ {ctx.creator_name}: {ctx.recommended_contact['value']}")
    
    # ========== 4. OutreachAgent ==========
    print("\n" + "✉️" * 30)
    print("4. OutreachAgent - 邮件生成")
    print("✉️" * 30)
    
    outreach_agent = OutreachAgent()
    
    for ctx in contexts:
        result = outreach_agent.execute(
            ctx,
            game_name="Star Legends",
            template_type="short"
        )
        if result["status"] == "success":
            engine = PipelineEngine(ctx)
            engine.transition(PipelineStage.OUTREACH_SENT, "邮件已发送")
            
            print(f"  ✓ {ctx.creator_name}: 邮件已生成 ({result['email_draft']['word_count']}词)")
    
    # ========== 5. NegotiationAgent ==========
    print("\n" + "🤝" * 30)
    print("5. NegotiationAgent - 谈判处理")
    print("🤝" * 30)
    
    negotiation_agent = NegotiationAgent()
    
    # 模拟第一个创作者压价
    reply1 = "Thanks for the offer! But your price is too high for me."
    result1 = negotiation_agent.execute(contexts[0], raw_reply=reply1)
    
    if result1["status"] == "success":
        engine = PipelineEngine(contexts[0])
        engine.transition(PipelineStage.NEGOTIATING, "进入谈判")
        print(f"  ✓ {contexts[0].creator_name}: 压价处理，提供两档方案")
    
    # 模拟第二个创作者接受
    reply2 = "Sounds great! Let's do it."
    result2 = negotiation_agent.execute(contexts[1], raw_reply=reply2)
    
    if result2["status"] == "success":
        engine = PipelineEngine(contexts[1])
        engine.transition(PipelineStage.NEGOTIATING, "进入谈判")
        engine.transition(PipelineStage.BRIEF_SENT, "接受报价")
        print(f"  ✓ {contexts[1].creator_name}: 接受报价，进入Brief阶段")
    
    # ========== 6. BriefAgent ==========
    print("\n" + "📦" * 30)
    print("6. BriefAgent - Brief生成")
    print("📦" * 30)
    
    brief_agent = BriefAgent()
    
    result = brief_agent.execute(
        contexts[1],
        game_info="Star Legends",
        key_messages=["Epic space battles", "Build your fleet", "Free to play"],
        landing_url="https://starlegends.com"
    )
    
    if result["status"] == "success":
        print(f"  ✓ {contexts[1].creator_name}: Brief已生成")
        print(f"    - 内容方向: {len(result['brief']['content_directions'])}条建议")
        print(f"    - 素材邮件: 已生成")
    
    # ========== 7. DailyReportAgent ==========
    print("\n" + "📈" * 30)
    print("7. DailyReportAgent - 日报生成")
    print("📈" * 30)
    
    daily_agent = DailyReportAgent()
    
    result = daily_agent.execute(contexts, date="2026-03-25")
    
    if result["status"] == "success":
        report = result["daily_report"]
        print(f"\n  📅 日期: {report['date']}")
        print(f"  📝 摘要: {report['summary']}")
        print(f"\n  📊 Pipeline分布:")
        for item in report['pipeline_breakdown']:
            print(f"    - {item['stage']}: {item['count']}个")
        print(f"\n  📧 触达统计:")
        print(f"    - 发送: {report['outreach']['sent']}封")
        print(f"    - 回复: {report['outreach']['replied']}封")
        print(f"\n  ⚠️ 风险项: {len(report['risks'])}个")
        print(f"  📅 明日计划: {len(report['tomorrow_plan'])}项")
    
    # ========== 最终状态汇总 ==========
    print("\n" + "=" * 80)
    print("最终状态汇总")
    print("=" * 80)
    
    print(f"\n{'创作者':<20} {'当前阶段':<25} {'操作'}")
    print("-" * 80)
    
    for ctx in contexts:
        stage_emoji = {
            "lead_collected": "📝",
            "data_collecting": "📊",
            "data_ready": "✅",
            "pricing_drafted": "💰",
            "contact_finding": "📧",
            "outreach_sent": "✉️",
            "negotiating": "🤝",
            "brief_sent": "📦",
            "schedule_confirmed": "📅",
            "deliverable_live": "🎥",
            "closed_won": "🏆",
            "closed_lost": "❌"
        }.get(ctx.current_stage.value, "⏳")
        
        next_action = {
            "negotiating": "等待对方回复",
            "brief_sent": "等待创作者确认Brief",
            "outreach_sent": "48小时后跟进"
        }.get(ctx.current_stage.value, "继续推进")
        
        print(f"{ctx.creator_name:<20} {stage_emoji} {ctx.current_stage.value:<20} {next_action}")
    
    print("\n" + "=" * 80)
    print("所有Agent演示完成！")
    print("=" * 80)
    print("\n系统已实现的Agent：")
    print("  ✅ DataCollectionAgent - 数据采集")
    print("  ✅ PricingAgent - 报价计算")
    print("  ✅ ContactFindingAgent - 联系方式查找")
    print("  ✅ OutreachAgent - 邮件生成")
    print("  ✅ NegotiationAgent - 谈判处理")
    print("  ✅ BriefAgent - Brief生成")
    print("  ✅ DailyReportAgent - 日报汇总")


if __name__ == "__main__":
    demo_all_agents()
