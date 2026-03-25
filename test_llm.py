"""
测试LLM配置 - 验证阿里云百炼是否正常工作
"""
import os
from pathlib import Path

# 加载.env文件
env_path = Path('.') / '.env'
if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value  # 直接设置，覆盖已有值

from src.tools.llm import LLMTool


def test_llm():
    """测试LLM连接"""
    print("=" * 80)
    print("LLM配置测试")
    print("=" * 80)
    print()
    
    # 检测配置
    provider = os.getenv("LLM_PROVIDER", "openai")
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("ALIBABA_BAILIAN_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    
    print(f"检测到配置:")
    print(f"  提供商: {provider}")
    print(f"  模型: {model}")
    print(f"  API Key: {api_key[:15]}..." if api_key else "  API Key: 未配置")
    print()
    
    if not api_key:
        print("❌ 未找到API Key，请先运行: python setup_llm.py")
        return
    
    # 初始化LLM工具
    llm = LLMTool(
        provider=provider,
        api_key=api_key,
        model=model
    )
    
    print("测试LLM连接...")
    if llm.is_available():
        print("✅ LLM工具初始化成功")
    else:
        print("❌ LLM工具初始化失败")
        return
    
    print()
    print("测试生成邮件...")
    
    # 测试生成邮件
    result = llm.generate_outreach_email(
        creator_name="Test Creator",
        game_name="Epic Battle Game",
        recent_videos=[
            {"title": "Amazing Gameplay Part 1", "views": 50000},
            {"title": "Epic Boss Fight", "views": 75000},
            {"title": "Tutorial for Beginners", "views": 100000}
        ],
        baseline_views=75000
    )
    
    if result["status"] == "success":
        print("✅ 邮件生成成功!")
        print()
        print("生成的邮件:")
        print("-" * 80)
        if result.get("subject_options"):
            print(f"主题选项: {result['subject_options']}")
        print()
        print(result.get("body", "No body generated"))
        print("-" * 80)
        print()
        print(f"个性化备注: {result.get('personalization_note', 'N/A')}")
        print(f"词数: {result.get('word_count', 0)}")
    else:
        print(f"❌ 邮件生成失败: {result.get('error', 'Unknown error')}")
        if result.get("fallback"):
            print("(使用了fallback模式)")


if __name__ == "__main__":
    test_llm()
