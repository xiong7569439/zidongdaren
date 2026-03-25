"""
工具接口 - 文件存储
"""
import os
import json
from typing import Optional, Dict, Any
from datetime import datetime


class StorageTool:
    """
    文件存储工具
    
    用于保存生成的工件（表格、JSON、邮件正文、Brief等）
    """
    
    def __init__(self, base_path: str = "data/artifacts"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def save(self, filename: str, content: str, 
             subfolder: Optional[str] = None) -> Dict[str, Any]:
        """
        保存文件
        
        Args:
            filename: 文件名
            content: 文件内容
            subfolder: 子文件夹（如 creator_name）
            
        Returns:
            {
                "status": "success" | "error",
                "file_path": 完整文件路径,
                "error": 错误信息（如果有）
            }
        """
        try:
            folder = self.base_path
            if subfolder:
                folder = os.path.join(folder, subfolder)
                os.makedirs(folder, exist_ok=True)
            
            file_path = os.path.join(folder, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "status": "success",
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def save_json(self, filename: str, data: Dict, 
                  subfolder: Optional[str] = None) -> Dict[str, Any]:
        """保存JSON文件"""
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return self.save(filename, content, subfolder)
    
    def save_csv(self, filename: str, rows: list, 
                 headers: Optional[list] = None,
                 subfolder: Optional[str] = None) -> Dict[str, Any]:
        """
        保存CSV文件
        
        Args:
            filename: 文件名
            rows: 数据行列表
            headers: 表头（可选）
        """
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if headers:
            writer.writerow(headers)
        
        writer.writerows(rows)
        
        content = output.getvalue()
        output.close()
        
        return self.save(filename, content, subfolder)
    
    def load(self, filename: str, 
             subfolder: Optional[str] = None) -> Dict[str, Any]:
        """加载文件"""
        try:
            folder = self.base_path
            if subfolder:
                folder = os.path.join(folder, subfolder)
            
            file_path = os.path.join(folder, filename)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "status": "success",
                "content": content,
                "file_path": file_path
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def load_json(self, filename: str, 
                  subfolder: Optional[str] = None) -> Dict[str, Any]:
        """加载JSON文件"""
        result = self.load(filename, subfolder)
        
        if result["status"] == "success":
            try:
                result["data"] = json.loads(result["content"])
            except json.JSONDecodeError as e:
                return {
                    "status": "error",
                    "error": f"JSON解析失败: {e}"
                }
        
        return result
    
    def list_files(self, subfolder: Optional[str] = None) -> list:
        """列出文件"""
        folder = self.base_path
        if subfolder:
            folder = os.path.join(folder, subfolder)
        
        if not os.path.exists(folder):
            return []
        
        return os.listdir(folder)
