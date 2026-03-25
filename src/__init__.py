"""
YouTube网红曝光合作系统 - 主入口
"""
from src.core import (
    AgentOrchestrator,
    PipelineStage,
    PipelineContext,
)
from src.tools import (
    WebFetchTool,
    YouTubeAPITool,
    EmailTool,
    CRMStorage,
    StorageTool,
)


def main():
    """
    系统主入口
    
    使用示例：
    
    1. 初始化系统
        orchestrator = AgentOrchestrator()
    
    2. 创建新线索
        context = orchestrator.create_lead(
            channel_url="https://www.youtube.com/@example",
            creator_name="Example Creator"
        )
    
    3. 运行Pipeline（自动执行到需要人工干预）
        result = orchestrator.run_pipeline(
            channel_url="https://www.youtube.com/@example",
            auto_run=True
        )
    
    4. 处理收到的回复
        result = orchestrator.handle_incoming_reply(
            channel_url="https://www.youtube.com/@example",
            email_content="对方邮件内容..."
        )
    
    5. 人工审批后继续
        result = orchestrator.approve_and_continue(
            channel_url="https://www.youtube.com/@example",
            approval_notes="已确认报价"
        )
    
    6. 生成日报
        report = orchestrator.generate_daily_report(date="2026-03-25")
    """
    print("YouTube网红曝光合作系统")
    print("=" * 50)
    print("系统已初始化，请使用AgentOrchestrator类进行操作")
    print()
    print("快速开始：")
    print("  orchestrator = AgentOrchestrator()")
    print("  context = orchestrator.create_lead('https://www.youtube.com/@channel')")
    print("  result = orchestrator.run_pipeline('https://www.youtube.com/@channel')")


if __name__ == "__main__":
    main()
