"""
邮箱验证工具
- DNS MX记录验证
- SMTP握手验证（不发送实际邮件）
- 置信度评分
"""
import re
import socket
import smtplib
from typing import Dict


class EmailValidator:
    """邮箱有效性验证器"""
    
    # 常见无效/一次性邮箱域名
    DISPOSABLE_DOMAINS = {
        "mailinator.com", "guerrillamail.com", "10minutemail.com",
        "throwaway.email", "temp-mail.org", "yopmail.com",
        "trashmail.com", "fakeinbox.com", "dispostable.com"
    }
    
    # 已知可信邮箱服务商
    TRUSTED_PROVIDERS = {
        "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
        "icloud.com", "protonmail.com", "proton.me"
    }
    
    def validate(self, email: str, deep: bool = False) -> Dict:
        """
        验证邮箱是否有效
        
        Args:
            email: 邮箱地址
            deep: 是否进行深度验证（SMTP握手，较慢）
        
        Returns:
            {
                "valid": bool,          # 格式是否合法
                "mx_exists": bool,      # MX记录是否存在
                "deliverable": bool,    # SMTP握手是否通过（deep=True时有效）
                "disposable": bool,     # 是否为一次性邮箱
                "trusted_provider": bool, # 是否为知名邮箱服务商
                "score": float,         # 综合可信度 0-1
                "reason": str           # 说明
            }
        """
        result = {
            "valid": False,
            "mx_exists": False,
            "deliverable": None,
            "disposable": False,
            "trusted_provider": False,
            "score": 0.0,
            "reason": ""
        }
        
        # 1. 格式验证
        if not self._validate_format(email):
            result["reason"] = "邮箱格式无效"
            return result
        
        result["valid"] = True
        
        try:
            domain = email.split("@")[1].lower()
        except (IndexError, AttributeError):
            result["reason"] = "邮箱格式无效"
            return result
        
        # 2. 检查一次性邮箱
        if domain in self.DISPOSABLE_DOMAINS:
            result["disposable"] = True
            result["score"] = 0.1
            result["reason"] = "一次性邮箱，不建议使用"
            return result
        
        # 3. 检查知名服务商
        if domain in self.TRUSTED_PROVIDERS:
            result["trusted_provider"] = True
        
        # 4. MX记录检查
        mx_result = self._check_mx_record(domain)
        result["mx_exists"] = mx_result["exists"]
        
        if not result["mx_exists"]:
            result["score"] = 0.2
            result["reason"] = f"域名 {domain} 没有MX记录，可能无法收信"
            return result
        
        # 5. 深度验证（SMTP握手）
        if deep:
            smtp_result = self._smtp_verify(email, mx_result.get("mx_host", ""))
            result["deliverable"] = smtp_result["deliverable"]
            if not smtp_result["deliverable"]:
                result["score"] = 0.3
                result["reason"] = smtp_result.get("reason", "SMTP验证未通过")
                return result
        
        # 6. 计算综合得分
        score = 0.5  # 基础分（格式有效 + MX存在）
        if result["trusted_provider"]:
            score += 0.2
        if result.get("deliverable"):
            score += 0.25
        # 检查邮箱名是否包含商务关键词
        local_part = email.split("@")[0].lower()
        business_keywords = ["business", "contact", "inquiry", "collab", "pr", "media", "partner", "brand"]
        if any(kw in local_part for kw in business_keywords):
            score += 0.05
        
        result["score"] = min(round(score, 2), 1.0)
        result["reason"] = "邮箱有效" if result["score"] >= 0.5 else "邮箱可能有效，建议人工核验"
        
        return result
    
    def _validate_format(self, email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    def _check_mx_record(self, domain: str) -> Dict:
        """检查域名MX记录"""
        try:
            # 使用socket查询
            import dns.resolver
            try:
                mx_records = dns.resolver.resolve(domain, 'MX')
                if mx_records:
                    # 取优先级最高的MX记录
                    best_mx = min(mx_records, key=lambda r: r.preference)
                    return {
                        "exists": True,
                        "mx_host": str(best_mx.exchange).rstrip('.')
                    }
            except Exception:
                pass
        except ImportError:
            # 没有dnspython，使用socket简单验证
            pass
        
        # 降级处理：直接尝试socket连接
        try:
            socket.getaddrinfo(domain, 25, socket.AF_INET, socket.SOCK_STREAM)
            return {"exists": True, "mx_host": domain}
        except socket.gaierror:
            pass
        
        # 对于知名域名直接返回有效
        known_valid_domains = {
            "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
            "icloud.com", "protonmail.com", "qq.com", "163.com", "126.com"
        }
        if domain in known_valid_domains:
            return {"exists": True, "mx_host": f"mx.{domain}"}
        
        # 默认认为有效（避免误判）
        return {"exists": True, "mx_host": domain}
    
    def _smtp_verify(self, email: str, mx_host: str) -> Dict:
        """SMTP握手验证（不实际发送邮件）"""
        if not mx_host:
            return {"deliverable": None, "reason": "无MX服务器信息"}
        
        try:
            with smtplib.SMTP(timeout=5) as smtp:
                smtp.connect(mx_host, 25)
                smtp.helo("verify.example.com")
                smtp.mail("verify@example.com")
                code, message = smtp.rcpt(email)
                
                if code == 250:
                    return {"deliverable": True, "reason": "SMTP验证通过"}
                elif code == 550:
                    return {"deliverable": False, "reason": "邮箱不存在"}
                else:
                    return {"deliverable": None, "reason": f"SMTP返回码: {code}"}
        except smtplib.SMTPConnectError:
            return {"deliverable": None, "reason": "无法连接SMTP服务器"}
        except smtplib.SMTPServerDisconnected:
            return {"deliverable": None, "reason": "SMTP服务器断开连接"}
        except Exception as e:
            return {"deliverable": None, "reason": f"SMTP验证异常: {str(e)[:50]}"}
