"""
数据采集Agent使用示例
展示如何在实际流程中使用DataCollectionAgent
"""
from src.core import AgentOrchestrator, PipelineStage


def example_full_pipeline():
    """
    示例：完整的Pipeline流程
    从创建线索到数据采集
    """
    print("=" * 80)
    print("示例：使用AgentOrchestrator运行完整Pipeline")
    print("=" * 80)
    
    # 1. 初始化编排器
    orchestrator = AgentOrchestrator()
    print("\n✓ 编排器初始化完成")
    
    # 2. 创建新线索
    channel_url = "https://www.youtube.com/@TestGamingChannel"
    creator_name = "Test Gaming Channel"
    
    context = orchestrator.create_lead(channel_url, creator_name)
    print(f"\n✓ 线索已创建")
    print(f"  - 频道: {creator_name}")
    print(f"  - URL: {channel_url}")
    print(f"  - 当前状态: {context.current_stage.value}")
    
    # 3. 运行Pipeline（会自动执行数据采集）
    print(f"\n▶ 开始运行Pipeline...")
    result = orchestrator.run_pipeline(channel_url, auto_run=True)
    
    print(f"\n✓ Pipeline执行结果:")
    print(f"  - 最终状态: {result['final_stage']}")
    
    # 4. 查看采集结果
    context = orchestrator.get_context(channel_url)
    
    if context.creator_profile:
        print(f"\n📊 创作者画像:")
        profile = context.creator_profile
        print(f"  - 名称: {profile.get('creator_name', 'N/A')}")
        print(f"  - 订阅数: {profile.get('subscriber_count', 'N/A')}")
        print(f"  - 语言: {profile.get('language_guess', 'N/A')}")
        print(f"  - 地区: {profile.get('region_guess', 'N/A')}")
    
    if context.videos_data:
        print(f"\n📹 视频数据:")
        print(f"  - 采集数量: {len(context.videos_data)}")
        if context.videos_data:
            print(f"  - 第一条: {context.videos_data[0]['title'][:50]}...")
    
    print(f"\n📈 数据置信度: {context.data_confidence}")
    
    # 5. 查看CRM记录
    crm_records = orchestrator.get_crm_records(channel_url)
    print(f"\n📝 CRM记录数: {len(crm_records)}")
    for record in crm_records:
        print(f"  - [{record['timestamp']}] {record['action']}: {record['result']}")
    
    print("\n" + "=" * 80)


def example_direct_agent_usage():
    """
    示例：直接使用DataCollectionAgent
    适用于需要更精细控制的场景
    """
    print("=" * 80)
    print("示例：直接使用DataCollectionAgent")
    print("=" * 80)
    
    from src.core import PipelineContext, DataCollectionAgent
    
    # 1. 创建Context
    context = PipelineContext(
        channel_url="https://www.youtube.com/@AnotherTestChannel",
        creator_name="Another Test Channel"
    )
    print(f"\n✓ Context已创建")
    
    # 2. 创建Agent（可以传入YouTube API Key）
    # agent = DataCollectionAgent(youtube_api_key="YOUR_API_KEY")
    agent = DataCollectionAgent()  # 使用网页抓取模式
    print(f"✓ Agent已创建")
    
    # 3. 执行数据采集
    print(f"\n▶ 开始数据采集...")
    print(f"  - 目标: {context.channel_url}")
    
    # 注意：这里会使用网络请求，实际运行时需要网络连接
    # 为了演示，我们使用模拟数据
    result = {
        "status": "success",
        "creator_profile": {
            "creator_name": "Another Test Channel",
            "channel_url": context.channel_url,
            "subscriber_count": 100000,
            "language_guess": "en",
            "region_guess": "US",
            "content_focus": ["Gaming"],
            "notes": "模拟数据"
        },
        "videos_table": [
            {
                "video_url": "https://www.youtube.com/watch?v=example1",
                "title": "Example Game Review",
                "views": 50000,
                "is_shorts": False,
                "duration_seconds": 600
            }
        ],
        "metrics": {
            "video_count": 1,
            "mean_views": 50000,
            "median_views": 50000,
            "baseline_views": 50000,
            "viral_rate": 0.0
        },
        "data_confidence": "medium",
        "next_step": "YES"
    }
    
    # 更新Context
    context.creator_profile = result["creator_profile"]
    context.videos_data = result["videos_table"]
    context.data_confidence = result["data_confidence"]
    
    print(f"\n✓ 数据采集完成")
    print(f"  - 状态: {result['status']}")
    print(f"  - 置信度: {result['data_confidence']}")
    print(f"  - 下一步: {result['next_step']}")
    
    # 4. 查看执行日志
    print(f"\n📋 Agent执行日志:")
    for log in agent.execution_log:
        print(f"  - [{log['timestamp']}] {log['action']}: {log['result']}")
    
    print("\n" + "=" * 80)


