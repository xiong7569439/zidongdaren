"""
YouTube网红曝光合作 - 核心Pipeline状态机
定义整个业务流程的状态流转
"""
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PipelineStage(Enum):
    """Pipeline状态定义"""
    LEAD_COLLECTED = "lead_collected"           # 已拿到频道链接/ID
    DATA_COLLECTING = "data_collecting"         # 采集频道与视频数据中
    DATA_READY = "data_ready"                   # 数据表与画像完成
    PRICING_DRAFTED = "pricing_drafted"         # 报价卡完成
    CONTACT_FINDING = "contact_finding"         # 找联系方式中
    OUTREACH_SENT = "outreach_sent"             # 已发出首封合作邮件
    NEGOTIATING = "negotiating"                 # 在谈（对方回复/压价/问素材）
    BRIEF_SENT = "brief_sent"                   # 已发 Brief/素材包
    SCHEDULE_CONFIRMED = "schedule_confirmed"   # 排期确认
    DELIVERABLE_LIVE = "deliverable_live"       # 视频发布上线
    WRAP_UP = "wrap_up"                         # 验收与复盘
    CLOSED_WON = "closed_won"                   # 成交归档
    CLOSED_LOST = "closed_lost"                 # 失败归档
    NEED_HUMAN_APPROVAL = "need_human_approval" # 需人工审批


@dataclass
class PipelineContext:
    """Pipeline上下文 - 贯穿整个流程的数据容器"""
    # 基础信息
    creator_name: str = ""
    channel_url: str = ""
    channel_id: Optional[str] = None
    
    # 当前状态
    current_stage: PipelineStage = PipelineStage.LEAD_COLLECTED
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 数据收集结果
    creator_profile: Optional[Dict] = None
    videos_data: List[Dict] = field(default_factory=list)
    data_confidence: str = "low"  # high/medium/low
    
    # 报价信息
    pricing_card: Optional[Dict] = None
    
    # 联系方式
    contact_candidates: List[Dict] = field(default_factory=list)
    recommended_contact: Optional[Dict] = None
    
    # 联系尝试记录
    contact_attempts: List[Dict] = field(default_factory=list)
    contact_verification: Dict = field(default_factory=dict)
    
    # 邮件记录
    email_history: List[Dict] = field(default_factory=list)
    
    # 邮件序列跟进
    email_sequence: Optional[Dict] = None  # {"current_step": 0, "started_at": "...", "next_scheduled": "..."}
    
    # 谈判记录
    negotiation_log: List[Dict] = field(default_factory=list)
    
    # Brief和素材
    brief_data: Optional[Dict] = None
    asset_pack_url: Optional[str] = None
    
    # 排期
    schedule_confirmed: Optional[Dict] = None
    
    # 上线信息
    live_video_url: Optional[str] = None
    performance_data: Optional[Dict] = None
    
    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    assigned_agent: str = "default"
    
    def transition_to(self, new_stage: PipelineStage, reason: str = ""):
        """状态流转"""
        self.stage_history.append({
            "from": self.current_stage.value,
            "to": new_stage.value,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })
        self.current_stage = new_stage
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "creator_name": self.creator_name,
            "channel_url": self.channel_url,
            "channel_id": self.channel_id,
            "current_stage": self.current_stage.value,
            "stage_history": self.stage_history,
            "data_confidence": self.data_confidence,
            "pricing_card": self.pricing_card,
            "recommended_contact": self.recommended_contact,
            "email_history": self.email_history,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class PipelineEngine:
    """Pipeline引擎 - 驱动状态流转"""
    
    # 定义合法的状态流转路径
    VALID_TRANSITIONS = {
        PipelineStage.LEAD_COLLECTED: [PipelineStage.DATA_COLLECTING],
        PipelineStage.DATA_COLLECTING: [PipelineStage.DATA_READY, PipelineStage.NEED_HUMAN_APPROVAL],
        PipelineStage.DATA_READY: [PipelineStage.PRICING_DRAFTED, PipelineStage.NEED_HUMAN_APPROVAL],
        PipelineStage.PRICING_DRAFTED: [PipelineStage.CONTACT_FINDING, PipelineStage.NEED_HUMAN_APPROVAL],
        PipelineStage.CONTACT_FINDING: [PipelineStage.OUTREACH_SENT, PipelineStage.NEED_HUMAN_APPROVAL],
        PipelineStage.OUTREACH_SENT: [PipelineStage.NEGOTIATING, PipelineStage.CLOSED_LOST],
        PipelineStage.NEGOTIATING: [PipelineStage.BRIEF_SENT, PipelineStage.CLOSED_WON, 
                                     PipelineStage.CLOSED_LOST, PipelineStage.NEED_HUMAN_APPROVAL],
        PipelineStage.BRIEF_SENT: [PipelineStage.SCHEDULE_CONFIRMED, PipelineStage.NEGOTIATING],
        PipelineStage.SCHEDULE_CONFIRMED: [PipelineStage.DELIVERABLE_LIVE, PipelineStage.NEGOTIATING],
        PipelineStage.DELIVERABLE_LIVE: [PipelineStage.WRAP_UP],
        PipelineStage.WRAP_UP: [PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST],
        PipelineStage.NEED_HUMAN_APPROVAL: [PipelineStage.DATA_COLLECTING, PipelineStage.PRICING_DRAFTED,
                                             PipelineStage.CONTACT_FINDING, PipelineStage.NEGOTIATING,
                                             PipelineStage.CLOSED_LOST],
    }
    
    def __init__(self, context: PipelineContext):
        self.context = context
    
    def can_transition_to(self, target_stage: PipelineStage) -> bool:
        """检查是否可以流转到目标状态"""
        current = self.context.current_stage
        allowed = self.VALID_TRANSITIONS.get(current, [])
        return target_stage in allowed
    
    def transition(self, target_stage: PipelineStage, reason: str = "") -> bool:
        """执行状态流转"""
        if not self.can_transition_to(target_stage):
            raise ValueError(
                f"非法状态流转: {self.context.current_stage.value} -> {target_stage.value}"
            )
        
        self.context.transition_to(target_stage, reason)
        return True
    
    def get_available_transitions(self) -> List[PipelineStage]:
        """获取当前可用的流转目标"""
        return self.VALID_TRANSITIONS.get(self.context.current_stage, [])
