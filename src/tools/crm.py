"""
工具接口 - CRM记录
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os


class CRMStorage:
    """
    CRM存储工具
    
    支持多种存储方式：
    1. 本地JSON文件（开发/测试）
    2. 数据库（生产环境）
    3. Notion API（可选）
    """
    
    def __init__(self, storage_type: str = "json", 
                 file_path: Optional[str] = None,
                 db_connection: Optional[str] = None):
        self.storage_type = storage_type
        self.file_path = file_path or "data/crm_records.json"
        self.db_connection = db_connection
        self._records: List[Dict] = []
        self._load()
    
    def _load(self):
        """加载已有记录"""
        if self.storage_type == "json" and os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    self._records = json.load(f)
            except Exception:
                self._records = []
    
    def _save(self):
        """保存记录"""
        if self.storage_type == "json":
            os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._records, f, ensure_ascii=False, indent=2)
    
    def upsert(self, record: Dict[str, Any]) -> str:
        """
        插入或更新记录
        
        Args:
            record: 记录字典，必须包含timestamp和channel_url
            
        Returns:
            记录ID
        """
        record_id = record.get("id") or f"{record['channel_url']}_{record['timestamp']}"
        record["id"] = record_id
        record["updated_at"] = datetime.now().isoformat()
        
        # 查找是否已存在
        existing_idx = None
        for idx, r in enumerate(self._records):
            if r.get("id") == record_id:
                existing_idx = idx
                break
        
        if existing_idx is not None:
            self._records[existing_idx] = record
        else:
            self._records.append(record)
        
        self._save()
        return record_id
    
    def get(self, record_id: str) -> Optional[Dict]:
        """获取单条记录"""
        for r in self._records:
            if r.get("id") == record_id:
                return r
        return None
    
    def query(self, channel_url: Optional[str] = None,
              pipeline_stage: Optional[str] = None,
              date_from: Optional[str] = None,
              date_to: Optional[str] = None) -> List[Dict]:
        """
        查询记录
        
        Args:
            channel_url: 频道URL筛选
            pipeline_stage: Pipeline阶段筛选
            date_from: 开始日期（ISO格式）
            date_to: 结束日期（ISO格式）
        """
        results = self._records
        
        if channel_url:
            results = [r for r in results if r.get("channel_url") == channel_url]
        
        if pipeline_stage:
            results = [r for r in results if r.get("pipeline_stage") == pipeline_stage]
        
        if date_from:
            results = [r for r in results if r.get("timestamp", "") >= date_from]
        
        if date_to:
            results = [r for r in results if r.get("timestamp", "") <= date_to]
        
        return sorted(results, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """获取Pipeline汇总统计"""
        from collections import Counter
        
        stages = [r.get("pipeline_stage", "unknown") for r in self._records]
        stage_counts = Counter(stages)
        
        # 按创作者去重后的最新状态
        creator_latest = {}
        for r in sorted(self._records, key=lambda x: x.get("timestamp", "")):
            creator_latest[r.get("channel_url")] = r.get("pipeline_stage")
        
        latest_stage_counts = Counter(creator_latest.values())
        
        return {
            "total_records": len(self._records),
            "unique_creators": len(creator_latest),
            "stage_distribution": dict(latest_stage_counts),
            "all_stage_counts": dict(stage_counts),
        }
