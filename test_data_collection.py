"""
数据采集Agent测试脚本
"""
import sys
import json
from src.core import PipelineContext, DataCollectionAgent


def test_data_collection():
    """测试数据采集功能"""
    
    # 测试用的YouTube频道（使用一个知名的游戏频道作为示例）
    test_channels = [
        {
            "url": "https://www.youtube.com/@MrBeast",
            "name": "MrBeast"
        },
        # 可以添加更多测试频道
    ]
    
    print("=" * 80)
    print("YouTube数据采集Agent测试")
    print("=" * 80)
    
    for channel in test_channels:
        print(f"\n测试频道: {channel['name']}")
        print(f"URL: {channel['url']}")
        print("-" * 80)
        
        # 创建PipelineContext
        context = PipelineContext(
            channel_url=channel["url"],
            creator_name=channel["name"]
        )
        
        # 创建Agent并执行
        agent = DataCollectionAgent()
        
        try:
            result = agent.execute(context, video_count=10)  # 先测试采集10条
            
            print(f"\n采集状态: {result['status']}")
            print(f"数据置信度: {result['data_confidence']}")
            print(f"下一步: {result['next_step']}")
            print(f"消息: {result['message']}")
            
            if result['status'] == 'success':
                # 打印创作者画像
                profile = result.get('creator_profile', {})
                print(f"\n创作者画像:")
                print(f"  - 名称: {profile.get('creator_name', 'N/A')}")
                print(f"  - 订阅数: {profile.get('subscriber_count', 'N/A')}")
                print(f"  - 总播放量: {profile.get('total_view_count', 'N/A')}")
                print(f"  - 语言推断: {profile.get('language_guess', 'N/A')}")
                print(f"  - 地区推断: {profile.get('region_guess', 'N/A')}")
                print(f"  - 内容焦点: {profile.get('content_focus', [])}")
                
                # 打印指标
                metrics = result.get('metrics', {})
                print(f"\n关键指标:")
                print(f"  - 视频数: {metrics.get('video_count', 0)}")
                print(f"  - 平均播放: {metrics.get('mean_views', 0):,.0f}")
                print(f"  - 中位数播放: {metrics.get('median_views', 0):,.0f}")
                print(f"  - P75播放: {metrics.get('p75_views', 0):,.0f}")
                print(f"  - 基线播放: {metrics.get('baseline_views', 0):,.0f}")
                print(f"  - 爆款率: {metrics.get('viral_rate', 0)*100:.1f}%")
                print(f"  - Shorts比例: {metrics.get('shorts_ratio', 0)*100:.1f}%")
                
                # 打印视频列表明细（前3条）
                videos = result.get('videos_table', [])
                print(f"\n视频列表明细（前3条）:")
                for i, video in enumerate(videos[:3], 1):
                    print(f"  {i}. {video['title'][:60]}...")
                    print(f"     播放: {video['views']:,.0f} | "
                          f"时长: {video['duration_seconds']}s | "
                          f"Shorts: {video['is_shorts']}")
            else:
                print(f"\n采集失败:")
                print(f"  错误类型: {result.get('error_type', 'unknown')}")
                print(f"  错误信息: {result.get('message', '')}")
                
                alternatives = result.get('alternatives', [])
                if alternatives:
                    print(f"\n  替代方案:")
                    for alt in alternatives:
                        print(f"    - {alt}")
            
            # 保存完整结果到文件
            output_file = f"test_result_{channel['name']}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n完整结果已保存到: {output_file}")
            
        except Exception as e:
            print(f"\n测试出错: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


def test_with_mock_data():
    """使用模拟数据测试（无需网络）"""
    print("\n" + "=" * 80)
    print("模拟数据测试（无需网络）")
    print("=" * 80)
    
    # 创建模拟的PipelineContext
    context = PipelineContext(
        channel_url="https://www.youtube.com/@TestGamer",
        creator_name="Test Gamer"
    )
    
    # 手动设置一些模拟数据
    context.creator_profile = {
        "creator_name": "Test Gamer",
        "channel_url": "https://www.youtube.com/@TestGamer",
        "subscriber_count": 500000,
        "language_guess": "en",
        "region_guess": "US",
        "content_focus": ["Gaming"],
        "notes": "模拟数据"
    }
    
    context.videos_data = [
        {
            "video_url": "https://www.youtube.com/watch?v=test1",
            "title": "Game Review 1",
            "views": 100000,
            "is_shorts": False,
            "duration_seconds": 600
        },
        {
            "video_url": "https://www.youtube.com/watch?v=test2",
            "title": "Game Review 2",
            "views": 150000,
            "is_shorts": False,
            "duration_seconds": 900
        },
        {
            "video_url": "https://www.youtube.com/watch?v=test3",
            "title": "Short Video",
            "views": 50000,
            "is_shorts": True,
            "duration_seconds": 30
        }
    ]
    
    context.data_confidence = "high"
    
    print(f"\n模拟创作者: {context.creator_name}")
    print(f"订阅数: {context.creator_profile['subscriber_count']:,}")
    print(f"视频数: {len(context.videos_data)}")
    print(f"数据置信度: {context.data_confidence}")
    
    print("\n模拟数据测试通过！")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="测试数据采集Agent")
    parser.add_argument("--mock", action="store_true", help="使用模拟数据测试（无需网络）")
    parser.add_argument("--url", type=str, help="测试指定的YouTube频道URL")
    
    args = parser.parse_args()
    
    if args.mock:
        test_with_mock_data()
    elif args.url:
        # 测试指定URL
        print("=" * 80)
        print(f"测试指定URL: {args.url}")
        print("=" * 80)
        
        context = PipelineContext(channel_url=args.url, creator_name="Custom")
        agent = DataCollectionAgent()
        
        try:
            result = agent.execute(context, video_count=5)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"错误: {e}")
            import traceback
            traceback.print_exc()
    else:
        # 默认运行完整测试
        test_data_collection()
