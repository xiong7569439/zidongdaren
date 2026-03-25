"""
配置管理模块
"""
import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class YouTubeAPIConfig:
    """YouTube API配置"""
    api_key: str = ""
    enabled: bool = True


@dataclass
class SMTPConfig:
    """SMTP配置"""
    host: str = "smtp.gmail.com"
    port: int = 587
    user: str = ""
    password: str = ""
    use_tls: bool = True


@dataclass
class SendGridConfig:
    """SendGrid配置"""
    api_key: str = ""


@dataclass
class EmailConfig:
    """邮件配置"""
    mode: str = "mock"  # mock / smtp / sendgrid
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    sendgrid: SendGridConfig = field(default_factory=SendGridConfig)
    default_from: str = "cooperate@topuplive.com"


@dataclass
class CRMConfig:
    """CRM配置"""
    storage_type: str = "json"
    json_file: str = "data/crm_records.json"


@dataclass
class DataCollectionConfig:
    """数据采集配置"""
    default_video_count: int = 30
    confidence_threshold: str = "medium"
    prefer_api: bool = True


@dataclass
class PricingConfig:
    """报价配置"""
    default_cpm_min: int = 8
    default_cpm_max: int = 25


@dataclass
class Config:
    """全局配置"""
    youtube_api: YouTubeAPIConfig = field(default_factory=YouTubeAPIConfig)
    email: EmailConfig = field(default_factory=EmailConfig)
    crm: CRMConfig = field(default_factory=CRMConfig)
    data_collection: DataCollectionConfig = field(default_factory=DataCollectionConfig)
    pricing: PricingConfig = field(default_factory=PricingConfig)


def load_config(config_path: str = "config.yaml") -> Config:
    """
    从YAML文件加载配置
    
    优先级：
    1. 配置文件中的值
    2. 环境变量（覆盖配置文件）
    3. 默认值
    """
    config = Config()
    
    # 尝试读取配置文件
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if data:
            # YouTube API
            if 'youtube_api' in data:
                config.youtube_api.api_key = data['youtube_api'].get('api_key', '')
                config.youtube_api.enabled = data['youtube_api'].get('enabled', True)
            
            # Email
            if 'email' in data:
                email_data = data['email']
                config.email.mode = email_data.get('mode', 'mock')
                config.email.default_from = email_data.get('default_from', 'cooperate@topuplive.com')
                
                if 'smtp' in email_data:
                    smtp_data = email_data['smtp']
                    config.email.smtp.host = smtp_data.get('host', 'smtp.gmail.com')
                    config.email.smtp.port = smtp_data.get('port', 587)
                    config.email.smtp.user = smtp_data.get('user', '')
                    config.email.smtp.password = smtp_data.get('password', '')
                    config.email.smtp.use_tls = smtp_data.get('use_tls', True)
                
                if 'sendgrid' in email_data:
                    config.email.sendgrid.api_key = email_data['sendgrid'].get('api_key', '')
            
            # CRM
            if 'crm' in data:
                crm_data = data['crm']
                config.crm.storage_type = crm_data.get('storage_type', 'json')
                config.crm.json_file = crm_data.get('json_file', 'data/crm_records.json')
            
            # Data Collection
            if 'data_collection' in data:
                dc_data = data['data_collection']
                config.data_collection.default_video_count = dc_data.get('default_video_count', 30)
                config.data_collection.confidence_threshold = dc_data.get('confidence_threshold', 'medium')
                config.data_collection.prefer_api = dc_data.get('prefer_api', True)
            
            # Pricing
            if 'pricing' in data:
                pricing_data = data['pricing']
                if 'default_cpm_range' in pricing_data:
                    config.pricing.default_cpm_min = pricing_data['default_cpm_range'].get('min', 8)
                    config.pricing.default_cpm_max = pricing_data['default_cpm_range'].get('max', 25)
    
    # 环境变量覆盖
    # YouTube API Key
    if os.getenv('YOUTUBE_API_KEY'):
        config.youtube_api.api_key = os.getenv('YOUTUBE_API_KEY')
    
    # Email SMTP
    if os.getenv('SMTP_HOST'):
        config.email.smtp.host = os.getenv('SMTP_HOST')
    if os.getenv('SMTP_PORT'):
        config.email.smtp.port = int(os.getenv('SMTP_PORT'))
    if os.getenv('SMTP_USER'):
        config.email.smtp.user = os.getenv('SMTP_USER')
    if os.getenv('SMTP_PASSWORD'):
        config.email.smtp.password = os.getenv('SMTP_PASSWORD')
    
    # SendGrid
    if os.getenv('SENDGRID_API_KEY'):
        config.email.sendgrid.api_key = os.getenv('SENDGRID_API_KEY')
    
    return config


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config():
    """重新加载配置"""
    global _config
    _config = load_config()