def example_batch_processing():
    """
    示例：批量处理多个频道
    """
    print("=" * 80)
    print("示例：批量处理多个频道")
    print("=" * 80)
    
    orchestrator = AgentOrchestrator()
    
    # 批量创建线索
    channels = [
        {"url": "https://www.youtube.com/@Channel1", "name": "Channel 1"},
        {"url": "https://www.youtube.com/@Channel2", "name": "Channel 2"},
        {"url": "https://www.youtube.com/@Channel3", "name": "Channel 3"},
    ]
    
    print(f"\n▶ 批量创建 {len(channels)} 个线索...")
    
    for ch in channels:
        context = orchestrator.create_lead(ch["url"], ch["name"])
        print(f"  ✓ {ch['name']}: {context.current_stage.value}")
    
    # 查看所有线索
    all_contexts = orchestrator.get_all_contexts()
    print(f"\n📊 当前所有线索:")
    for ctx in all_contexts:
        print(f"  - {ctx.creator_name}: {ctx.current_stage.value}")
    
    # 生成日报
    print(f"\n▶ 生成日报...")
    report = orchestrator.generate_daily_report()
    
    if report.get("status") == "success":
        daily_report = report.get("daily_report", {})
        print(f"\n📈 日报摘要:")
        print(f"  - 日期: {daily_report.get('date', 'N/A')}")
        print(f"  - 新增线索: {len(daily_report.get('new_leads', []))}")
        print(f"  - Pipeline分布: {daily_report.get('pipeline_breakdown', [])}")
    
    print("\n" + "=" * 80)


def example_error_handling():
    """
    示例：错误处理和失败分支
    """
    print("=" * 80)
    print("示例：错误处理和失败分支")
    print("=" * 80)
    
    from src.core import PipelineContext, DataCollectionAgent
    
    # 模拟一个会失败的场景（无效URL）
    context = PipelineContext(
        channel_url="https://invalid-url.com/not-youtube",
        creator_name="Invalid Channel"
    )
    
    agent = DataCollectionAgent()
    
    print(f"\n▶ 尝试采集无效URL...")
    # 实际执行会失败，这里模拟失败结果
    result = {
        "status": "error",
        "error_type": "data_unavailable",
        "message": "无法获取频道数据: Invalid URL",
        "alternatives": [
            "使用YouTube Data API（需要API Key）",
            "手动补充频道数据",
            "使用第三方数据服务（如SocialBlade）"
        ]
    }
    
    print(f"\n⚠ 采集失败:")
    print(f"  - 错误类型: {result['error_type']}")
    print(f"  - 错误信息: {result['message']}")
    
    print(f"\n💡 替代方案:")
    for alt in result['alternatives']:
        print(f"  - {alt}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import sys
    
    print("\n" + "=" * 80)
    print("数据采集Agent使用示例")
    print("=" * 80)
    
    # 运行所有示例
    examples = [
        ("完整Pipeline流程", example_full_pipeline),
        ("直接使用Agent", example_direct_agent_usage),
        ("批量处理", example_batch_processing),
        ("错误处理", example_error_handling),
    ]
    
    for i, (name, func) in enumerate(examples, 1):
        print(f"\n{'='*80}")
        print(f"示例 {i}/{len(examples)}: {name}")
        print(f"{'='*80}")
        func()
        if i < len(examples):
            input("\n按Enter继续下一个示例...")
    
    print("\n" + "=" * 80)
    print("所有示例运行完成！")
    print("=" * 80)
