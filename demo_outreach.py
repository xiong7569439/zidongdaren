"""
邮件生成Agent演示脚本
"""
from src.core import (
    AgentOrchestrator, PipelineContext, PipelineStage, 
    PipelineEngine, OutreachAgent
)


def demo_outreach():
    """演示邮件生成流程"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 邮件生成演示")
    print("=" * 80)
    
    # ========== 场景1: 标准首封邮件 ==========
    print("\n" + "📧" * 20)
    print("场景1: 标准首封邮件（Standard Template）")
    print("📧" * 20)
    
    context = PipelineContext(
        channel_url="https://www.youtube.com/@GamingCreatorDemo",
        creator_name="Alex Gaming"
    )
    
    # 设置完整的数据
    context.creator_profile = {
        "creator_name": "Alex Gaming",
        "recent_metrics": {
            "baseline_views": 75000
        }
    }
    context.videos_data = [
        {"title": "Elden Ring Complete Walkthrough", "views": 120000, "is_suspected_sponsored": False},
        {"title": "Best RPG Games 2024", "views": 95000, "is_suspected_sponsored": False},
        {"title": "Genshin Impact Update Review", "views": 88000, "is_suspected_sponsored": True},
    ]
    context.pricing_card = {
        "anchor_price": 1800,
        "target_price": 1400,
        "floor_price": 1000
    }
    context.recommended_contact = {
        "type": "business_email",
        "value": "business@alexgaming.com"
    }
    
    agent = OutreachAgent()
    
    result = agent.execute(
        context,
        game_name="Eternal Odyssey",
        game_genre="MMORPG",
        game_platform="Mobile/PC",
        template_type="standard"
    )
    
    if result["status"] == "success":
        draft = result["email_draft"]
        print(f"\n✓ 邮件生成成功（{draft['word_count']}词）")
        print(f"\n📧 邮件主题选项：")
        for i, subject in enumerate(draft["subject_options"], 1):
            print(f"  {i}. {subject}")
        
        print(f"\n📝 邮件正文：")
        print("-" * 80)
        print(draft["body"])
        print("-" * 80)
        
        print(f"\n📍 CTA: {draft['cta']}")
        print(f"📍 个性化引用: {draft['personalization']['video_referenced']}")
    
    # ========== 场景2: 简短邮件 ==========
    print("\n" + "💬" * 20)
    print("场景2: 简短邮件（Short Template）")
    print("💬" * 20)
    
    result2 = agent.execute(
        context,
        game_name="Eternal Odyssey",
        template_type="short"
    )
    
    if result2["status"] == "success":
        draft2 = result2["email_draft"]
        print(f"\n✓ 简短邮件生成成功（{draft2['word_count']}词）")
        print(f"\n📝 邮件正文：")
        print("-" * 80)
        print(draft2["body"])
        print("-" * 80)
    
    # ========== 场景3: 跟进邮件 ==========
    print("\n" + "🔄" * 20)
    print("场景3: 跟进邮件（Follow-up Template）")
    print("🔄" * 20)
    
    result3 = agent.generate_follow_up(
        context,
        game_name="Eternal Odyssey",
        follow_up_count=1
    )
    
    if result3["status"] == "success":
        draft3 = result3["email_draft"]
        print(f"\n✓ 跟进邮件生成成功（{draft3['word_count']}词）")
        print(f"\n📝 邮件正文：")
        print("-" * 80)
        print(draft3["body"])
        print("-" * 80)
    
    # ========== 场景4: 双语邮件 ==========
    print("\n" + "🌐" * 20)
    print("场景4: 中英双语邮件")
    print("🌐" * 20)
    
    result4 = agent.execute(
        context,
        game_name="Eternal Odyssey",
        game_genre="MMORPG",
        template_type="standard",
        language="bilingual"
    )
    
    if result4["status"] == "success":
        draft4 = result4["email_draft"]
        print(f"\n✓ 双语邮件生成成功")
        print(f"\n📝 邮件正文（节选）：")
        print("-" * 80)
        # 只显示前500字符
        body_preview = draft4["body"][:500] + "..."
        print(body_preview)
        print("-" * 80)
    
    # ========== 场景5: 完整Pipeline流程 ==========
    print("\n" + "🔄" * 20)
    print("场景5: 完整Pipeline中的邮件生成")
    print("🔄" * 20)
    
    orchestrator = AgentOrchestrator()
    
    # 创建线索并完成前面所有阶段
    channel_url = "https://www.youtube.com/@FullPipelineCreator"
    creator_name = "Full Pipeline Creator"
    
    context5 = orchestrator.create_lead(channel_url, creator_name)
    
    # 模拟完成前面阶段
    context5.creator_profile = {
        "creator_name": creator_name,
        "recent_metrics": {"baseline_views": 60000}
    }
    context5.videos_data = [
        {"title": "Amazing Gameplay Video", "views": 80000, "is_suspected_sponsored": False}
    ]
    context5.pricing_card = {
        "anchor_price": 1500,
        "target_price": 1200,
        "floor_price": 900
    }
    context5.contact_candidates = [
        {"type": "business_email", "value": "partnerships@fullpipeline.com", "confidence": 0.9}
    ]
    context5.recommended_contact = context5.contact_candidates[0]
    
    # 流转状态
    engine = PipelineEngine(context5)
    engine.transition(PipelineStage.DATA_COLLECTING, "开始数据采集")
    engine.transition(PipelineStage.DATA_READY, "数据采集完成")
    engine.transition(PipelineStage.PRICING_DRAFTED, "报价计算完成")
    engine.transition(PipelineStage.CONTACT_FINDING, "开始查找联系方式")
    engine.transition(PipelineStage.OUTREACH_SENT, "准备发送邮件")
    
    print(f"\n当前Pipeline状态: {context5.current_stage.value}")
    
    # 生成邮件
    result5 = agent.execute(
        context5,
        game_name="Star Legends",
        game_genre="Strategy",
        sender_info={
            "name": "Sarah Chen",
            "title": "Partnership Manager",
            "company": "TOPUPlive",
            "email": "cooperate@topuplive.com"
        }
    )
    
    if result5["status"] == "success":
        draft5 = result5["email_draft"]
        print(f"\n✓ 邮件生成成功")
        print(f"\n📧 收件人: {draft5['to']}")
        print(f"📧 主题: {draft5['subject']}")
        print(f"📧 字数: {draft5['word_count']}")
        print(f"\n📝 邮件正文：")
        print("-" * 80)
        print(draft5['body'])
        print("-" * 80)
        
        # 查看邮件历史
        print(f"\n📨 邮件历史记录:")
        for email in context5.email_history:
            print(f"  - [{email['timestamp'][:19]}] {email['type']} ({email['template_type']})")
    
    # ========== 场景6: 不同游戏品类的邮件 ==========
    print("\n" + "🎮" * 20)
    print("场景6: 不同游戏品类的邮件对比")
    print("🎮" * 20)
    
    games = [
        ("mobile_game", "Puzzle Quest", "Puzzle", "Mobile"),
        ("online_game", "Arena of Valor", "MOBA", "Mobile/PC"),
        ("mihoyo_game", "Honkai Star Rail", "RPG", "Mobile/PC"),
        ("aaa_game", "Elden Ring", "ARPG", "PC/Console"),
    ]
    
    for game_category, game_name, genre, platform in games:
        result = agent.execute(
            context,
            game_name=game_name,
            game_genre=genre,
            game_platform=platform,
            template_type="short"
        )
        
        if result["status"] == "success":
            draft = result["email_draft"]
            subject = draft["subject"]
            print(f"\n{game_category}:")
            print(f"  游戏: {game_name}")
            print(f"  主题: {subject[:60]}...")
    
    print("\n" + "=" * 80)
    print("邮件生成演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    demo_outreach()
