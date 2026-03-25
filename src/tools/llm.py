"""
LLM工具接口 - 集成AI模型生成邮件和谈判回复
支持多种LLM提供商：OpenAI、Anthropic、Azure、阿里云百炼等
"""
from typing import Dict, Any, Optional, List
import os
import json


class LLMTool:
    """
    LLM工具 - 用于生成个性化邮件和谈判回复
    """
    
    # 阿里云百炼默认配置
    # 注意：阿里云百炼使用OpenAI兼容模式，但端点是 /v1/chat/completions
    ALIBABA_BAILIAN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ALIBABA_BAILIAN_DEFAULT_MODEL = "qwen-plus"
    
    # DeepSeek默认配置
    DEEPSEEK_BASE_URL = "https://api.deepseek.com"
    DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"
    
    def __init__(self, 
                 provider: str = "openai",
                 api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 base_url: Optional[str] = None):
        """
        初始化LLM工具
        
        Args:
            provider: LLM提供商 (openai/anthropic/azure/alibaba/deepseek)
            api_key: API密钥
            model: 模型名称
            base_url: 自定义API基础URL（用于兼容OpenAI格式的服务）
        """
        self.provider = provider.lower()
        self.api_key = api_key or self._get_api_key_from_env()
        self.model = model or self._get_default_model()
        self.base_url = base_url or self._get_default_base_url()
        
    def _get_api_key_from_env(self) -> Optional[str]:
        """从环境变量获取API Key"""
        env_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "azure": "AZURE_OPENAI_API_KEY",
            "alibaba": "ALIBABA_BAILIAN_API_KEY",
            "bailian": "ALIBABA_BAILIAN_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY"
        }
        return os.getenv(env_vars.get(self.provider, "OPENAI_API_KEY"))
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        defaults = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "azure": "gpt-4",
            "alibaba": self.ALIBABA_BAILIAN_DEFAULT_MODEL,
            "bailian": self.ALIBABA_BAILIAN_DEFAULT_MODEL,
            "deepseek": self.DEEPSEEK_DEFAULT_MODEL
        }
        return defaults.get(self.provider, "gpt-4o-mini")
    
    def _get_default_base_url(self) -> Optional[str]:
        """获取默认API基础URL"""
        if self.provider in ["alibaba", "bailian"]:
            return self.ALIBABA_BAILIAN_BASE_URL
        elif self.provider == "deepseek":
            return self.DEEPSEEK_BASE_URL
        return None
    
    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return self.api_key is not None
    
    def generate_mock_email(self,
                           creator_name: str,
                           game_name: str,
                           recent_videos: List[Dict],
                           baseline_views: int) -> Dict[str, Any]:
        """生成模拟邮件（用于测试）"""
        video_titles = [v.get('title', '') for v in recent_videos[:2]]
        
        body = f"""Hi {creator_name},

I hope this message finds you well. I've been following your channel and was particularly impressed by your recent videos, especially "{video_titles[0] if video_titles else 'your content'}" which has gained significant traction.

I'm reaching out from TOPUPlive regarding a potential collaboration opportunity for {game_name}. Based on your content style and audience engagement (averaging {baseline_views:,} views), I believe this partnership could be mutually beneficial.

We'd love to discuss how we can work together. Would you be open to a quick 15-minute call this week to explore this opportunity? Alternatively, feel free to share your media kit or rate card.

Looking forward to hearing from you!

Best regards,
TOPUPlive Partnership Team"""
        
        return {
            "status": "success",
            "subject_options": [
                f"Collaboration opportunity: {game_name}",
                f"Partnership proposal for {creator_name}",
                f"Sponsored content opportunity"
            ],
            "body": body,
            "personalization_note": f"Referenced recent videos: {', '.join(video_titles)}",
            "word_count": len(body.split()),
            "mock": True
        }
    
    def generate_outreach_email(self,
                                creator_name: str,
                                game_name: str,
                                recent_videos: List[Dict],
                                baseline_views: int,
                                language: str = "en") -> Dict[str, Any]:
        """
        生成首封合作邮件
        
        Args:
            creator_name: 创作者名称
            game_name: 游戏名称
            recent_videos: 最近视频列表
            baseline_views: 基线播放量
            language: 语言 (en/zh)
        """
        if not self.is_available():
            return {
                "status": "error",
                "error": "LLM API Key未配置",
                "fallback": True
            }
        
        # 构建视频引用
        video_mentions = []
        for i, video in enumerate(recent_videos[:3]):
            video_mentions.append(f"- {video.get('title', '')} ({video.get('views', 0):,} views)")
        
        video_text = "\n".join(video_mentions)
        
        # 构建prompt
        system_prompt = """You are an expert outreach specialist for gaming influencer partnerships.
Your task is to write personalized, compelling outreach emails to YouTube creators.

Guidelines:
1. Keep the email under 180 words
2. Be specific - mention their actual video titles and performance
3. Show you understand their content
4. Include a clear CTA (call to action)
5. Be professional but friendly
6. Don't use generic templates - make it personal"""

        user_prompt = f"""Write an outreach email to {creator_name} about a collaboration opportunity for {game_name}.

Creator Stats:
- Baseline views: {baseline_views:,}

Recent Videos:
{video_text}

Requirements:
- Subject line: 3 options
- Body: Under 180 words
- Tone: Professional but enthusiastic
- CTA: Ask for their media kit or a 15-min call

Output format (JSON):
{{
    "subject_options": ["option1", "option2", "option3"],
    "body": "email body here",
    "personalization_note": "what specific detail shows this is personalized"
}}"""

        try:
            result = self._call_api(system_prompt, user_prompt)
            
            # 解析JSON响应
            content = result.get("content", "")
            # 提取JSON部分
            json_match = self._extract_json(content)
            
            if json_match:
                email_data = json.loads(json_match)
                return {
                    "status": "success",
                    "subject_options": email_data.get("subject_options", []),
                    "body": email_data.get("body", ""),
                    "personalization_note": email_data.get("personalization_note", ""),
                    "word_count": len(email_data.get("body", "").split())
                }
            else:
                # 返回原始文本
                return {
                    "status": "success",
                    "subject_options": [f"Collaboration: {game_name}"],
                    "body": content,
                    "personalization_note": "Generated by AI",
                    "word_count": len(content.split())
                }
                
        except Exception as e:
            # API调用失败，使用模拟模式
            print(f"⚠️ LLM API调用失败: {e}")
            print("📝 使用模拟邮件生成...")
            mock_result = self.generate_mock_email(creator_name, game_name, recent_videos, baseline_views)
            mock_result["api_error"] = str(e)
            return mock_result
    
    def generate_negotiation_reply(self,
                                   creator_name: str,
                                   game_name: str,
                                   reply_type: str,
                                   their_message: str,
                                   pricing_card: Dict,
                                   context: Dict) -> Dict[str, Any]:
        """
        生成谈判回复
        
        Args:
            creator_name: 创作者名称
            game_name: 游戏名称
            reply_type: 回复类型 (price_objection/accept/decline/question)
            their_message: 对方的消息内容
            pricing_card: 报价卡信息
            context: 上下文信息
        """
        if not self.is_available():
            return {
                "status": "error",
                "error": "LLM API Key未配置"
            }
        
        system_prompt = """You are a skilled partnership negotiator for gaming influencer collaborations.
You need to respond to creator inquiries professionally and persuasively.

Guidelines:
1. Be respectful and understanding
2. Address their specific concerns
3. Provide clear options when appropriate
4. Don't make promises you can't keep
5. Keep responses concise and professional"""

        user_prompt = f"""Respond to this message from {creator_name} about collaborating on {game_name}.

Their message: "{their_message}"

Detected intent: {reply_type}

Our pricing:
- Anchor: ${pricing_card.get('anchor_price', 0)}
- Target: ${pricing_card.get('target_price', 0)}
- Floor: ${pricing_card.get('floor_price', 0)}

Context:
- Baseline views: {context.get('baseline_views', 'N/A')}
- Previous emails: {len(context.get('email_history', []))}

Generate an appropriate response based on their intent."""

        try:
            result = self._call_api(system_prompt, user_prompt)
            
            return {
                "status": "success",
                "reply": result.get("content", ""),
                "reply_type": reply_type
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def analyze_creator_fit(self,
                           videos: List[Dict],
                           target_game_category: str) -> Dict[str, Any]:
        """
        分析创作者与游戏的匹配度
        
        Args:
            videos: 视频列表
            target_game_category: 目标游戏品类
        """
        if not self.is_available():
            return {
                "status": "error",
                "error": "LLM API Key未配置"
            }
        
        # 构建视频文本
        video_text = "\n".join([
            f"- {v.get('title', '')}" for v in videos[:10]
        ])
        
        system_prompt = """You are a gaming marketing analyst. Analyze YouTube creator content to determine fit for game partnerships."""

        user_prompt = f"""Analyze this creator's content fit for {target_game_category} partnerships.

Recent video titles:
{video_text}

Provide analysis in JSON format:
{{
    "content_match_score": 1-10,
    "primary_content_type": "gaming/vlog/review/etc",
    "audience_alignment": "description",
    "partnership_potential": "high/medium/low",
    "recommended_approach": "specific recommendation"
}}"""

        try:
            result = self._call_api(system_prompt, user_prompt)
            json_match = self._extract_json(result.get("content", ""))
            
            if json_match:
                return {
                    "status": "success",
                    "analysis": json.loads(json_match)
                }
            else:
                return {
                    "status": "success",
                    "analysis": {
                        "content_match_score": 5,
                        "note": "Raw response",
                        "raw": result.get("content", "")
                    }
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _call_api(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """调用LLM API"""
        if self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        else:
            # 默认使用OpenAI格式
            return self._call_openai(system_prompt, user_prompt)
    
    def _call_openai(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """调用OpenAI API（兼容阿里云百炼）"""
        import requests
        
        # 阿里云百炼和DeepSeek使用OpenAI兼容格式
        if self.provider in ["alibaba", "bailian"]:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        elif self.provider == "deepseek":
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        else:
            url = self.base_url or "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return {
                "content": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {})
            }
        except requests.exceptions.HTTPError as e:
            error_msg = f"API错误: {e}"
            try:
                error_detail = response.json()
                error_msg = f"API错误: {error_detail.get('error', {}).get('message', str(e))}"
            except:
                pass
            raise Exception(error_msg)
    
    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """调用Anthropic Claude API"""
        import requests
        
        url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": self.model,
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt}
            ]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        return {
            "content": result["content"][0]["text"],
            "usage": result.get("usage", {})
        }
    
    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON"""
        import re
        
        # 尝试匹配代码块
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # 尝试匹配普通JSON对象
        json_match = re.search(r'(\{[\s\S]*\})', text)
        if json_match:
            return json_match.group(1)
        
        return None
