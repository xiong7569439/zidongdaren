"""
实际运行示例 - 使用真实API

使用前请确保：
1. 在 config.yaml 中配置 YouTube API Key
2. 配置邮件发送方式（SMTP或SendGrid）
3. 或设置环境变量

获取YouTube API Key:
https://console.cloud.google.com/apis/credentials

环境变量设置（可选）:
- YOUTUBE_API_KEY: YouTube Data API Key
- SMTP_USER: 邮箱地址
- SMTP_PASSWORD: 邮箱密码
"""
import os
import sys

# 检查配置
from src.config import get_config, reload_config

config = get_config()

print("=" * 80)
print("YouTube网红曝光合作系统 - 实际运行示例")
print("=" * 80)

# 检查YouTube API配置
if not config.youtube_api.api_key:
    print("\n⚠️ 警告: YouTube API Key未配置")
    print("请执行以下操作之一：")
    print("1. 在 config.yaml 中设置 youtube_api.api_key")
    print("2. 设置环境变量 YOUTUBE_API_KEY")
    print("\n获取API Key: https://console.cloud.google.com/apis/credentials")
    print("\n继续以模拟模式运行...\n")
else:
    print(f"\n✓ YouTube API 已配置")
    print(f"  API Key: {config.youtube_api.api_key[:10]}...")

# 检查邮件配置
if config.email.mode == "mock":
    print(f"\n✓ 邮件模式: 模拟模式 (邮件不会实际发送)")
    print("  要实际发送邮件，请在 config.yaml 中配置 SMTP 或 SendGrid")
elif config.email.mode == "smtp":
    if config.email.smtp.user and config.email.smtp.password:
        print(f"\n✓ 邮件模式: SMTP")
        print(f"  服务器: {config.email.smtp.host}:{config.email.smtp.port}")
        print(f"  用户: {config.email.smtp.user}")
    else:
        print(f"\n⚠️ 邮件模式: SMTP (未配置完整)")
        print("  请在 config.yaml 中设置 smtp.user 和 smtp.password")

print("\n" + "=" * 80)

# 导入系统组件
from src.core import AgentOrchestrator, PipelineStage
from src.tools import YouTubeAPITool, EmailTool


def demo_with_real_api():
    """使用真实API的演示"""
    
    # 初始化工具
    youtube_api = None
    if config.youtube_api.api_key:
        youtube_api = YouTubeAPITool(config.youtube_api.api_key)
        # 测试API连接
        print("\n测试YouTube API连接...")
        test_result = youtube_api.get_channel_by_url("https://www.youtube.com/@YouTube")
        if test_result.get("status") == "success":
            print(f"✓ API连接成功")
            print(f"  测试频道: {test_result.get('channel_title')}")
        else:
            print(f"✗ API连接失败: {test_result.get('error')}")
            youtube_api = None
    
    # 初始化邮件工具
    email_tool = None
    if config.email.mode == "smtp" and config.email.smtp.user:
        email_tool = EmailTool(
            smtp_host=config.email.smtp.host,
            smtp_port=config.email.smtp.port,
            smtp_user=config.email.smtp.user,
            smtp_password=config.email.smtp.password,
            mock_mode=False
        )
    elif config.email.mode == "mock":
        email_tool = EmailTool(mock_mode=True)
    
    # 创建测试线索
    print("\n" + "-" * 80)
    print("创建测试线索...")
    
    test_channels = [
        {
            "url": "https://www.youtube.com/@MrBeast",
            "name": "MrBeast"
        },
        {
            "url": "https://www.youtube.com/@PewDiePie",
            "name": "PewDiePie"
        }
    ]
    
    orchestrator = AgentOrchestrator()
    contexts = []
    
    for channel in test_channels:
        ctx = orchestrator.create_lead(channel["url"], channel["name"])
        contexts.append(ctx)
        print(f"  ✓ {channel['name']}: {ctx.current_stage.value}")
    
    # 数据采集（使用真实API）
    if youtube_api:
        print("\n" + "-" * 80)
        print("执行数据采集（使用真实YouTube API）...")
        
        from src.core import DataCollectionAgent
        
        agent = DataCollectionAgent(config.youtube_api.api_key)
        
        for ctx in contexts:
            print(f"\n  采集: {ctx.creator_name}")
            result = agent.execute(ctx, video_count=10)  # 只采集10条视频用于演示
            
            if result["status"] == "success":
                profile = result.get("creator_profile", {})
                metrics = result.get("metrics", {})
                
                print(f"    ✓ 频道: {profile.get('channel_title')}")
                print(f"    ✓ 订阅数: {profile.get('subscriber_count', 'N/A'):,}")
                print(f"    ✓ 视频数: {profile.get('video_count', 'N/A'):,}")
                print(f"    ✓ 平均播放量: {metrics.get('mean_views', 0):,.0f}")
                print(f"    ✓ 置信度: {result.get('data_confidence')}")
            else:
                print(f"    ✗ 失败: {result.get('message')}")
    else:
        print("\n跳过数据采集（未配置API）")
    
    # 邮件发送测试
    if email_tool:
        print("\n" + "-" * 80)
        print("测试邮件发送...")
        
        result = email_tool.send_outreach_email(
            to_addr="test@example.com",
            creator_name="Test Creator",
            subject="Test Email",
            body="This is a test email from the YouTube Agent system."
        )
        
        if result["status"] == "success":
            print(f"  ✓ 邮件发送成功")
            print(f"    模式: {result.get('method', 'mock')}")
            print(f"    消息ID: {result.get('message_id')}")
        else:
            print(f"  ✗ 发送失败: {result.get('error')}")
    
    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)


def interactive_mode():
    """交互模式 - 输入YouTube频道URL进行处理"""
    print("\n" + "=" * 80)
    print("交互模式")
    print("=" * 80)
    print("输入YouTube频道URL进行处理（输入 'quit' 退出）")
    
    orchestrator = AgentOrchestrator()
    
    while True:
        print("\n" + "-" * 80)
        url = input("\n频道URL: ").strip()
        
        if url.lower() in ['quit', 'exit', 'q']:
            break
        
        if not url.startswith('https://www.youtube.com/'):
            print("⚠️ 无效的YouTube URL")
            continue
        
        name = input("创作者名称（可选，直接回车自动获取）: ").strip()
        
        print(f"\n开始处理: {url}")
        
        # 创建线索
        ctx = orchestrator.create_lead(url, name or "Unknown")
        print(f"✓ 线索已创建: {ctx.current_stage.value}")
        
        # 如果配置了API，执行数据采集
        if config.youtube_api.api_key:
            from src.core import DataCollectionAgent
            
            print("\n执行数据采集...")
            agent = DataCollectionAgent(config.youtube_api.api_key)
            result = agent.execute(ctx, video_count=10)
            
            if result["status"] == "success":
                profile = result.get("creator_profile", {})
                print(f"✓ 数据采集完成")
                print(f"  频道: {profile.get('channel_title')}")
                print(f"  订阅数: {profile.get('subscriber_count', 'N/A'):,}")
                print(f"  置信度: {result.get('data_confidence')}")
            else:
                print(f"✗ 数据采集失败: {result.get('message')}")
        
        print(f"\n当前状态: {ctx.current_stage.value}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube网红曝光合作系统')
    parser.add_argument('--interactive', '-i', action='store_true', 
                       help='进入交互模式')
    parser.add_argument('--demo', '-d', action='store_true',
                       help='运行演示')
    
    args = parser.parse_args()
    
    if args.interactive:
        interactive_mode()
    else:
        demo_with_real_api()
