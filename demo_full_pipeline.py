"""
完整Pipeline演示：数据采集 → 报价计算
"""
from src.core import (
    AgentOrchestrator, PipelineContext, PipelineStage, 
    PipelineEngine, DataCollectionAgent, PricingAgent
)


def demo_full_pipeline():
    """演示完整流程：数据采集 → 报价计算"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 完整Pipeline演示")
    print("流程: 线索创建 → 数据采集 → 报价计算")
    print("=" * 80)
    
    # ========== 阶段1: 创建线索 ==========
    print("\n" + "📝" * 20)
    print("阶段1: 创建线索")
    print("📝" * 20)
    
    orchestrator = AgentOrchestrator()
    
    channel_url = "https://www.youtube.com/@GamingCreator2024"
    creator_name = "Gaming Creator 2024"
    
    context = orchestrator.create_lead(channel_url, creator_name)
    print(f"✓ 线索已创建")
    print(f"  频道: {creator_name}")
    print(f"  URL: {channel_url}")
    print(f"  当前状态: {context.current_stage.value}")
    
    # ========== 阶段2: 数据采集 ==========
    print("\n" + "📊" * 20)
    print("阶段2: 数据采集")
    print("📊" * 20)
    
    # 模拟数据采集结果（实际使用时会真的去抓取）
    print("  正在采集频道数据...")
    
    # 模拟从YouTube获取的数据
    collected_data = {
        "creator_profile": {
            "creator_name": creator_name,
            "channel_url": channel_url,
            "subscriber_count": 180000,
            "total_view_count": 8500000,
            "language_guess": "en",
            "region_guess": "US/UK",
            "content_focus": ["Gaming", "RPG"],
            "content_types": ["长视频为主", "少量Shorts"],
            "recent_metrics": {
                "video_count": 30,
                "mean_views": 65000,
                "median_views": 58000,
                "p75_views": 82000,
                "baseline_views": 58000,  # max(58000, 65000*0.8=52000)
                "viral_rate": 0.10,
                "avg_duration_seconds": 720,
                "shorts_ratio": 0.10
            }
        },
        "videos_data": [
            {"title": "Elden Ring Boss Guide", "views": 95000, "is_suspected_sponsored": False, "duration_seconds": 900},
            {"title": "Genshin Impact Update Review", "views": 78000, "is_suspected_sponsored": True, "duration_seconds": 600},
            {"title": "Best RPG Games 2024", "views": 62000, "is_suspected_sponsored": False, "duration_seconds": 480},
            {"title": "Honkai Star Rail Tips", "views": 58000, "is_suspected_sponsored": False, "duration_seconds": 540},
            {"title": "Mobile Gaming Setup", "views": 45000, "is_suspected_sponsored": False, "duration_seconds": 420},
        ] * 6,  # 模拟30条视频
        "data_confidence": "high"
    }
    
    # 更新Context
    context.creator_profile = collected_data["creator_profile"]
    context.videos_data = collected_data["videos_data"]
    context.data_confidence = collected_data["data_confidence"]
    
    # 流转状态
    engine = PipelineEngine(context)
    engine.transition(PipelineStage.DATA_COLLECTING, "开始数据采集")
    engine.transition(PipelineStage.DATA_READY, "数据采集完成")
    
    print(f"✓ 数据采集完成")
    print(f"  订阅数: {context.creator_profile['subscriber_count']:,}")
    print(f"  总播放量: {context.creator_profile['total_view_count']:,}")
    print(f"  Baseline Views: {context.creator_profile['recent_metrics']['baseline_views']:,}")
    print(f"  数据置信度: {context.data_confidence}")
    print(f"  当前状态: {context.current_stage.value}")
    
    # ========== 阶段3: 报价计算 ==========
    print("\n" + "💰" * 20)
    print("阶段3: 报价计算")
    print("💰" * 20)
    
    # 场景A: 网络游戏合作
    print("\n场景A: 网络游戏合作")
    pricing_agent = PricingAgent()
    result_a = pricing_agent.execute(context, game_category="online_game")
    
    if result_a["status"] == "success":
        card_a = result_a["pricing_card"]
        print(f"  ✓ 报价计算完成")
        print(f"    CPM: ${card_a['assumed_cpm_usd_range'][0]}-${card_a['assumed_cpm_usd_range'][1]}")
        print(f"    基础价格: ${card_a['base_fee_range'][0]:,.0f}-${card_a['base_fee_range'][1]:,.0f}")
        print(f"    调整: {card_a['total_adjustment_pct']:+}%")
        print(f"    ┌─────────────┬──────────┐")
        print(f"    │ 开价(Anchor)│ ${card_a['anchor_price']:>8,} │")
        print(f"    │ 目标(Target)│ ${card_a['target_price']:>8,} │")
        print(f"    │ 底价(Floor) │ ${card_a['floor_price']:>8,} │")
        print(f"    └─────────────┴──────────┘")
    
    # 场景B: 米哈游游戏合作（更高的匹配度）
    print("\n场景B: 米哈游游戏合作（米哈游受众匹配度更高）")
    result_b = pricing_agent.execute(context, game_category="mihoyo_game")
    
    if result_b["status"] == "success":
        card_b = result_b["pricing_card"]
        print(f"  ✓ 报价计算完成")
        print(f"    调整: {card_b['total_adjustment_pct']:+}%")
        print(f"    ┌─────────────┬──────────┐")
        print(f"    │ 开价(Anchor)│ ${card_b['anchor_price']:>8,} │")
        print(f"    │ 目标(Target)│ ${card_b['target_price']:>8,} │")
        print(f"    │ 底价(Floor) │ ${card_b['floor_price']:>8,} │")
        print(f"    └─────────────┴──────────┘")
        print(f"    比网络游戏高: ${card_b['target_price'] - card_a['target_price']:,}")
    
    # 保存报价卡到Context
    context.pricing_card = card_b
    engine.transition(PipelineStage.PRICING_DRAFTED, "报价计算完成")
    
    # ========== 阶段4: 生成报价卡摘要 ==========
    print("\n" + "📋" * 20)
    print("阶段4: 报价卡摘要")
    print("📋" * 20)
    
    card = context.pricing_card
    
    print(f"\n{'='*60}")
    print(f"报价卡: {creator_name}")
    print(f"{'='*60}")
    
    print(f"\n【创作者信息】")
    print(f"  频道: {context.creator_profile['creator_name']}")
    print(f"  订阅: {context.creator_profile['subscriber_count']:,}")
    print(f"  地区: {context.creator_profile['region_guess']}")
    print(f"  语言: {context.creator_profile['language_guess']}")
    
    print(f"\n【数据基础】")
    print(f"  Baseline Views: {card['baseline_views']:,}")
    print(f"  CPM: ${card['assumed_cpm_usd_range'][0]}-${card['assumed_cpm_usd_range'][1]}")
    print(f"  基础价格: ${card['base_fee_range'][0]:,.0f}-${card['base_fee_range'][1]:,.0f}")
    
    print(f"\n【价格三档】")
    print(f"  ┌─────────────┬──────────┬────────┐")
    print(f"  │   价格类型   │  金额    │ 策略   │")
    print(f"  ├─────────────┼──────────┼────────┤")
    print(f"  │ 开价(Anchor)│ ${card['anchor_price']:>8,} │ 初始报价│")
    print(f"  │ 目标(Target)│ ${card['target_price']:>8,} │ 期望成交│")
    print(f"  │ 底价(Floor) │ ${card['floor_price']:>8,} │ 最低接受│")
    print(f"  └─────────────┴──────────┴────────┘")
    print(f"  谈判空间: {(card['anchor_price'] - card['floor_price']) / card['floor_price'] * 100:.0f}%")
    
    print(f"\n【调整因子】")
    for adj in card['adjustments']:
        print(f"  • {adj['name']}: {adj['impact_pct']:+}% - {adj['reason']}")
    
    print(f"\n【交付清单】")
    for i, item in enumerate(card['deliverables'], 1):
        print(f"  {i}. {item}")
    
    print(f"\n【加项菜单】")
    for item in card['add_on_menu'][:3]:  # 只显示前3个
        print(f"  • {item['item']}: +${item['price']}")
    
    print(f"\n【绩效奖励】")
    print(f"  {card['other_terms']['bonus_for_performance']}")
    
    print(f"\n【风险提示】")
    for risk in card['assumptions_and_risks'][:2]:  # 只显示前2个
        print(f"  ⚠ {risk}")
    
    print(f"\n{'='*60}")
    
    # ========== 阶段5: Pipeline状态总结 ==========
    print("\n" + "📊" * 20)
    print("阶段5: Pipeline状态总结")
    print("📊" * 20)
    
    print(f"\n当前状态: {context.current_stage.value}")
    print(f"\n状态流转历史:")
    for i, history in enumerate(context.stage_history, 1):
        print(f"  {i}. {history['from']} → {history['to']}")
        print(f"     原因: {history['reason']}")
        print(f"     时间: {history['timestamp'][:19]}")
    
    # 查看CRM记录
    crm_records = orchestrator.get_crm_records(channel_url)
    print(f"\nCRM记录:")
    for record in crm_records:
        print(f"  • [{record['timestamp'][:19]}] {record['action']}: {record['result']}")
    
    # ========== 下一步建议 ==========
    print("\n" + "🚀" * 20)
    print("下一步建议")
    print("🚀" * 20)
    
    print(f"""
基于当前Pipeline状态({context.current_stage.value})，建议下一步:

1. 【查找联系方式】
   使用ContactFindingAgent查找创作者的商务合作邮箱
   
2. 【生成首封邮件】
   使用OutreachAgent生成个性化的合作邀请邮件
   引用报价卡中的价格: Target ${context.pricing_card['target_price']:,}
   
3. 【发送邮件】
   通过EmailTool发送邮件到 cooperate@topuplive.com
   
4. 【等待回复】
   如果对方48小时未回复，自动触发Follow-up流程
    """)
    
    print("\n" + "=" * 80)
    print("完整Pipeline演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    demo_full_pipeline()
