"""
数据采集Agent演示脚本
"""
from src.core import AgentOrchestrator, PipelineStage


def demo():
    """演示完整流程"""
    print("=" * 80)
    print("YouTube网红曝光合作系统 - 数据采集演示")
    print("=" * 80)
    
    # 1. 初始化编排器
    print("\n[1/5] 初始化系统...")
    orchestrator = AgentOrchestrator()
    print("✓ 编排器初始化完成")
    
    # 2. 创建新线索
    print("\n[2/5] 创建线索...")
    channel_url = "https://www.youtube.com/@DemoGamingChannel"
    creator_name = "Demo Gaming Channel"
    
    context = orchestrator.create_lead(channel_url, creator_name)
    print(f"✓ 线索已创建: {creator_name}")
    print(f"  初始状态: {context.current_stage.value}")
    
    # 3. 运行Pipeline
    print("\n[3/5] 执行数据采集...")
    print(f"  目标URL: {channel_url}")
    print(f"  注意：实际运行时会进行网络请求，这里使用模拟数据")
    
    # 为了演示，我们直接模拟数据采集结果
    from src.core import DataCollectionAgent
    
    agent = DataCollectionAgent()
    
    # 模拟执行（实际使用时会真的去抓取）
    result = {
        "status": "success",
        "creator_profile": {
            "creator_name": "Demo Gaming Channel",
            "channel_url": channel_url,
            "subscriber_count": 250000,
            "total_view_count": 15000000,
            "language_guess": "en",
            "region_guess": "US",
            "content_focus": ["Gaming"],
            "content_types": ["长视频为主"],
            "notes": "基于最近30条视频分析"
        },
        "videos_table": [
            {
                "video_url": "https://www.youtube.com/watch?v=demo1",
                "title": "Epic Game Review 2024",
                "published_text": "3 days ago",
                "is_shorts": False,
                "duration_seconds": 1200,
                "views": 125000,
                "likes": None,
                "comments": None,
                "is_suspected_sponsored": False,
                "sponsor_evidence": "",
                "source": "demo"
            },
            {
                "video_url": "https://www.youtube.com/watch?v=demo2",
                "title": "Top 10 RPG Games",
                "published_text": "1 week ago",
                "is_shorts": False,
                "duration_seconds": 900,
                "views": 98000,
                "likes": None,
                "comments": None,
                "is_suspected_sponsored": True,
                "sponsor_evidence": "标题含#ad",
                "source": "demo"
            },
            {
                "video_url": "https://www.youtube.com/watch?v=demo3",
                "title": "Quick Gaming Tips #shorts",
                "published_text": "2 weeks ago",
                "is_shorts": True,
                "duration_seconds": 45,
                "views": 45000,
                "likes": None,
                "comments": None,
                "is_suspected_sponsored": False,
                "sponsor_evidence": "",
                "source": "demo"
            }
        ],
        "metrics": {
            "video_count": 30,
            "mean_views": 87500,
            "median_views": 82000,
            "p75_views": 115000,
            "baseline_views": 82000,
            "viral_rate": 0.13,
            "avg_duration_seconds": 680,
            "shorts_ratio": 0.15,
            "formulas": {
                "mean_views": "sum(views) / count",
                "median_views": "sorted(views)[n//2]",
                "p75_views": "sorted(views)[int(n*0.75)]",
                "viral_rate": "count(views > P75*1.5) / total",
                "baseline_views": "max(median_views, mean_views * 0.8)"
            }
        },
        "data_confidence": "high",
        "next_step": "YES",
        "message": "数据采集完成，置信度: high"
    }
    
    # 更新上下文
    context.creator_profile = result["creator_profile"]
    context.videos_data = result["videos_table"]
    context.data_confidence = result["data_confidence"]
    
    # 手动流转状态（模拟Pipeline执行）
    from src.core import PipelineEngine
    engine = PipelineEngine(context)
    engine.transition(PipelineStage.DATA_COLLECTING, "开始数据采集")
    engine.transition(PipelineStage.DATA_READY, "数据采集完成")
    
    print("✓ 数据采集完成")
    
    # 4. 展示结果
    print("\n[4/5] 数据采集结果:")
    print("-" * 80)
    
    # 创作者画像
    profile = result["creator_profile"]
    print(f"\n📊 创作者画像:")
    print(f"  名称: {profile['creator_name']}")
    print(f"  订阅数: {profile['subscriber_count']:,}")
    print(f"  总播放量: {profile['total_view_count']:,}")
    print(f"  语言: {profile['language_guess']}")
    print(f"  地区: {profile['region_guess']}")
    print(f"  内容焦点: {', '.join(profile['content_focus'])}")
    print(f"  内容类型: {', '.join(profile['content_types'])}")
    
    # 关键指标
    metrics = result["metrics"]
    print(f"\n📈 关键指标（最近{metrics['video_count']}条视频）:")
    print(f"  平均播放: {metrics['mean_views']:,.0f}")
    print(f"  中位数播放: {metrics['median_views']:,.0f}")
    print(f"  P75播放: {metrics['p75_views']:,.0f}")
    print(f"  基线播放: {metrics['baseline_views']:,.0f} (用于定价)")
    print(f"  爆款率: {metrics['viral_rate']*100:.1f}%")
    print(f"  平均时长: {metrics['avg_duration_seconds']:.0f}秒")
    print(f"  Shorts比例: {metrics['shorts_ratio']*100:.1f}%")
    
    # 视频列表
    print(f"\n📹 视频列表明细（前3条）:")
    for i, video in enumerate(result["videos_table"], 1):
        print(f"  {i}. {video['title']}")
        print(f"     播放: {video['views']:,} | 时长: {video['duration_seconds']}s | Shorts: {video['is_shorts']}")
        if video['is_suspected_sponsored']:
            print(f"     ⚠ 疑似商单: {video['sponsor_evidence']}")
    
    print(f"\n✓ 数据置信度: {result['data_confidence']}")
    print(f"✓ 下一步: 进入定价阶段 ({result['next_step']})")
    
    # 5. 查看状态
    print("\n[5/5] 当前Pipeline状态:")
    print(f"  当前状态: {context.current_stage.value}")
    print(f"  状态历史:")
    for history in context.stage_history:
        print(f"    - {history['from']} → {history['to']} ({history['reason']})")
    
    # 查看CRM记录
    crm_records = orchestrator.get_crm_records(channel_url)
    print(f"\n📝 CRM记录:")
    for record in crm_records:
        print(f"  - [{record['timestamp'][:19]}] {record['action']}: {record['result']}")
    
    print("\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)
    print("\n下一步可以:")
    print("  1. 运行定价Agent计算报价")
    print("  2. 查找创作者联系方式")
    print("  3. 生成首封合作邮件")


if __name__ == "__main__":
    demo()
