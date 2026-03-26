"""
工具接口 - 邮件发送
支持SMTP和邮件服务API
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import smtplib
import ssl
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import uuid


@dataclass
class EmailMessage:
    """邮件消息"""
    from_addr: str
    to_addr: str
    subject: str
    body: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    attachments: Optional[List[str]] = None
    html_body: Optional[str] = None  # HTML格式正文


class EmailTool:
    """
    邮件发送工具
    
    支持多种发送方式：
    1. SMTP（需要配置SMTP服务器）
    2. 邮件服务API（如SendGrid、AWS SES等）
    3. 模拟发送（用于测试）
    """
    
    DEFAULT_FROM = "cooperate@topuplive.com"
    
    def __init__(self, 
                 # SMTP配置
                 smtp_host: Optional[str] = None,
                 smtp_port: int = 587,
                 smtp_user: Optional[str] = None,
                 smtp_password: Optional[str] = None,
                 use_tls: bool = True,
                 use_ssl: bool = False,
                 # SendGrid配置
                 sendgrid_api_key: Optional[str] = None,
                 # 模式
                 mock_mode: bool = False):
        
        # 从环境变量读取配置
        self.smtp_host = smtp_host or os.getenv("EMAIL_SMTP_HOST")
        self.smtp_port = smtp_port or int(os.getenv("EMAIL_SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("EMAIL_SENDER")
        self.smtp_password = smtp_password or os.getenv("EMAIL_PASSWORD")
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        
        # 自动检测连接方式：465端口使用SSL，587端口使用STARTTLS
        if self.smtp_port == 465:
            self.use_ssl = True
            self.use_tls = False
        elif self.smtp_port == 587:
            self.use_ssl = False
            self.use_tls = True
        
        # SendGrid配置
        self.sendgrid_api_key = sendgrid_api_key
        
        # 模式 - 如果有SMTP或SendGrid配置则禁用模拟模式
        is_configured = self.is_smtp_configured() or self.is_sendgrid_configured()
        self.mock_mode = mock_mode if not is_configured else False
        
        # 记录
        self.sent_emails: List[EmailMessage] = []
    
    def is_smtp_configured(self) -> bool:
        """检查SMTP是否已配置"""
        return all([self.smtp_host, self.smtp_user, self.smtp_password])
    
    def is_sendgrid_configured(self) -> bool:
        """检查SendGrid是否已配置"""
        return self.sendgrid_api_key is not None
    
    def send(self, message: EmailMessage) -> Dict[str, Any]:
        """
        发送邮件
        
        优先级：mock_mode > SMTP > SendGrid > 错误
        """
        if self.mock_mode:
            return self._send_mock(message)
        
        if self.is_smtp_configured():
            return self._send_smtp(message)
        
        if self.is_sendgrid_configured():
            return self._send_sendgrid(message)
        
        return {
            "status": "error",
            "error": "未配置任何邮件发送方式",
            "error_type": "not_configured"
        }
    
    def _send_mock(self, message: EmailMessage) -> Dict[str, Any]:
        """模拟发送（用于测试）"""
        self.sent_emails.append(message)
        message_id = f"mock_{uuid.uuid4().hex[:8]}"
        
        print(f"[MOCK EMAIL]")
        print(f"  From: {message.from_addr}")
        print(f"  To: {message.to_addr}")
        print(f"  Subject: {message.subject}")
        print(f"  Body: {message.body[:100]}...")
        
        return {
            "status": "success",
            "message_id": message_id,
            "mock": True
        }
    
    def _send_smtp(self, message: EmailMessage) -> Dict[str, Any]:
        """使用SMTP发送邮件"""
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = message.subject
            msg['From'] = message.from_addr
            msg['To'] = message.to_addr
            
            if message.cc:
                msg['Cc'] = ', '.join(message.cc)
            
            # 添加正文
            # 优先使用HTML格式
            if message.html_body:
                msg.attach(MIMEText(message.html_body, 'html', 'utf-8'))
            
            # 同时添加纯文本格式
            msg.attach(MIMEText(message.body, 'plain', 'utf-8'))
            
            # 添加附件
            if message.attachments:
                for filepath in message.attachments:
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                        encoders.encode_base64(part)
                        filename = os.path.basename(filepath)
                        part.add_header(
                            'Content-Disposition',
                            f'attachment; filename= {filename}'
                        )
                        msg.attach(part)
            
            # 连接SMTP服务器并发送
            context = ssl.create_default_context()
            
            # 根据配置选择SSL或STARTTLS
            # 设置超时时间为30秒，防止网络问题导致无限等待
            timeout = 30
            
            if self.use_ssl:
                # SSL连接（阿里云企业邮箱等）
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context, timeout=timeout) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    
                    recipients = [message.to_addr]
                    if message.cc:
                        recipients.extend(message.cc)
                    if message.bcc:
                        recipients.extend(message.bcc)
                    
                    server.sendmail(
                        message.from_addr,
                        recipients,
                        msg.as_string()
                    )
            else:
                # STARTTLS连接（标准SMTP）
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=timeout) as server:
                    if self.use_tls:
                        server.starttls(context=context)
                    
                    server.login(self.smtp_user, self.smtp_password)
                    
                    recipients = [message.to_addr]
                    if message.cc:
                        recipients.extend(message.cc)
                    if message.bcc:
                        recipients.extend(message.bcc)
                    
                    server.sendmail(
                        message.from_addr,
                        recipients,
                        msg.as_string()
                    )
            
            message_id = str(uuid.uuid4())
            self.sent_emails.append(message)
            
            return {
                "status": "success",
                "message_id": message_id,
                "method": "smtp"
            }
            
        except socket.timeout:
            return {
                "status": "error",
                "error": "SMTP连接超时，请检查网络或SMTP服务器配置",
                "error_type": "smtp_timeout"
            }
        except smtplib.SMTPAuthenticationError as e:
            return {
                "status": "error",
                "error": f"SMTP认证失败: {str(e)}",
                "error_type": "smtp_auth"
            }
        except smtplib.SMTPException as e:
            return {
                "status": "error",
                "error": f"SMTP错误: {str(e)}",
                "error_type": "smtp_error"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"发送失败: {str(e)}",
                "error_type": "send_failed"
            }
    
    def _send_sendgrid(self, message: EmailMessage) -> Dict[str, Any]:
        """使用SendGrid API发送邮件"""
        import requests
        
        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {self.sendgrid_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "personalizations": [{
                "to": [{"email": message.to_addr}]
            }],
            "from": {"email": message.from_addr},
            "subject": message.subject,
            "content": [
                {
                    "type": "text/plain",
                    "value": message.body
                }
            ]
        }
        
        if message.html_body:
            data["content"].append({
                "type": "text/html",
                "value": message.html_body
            })
        
        if message.cc:
            data["personalizations"][0]["cc"] = [
                {"email": addr} for addr in message.cc
            ]
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            message_id = response.headers.get('X-Message-Id', str(uuid.uuid4()))
            self.sent_emails.append(message)
            
            return {
                "status": "success",
                "message_id": message_id,
                "method": "sendgrid"
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"SendGrid API错误: {str(e)}",
                "error_type": "sendgrid_error"
            }
    
    def send_outreach_email(self, to_addr: str, creator_name: str,
                           subject: str, body: str,
                           from_addr: Optional[str] = None,
                           html_body: Optional[str] = None) -> Dict[str, Any]:
        """
        发送合作邮件（快捷方法）
        
        Args:
            to_addr: 收件人地址
            creator_name: 创作者名称
            subject: 邮件主题
            body: 邮件正文（纯文本）
            from_addr: 发件人地址（默认cooperate@topuplive.com）
            html_body: HTML格式正文（可选）
        """
        message = EmailMessage(
            from_addr=from_addr or self.DEFAULT_FROM,
            to_addr=to_addr,
            subject=subject,
            body=body,
            html_body=html_body
        )
        return self.send(message)
    
    def send_follow_up(self, to_addr: str, creator_name: str,
                      original_subject: str, days_waited: int,
                      from_addr: Optional[str] = None) -> Dict[str, Any]:
        """
        发送跟进邮件
        
        Args:
            to_addr: 收件人地址
            creator_name: 创作者名称
            original_subject: 原始邮件主题
            days_waited: 等待天数
            from_addr: 发件人地址
        """
        subject = f"Re: {original_subject}"
        
        body = f"""Hi {creator_name},

I hope this email finds you well. I wanted to follow up on my previous message regarding a potential collaboration opportunity.

I understand you receive many inquiries, and I don't want to be pushy. However, I believe this partnership could be mutually beneficial.

If you're interested, I'd love to schedule a quick 15-minute call to discuss the details. If not, I completely understand and wish you continued success with your channel.

Looking forward to hearing from you.

Best regards,
TOPUPlive Team
"""
        
        return self.send_outreach_email(to_addr, creator_name, subject, body, from_addr)
    
    def get_sent_emails(self) -> List[EmailMessage]:
        """获取已发送邮件列表（用于测试）"""
        return self.sent_emails
    
    def get_stats(self) -> Dict[str, Any]:
        """获取发送统计"""
        return {
            "total_sent": len(self.sent_emails),
            "mock_mode": self.mock_mode,
            "smtp_configured": self.is_smtp_configured(),
            "sendgrid_configured": self.is_sendgrid_configured()
        }
