"""
报价计算Agent演示脚本
"""
from src.core import AgentOrchestrator, PipelineContext, PipelineStage, PricingAgent


def demo_pricing():
    """演示报价计算流程"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 报价计算演示")
    print("=" * 80)
    
    # 1. 创建模拟的PipelineContext（包含数据采集结果）
    print("\n[1/4] 准备数据...")
    
    context = PipelineContext(
        channel_url="https://www.youtube.com/@DemoGamingChannel",
        creator_name="Demo Gaming Channel"
    )
    
    # 设置创作者画像（模拟数据采集结果）
    context.creator_profile = {
        "creator_name": "Demo Gaming Channel",
        "channel_url": "https://www.youtube.com/@DemoGamingChannel",
        "subscriber_count": 250000,
        "total_view_count": 15000000,
        "language_guess": "en",
        "region_guess": "US",
        "content_focus": ["Gaming"],
        "content_types": ["长视频为主"],
        "recent_metrics": {
            "video_count": 30,
            "mean_views": 87500,
            "median_views": 82000,
            "p75_views": 115000,
            "baseline_views": 82000,  # 这是定价的核心输入
            "viral_rate": 0.13,
            "avg_duration_seconds": 680,
            "shorts_ratio": 0.15
        },
        "notes": "基于最近30条视频分析"
    }
    
    # 设置视频数据（用于计算商单密度等）
    context.videos_data = [
        {"title": "Game Review 1", "is_suspected_sponsored": False, "views": 125000},
        {"title": "Game Review 2 #ad", "is_suspected_sponsored": True, "views": 98000},
        {"title": "Game Tips", "is_suspected_sponsored": False, "views": 85000},
        {"title": "RPG Guide", "is_suspected_sponsored": False, "views": 78000},
        {"title": "Indie Game #sponsored", "is_suspected_sponsored": True, "views": 92000},
    ] * 6  # 模拟30条视频
    
    context.data_confidence = "high"
    context.current_stage = PipelineStage.DATA_READY
    
    print(f"✓ 数据准备完成")
    print(f"  - 创作者: {context.creator_name}")
    print(f"  - 订阅数: {context.creator_profile['subscriber_count']:,}")
    print(f"  - Baseline Views: {context.creator_profile['recent_metrics']['baseline_views']:,}")
    print(f"  - 地区: {context.creator_profile['region_guess']}")
    
    # 2. 执行报价计算
    print("\n[2/4] 执行报价计算...")
    
    agent = PricingAgent()
    
    # 场景1：手机游戏合作
    print("\n场景1: 手机游戏合作")
    result1 = agent.execute(context, game_category="mobile_game")
    
    if result1["status"] == "success":
        card1 = result1["pricing_card"]
        print(f"  ✓ 报价计算完成")
        print(f"    CPM范围: ${card1['assumed_cpm_usd_range'][0]}-${card1['assumed_cpm_usd_range'][1]}")
        print(f"    基础价格: ${card1['base_fee_range'][0]:,.0f} - ${card1['base_fee_range'][1]:,.0f}")
        print(f"    调整因子: {card1['total_adjustment_pct']}%")
        print(f"    报价三档:")
        print(f"      - 开价(Anchor): ${card1['anchor_price']:,}")
        print(f"      - 目标(Target): ${card1['target_price']:,}")
        print(f"      - 底价(Floor): ${card1['floor_price']:,}")
    
    # 场景2：米哈游游戏合作（应该有更高的价格）
    print("\n场景2: 米哈游游戏合作（受众匹配度更高）")
    result2 = agent.execute(context, game_category="mihoyo_game")
    
    if result2["status"] == "success":
        card2 = result2["pricing_card"]
        print(f"  ✓ 报价计算完成")
        print(f"    调整因子: {card2['total_adjustment_pct']}%")
        print(f"    报价三档:")
        print(f"      - 开价(Anchor): ${card2['anchor_price']:,}")
        print(f"      - 目标(Target): ${card2['target_price']:,}")
        print(f"      - 底价(Floor): ${card2['floor_price']:,}")
        print(f"    比手机游戏高: ${card2['target_price'] - card1['target_price']:,}")
    
    # 场景3：带预算限制
    print("\n场景3: 带预算限制 [1000, 3000]")
    result3 = agent.execute(context, game_category="mobile_game", budget_range=[1000, 3000])
    
    if result3["status"] == "success":
        card3 = result3["pricing_card"]
        print(f"  ✓ 报价计算完成（已适配预算）")
        print(f"    报价三档:")
        print(f"      - 开价(Anchor): ${card3['anchor_price']:,}")
        print(f"      - 目标(Target): ${card3['target_price']:,}")
        print(f"      - 底价(Floor): ${card3['floor_price']:,}")
    elif result3["status"] == "error" and result3.get("error_type") == "budget_exceeded":
        print(f"  ⚠ 超出预算: 底价${result3['pricing_card']['floor_price']:,} > 预算上限${result3['pricing_card']['budget_limit']:,}")
    
    # 3. 展示详细报价卡
    print("\n[3/4] 详细报价卡（场景2 - 米哈游游戏）:")
    print("-" * 80)
    
    card = result2["pricing_card"]
    
    print(f"\n📊 定价基础:")
    print(f"  Baseline Views: {card['baseline_views']:,}")
    print(f"  CPM范围: ${card['assumed_cpm_usd_range'][0]}-${card['assumed_cpm_usd_range'][1]} ({card['cpm_note']})")
    print(f"  基础价格: ${card['base_fee_range'][0]:,.0f} - ${card['base_fee_range'][1]:,.0f}")
    
    print(f"\n📈 调整因子:")
    for adj in card['adjustments']:
        print(f"  - {adj['name']}: {adj['impact_pct']:+}% ({adj['reason']})")
    print(f"  总调整: {card['total_adjustment_pct']}%")
    
    print(f"\n💰 报价三档:")
    print(f"  ┌─────────────┬──────────┐")
    print(f"  │ 开价(Anchor)│ ${card['anchor_price']:>8,} │")
    print(f"  │ 目标(Target)│ ${card['target_price']:>8,} │")
    print(f"  │ 底价(Floor) │ ${card['floor_price']:>8,} │")
    print(f"  └─────────────┴──────────┘")
    
    print(f"\n📦 交付清单:")
    for i, item in enumerate(card['deliverables'], 1):
        print(f"  {i}. {item}")
    
    print(f"\n➕ 加项菜单:")
    for item in card['add_on_menu']:
        print(f"  - {item['item']}: +${item['price']} ({item['notes']})")
    
    print(f"\n🎁 其他条款:")
    print(f"  绩效奖励: {card['other_terms']['bonus_for_performance']}")
    print(f"  打包折扣: {card['other_terms']['bundle_discount']}")
    print(f"  授权费用: {card['other_terms']['usage_rights_fee']}")
    
    print(f"\n⚠️ 假设与风险:")
    for risk in card['assumptions_and_risks']:
        print(f"  - {risk}")
    
    print(f"\n📝 计算公式:")
    for key, formula in card['calculation_formulas'].items():
        print(f"  {key}: {formula}")
    
    # 4. 更新Context并查看状态
    print("\n[4/4] 更新Pipeline状态...")
    context.pricing_card = card
    
    from src.core import PipelineEngine
    engine = PipelineEngine(context)
    engine.transition(PipelineStage.PRICING_DRAFTED, "报价计算完成")
    
    print(f"✓ 当前状态: {context.current_stage.value}")
    print(f"✓ 报价卡已保存到Context")
    
    print("\n" + "=" * 80)
    print("报价计算演示完成！")
    print("=" * 80)
    print("\n下一步可以:")
    print("  1. 查找创作者联系方式")
    print("  2. 生成首封合作邮件")
    print("  3. 导出报价卡PDF/Excel")


def demo_different_regions():
    """演示不同地区的CPM差异"""
    print("\n" + "=" * 80)
    print("不同地区CPM对比演示")
    print("=" * 80)
    
    regions = [
        ("US", "美国", "en", "US"),
        ("UK", "英国", "en", "UK"),
        ("JP", "日本", "ja", "JP"),
        ("CN", "中国", "zh", "CN"),
        ("SEA", "东南亚", "en", "SEA"),
    ]
    
    baseline_views = 100000
    
    print(f"\n假设Baseline Views: {baseline_views:,}")
    print(f"\n{'地区':<10} {'CPM范围':<15} {'基础价格范围':<25} {'说明'}")
    print("-" * 80)
    
    for region_code, region_name, lang, region_guess in regions:
        context = PipelineContext(
            channel_url=f"https://www.youtube.com/@Test{region_code}",
            creator_name=f"Test {region_name}"
        )
        context.creator_profile = {
            "language_guess": lang,
            "region_guess": region_guess,
            "content_focus": ["Gaming"],
            "recent_metrics": {"baseline_views": baseline_views}
        }
        context.videos_data = []
        context.data_confidence = "high"
        
        agent = PricingAgent()
        result = agent.execute(context, game_category="mobile_game")
        
        if result["status"] == "success":
            card = result["pricing_card"]
            cpm_range = f"${card['assumed_cpm_usd_range'][0]}-${card['assumed_cpm_usd_range'][1]}"
            price_range = f"${card['base_fee_range'][0]:,.0f}-${card['base_fee_range'][1]:,.0f}"
            print(f"{region_name:<10} {cpm_range:<15} {price_range:<25} {card['cpm_note']}")


def demo_budget_scenarios():
    """演示预算场景"""
    print("\n" + "=" * 80)
    print("预算场景演示")
    print("=" * 80)
    
    scenarios = [
        ("无预算限制", None),
        ("预算充足 [500, 5000]", [500, 5000]),
        ("预算紧张 [500, 1500]", [500, 1500]),
        ("预算过低 [100, 500]", [100, 500]),
    ]
    
    context = PipelineContext(
        channel_url="https://www.youtube.com/@BudgetTest",
        creator_name="Budget Test"
    )
    context.creator_profile = {
        "language_guess": "en",
        "region_guess": "US",
        "content_focus": ["Gaming"],
        "recent_metrics": {"baseline_views": 80000}  # 约 $1200-2000
    }
    context.videos_data = []
    context.data_confidence = "high"
    
    print(f"\n创作者Baseline Views: 80,000（预估价格$1200-2000）\n")
    
    for scenario_name, budget in scenarios:
        agent = PricingAgent()
        result = agent.execute(context, game_category="mobile_game", budget_range=budget)
        
        print(f"场景: {scenario_name}")
        if result["status"] == "success":
            card = result["pricing_card"]
            print(f"  ✓ 报价: ${card['floor_price']:,}-${card['anchor_price']:,}")
            if budget:
                print(f"    适配预算: ${budget[0]:,}-${budget[1]:,}")
        elif result["status"] == "error":
            print(f"  ✗ {result['message']}")
        print()


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print("报价计算Agent演示")
    print("=" * 80)
    
    # 运行所有演示
    demo_pricing()
    demo_different_regions()
    demo_budget_scenarios()
    
    print("\n" + "=" * 80)
    print("所有演示运行完成！")
    print("=" * 80)
