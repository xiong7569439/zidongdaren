"""
YouTube网红曝光合作 - 总控编排器
负责协调各个Agent的执行顺序和状态流转
"""
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import json

from .pipeline import PipelineContext, PipelineStage, PipelineEngine
from .agent import (
    BaseAgent, DataCollectionAgent, PricingAgent, ContactFindingAgent,
    OutreachAgent, NegotiationAgent, BriefAgent, DailyReportAgent
)


class AgentOrchestrator:
    """
    Agent编排器 - 总控Agent
    负责：
    1. 管理Pipeline状态流转
    2. 调度各子Agent执行
    3. 处理失败分支
    4. 触发人工审批
    """
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {
            "data_collection": DataCollectionAgent(),
            "pricing": PricingAgent(),
            "contact_finding": ContactFindingAgent(),
            "outreach": OutreachAgent(),
            "negotiation": NegotiationAgent(),
            "brief": BriefAgent(),
            "daily_report": DailyReportAgent(),
        }
        self.contexts: Dict[str, PipelineContext] = {}  # channel_url -> context
        self.crm_records: List[Dict] = []
    
    def create_lead(self, channel_url: str, creator_name: str = "") -> PipelineContext:
        """创建新线索"""
        context = PipelineContext(
            channel_url=channel_url,
            creator_name=creator_name,
            current_stage=PipelineStage.LEAD_COLLECTED
        )
        self.contexts[channel_url] = context
        
        self._create_crm_record(context, "create_lead", "success", "线索已创建")
        return context
    
    def run_pipeline(self, channel_url: str, auto_run: bool = True) -> Dict[str, Any]:
        """
        运行Pipeline，根据当前状态执行相应Agent
        
        Args:
            channel_url: 频道链接
            auto_run: 是否自动执行到下一个需要人工干预的节点
        
        Returns:
            执行结果
        """
        if channel_url not in self.contexts:
            return {"status": "error", "message": "线索不存在，请先创建"}
        
        context = self.contexts[channel_url]
        engine = PipelineEngine(context)
        results = []
        
        while True:
            stage = context.current_stage
            
            # 根据当前状态选择执行的Agent
            if stage == PipelineStage.LEAD_COLLECTED:
                result = self._run_data_collection(context)
                
            elif stage == PipelineStage.DATA_COLLECTING:
                result = self._run_data_collection(context)
                
            elif stage == PipelineStage.DATA_READY:
                result = self._run_pricing(context)
                
            elif stage == PipelineStage.PRICING_DRAFTED:
                result = self._run_contact_finding(context)
                
            elif stage == PipelineStage.CONTACT_FINDING:
                result = self._run_outreach(context)
                
            elif stage == PipelineStage.OUTREACH_SENT:
                # 等待对方回复，设置自动跟进
                result = self._schedule_follow_up(context)
                
            elif stage == PipelineStage.NEGOTIATING:
                # 需要对方邮件才能继续
                result = {"status": "waiting", "message": "等待对方回复"}
                
            elif stage == PipelineStage.BRIEF_SENT:
                result = self._run_schedule_confirmation(context)
                
            elif stage == PipelineStage.SCHEDULE_CONFIRMED:
                result = {"status": "waiting", "message": "等待视频上线"}
                
            elif stage == PipelineStage.DELIVERABLE_LIVE:
                result = self._run_wrap_up(context)
                
            elif stage == PipelineStage.NEED_HUMAN_APPROVAL:
                result = {"status": "need_approval", "message": "需要人工审批"}
                
            else:
                result = {"status": "completed", "stage": stage.value}
            
            results.append({
                "stage": stage.value,
                "result": result
            })
            
            # 如果不自动运行，或遇到需要等待/审批的情况，停止
            if not auto_run or result.get("status") in ["waiting", "need_approval", "error"]:
                break
            
            # 如果已完成，停止
            if stage in [PipelineStage.CLOSED_WON, PipelineStage.CLOSED_LOST]:
                break
        
        return {
            "status": "success",
            "channel_url": channel_url,
            "final_stage": context.current_stage.value,
            "results": results
        }
    
    def _run_data_collection(self, context: PipelineContext) -> Dict[str, Any]:
        """执行数据采集"""
        agent = self.agents["data_collection"]
        engine = PipelineEngine(context)
        
        # 先流转到数据采集状态
        if context.current_stage == PipelineStage.LEAD_COLLECTED:
            engine.transition(PipelineStage.DATA_COLLECTING, "开始数据采集")
        
        # 尝试数据采集
        result = agent.execute(context)
        
        if result["status"] == "success":
            # 检查数据置信度
            if context.data_confidence == "low":
                # 数据质量低，进入人工审批
                engine.transition(
                    PipelineStage.NEED_HUMAN_APPROVAL,
                    "数据置信度低，需要人工确认"
                )
                self._create_crm_record(context, "data_collection", "low_confidence", 
                                       "数据置信度低，进入人工审批")
            else:
                # 数据正常，进入数据就绪状态
                engine.transition(PipelineStage.DATA_READY, "数据采集完成")
                self._create_crm_record(context, "data_collection", "success", 
                                       f"数据采集完成，置信度: {context.data_confidence}")
        else:
            # 采集失败，进入失败分支
            self._handle_failure(context, "data_collection", result)
        
        return result
    
    def _run_pricing(self, context: PipelineContext) -> Dict[str, Any]:
        """执行报价计算"""
        agent = self.agents["pricing"]
        result = agent.execute(context)
        
        if result["status"] == "success":
            engine = PipelineEngine(context)
            engine.transition(PipelineStage.PRICING_DRAFTED, "报价计算完成")
            self._create_crm_record(context, "pricing", "success", 
                                   f"报价: anchor={result['pricing_card']['anchor_price']}")
        else:
            self._handle_failure(context, "pricing", result)
        
        return result
    
    def _run_contact_finding(self, context: PipelineContext) -> Dict[str, Any]:
        """执行联系方式查找"""
        agent = self.agents["contact_finding"]
        result = agent.execute(context)
        
        if result["status"] == "success":
            if not context.contact_candidates:
                # 找不到联系方式，进入人工审批
                engine = PipelineEngine(context)
                engine.transition(
                    PipelineStage.NEED_HUMAN_APPROVAL,
                    "找不到联系方式，需要人工补充"
                )
                self._create_crm_record(context, "contact_finding", "no_contact", 
                                       "找不到联系方式")
            else:
                engine = PipelineEngine(context)
                engine.transition(PipelineStage.CONTACT_FINDING, "联系方式查找完成")
                self._create_crm_record(context, "contact_finding", "success", 
                                       f"找到{len(context.contact_candidates)}个联系方式")
        else:
            self._handle_failure(context, "contact_finding", result)
        
        return result
    
    def _run_outreach(self, context: PipelineContext) -> Dict[str, Any]:
        """执行首封邮件发送"""
        agent = self.agents["outreach"]
        result = agent.execute(context)
        
        if result["status"] == "success":
            engine = PipelineEngine(context)
            engine.transition(PipelineStage.OUTREACH_SENT, "首封邮件已发送")
            self._create_crm_record(context, "outreach", "sent", 
                                   f"邮件已发送至: {result['email_draft'].get('to')}")
        else:
            self._handle_failure(context, "outreach", result)
        
        return result
    
    def _schedule_follow_up(self, context: PipelineContext) -> Dict[str, Any]:
        """设置自动跟进"""
        # 48小时后自动跟进
        follow_up_time = datetime.now() + timedelta(hours=48)
        
        self._create_crm_record(
            context, "follow_up", "scheduled",
            f"已设置48小时跟进，时间: {follow_up_time.isoformat()}"
        )
        
        return {
            "status": "scheduled",
            "follow_up_time": follow_up_time.isoformat(),
            "message": "已设置自动跟进"
        }
    
    def handle_incoming_reply(self, channel_url: str, email_content: str) -> Dict[str, Any]:
        """处理收到的回复邮件"""
        if channel_url not in self.contexts:
            return {"status": "error", "message": "线索不存在"}
        
        context = self.contexts[channel_url]
        agent = self.agents["negotiation"]
        
        result = agent.execute(context, raw_reply=email_content)
        
        # 根据谈判结果更新状态
        if result.get("need_human_approval"):
            engine = PipelineEngine(context)
            engine.transition(
                PipelineStage.NEED_HUMAN_APPROVAL,
                f"谈判中出现敏感条款: {result.get('risks', [])}"
            )
        else:
            # 更新到相应状态
            new_stage = result.get("updated_stage")
            if new_stage:
                engine = PipelineEngine(context)
                engine.transition(PipelineStage(new_stage), "谈判推进")
        
        self._create_crm_record(context, "negotiation", "reply_handled", 
                               f"已处理回复: {result.get('message', '')}")
        
        return result
    
    def send_brief(self, channel_url: str, **brief_kwargs) -> Dict[str, Any]:
        """发送Brief"""
        if channel_url not in self.contexts:
            return {"status": "error", "message": "线索不存在"}
        
        context = self.contexts[channel_url]
        agent = self.agents["brief"]
        
        result = agent.execute(context, **brief_kwargs)
        
        if result["status"] == "success":
            engine = PipelineEngine(context)
            engine.transition(PipelineStage.BRIEF_SENT, "Brief已发送")
            self._create_crm_record(context, "brief", "sent", "Brief和素材已发送")
        
        return result
    
    def confirm_schedule(self, channel_url: str, schedule_info: Dict) -> Dict[str, Any]:
        """确认排期"""
        if channel_url not in self.contexts:
            return {"status": "error", "message": "线索不存在"}
        
        context = self.contexts[channel_url]
        context.schedule_confirmed = schedule_info
        
        engine = PipelineEngine(context)
        engine.transition(PipelineStage.SCHEDULE_CONFIRMED, "排期已确认")
        
        self._create_crm_record(context, "schedule", "confirmed", 
                               f"排期确认: {schedule_info}")
        
        return {"status": "success", "message": "排期已确认"}
    
    def confirm_live(self, channel_url: str, video_url: str, 
                     performance_data: Optional[Dict] = None) -> Dict[str, Any]:
        """确认视频上线"""
        if channel_url not in self.contexts:
            return {"status": "error", "message": "线索不存在"}
        
        context = self.contexts[channel_url]
        context.live_video_url = video_url
        context.performance_data = performance_data
        
        engine = PipelineEngine(context)
        engine.transition(PipelineStage.DELIVERABLE_LIVE, "视频已上线")
        
        self._create_crm_record(context, "live", "confirmed", 
                               f"视频上线: {video_url}")
        
        return {"status": "success", "message": "视频上线已确认"}
    
    def _run_wrap_up(self, context: PipelineContext) -> Dict[str, Any]:
        """执行收尾"""
        # 根据合作结果决定是CLOSED_WON还是CLOSED_LOST
        # 这里简化处理，假设成功
        engine = PipelineEngine(context)
        engine.transition(PipelineStage.CLOSED_WON, "合作完成")
        
        self._create_crm_record(context, "wrap_up", "completed", "合作完成归档")
        
        return {"status": "success", "message": "合作完成"}
    
    def _run_schedule_confirmation(self, context: PipelineContext) -> Dict[str, Any]:
        """执行排期确认（等待人工确认）"""
        return {"status": "waiting", "message": "等待排期确认"}
    
    def _handle_failure(self, context: PipelineContext, 
                       action: str, result: Dict) -> None:
        """处理失败分支"""
        # 根据失败类型决定处理方式
        error_type = result.get("error_type", "unknown")
        
        if error_type in ["data_unavailable", "api_error"]:
            # 数据问题，尝试替代方案或进入人工审批
            engine = PipelineEngine(context)
            engine.transition(
                PipelineStage.NEED_HUMAN_APPROVAL,
                f"{action}失败: {result.get('message')}"
            )
        
        self._create_crm_record(context, action, "failed", result.get("message", ""))
    
    def approve_and_continue(self, channel_url: str, 
                            approval_notes: str = "") -> Dict[str, Any]:
        """人工审批后继续执行"""
        if channel_url not in self.contexts:
            return {"status": "error", "message": "线索不存在"}
        
        context = self.contexts[channel_url]
        
        if context.current_stage != PipelineStage.NEED_HUMAN_APPROVAL:
            return {"status": "error", "message": "当前不需要审批"}
        
        # 记录审批
        self._create_crm_record(context, "human_approval", "approved", approval_notes)
        
        # 根据历史状态决定下一步
        # 简化处理：尝试继续执行
        return self.run_pipeline(channel_url, auto_run=True)
    
    def generate_daily_report(self, date: Optional[str] = None) -> Dict[str, Any]:
        """生成日报"""
        agent = self.agents["daily_report"]
        contexts = list(self.contexts.values())
        
        result = agent.execute(contexts, date=date)
        return result
    
    def _create_crm_record(self, context: PipelineContext, 
                          action: str, result: str, notes: str = ""):
        """创建CRM记录"""
        record = {
            "timestamp": datetime.now().isoformat(),
            "creator_name": context.creator_name,
            "channel_url": context.channel_url,
            "pipeline_stage": context.current_stage.value,
            "action": action,
            "result": result,
            "next_step": self._get_next_step(context),
            "next_follow_up_time": None,
            "artifacts": [],
            "need_human_approval": context.current_stage == PipelineStage.NEED_HUMAN_APPROVAL,
            "approval_reason": notes if context.current_stage == PipelineStage.NEED_HUMAN_APPROVAL else "",
            "notes": notes
        }
        self.crm_records.append(record)
        return record
    
    def _get_next_step(self, context: PipelineContext) -> str:
        """获取下一步行动"""
        stage_actions = {
            PipelineStage.LEAD_COLLECTED: "开始数据采集",
            PipelineStage.DATA_COLLECTING: "等待数据采集完成",
            PipelineStage.DATA_READY: "开始报价计算",
            PipelineStage.PRICING_DRAFTED: "开始查找联系方式",
            PipelineStage.CONTACT_FINDING: "准备发送首封邮件",
            PipelineStage.OUTREACH_SENT: "等待对方回复",
            PipelineStage.NEGOTIATING: "处理对方回复",
            PipelineStage.BRIEF_SENT: "等待排期确认",
            PipelineStage.SCHEDULE_CONFIRMED: "等待视频上线",
            PipelineStage.DELIVERABLE_LIVE: "执行收尾",
            PipelineStage.NEED_HUMAN_APPROVAL: "等待人工审批",
        }
        return stage_actions.get(context.current_stage, "未知")
    
    def get_context(self, channel_url: str) -> Optional[PipelineContext]:
        """获取指定线索的上下文"""
        return self.contexts.get(channel_url)
    
    def get_all_contexts(self) -> List[PipelineContext]:
        """获取所有线索上下文"""
        return list(self.contexts.values())
    
    def get_crm_records(self, channel_url: Optional[str] = None) -> List[Dict]:
        """获取CRM记录"""
        if channel_url:
            return [r for r in self.crm_records if r["channel_url"] == channel_url]
        return self.crm_records
