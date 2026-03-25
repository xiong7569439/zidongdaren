"""
LLM配置助手 - 快速配置阿里云百炼或其他LLM

使用方法:
    python setup_llm.py

获取阿里云百炼API Key:
    https://bailian.console.aliyun.com/
"""
import os
import sys


def setup_alibaba_bailian():
    """配置阿里云百炼"""
    print("=" * 80)
    print("阿里云百炼 LLM 配置")
    print("=" * 80)
    print()
    print("阿里云百炼提供兼容OpenAI格式的API，支持通义千问系列模型。")
    print()
    print("支持的模型:")
    print("  - qwen-plus (推荐，性价比高)")
    print("  - qwen-max (最强性能)")
    print("  - qwen-turbo (快速响应)")
    print()
    print("获取API Key: https://bailian.console.aliyun.com/")
    print()
    
    api_key = input("请输入阿里云百炼 API Key: ").strip()
    
    if not api_key:
        print("❌ API Key不能为空")
        return False
    
    model = input("请选择模型 [qwen-plus/qwen-max/qwen-turbo] (默认: qwen-plus): ").strip()
    if not model:
        model = "qwen-plus"
    
    # 写入.env文件
    env_content = f"""# LLM配置 - 阿里云百炼
LLM_PROVIDER=alibaba
ALIBABA_BAILIAN_API_KEY={api_key}
LLM_MODEL={model}
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print()
    print("✅ 配置已保存到 .env 文件")
    print()
    print("配置内容:")
    print(f"  提供商: alibaba")
    print(f"  模型: {model}")
    print(f"  API Key: {api_key[:10]}...")
    print()
    print("请重启Web应用以加载新配置:")
    print("  1. 按 Ctrl+C 停止当前服务")
    print("  2. 运行: python web_app.py")
    print()
    
    return True


def setup_openai():
    """配置OpenAI"""
    print("=" * 80)
    print("OpenAI LLM 配置")
    print("=" * 80)
    print()
    print("获取API Key: https://platform.openai.com/api-keys")
    print()
    
    api_key = input("请输入 OpenAI API Key: ").strip()
    
    if not api_key:
        print("❌ API Key不能为空")
        return False
    
    model = input("请选择模型 [gpt-4o-mini/gpt-4o/gpt-4] (默认: gpt-4o-mini): ").strip()
    if not model:
        model = "gpt-4o-mini"
    
    env_content = f"""# LLM配置 - OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY={api_key}
LLM_MODEL={model}
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print()
    print("✅ 配置已保存到 .env 文件")
    print()
    print("请重启Web应用以加载新配置")
    
    return True


def setup_anthropic():
    """配置Anthropic Claude"""
    print("=" * 80)
    print("Anthropic Claude LLM 配置")
    print("=" * 80)
    print()
    print("获取API Key: https://console.anthropic.com/")
    print()
    
    api_key = input("请输入 Anthropic API Key: ").strip()
    
    if not api_key:
        print("❌ API Key不能为空")
        return False
    
    model = input("请选择模型 [claude-3-haiku/claude-3-sonnet/claude-3-opus] (默认: claude-3-haiku): ").strip()
    if not model:
        model = "claude-3-haiku-20240307"
    
    env_content = f"""# LLM配置 - Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY={api_key}
LLM_MODEL={model}
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print()
    print("✅ 配置已保存到 .env 文件")
    print()
    print("请重启Web应用以加载新配置")
    
    return True


def setup_deepseek():
    """配置DeepSeek"""
    print("=" * 80)
    print("DeepSeek LLM 配置")
    print("=" * 80)
    print()
    print("DeepSeek提供高性能的AI模型，性价比高。")
    print()
    print("支持的模型:")
    print("  - deepseek-chat (推荐，通用对话)")
    print("  - deepseek-coder (代码生成)")
    print()
    print("获取API Key: https://platform.deepseek.com/")
    print()
    
    api_key = input("请输入 DeepSeek API Key: ").strip()
    
    if not api_key:
        print("❌ API Key不能为空")
        return False
    
    model = input("请选择模型 [deepseek-chat/deepseek-coder] (默认: deepseek-chat): ").strip()
    if not model:
        model = "deepseek-chat"
    
    env_content = f"""# LLM配置 - DeepSeek
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY={api_key}
LLM_MODEL={model}
"""
    
    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_content)
    
    print()
    print("✅ 配置已保存到 .env 文件")
    print()
    print("配置内容:")
    print(f"  提供商: deepseek")
    print(f"  模型: {model}")
    print(f"  API Key: {api_key[:10]}...")
    print()
    print("请重启Web应用以加载新配置:")
    print("  1. 按 Ctrl+C 停止当前服务")
    print("  2. 运行: python web_app.py")
    print()
    
    return True


def main():
    """主函数"""
    print("=" * 80)
    print("LLM 配置助手")
    print("=" * 80)
    print()
    print("选择LLM提供商:")
    print("  1. DeepSeek (推荐，性价比高)")
    print("  2. 阿里云百炼 (国内用户)")
    print("  3. OpenAI")
    print("  4. Anthropic Claude")
    print()
    
    choice = input("请输入选项 [1/2/3/4]: ").strip()
    
    if choice == "1":
        setup_deepseek()
    elif choice == "2":
        setup_alibaba_bailian()
    elif choice == "3":
        setup_openai()
    elif choice == "4":
        setup_anthropic()
    else:
        print("❌ 无效选项")
        sys.exit(1)


if __name__ == "__main__":
    main()
