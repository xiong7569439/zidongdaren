"""
YouTube网红曝光合作系统 - 核心模块
"""
from .pipeline import PipelineStage, PipelineContext, PipelineEngine
from .agent import (
    BaseAgent, DataCollectionAgent, PricingAgent, ContactFindingAgent,
    OutreachAgent, NegotiationAgent, BriefAgent, DailyReportAgent,
    ContactRefreshAgent, EmailSequenceManager
)
from .orchestrator import AgentOrchestrator

__all__ = [
    'PipelineStage',
    'PipelineContext',
    'PipelineEngine',
    'BaseAgent',
    'DataCollectionAgent',
    'PricingAgent',
    'ContactFindingAgent',
    'OutreachAgent',
    'NegotiationAgent',
    'BriefAgent',
    'DailyReportAgent',
    'ContactRefreshAgent',
    'EmailSequenceManager',
    'AgentOrchestrator',
]
