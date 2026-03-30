"""
YouTube网红曝光合作 - AI Agent总控
负责协调各个子任务Agent的执行
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json

from .pipeline import PipelineContext, PipelineStage, PipelineEngine


class BaseAgent(ABC):
    """Agent基类"""
    
    def __init__(self, name: str, system_prompt: str = ""):
        self.name = name
        self.system_prompt = system_prompt
        self.execution_log: List[Dict] = []
    
    @abstractmethod
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """执行Agent任务，返回结果字典"""
        pass
    
    def log_execution(self, action: str, result: str, metadata: Dict = None):
        """记录执行日志"""
        self.execution_log.append({
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "action": action,
            "result": result,
            "metadata": metadata or {}
        })


class DataCollectionAgent(BaseAgent):
    """A. YouTube数据采集与画像Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的数据采集专员。
负责采集YouTube创作者频道和视频数据，生成数据画像。

工作原则：
1. 不编造：任何数据找不到，明确标注"缺失/不确定"
2. 结构化：输出必须是可复用的表格/JSON格式
3. 可解释：所有计算指标必须给出公式

采集范围：最近30条公开视频（若不足则全量）
"""
    
    def __init__(self, youtube_api_key: Optional[str] = None):
        super().__init__("DataCollectionAgent", self.SYSTEM_PROMPT)
        self.youtube_api_key = youtube_api_key
        self.web_fetch = None
        self.youtube_api = None
    
    def _init_tools(self):
        """初始化工具"""
        if self.web_fetch is None:
            from ..tools.web_fetch import WebFetchTool
            self.web_fetch = WebFetchTool()
        
        if self.youtube_api is None and self.youtube_api_key:
            from ..tools.youtube_api import YouTubeAPITool
            self.youtube_api = YouTubeAPITool(self.youtube_api_key)
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        执行数据采集任务
        
        输入参数：
        - video_count: 采集视频数量（默认30）
        - use_api: 是否优先使用API（默认True，如可用）
        
        输出结果：
        - creator_profile: 创作者画像
        - videos_table: 视频数据表
        - metrics: 计算指标
        - data_confidence: 数据置信度
        - next_step: 是否进入定价
        """
        self._init_tools()
        self.log_execution("start", f"开始采集: {context.channel_url}")
        
        video_count = kwargs.get("video_count", 30)
        use_api = kwargs.get("use_api", True)
        
        try:
            # 1. 获取频道信息
            channel_info = self._fetch_channel_info(context.channel_url, use_api)
            
            if channel_info.get("status") == "error":
                return self._handle_failure(context, channel_info)
            
            # 2. 获取视频列表
            videos = self._fetch_videos(channel_info, video_count, use_api)
            
            # 3. 计算指标
            metrics = self._calculate_metrics(videos)
            
            # 4. 生成创作者画像
            creator_profile = self._create_creator_profile(channel_info, videos, metrics)
            
            # 5. 确定数据置信度
            data_confidence = self._assess_confidence(channel_info, videos, metrics)
            
            # 6. 构建视频数据表
            videos_table = self._build_videos_table(videos)
            
            result = {
                "status": "success",
                "creator_profile": creator_profile,
                "videos_table": videos_table,
                "metrics": metrics,
                "data_confidence": data_confidence,
                "next_step": "YES" if data_confidence in ["high", "medium"] else "NO",
                "message": f"数据采集完成，置信度: {data_confidence}"
            }
            
        except Exception as e:
            result = {
                "status": "error",
                "error_type": "collection_failed",
                "message": f"数据采集失败: {str(e)}",
                "creator_profile": {},
                "videos_table": [],
                "metrics": {},
                "data_confidence": "low",
                "next_step": "NO"
            }
        
        # 更新上下文
        context.creator_profile = result.get("creator_profile", {})
        context.videos_data = result.get("videos_table", [])
        context.data_confidence = result.get("data_confidence", "low")
        
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _fetch_channel_info(self, channel_url: str, use_api: bool) -> Dict[str, Any]:
        """获取频道信息"""
        # 优先使用API
        if use_api and self.youtube_api and self.youtube_api.is_available():
            result = self.youtube_api.get_channel_by_url(channel_url)
            if result.get("status") == "success":
                # API获取基本信息后，仍需抓取About页面获取详细说明和链接
                about_info = self._fetch_about_page(channel_url)
                result.update(about_info)
                return result
        
        # 回退到网页抓取
        return self._fetch_channel_from_web(channel_url)
    
    def _fetch_channel_from_web(self, channel_url: str) -> Dict[str, Any]:
        """从网页抓取频道信息"""
        result = self.web_fetch.fetch(channel_url)
        
        if result["status"] != "success":
            return result
        
        html = result["html"]
        
        # 解析频道信息
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        channel_info = {
            "status": "success",
            "channel_url": channel_url,
            "channel_title": "",
            "subscriber_count": None,
            "view_count": None,
            "video_count": None,
            "description": "",
            "custom_url": "",
            "source": "web_fetch",
            "about_description": "",  # About页面完整说明
            "about_links": []  # About页面链接列表
        }
        
        # 尝试提取频道名称
        title_tag = soup.find("meta", property="og:title")
        if title_tag:
            channel_info["channel_title"] = title_tag.get("content", "")
        
        # 尝试从script标签中提取数据
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                # 尝试提取订阅数
                sub_match = re.search(r'"subscriberCountText":\s*\{[^}]*"simpleText":\s*"([^"]+)"', script.string)
                if sub_match and not channel_info["subscriber_count"]:
                    sub_text = sub_match.group(1)
                    channel_info["subscriber_count"] = self._parse_count(sub_text)
                
                # 尝试提取总播放量
                view_match = re.search(r'"viewCountText":\s*\{[^}]*"simpleText":\s*"([^"]+)"', script.string)
                if view_match and not channel_info["view_count"]:
                    view_text = view_match.group(1)
                    channel_info["view_count"] = self._parse_count(view_text)
                
                # 尝试提取视频数
                video_match = re.search(r'"videoCountText":\s*\{[^}]*"simpleText":\s*"([^"]+)"', script.string)
                if video_match and not channel_info["video_count"]:
                    video_text = video_match.group(1)
                    channel_info["video_count"] = self._parse_count(video_text)
        
        # 尝试提取描述
        desc_tag = soup.find("meta", property="og:description")
        if desc_tag:
            channel_info["description"] = desc_tag.get("content", "")
        
        # 提取handle
        handle_match = re.search(r'youtube\.com/@([^/?]+)', channel_url)
        if handle_match:
            channel_info["custom_url"] = handle_match.group(1)
        
        # 获取About页面的详细信息
        about_info = self._fetch_about_page(channel_url)
        channel_info.update(about_info)
        
        return channel_info
    
    def _fetch_about_page(self, channel_url: str) -> Dict[str, Any]:
        """获取About页面的详细说明和链接"""
        import re
        from bs4 import BeautifulSoup
        
        about_info = {
            "about_description": "",
            "about_links": []
        }
        
        # 构建About页面URL
        if "/@" in channel_url:
            base_url = channel_url.split("/@")[0] + "/@" + channel_url.split("/@")[1].split("/")[0]
            about_url = base_url + "/about"
        elif "/channel/" in channel_url:
            about_url = channel_url.rstrip("/") + "/about"
        else:
            about_url = channel_url.rstrip("/") + "/about"
        
        result = self.web_fetch.fetch(about_url)
        
        if result["status"] != "success":
            return about_info
        
        html = result["html"]
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试从JSON数据中提取说明
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "var ytInitialData" in script.string:
                try:
                    json_match = re.search(r'var ytInitialData = ({.+?});', script.string)
                    if json_match:
                        import json
                        data = json.loads(json_match.group(1))
                        
                        # 提取About描述
                        about_description = self._extract_about_description(data)
                        if about_description:
                            about_info["about_description"] = about_description
                        
                        # 提取About链接
                        about_links = self._extract_about_links(data)
                        if about_links:
                            about_info["about_links"] = about_links
                        
                        break
                except Exception:
                    continue
        
        # 如果JSON提取失败，尝试HTML解析
        if not about_info["about_description"]:
            # 尝试从页面文本中提取描述
            text_content = soup.get_text(separator='\n', strip=True)
            # 查找常见的描述模式
            desc_patterns = [
                r'About\s*\n+([\s\S]{50,500})\n+',
                r'Description\s*\n+([\s\S]{50,500})\n+',
                r'Bio\s*\n+([\s\S]{50,500})\n+'
            ]
            for pattern in desc_patterns:
                match = re.search(pattern, text_content, re.IGNORECASE)
                if match:
                    about_info["about_description"] = match.group(1).strip()[:500]
                    break
        
        # 提取所有外部链接
        if not about_info["about_links"]:
            links = soup.find_all("a", href=re.compile(r'^https?://'))
            seen_urls = set()
            for link in links:
                url = link.get("href", "")
                # 排除YouTube自身链接
                if url and "youtube.com" not in url and "youtu.be" not in url and url not in seen_urls:
                    seen_urls.add(url)
                    about_info["about_links"].append({
                        "url": url,
                        "title": link.get_text(strip=True) or url,
                        "type": self._detect_link_type(url)
                    })
        
        return about_info
    
    def _extract_about_description(self, data: Dict) -> str:
        """从JSON数据中提取About描述"""
        try:
            # 方法1: 从metadata.channelMetadataRenderer.description获取（最可靠）
            metadata = data.get("metadata", {})
            channel_metadata = metadata.get("channelMetadataRenderer", {})
            description = channel_metadata.get("description", "")
            if description:
                return description
            
            # 方法2: 从tabs中查找About标签
            contents = data.get("contents", {})
            two_column = contents.get("twoColumnBrowseResultsRenderer", {})
            tabs = two_column.get("tabs", [])
            
            for tab in tabs:
                tab_renderer = tab.get("tabRenderer", {})
                tab_title = tab_renderer.get("title", "")
                # YouTube About页面的title可能是"About"或空字符串
                if tab_title == "About" or tab_title == "":
                    content = tab_renderer.get("content", {})
                    if not content:
                        continue
                    section_list = content.get("sectionListRenderer", {})
                    sections = section_list.get("contents", [])
                    
                    for section in sections:
                        item_section = section.get("itemSectionRenderer", {})
                        items = item_section.get("contents", [])
                        
                        for item in items:
                            # 查找描述文本
                            about_renderer = item.get("channelAboutFullMetadataRenderer", {})
                            if about_renderer:
                                description = about_renderer.get("description", {})
                                simple_text = description.get("simpleText", "")
                                if simple_text:
                                    return simple_text
                                
                                # 尝试从runs中提取
                                runs = description.get("runs", [])
                                if runs:
                                    return "".join([run.get("text", "") for run in runs])
            
            return ""
        except Exception:
            return ""
    
    def _extract_about_links(self, data: Dict) -> List[Dict]:
        """从JSON数据中提取About链接"""
        links = []
        try:
            contents = data.get("contents", {})
            two_column = contents.get("twoColumnBrowseResultsRenderer", {})
            tabs = two_column.get("tabs", [])
            
            for tab in tabs:
                tab_renderer = tab.get("tabRenderer", {})
                if tab_renderer.get("title") == "About":
                    content = tab_renderer.get("content", {})
                    section_list = content.get("sectionListRenderer", {})
                    sections = section_list.get("contents", [])
                    
                    for section in sections:
                        item_section = section.get("itemSectionRenderer", {})
                        items = item_section.get("contents", [])
                        
                        for item in items:
                            about_renderer = item.get("channelAboutFullMetadataRenderer", {})
                            if about_renderer:
                                # 提取主要链接
                                primary_links = about_renderer.get("primaryLinks", [])
                                for link in primary_links:
                                    title = link.get("title", {}).get("simpleText", "")
                                    url = link.get("navigationEndpoint", {}).get("urlEndpoint", {}).get("url", "")
                                    if url:
                                        links.append({
                                            "url": url,
                                            "title": title or url,
                                            "type": self._detect_link_type(url)
                                        })
                                
                                # 提取其他社交链接
                                secondary_links = about_renderer.get("secondaryLinks", [])
                                for link in secondary_links:
                                    title = link.get("title", {}).get("simpleText", "")
                                    url = link.get("navigationEndpoint", {}).get("urlEndpoint", {}).get("url", "")
                                    if url:
                                        links.append({
                                            "url": url,
                                            "title": title or url,
                                            "type": self._detect_link_type(url)
                                        })
            
            return links
        except Exception:
            return links
    
    def _detect_link_type(self, url: str) -> str:
        """检测链接类型"""
        url_lower = url.lower()
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"
        elif "instagram.com" in url_lower:
            return "instagram"
        elif "twitch.tv" in url_lower:
            return "twitch"
        elif "discord" in url_lower:
            return "discord"
        elif "tiktok.com" in url_lower:
            return "tiktok"
        elif "facebook.com" in url_lower:
            return "facebook"
        elif "linkedin.com" in url_lower:
            return "linkedin"
        elif "github.com" in url_lower:
            return "github"
        elif "linktr.ee" in url_lower:
            return "linktree"
        elif "mailto:" in url_lower:
            return "email"
        else:
            return "website"
    
    def _parse_count(self, count_text: str) -> Optional[int]:
        """解析数量文本（如 "1.2M subscribers" -> 1200000）"""
        if not count_text:
            return None
        
        import re
        
        # 提取数字部分
        match = re.search(r'([\d.,]+)\s*([KMB]?)', count_text.replace(",", ""))
        if not match:
            return None
        
        try:
            number = float(match.group(1))
            unit = match.group(2).upper()
            
            multipliers = {
                '': 1,
                'K': 1000,
                'M': 1000000,
                'B': 1000000000
            }
            
            return int(number * multipliers.get(unit, 1))
        except (ValueError, TypeError):
            return None
    
    def _fetch_videos(self, channel_info: Dict, max_results: int, use_api: bool) -> List[Dict]:
        """获取视频列表"""
        channel_id = channel_info.get("channel_id") or channel_info.get("custom_url")
        
        if not channel_id:
            return []
        
        # 优先使用API
        if use_api and self.youtube_api and self.youtube_api.is_available():
            videos = self.youtube_api.list_videos(channel_id, max_results)
            if videos:
                return videos
        
        # 回退到网页抓取
        return self._fetch_videos_from_web(channel_info, max_results)
    
    def _fetch_videos_from_web(self, channel_info: Dict, max_results: int) -> List[Dict]:
        """从网页抓取视频列表"""
        channel_url = channel_info.get("channel_url", "")
        
        # 构建视频页面URL
        if "/@" in channel_url:
            videos_url = channel_url.split("/@")[0] + "/@" + channel_url.split("/@")[1].split("/")[0] + "/videos"
        else:
            videos_url = channel_url + "/videos"
        
        result = self.web_fetch.fetch(videos_url)
        
        if result["status"] != "success":
            return []
        
        html = result["html"]
        videos = []
        
        import re
        from bs4 import BeautifulSoup
        from datetime import datetime
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 尝试从script中提取视频数据
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string and "var ytInitialData" in script.string:
                try:
                    # 提取JSON数据
                    json_match = re.search(r'var ytInitialData = ({.+?});', script.string)
                    if json_match:
                        import json
                        data = json.loads(json_match.group(1))
                        
                        # 解析视频列表
                        videos = self._parse_videos_from_json(data, max_results)
                        break
                except Exception:
                    continue
        
        # 如果JSON解析失败，尝试HTML解析
        if not videos:
            videos = self._parse_videos_from_html(html, max_results)
        
        return videos
    
    def _parse_videos_from_json(self, data: Dict, max_results: int) -> List[Dict]:
        """从JSON数据解析视频列表"""
        videos = []
        
        try:
            # 导航到视频列表
            contents = data.get("contents", {})
            two_column_browse = contents.get("twoColumnBrowseResultsRenderer", {})
            tabs = two_column_browse.get("tabs", [])
            
            for tab in tabs:
                tab_renderer = tab.get("tabRenderer", {})
                if tab_renderer.get("title") == "Videos":
                    content = tab_renderer.get("content", {})
                    rich_grid = content.get("richGridRenderer", {})
                    items = rich_grid.get("contents", [])
                    
                    for item in items[:max_results]:
                        video = self._extract_video_from_item(item)
                        if video:
                            videos.append(video)
                    
                    break
        except Exception:
            pass
        
        return videos
    
    def _extract_video_from_item(self, item: Dict) -> Optional[Dict]:
        """从item中提取视频信息"""
        try:
            rich_item = item.get("richItemRenderer", {})
            content = rich_item.get("content", {})
            video_renderer = content.get("videoRenderer", {})
            
            if not video_renderer:
                return None
            
            video_id = video_renderer.get("videoId", "")
            title = video_renderer.get("title", {}).get("runs", [{}])[0].get("text", "")
            
            # 提取播放量
            view_count_text = video_renderer.get("viewCountText", {}).get("simpleText", "")
            views = self._parse_count(view_count_text) or 0
            
            # 提取发布时间
            published_text = video_renderer.get("publishedTimeText", {}).get("simpleText", "")
            
            # 提取时长
            length_text = video_renderer.get("lengthText", {}).get("simpleText", "")
            duration_seconds = self._parse_duration(length_text)
            
            # 判断是否为Shorts
            is_shorts = "shorts" in video_renderer.get("navigationEndpoint", {}).get("commandMetadata", {}).get("webCommandMetadata", {}).get("url", "").lower()
            
            return {
                "video_id": video_id,
                "video_url": f"https://www.youtube.com/watch?v={video_id}",
                "title": title,
                "published_text": published_text,
                "views": views,
                "duration_text": length_text,
                "duration_seconds": duration_seconds,
                "is_shorts": is_shorts,
                "thumbnail": video_renderer.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", ""),
                "source": "web_json"
            }
        except Exception:
            return None
    
    def _parse_duration(self, duration_text: str) -> int:
        """解析时长文本（如 "10:30" -> 630秒）"""
        if not duration_text:
            return 0
        
        import re
        
        parts = duration_text.split(":")
        try:
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except (ValueError, IndexError):
            pass
        
        return 0
    
    def _parse_videos_from_html(self, html: str, max_results: int) -> List[Dict]:
        """从HTML解析视频列表（备用方案）"""
        videos = []
        
        import re
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找视频链接
        video_links = soup.find_all("a", href=re.compile(r"/watch\?v="))
        
        seen_ids = set()
        for link in video_links:
            if len(videos) >= max_results:
                break
            
            href = link.get("href", "")
            video_id_match = re.search(r"v=([a-zA-Z0-9_-]+)", href)
            
            if video_id_match:
                video_id = video_id_match.group(1)
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                
                # 尝试提取标题
                title = ""
                title_elem = link.find("span", {"id": "video-title"})
                if title_elem:
                    title = title_elem.get_text(strip=True)
                
                videos.append({
                    "video_id": video_id,
                    "video_url": f"https://www.youtube.com/watch?v={video_id}",
                    "title": title,
                    "published_text": "",
                    "views": 0,
                    "duration_text": "",
                    "duration_seconds": 0,
                    "is_shorts": False,
                    "thumbnail": f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                    "source": "web_html"
                })
        
        return videos
    
    def _calculate_metrics(self, videos: List[Dict]) -> Dict[str, Any]:
        """计算指标"""
        if not videos:
            return {
                "video_count": 0,
                "mean_views": 0,
                "median_views": 0,
                "p75_views": 0,
                "viral_rate": 0,
                "avg_duration_seconds": 0,
                "shorts_ratio": 0,
                "formulas": {}
            }
        
        views_list = [v.get("views", 0) for v in videos if v.get("views", 0) > 0]
        
        if not views_list:
            views_list = [0]
        
        # 计算均值
        mean_views = sum(views_list) / len(views_list)
        
        # 计算中位数
        sorted_views = sorted(views_list)
        n = len(sorted_views)
        median_views = sorted_views[n // 2] if n % 2 == 1 else (sorted_views[n // 2 - 1] + sorted_views[n // 2]) / 2
        
        # 计算P75
        p75_index = int(n * 0.75)
        p75_views = sorted_views[min(p75_index, n - 1)]
        
        # 计算爆款率（views > P75 * 1.5）
        viral_threshold = p75_views * 1.5
        viral_count = sum(1 for v in views_list if v > viral_threshold)
        viral_rate = viral_count / len(views_list) if views_list else 0
        
        # 计算平均时长
        durations = [v.get("duration_seconds", 0) for v in videos]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # 计算Shorts比例
        shorts_count = sum(1 for v in videos if v.get("is_shorts", False))
        shorts_ratio = shorts_count / len(videos) if videos else 0
        
        return {
            "video_count": len(videos),
            "mean_views": round(mean_views, 0),
            "median_views": round(median_views, 0),
            "p75_views": round(p75_views, 0),
            "viral_rate": round(viral_rate, 2),
            "avg_duration_seconds": round(avg_duration, 0),
            "shorts_ratio": round(shorts_ratio, 2),
            "formulas": {
                "mean_views": "sum(views) / count",
                "median_views": "sorted(views)[n//2]",
                "p75_views": "sorted(views)[int(n*0.75)]",
                "viral_rate": "count(views > P75*1.5) / total",
                "baseline_views": "max(median_views, mean_views * 0.8)"
            },
            "baseline_views": round(max(median_views, mean_views * 0.8), 0)
        }
    
    def _create_creator_profile(self, channel_info: Dict, videos: List[Dict], metrics: Dict) -> Dict[str, Any]:
        """生成创作者画像"""
        # 分析内容类型
        content_types = []
        if metrics.get("shorts_ratio", 0) > 0.5:
            content_types.append("Shorts为主")
        elif metrics.get("shorts_ratio", 0) > 0:
            content_types.append("长视频+Shorts混合")
        else:
            content_types.append("长视频为主")
        
        # 分析发布频率（基于视频时间）
        # 简化处理，实际应该解析published_text
        
        # 推断语言和地区
        description = channel_info.get("description", "")
        title = channel_info.get("channel_title", "")
        
        language_guess = "unknown"
        region_guess = "unknown"
        
        # 简单的语言推断
        if any(char in description + title for char in "的是了"):
            language_guess = "zh"
            region_guess = "CN/TW/HK"
        elif any(char in description + title for char in "のです"):
            language_guess = "ja"
            region_guess = "JP"
        elif description or title:
            language_guess = "en"
            region_guess = "US/UK/Other"
        
        # 分析内容焦点
        content_focus = []
        all_titles = " ".join([v.get("title", "").lower() for v in videos[:10]])
        
        game_keywords = ["game", "gaming", "gameplay", "walkthrough", "review", 
                        "游戏", "攻略", "评测", "实况"]
        for keyword in game_keywords:
            if keyword in all_titles:
                content_focus.append("Gaming")
                break
        
        if not content_focus:
            content_focus.append("General")
        
        # 提取About页面的链接作为社交链接
        social_links = []
        about_links = channel_info.get("about_links", [])
        for link in about_links:
            social_links.append({
                "type": link.get("type", "website"),
                "url": link.get("url", ""),
                "title": link.get("title", ""),
                "source": "about_page"
            })
        
        # 推断国家/地区
        country = region_guess
        if region_guess == "CN/TW/HK":
            country = "中国"
        elif region_guess == "JP":
            country = "日本"
        elif region_guess == "US/UK/Other":
            country = "英语区"
        
        # 从About说明和描述中提取邮箱地址
        about_description = channel_info.get("about_description", "")
        description = channel_info.get("description", "")
        combined_text = f"{about_description} {description}"
        about_emails = self._extract_emails(combined_text)
        
        return {
            "creator_name": channel_info.get("channel_title", ""),
            "channel_url": channel_info.get("channel_url", ""),
            "channel_id": channel_info.get("channel_id", ""),
            "custom_url": channel_info.get("custom_url", ""),
            "subscriber_count": channel_info.get("subscriber_count"),
            "total_view_count": channel_info.get("view_count"),
            "total_video_count": channel_info.get("video_count"),
            "description": description,
            "about_description": about_description,  # About页面完整说明
            "about_links": about_links,  # About页面链接
            "about_emails": about_emails,  # 从About中提取的邮箱
            "social_links": social_links,  # 社交链接列表
            "thumbnail": channel_info.get("thumbnail"),  # 频道头像
            "language_guess": language_guess,
            "region_guess": region_guess,
            "country": country,
            "content_focus": content_focus,
            "content_types": content_types,
            "recent_metrics": metrics,
            "notes": f"基于最近{metrics.get('video_count', 0)}条视频分析"
        }
    
    def _extract_emails(self, text: str) -> List[str]:
        """从文本中提取邮箱地址"""
        import re
        
        if not text:
            return []
        
        # 邮箱正则表达式
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # 查找所有邮箱
        emails = re.findall(email_pattern, text)
        
        # 去重并保持顺序
        seen = set()
        unique_emails = []
        for email in emails:
            email_lower = email.lower()
            if email_lower not in seen:
                seen.add(email_lower)
                unique_emails.append(email)
        
        return unique_emails
    
    def _assess_confidence(self, channel_info: Dict, videos: List[Dict], metrics: Dict) -> str:
        """评估数据置信度"""
        confidence_score = 0
        reasons = []
        
        # 频道信息完整性
        if channel_info.get("subscriber_count"):
            confidence_score += 1
        else:
            reasons.append("缺少订阅数")
        
        if channel_info.get("channel_title"):
            confidence_score += 1
        else:
            reasons.append("缺少频道名称")
        
        # 视频数据质量
        video_count = len(videos)
        if video_count >= 30:
            confidence_score += 2
        elif video_count >= 10:
            confidence_score += 1
            reasons.append(f"视频样本较少({video_count}条)")
        else:
            reasons.append(f"视频样本过少({video_count}条)")
        
        # 播放量数据可用性
        videos_with_views = sum(1 for v in videos if v.get("views", 0) > 0)
        if videos_with_views >= len(videos) * 0.8:
            confidence_score += 2
        elif videos_with_views >= len(videos) * 0.5:
            confidence_score += 1
            reasons.append("部分视频缺少播放量数据")
        else:
            reasons.append("大部分视频缺少播放量数据")
        
        # 确定置信度等级
        if confidence_score >= 5:
            return "high"
        elif confidence_score >= 3:
            return "medium"
        else:
            return "low"
    
    def _build_videos_table(self, videos: List[Dict]) -> List[Dict]:
        """构建视频数据表"""
        table = []
        for video in videos:
            table.append({
                "video_url": video.get("video_url", ""),
                "title": video.get("title", ""),
                "published_text": video.get("published_text", ""),
                "is_shorts": video.get("is_shorts", False),
                "duration_seconds": video.get("duration_seconds", 0),
                "views": video.get("views", 0),
                "likes": None,  # 网页抓取通常获取不到
                "comments": None,  # 网页抓取通常获取不到
                "is_suspected_sponsored": self._check_sponsored(video),
                "sponsor_evidence": "",
                "source": video.get("source", "unknown")
            })
        return table
    
    def _check_sponsored(self, video: Dict) -> bool:
        """检查是否疑似商业合作"""
        title = video.get("title", "").lower()
        
        # 简单的关键词检查
        sponsored_keywords = ["#ad", "#sponsored", "sponsor", "partner", "合作", "赞助"]
        
        return any(keyword in title for keyword in sponsored_keywords)
    
    def _handle_failure(self, context: PipelineContext, error_info: Dict) -> Dict[str, Any]:
        """处理采集失败"""
        return {
            "status": "error",
            "error_type": "data_unavailable",
            "message": error_info.get("error", "无法获取频道数据"),
            "creator_profile": {},
            "videos_table": [],
            "metrics": {},
            "data_confidence": "low",
            "next_step": "NO",
            "alternatives": [
                "使用YouTube Data API（需要API Key）",
                "手动补充频道数据",
                "使用第三方数据服务（如SocialBlade）"
            ]
        }


class PricingAgent(BaseAgent):
    """B. 曝光合作报价计算Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的定价专员。
负责基于创作者数据生成可解释的报价卡。

定价模型要求：
1. baseline_views = max(median_views, mean_views * 0.8)
2. assumed_cpm_usd_range = 8-25 USD/千次曝光（按地区/语言浮动）
3. base_fee_range = baseline_views/1000 * assumed_cpm_usd_range
4. 调整因子：内容匹配度、商单密度、爆款率、交付权益

必须输出：anchor_price（开价）、target_price（目标）、floor_price（底价）
"""
    
    # CPM基准表（USD/千次曝光）
    CPM_RANGES = {
        # 按地区
        "US": {"min": 15, "max": 25, "note": "美国市场，CPM较高"},
        "UK": {"min": 12, "max": 20, "note": "英国市场"},
        "CA": {"min": 12, "max": 20, "note": "加拿大市场"},
        "AU": {"min": 12, "max": 20, "note": "澳洲市场"},
        "EU": {"min": 10, "max": 18, "note": "欧洲市场"},
        "JP": {"min": 10, "max": 18, "note": "日本市场"},
        "KR": {"min": 8, "max": 15, "note": "韩国市场"},
        "CN": {"min": 5, "max": 12, "note": "中国市场"},
        "TW": {"min": 6, "max": 14, "note": "台湾市场"},
        "HK": {"min": 6, "max": 14, "note": "香港市场"},
        "SEA": {"min": 5, "max": 12, "note": "东南亚市场"},
        "OTHER": {"min": 8, "max": 15, "note": "其他市场"},
    }
    
    # 游戏品类调整系数
    GAME_CATEGORY_MULTIPLIERS = {
        "mobile_game": 1.0,      # 手机游戏（基准）
        "online_game": 1.1,      # 网络游戏（+10%）
        "mihoyo_game": 1.15,     # 米哈游游戏（+15%，受众匹配度高）
        "aaa_game": 1.2,         # 3A大作（+20%）
        "indie_game": 0.9,       # 独立游戏（-10%）
    }
    
    def __init__(self):
        super().__init__("PricingAgent", self.SYSTEM_PROMPT)
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        执行报价计算任务
        
        输入参数：
        - game_category: 游戏品类 (mobile_game/online_game/mihoyo_game/aaa_game/indie_game)
        - budget_range: 预算区间，如 [1000, 5000]（可选）
        - target_region: 目标地区（可选，覆盖自动检测）
        - deliverables: 交付物清单（可选）
        - add_ons: 加项列表（可选）
        
        输出结果：
        - pricing_card: 完整报价卡
        """
        self.log_execution("start", f"开始定价: {context.creator_name}")
        
        try:
            # 1. 获取基础数据
            metrics = context.creator_profile.get("recent_metrics", {}) if context.creator_profile else {}
            baseline_views = metrics.get("baseline_views", 0)
            
            if baseline_views == 0:
                return self._handle_error("无法获取baseline_views，请先完成数据采集")
            
            # 2. 确定CPM范围
            cpm_range = self._determine_cpm_range(context, kwargs.get("target_region"))
            
            # 3. 计算基础价格
            base_fee_low = baseline_views / 1000 * cpm_range["min"]
            base_fee_high = baseline_views / 1000 * cpm_range["max"]
            
            # 4. 计算调整因子
            adjustments = self._calculate_adjustments(context, kwargs)
            
            # 5. 应用调整
            total_adjustment = sum(adj["impact_pct"] for adj in adjustments)
            adjusted_low = base_fee_low * (1 + total_adjustment)
            adjusted_high = base_fee_high * (1 + total_adjustment)
            
            # 6. 生成三档价格
            anchor_price = int(round(adjusted_high * 1.1, -1))  # 开价：上浮10%
            target_price = int(round((adjusted_low + adjusted_high) / 2, -1))  # 目标：中间值
            floor_price = int(round(adjusted_low * 0.9, -1))  # 底价：下浮10%
            
            # 7. 检查预算限制
            budget_range = kwargs.get("budget_range")
            if budget_range:
                if floor_price > budget_range[1]:
                    return self._handle_budget_exceeded(floor_price, budget_range)
                # 调整价格到预算范围内
                target_price = min(target_price, budget_range[1])
                anchor_price = min(anchor_price, budget_range[1] * 1.1)
            
            # 8. 构建交付物清单
            deliverables = self._build_deliverables(kwargs.get("deliverables"))
            
            # 9. 构建加项菜单
            add_on_menu = self._build_add_on_menu(kwargs.get("add_ons"))
            
            # 10. 构建其他条款
            other_terms = self._build_other_terms(baseline_views)
            
            # 11. 构建假设与风险
            assumptions_and_risks = self._build_assumptions_and_risks(context, cpm_range)
            
            pricing_card = {
                "currency": "USD",
                "baseline_views": baseline_views,
                "assumed_cpm_usd_range": [cpm_range["min"], cpm_range["max"]],
                "cpm_note": cpm_range["note"],
                "base_fee_range": [round(base_fee_low, 0), round(base_fee_high, 0)],
                "adjustments": adjustments,
                "total_adjustment_pct": round(total_adjustment * 100, 1),
                "anchor_price": anchor_price,
                "target_price": target_price,
                "floor_price": floor_price,
                "deliverables": deliverables,
                "add_on_menu": add_on_menu,
                "other_terms": other_terms,
                "assumptions_and_risks": assumptions_and_risks,
                "calculation_formulas": {
                    "baseline_views": "max(median_views, mean_views * 0.8)",
                    "base_fee": "baseline_views/1000 * CPM",
                    "adjusted_fee": "base_fee * (1 + total_adjustment)",
                    "anchor_price": "adjusted_high * 1.1",
                    "target_price": "(adjusted_low + adjusted_high) / 2",
                    "floor_price": "adjusted_low * 0.9"
                }
            }
            
            result = {
                "status": "success",
                "pricing_card": pricing_card,
                "message": f"报价计算完成: anchor=${anchor_price}, target=${target_price}, floor=${floor_price}"
            }
            
        except Exception as e:
            result = self._handle_error(f"报价计算失败: {str(e)}")
        
        context.pricing_card = result.get("pricing_card")
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _determine_cpm_range(self, context: PipelineContext, target_region: Optional[str] = None) -> Dict:
        """确定CPM范围"""
        # 如果指定了目标地区，直接使用
        if target_region and target_region in self.CPM_RANGES:
            return self.CPM_RANGES[target_region]
        
        # 从创作者画像推断地区
        region_guess = ""
        if context.creator_profile:
            region_guess = context.creator_profile.get("region_guess", "")
        
        # 映射到CPM表
        region_mapping = {
            "US": "US",
            "UK": "UK",
            "CA": "CA",
            "AU": "AU",
            "JP": "JP",
            "KR": "KR",
            "CN": "CN",
            "TW": "TW",
            "HK": "HK",
        }
        
        for key, value in region_mapping.items():
            if key in region_guess:
                return self.CPM_RANGES[value]
        
        # 默认返回OTHER
        return self.CPM_RANGES["OTHER"]
    
    def _calculate_adjustments(self, context: PipelineContext, kwargs: Dict) -> List[Dict]:
        """计算调整因子"""
        adjustments = []
        
        # 1. 内容匹配度调整
        content_match_score = self._assess_content_match(context, kwargs.get("game_category"))
        if content_match_score != 0:
            adjustments.append({
                "name": "内容匹配度",
                "impact_pct": content_match_score,
                "reason": self._get_content_match_reason(context, kwargs.get("game_category"))
            })
        
        # 2. 商单密度调整
        sponsored_ratio = self._calculate_sponsored_ratio(context)
        if sponsored_ratio > 0.3:  # 商单密度过高
            adjustment = min(-0.15, -(sponsored_ratio - 0.3) * 0.5)
            adjustments.append({
                "name": "商单密度过高",
                "impact_pct": adjustment,
                "reason": f"近期商单占比{sponsored_ratio:.0%}，可能影响自然流量"
            })
        
        # 3. 爆款率调整
        metrics = context.creator_profile.get("recent_metrics", {}) if context.creator_profile else {}
        viral_rate = metrics.get("viral_rate", 0)
        if viral_rate > 0.2:  # 爆款率高
            adjustment = min(0.2, viral_rate * 0.5)
            adjustments.append({
                "name": "爆款率高",
                "impact_pct": adjustment,
                "reason": f"爆款率{viral_rate:.0%}，内容质量稳定"
            })
        
        # 4. 游戏品类调整
        game_category = kwargs.get("game_category", "mobile_game")
        multiplier = self.GAME_CATEGORY_MULTIPLIERS.get(game_category, 1.0)
        if multiplier != 1.0:
            adjustment = multiplier - 1.0
            adjustments.append({
                "name": f"游戏品类({game_category})",
                "impact_pct": adjustment,
                "reason": f"{game_category}的受众匹配度调整"
            })
        
        return adjustments
    
    def _assess_content_match(self, context: PipelineContext, game_category: Optional[str]) -> float:
        """评估内容匹配度"""
        if not context.creator_profile or not game_category:
            return 0.0
        
        content_focus = context.creator_profile.get("content_focus", [])
        
        # Gaming内容匹配度高
        if "Gaming" in content_focus:
            if game_category in ["mihoyo_game", "aaa_game"]:
                return 0.15  # +15%
            return 0.10  # +10%
        
        return 0.0
    
    def _get_content_match_reason(self, context: PipelineContext, game_category: Optional[str]) -> str:
        """获取内容匹配度原因"""
        if not context.creator_profile:
            return "无法评估"
        
        content_focus = context.creator_profile.get("content_focus", [])
        if "Gaming" in content_focus:
            return f"频道内容为Gaming，与{game_category or '游戏'}品类高度匹配"
        return "内容匹配度一般"
    
    def _calculate_sponsored_ratio(self, context: PipelineContext) -> float:
        """计算商单比例"""
        if not context.videos_data:
            return 0.0
        
        sponsored_count = sum(1 for v in context.videos_data if v.get("is_suspected_sponsored", False))
        return sponsored_count / len(context.videos_data)
    
    def _build_deliverables(self, custom_deliverables: Optional[List] = None) -> List[str]:
        """构建交付物清单"""
        default_deliverables = [
            "1条YouTube长视频整合口播（60-90秒）",
            "视频描述区品牌链接放置",
            "置顶评论（含品牌信息）",
            "视频发布后7天内数据截图"
        ]
        
        if custom_deliverables:
            return custom_deliverables
        
        return default_deliverables
    
    def _build_add_on_menu(self, custom_add_ons: Optional[List] = None) -> List[Dict]:
        """构建加项菜单"""
        default_add_ons = [
            {
                "item": "视频时长延长至120秒",
                "price": 200,
                "notes": "口播时长增加"
            },
            {
                "item": "社区帖子（Community Post）",
                "price": 150,
                "notes": "视频发布前后各1条"
            },
            {
                "item": "Shorts预告片",
                "price": 100,
                "notes": "15-30秒短视频"
            },
            {
                "item": "二次授权（30天）",
                "price": 300,
                "notes": "可用于广告投放"
            },
            {
                "item": "二次授权（永久）",
                "price": 800,
                "notes": "无限期使用"
            }
        ]
        
        if custom_add_ons:
            return custom_add_ons
        
        return default_add_ons
    
    def _build_other_terms(self, baseline_views: int) -> Dict:
        """构建其他条款"""
        # 计算绩效奖励阈值（基于baseline的1.5倍和2倍）
        threshold_1_5x = int(baseline_views * 1.5)
        threshold_2x = int(baseline_views * 2)
        
        return {
            "bonus_for_performance": f"若30天播放超过{threshold_1_5x:,}，奖励$200；超过{threshold_2x:,}，奖励$500",
            "bundle_discount": "同时签约3条视频，总价享受9折优惠",
            "usage_rights_fee": "二次授权费用见add_on_menu，默认不含授权"
        }
    
    def _build_assumptions_and_risks(self, context: PipelineContext, cpm_range: Dict) -> List[str]:
        """构建假设与风险"""
        assumptions = []
        
        # CPM假设
        assumptions.append(f"CPM假设为经验值${cpm_range['min']}-${cpm_range['max']}/千次曝光，{cpm_range['note']}，需后续用对标修正")
        
        # 数据质量
        if context.data_confidence != "high":
            assumptions.append(f"数据置信度为{context.data_confidence}，报价可能存在偏差")
        
        # 播放量波动
        assumptions.append("实际播放量可能受发布时间、平台算法等因素影响，与baseline存在±30%波动")
        
        # 商单影响
        sponsored_ratio = self._calculate_sponsored_ratio(context)
        if sponsored_ratio > 0.2:
            assumptions.append(f"频道商单密度较高({sponsored_ratio:.0%})，可能影响自然推荐流量")
        
        # 受众匹配
        if context.creator_profile:
            language = context.creator_profile.get("language_guess", "unknown")
            if language != "en":
                assumptions.append(f"频道主要语言为{language}，需确认与目标市场匹配度")
        
        return assumptions
    
    def _handle_error(self, message: str) -> Dict[str, Any]:
        """处理错误"""
        return {
            "status": "error",
            "error_type": "pricing_failed",
            "message": message,
            "pricing_card": None
        }
    
    def _handle_budget_exceeded(self, floor_price: float, budget_range: List[float]) -> Dict[str, Any]:
        """处理超出预算"""
        return {
            "status": "error",
            "error_type": "budget_exceeded",
            "message": f"底价${floor_price}超出预算上限${budget_range[1]}",
            "pricing_card": {
                "floor_price": floor_price,
                "budget_limit": budget_range[1],
                "suggestion": "考虑选择其他创作者或调整预算"
            },
            "need_human_approval": True
        }


class ContactFindingAgent(BaseAgent):
    """C. 找联系方式Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的联系信息专员。
负责找到可用于商务合作的联系方式。

检查顺序（按可靠性排序）：
1. YouTube频道About页面（business email）
2. 视频描述区外链（Linktree、官网联系表单）
3. 经纪公司/MCN信息
4. 社媒DM入口（Twitter/X、Instagram）

输出按可靠性排序的联系方式候选列表，推荐最优路径。
"""
    
    # 邮箱域名权重（用于评估邮箱可靠性）
    EMAIL_DOMAIN_WEIGHTS = {
        "gmail.com": 0.7,
        "yahoo.com": 0.6,
        "outlook.com": 0.6,
        "hotmail.com": 0.5,
        "qq.com": 0.5,
        "163.com": 0.5,
        " protonmail.com": 0.8,
    }
    
    # 联系类型优先级
    CONTACT_PRIORITY = {
        "business_email": 1,
        "email": 2,
        "business_form": 3,
        "manager_contact": 4,
        "social_dm": 5,
    }
    
    def __init__(self):
        super().__init__("ContactFindingAgent", self.SYSTEM_PROMPT)
        self.web_fetch = None
    
    def _init_tools(self):
        """初始化工具"""
        if self.web_fetch is None:
            from ..tools.web_fetch import WebFetchTool
            self.web_fetch = WebFetchTool()
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        执行联系方式查找任务
        
        输入参数：
        - deep_search: 是否进行深度搜索（默认False）
        - max_candidates: 最大返回候选数（默认10）
        
        输出结果：
        - contact_candidates: 联系方式候选列表
        - recommended_contact: 推荐使用的联系方式
        - recommended_contact_path: 推荐路径说明
        """
        self._init_tools()
        self.log_execution("start", f"开始查找联系方式: {context.channel_url}")
        
        deep_search = kwargs.get("deep_search", False)
        max_candidates = kwargs.get("max_candidates", 10)
        
        candidates = []
        
        try:
            # 1. 检查YouTube About页面
            about_contacts = self._check_about_page(context.channel_url)
            candidates.extend(about_contacts)
            
            # 2. 检查视频描述区外链
            if context.videos_data:
                video_contacts = self._check_video_descriptions(context.videos_data[:5])
                candidates.extend(video_contacts)
            
            # 3. 深度搜索（如果需要）
            if deep_search and len(candidates) < 3:
                deep_contacts = self._deep_search(context)
                candidates.extend(deep_contacts)
            
            # 4. 去重和排序
            candidates = self._deduplicate_candidates(candidates)
            candidates = self._sort_candidates(candidates)
            
            # 5. 选择推荐联系方式
            recommended = self._select_recommended(candidates)
            
            # 6. 生成推荐路径说明
            recommended_path = self._generate_recommendation(recommended, candidates)
            
            if candidates:
                result = {
                    "status": "success",
                    "contact_candidates": candidates[:max_candidates],
                    "recommended_contact": recommended,
                    "recommended_contact_path": recommended_path,
                    "message": f"找到{len(candidates)}个联系方式"
                }
            else:
                result = self._handle_no_contact_found()
            
        except Exception as e:
            result = {
                "status": "error",
                "error_type": "search_failed",
                "message": f"联系方式查找失败: {str(e)}",
                "contact_candidates": [],
                "recommended_contact": None,
                "recommended_contact_path": None
            }
        
        # 更新上下文
        context.contact_candidates = result.get("contact_candidates", [])
        context.recommended_contact = result.get("recommended_contact")
        
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _check_about_page(self, channel_url: str) -> List[Dict]:
        """检查YouTube About页面"""
        contacts = []
        
        # 构建About页面URL
        if "/@" in channel_url:
            base_url = channel_url.split("/@")[0] + "/@" + channel_url.split("/@")[1].split("/")[0]
            about_url = base_url + "/about"
        elif "/channel/" in channel_url:
            about_url = channel_url.rstrip("/") + "/about"
        else:
            about_url = channel_url.rstrip("/") + "/about"
        
        result = self.web_fetch.fetch(about_url)
        
        if result["status"] != "success":
            return contacts
        
        html = result["html"]
        text = result["text"]
        
        # 提取邮箱（使用正则表达式）
        import re
        
        # 查找邮箱模式
        email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\s*[@\s]\s*[a-zA-Z0-9.-]+\s*\.\s*[a-zA-Z]{2,}',
        ]
        
        found_emails = set()
        for pattern in email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for email in matches:
                # 清理邮箱（去除空格）
                clean_email = re.sub(r'\s+', '', email.lower())
                if self._is_valid_email(clean_email) and clean_email not in found_emails:
                    found_emails.add(clean_email)
                    
                    # 判断是否为商务邮箱
                    is_business = any(keyword in text.lower()[:text.lower().find(clean_email)] 
                                     for keyword in ["business", "contact", "email", "合作", "商务", "inquiry"])
                    
                    contact_type = "business_email" if is_business else "email"
                    confidence = self._calculate_email_confidence(clean_email, is_business)
                    
                    contacts.append({
                        "type": contact_type,
                        "value": clean_email,
                        "source_url": about_url,
                        "confidence": confidence,
                        "notes": "从About页面提取" if is_business else "从About页面提取（非明确商务邮箱）"
                    })
        
        # 查找外部链接（Linktree等）
        linktree_pattern = r'https?://(?:www\.)?linktr\.ee/[^\s<>"\']+'
        linktree_matches = re.findall(linktree_pattern, html, re.IGNORECASE)
        
        for link in linktree_matches:
            # 深度抓取Linktree页面
            linktree_contacts = self._crawl_linktree(link)
            if linktree_contacts:
                contacts.extend(linktree_contacts)
            else:
                contacts.append({
                    "type": "linktree",
                    "value": link,
                    "source_url": about_url,
                    "confidence": 0.6,
                    "notes": "Linktree链接，可能包含联系方式"
                })
        
        # 查找社交媒体链接
        social_patterns = {
            "twitter": r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[a-zA-Z0-9_]+',
            "instagram": r'https?://(?:www\.)?instagram\.com/[a-zA-Z0-9_.]+',
            "tiktok": r'https?://(?:www\.)?tiktok\.com/@[a-zA-Z0-9_.]+',
            "discord": r'https?://(?:www\.)?discord\.(?:gg|com)/[a-zA-Z0-9]+',
            "twitch": r'https?://(?:www\.)?twitch\.tv/[a-zA-Z0-9_]+',
        }
        
        for platform, pattern in social_patterns.items():
            matches = re.findall(pattern, html, re.IGNORECASE)
            for link in matches[:2]:  # 每种平台最多2个
                contacts.append({
                    "type": "social_dm",
                    "value": link,
                    "source_url": about_url,
                    "confidence": 0.55,
                    "notes": f"{platform.capitalize()}主页，可尝试DM联系"
                })
        
        # 查找官网链接
        website_patterns = [
            r'https?://(?:www\.)?[a-zA-Z0-9.-]+\.(?:com|net|org|co\.\w{2})[^\s<>"\']*',
        ]
        
        for pattern in website_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for website in matches[:3]:  # 限制数量
                if "youtube.com" not in website.lower() and "google.com" not in website.lower():
                    # 排除已知的社交媒体
                    if not any(social in website.lower() for social in ['twitter', 'x.com', 'instagram', 'tiktok', 'facebook', 'linkedin']):
                        contacts.append({
                            "type": "website",
                            "value": website,
                            "source_url": about_url,
                            "confidence": 0.5,
                            "notes": "官网链接，可能有联系表单"
                        })
        
        return contacts
    
    def _crawl_linktree(self, linktree_url: str) -> List[Dict]:
        """深度抓取Linktree页面，提取隐藏的邮箱和联系方式"""
        contacts = []
        
        try:
            result = self.web_fetch.fetch(linktree_url)
            if result["status"] != "success":
                return contacts
            
            html = result["html"]
            text = result["text"]
            
            import re
            
            # 1. 从Linktree页面提取邮箱
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, text, re.IGNORECASE)
            
            for email in set(emails):
                clean_email = re.sub(r'\s+', '', email.lower())
                if self._is_valid_email(clean_email):
                    # 判断是否为商务邮箱
                    is_business = any(keyword in clean_email.lower() 
                                     for keyword in ["business", "contact", "inquiry", "collab", "pr", "media"])
                    contact_type = "business_email" if is_business else "email"
                    confidence = self._calculate_email_confidence(clean_email, is_business)
                    
                    contacts.append({
                        "type": contact_type,
                        "value": clean_email,
                        "source_url": linktree_url,
                        "confidence": min(confidence + 0.1, 1.0),  # Linktree来源略高置信度
                        "notes": f"从Linktree提取{'（商务邮箱）' if is_business else ''}"
                    })
            
            # 2. 尝试从JSON数据中提取链接
            json_pattern = r'"url":"([^"]+)"|"link":"([^"]+)"'
            json_matches = re.findall(json_pattern, html)
            
            for match in json_matches:
                url = match[0] or match[1]
                if url and not url.startswith('/'):
                    link_type = self._detect_link_type(url)
                    
                    # 社交媒体链接
                    if link_type in ['twitter', 'instagram', 'tiktok', 'twitch', 'discord']:
                        contacts.append({
                            "type": "social_dm",
                            "value": url,
                            "source_url": linktree_url,
                            "confidence": 0.7,
                            "notes": f"从Linktree提取的{link_type.capitalize()}链接"
                        })
                    # 可能是联系表单的网站
                    elif link_type == 'website':
                        contacts.append({
                            "type": "website",
                            "value": url,
                            "source_url": linktree_url,
                            "confidence": 0.5,
                            "notes": "从Linktree提取的网站链接，可能有联系表单"
                        })
            
            # 3. 提取Discord邀请链接
            discord_pattern = r'https?://(?:www\.)?discord\.(?:gg|com)/[a-zA-Z0-9]+'
            discord_links = re.findall(discord_pattern, html, re.IGNORECASE)
            for link in set(discord_links):
                contacts.append({
                    "type": "social_dm",
                    "value": link,
                    "source_url": linktree_url,
                    "confidence": 0.65,
                    "notes": "从Linktree提取的Discord链接"
                })
            
        except Exception as e:
            print(f"Linktree抓取失败: {e}")
        
        return contacts
    
    def _check_video_descriptions(self, videos: List[Dict]) -> List[Dict]:
        """检查视频描述区"""
        contacts = []
        
        # 实际实现中，这里需要抓取每个视频的页面来查看描述
        # 简化版本：基于已有数据进行推断
        
        for video in videos[:3]:  # 只检查前3个视频
            video_url = video.get("video_url", "")
            if not video_url:
                continue
            
            result = self.web_fetch.fetch(video_url)
            if result["status"] != "success":
                continue
            
            html = result["html"]
            text = result["text"]
            
            import re
            
            # 查找邮箱
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = re.findall(email_pattern, text, re.IGNORECASE)
            
            for email in set(emails):
                clean_email = re.sub(r'\s+', '', email.lower())
                if self._is_valid_email(clean_email):
                    contacts.append({
                        "type": "email",
                        "value": clean_email,
                        "source_url": video_url,
                        "confidence": 0.5,
                        "notes": f"从视频描述提取: {video.get('title', '')[:30]}..."
                    })
            
            # 查找Linktree等链接
            linktree_pattern = r'https?://(?:www\.)?linktr\.ee/[^\s<>"\']+'
            linktree_matches = re.findall(linktree_pattern, html, re.IGNORECASE)
            
            for link in linktree_matches:
                contacts.append({
                    "type": "linktree",
                    "value": link,
                    "source_url": video_url,
                    "confidence": 0.55,
                    "notes": "从视频描述提取的Linktree"
                })
        
        return contacts
    
    def _deep_search(self, context: PipelineContext) -> List[Dict]:
        """深度搜索（通过社媒等）"""
        contacts = []
        
        # 基于频道名称推断社媒账号
        if context.creator_profile:
            creator_name = context.creator_profile.get("creator_name", "")
            custom_url = context.creator_profile.get("custom_url", "")
            
            # 如果知道handle，可以构建社媒链接
            if custom_url:
                # Twitter/X
                contacts.append({
                    "type": "social_dm",
                    "value": f"https://twitter.com/{custom_url}",
                    "source_url": "inferred",
                    "confidence": 0.3,
                    "notes": "基于频道handle推断的Twitter/X链接（需验证）"
                })
                
                # Instagram
                contacts.append({
                    "type": "social_dm",
                    "value": f"https://instagram.com/{custom_url}",
                    "source_url": "inferred",
                    "confidence": 0.3,
                    "notes": "基于频道handle推断的Instagram链接（需验证）"
                })
        
        return contacts
    
    def _is_valid_email(self, email: str) -> bool:
        """验证邮箱格式"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _calculate_email_confidence(self, email: str, is_business: bool) -> float:
        """计算邮箱置信度"""
        confidence = 0.7 if is_business else 0.5
        
        # 检查域名
        domain = email.split("@")[-1].lower()
        domain_weight = self.EMAIL_DOMAIN_WEIGHTS.get(domain, 0.4)
        
        # 综合评分
        confidence = (confidence + domain_weight) / 2
        
        # 检查是否包含商务关键词
        business_keywords = ["business", "contact", "inquiry", "collab", "partnership", 
                            "pr", "media", "marketing", "brand", "sponsor"]
        local_part = email.split("@")[0].lower()
        if any(keyword in local_part for keyword in business_keywords):
            confidence = min(1.0, confidence + 0.15)
        
        return round(confidence, 2)
    
    def _deduplicate_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """去重"""
        seen = set()
        unique = []
        
        for candidate in candidates:
            value = candidate.get("value", "").lower()
            if value and value not in seen:
                seen.add(value)
                unique.append(candidate)
        
        return unique
    
    def _sort_candidates(self, candidates: List[Dict]) -> List[Dict]:
        """按优先级和置信度排序"""
        def sort_key(candidate):
            contact_type = candidate.get("type", "")
            priority = self.CONTACT_PRIORITY.get(contact_type, 99)
            confidence = candidate.get("confidence", 0)
            return (priority, -confidence)  # 优先级升序，置信度降序
        
        return sorted(candidates, key=sort_key)
    
    def _select_recommended(self, candidates: List[Dict]) -> Optional[Dict]:
        """选择推荐的联系方式"""
        if not candidates:
            return None
        
        # 选择第一个（已经按优先级排序）
        best = candidates[0]
        
        # 如果置信度太低，标记为需要验证
        if best.get("confidence", 0) < 0.5:
            best["needs_verification"] = True
        
        return best
    
    def _generate_recommendation(self, recommended: Optional[Dict], 
                                  candidates: List[Dict]) -> str:
        """生成推荐路径说明"""
        if not recommended:
            return "未找到可用联系方式，建议人工补充"
        
        contact_type = recommended.get("type", "")
        confidence = recommended.get("confidence", 0)
        
        recommendations = {
            "business_email": f"推荐使用商务邮箱联系（置信度{confidence:.0%}），这是最直接的合作渠道",
            "email": f"推荐使用邮箱联系（置信度{confidence:.0%}），建议首封邮件说明来意",
            "business_form": "推荐使用官网表单提交合作申请，适合正式商务合作",
            "manager_contact": "推荐通过经纪人联系，适合高价值合作",
            "social_dm": "推荐通过社媒私信初步接触，再引导至邮件沟通",
            "linktree": "推荐访问Linktree查找联系方式",
            "website": "推荐访问官网查找联系表单或邮箱",
        }
        
        base_recommendation = recommendations.get(contact_type, "使用找到的联系方式")
        
        # 添加备选方案
        if len(candidates) > 1:
            backup = candidates[1]
            base_recommendation += f"；如未回复，可尝试{backup.get('type', '其他方式')}"
        
        return base_recommendation
    
    def _handle_no_contact_found(self) -> Dict[str, Any]:
        """处理未找到联系方式的情况"""
        return {
            "status": "success",  # 技术上成功，但业务上需要人工介入
            "contact_candidates": [],
            "recommended_contact": None,
            "recommended_contact_path": "未找到可用联系方式",
            "message": "未找到任何联系方式",
            "needs_human_intervention": True,
            "manual_checklist": [
                "访问频道About页面手动查找",
                "检查视频描述区是否有Linktree链接",
                "通过Twitter/X私信联系",
                "通过Instagram DM联系",
                "查找创作者是否签约MCN/经纪公司",
                "使用第三方工具（如SocialBlade）查找联系信息"
            ]
        }


class OutreachAgent(BaseAgent):
    """D. 首封合作邮件Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的外联专员。
负责生成个性化的首封合作邮件。

要求：
1. 邮件主题3个备选
2. 邮件正文≤180词英文（或中英双语）
3. 清晰CTA：询问media kit/rate card、提供15分钟通话
4. 引用对方近期视频的具体表现作为个性化点
5. 不要首封写死过多条款，核心是建立意向

发件邮箱：cooperate@topuplive.com
"""
    
    # 邮件模板
    EMAIL_TEMPLATES = {
        "standard": {
            "subject_templates": [
                "Collaboration opportunity with {game_name} (YouTube integration)",
                "Paid YouTube sponsorship for your next video?",
                "Brand partnership: {game_name} + {creator_name}"
            ],
            "body_template": """Hi {creator_name},

I'm {sender_name} from {company}. We're working on {game_name} ({genre}, {platform}) and would love to explore a paid YouTube integration with you.

I've been watching your recent videos—especially {video_reference} (great pacing and audience engagement). Based on your typical performance, we think your channel could be a strong fit for a brand-awareness campaign.

**Proposed deliverable (flexible):**
- 1x YouTube long-form video integration (mid-roll or intro, your choice)
- Link in description + pinned comment

**Budget:** ${anchor_price} (open to your rate card / media kit)

If you're interested, could you share your sponsorship email and your current rates for a 60–90s integration? Happy to jump on a quick 15-min call as well.

Best regards,
{sender_name}
{sender_title}
{company}
{sender_email}"""
        },
        "short": {
            "subject_templates": [
                "Quick question: paid YouTube sponsorship?"
            ],
            "body_template": """Hi {creator_name} — I'm {sender_name} from {company}. We'd like to book a paid YouTube integration for {game_name}. Are you open to sponsorships this month?

If yes, could you share your rate card for a 60–90s integration + description link + pinned comment?

Thanks,
{sender_name}
{sender_email}"""
        },
        "follow_up": {
            "subject_templates": [
                "Re: Collaboration opportunity with {game_name}",
                "Following up: {game_name} partnership"
            ],
            "body_template": """Hi {creator_name},

Just following up in case my last email got buried. We'd still love to explore a paid YouTube integration for {game_name}.

If it helps, here's the quick ask:
- 1x long-form integration (60–90s)
- link in description + pinned comment

Could you share your rate card / media kit, or point me to the right contact?

Best,
{sender_name}
{sender_email}"""
        }
    }
    
    DEFAULT_SENDER = {
        "name": "Marketing Team",
        "title": "Partnership Manager",
        "company": "TOPUPlive",
        "email": "cooperate@topuplive.com"
    }
    
    def __init__(self):
        super().__init__("OutreachAgent", self.SYSTEM_PROMPT)
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        执行邮件生成任务
        
        输入参数：
        - game_name: 游戏名称（默认"our new mobile game"）
        - game_genre: 游戏类型（默认"RPG"）
        - game_platform: 游戏平台（默认"Mobile"）
        - template_type: 模板类型（standard/short/follow_up，默认standard）
        - sender_info: 发件人信息（可选）
        - personalization_note: 个性化引用点（可选，自动从videos_data提取）
        - language: 语言（en/zh/bilingual，默认en）
        
        输出结果：
        - email_draft: 邮件草稿
        """
        self.log_execution("start", f"开始生成邮件: {context.creator_name}")
        
        try:
            # 1. 准备参数
            params = self._prepare_email_params(context, kwargs)
            
            # 2. 选择模板
            template_type = kwargs.get("template_type", "standard")
            template = self.EMAIL_TEMPLATES.get(template_type, self.EMAIL_TEMPLATES["standard"])
            
            # 3. 生成邮件主题
            subject_options = self._generate_subjects(template["subject_templates"], params)
            
            # 4. 生成邮件正文
            body = self._generate_body(template["body_template"], params)
            
            # 5. 生成CTA
            cta = self._generate_cta(params)
            
            # 6. 处理语言
            language = kwargs.get("language", "en")
            if language == "bilingual":
                body = self._add_chinese_translation(body, params)
            elif language == "zh":
                # 简化处理：实际应该使用中文模板
                pass
            
            # 7. 构建邮件草稿
            email_draft = {
                "from": params["sender_email"],
                "to": params["recipient_email"],
                "subject_options": subject_options,
                "subject": subject_options[0],  # 默认使用第一个
                "body": body,
                "cta": cta,
                "language": language,
                "word_count": len(body.split()),
                "template_type": template_type,
                "personalization": {
                    "video_referenced": params.get("video_reference"),
                    "anchor_price": params.get("anchor_price"),
                    "creator_name": params.get("creator_name")
                }
            }
            
            result = {
                "status": "success",
                "email_draft": email_draft,
                "message": f"邮件生成完成（{email_draft['word_count']}词）"
            }
            
            # 8. 记录到Context
            context.email_history.append({
                "type": "outbound",
                "stage": "first_touch",
                "template_type": template_type,
                "content": email_draft,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            result = {
                "status": "error",
                "error_type": "email_generation_failed",
                "message": f"邮件生成失败: {str(e)}",
                "email_draft": None
            }
        
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _prepare_email_params(self, context: PipelineContext, kwargs: Dict) -> Dict:
        """准备邮件参数"""
        params = {}
        
        # 创作者信息
        params["creator_name"] = context.creator_name or kwargs.get("creator_name", "Creator")
        
        # 收件人邮箱
        if context.recommended_contact:
            params["recipient_email"] = context.recommended_contact.get("value", "")
        else:
            params["recipient_email"] = kwargs.get("to_email", "")
        
        # 游戏信息
        params["game_name"] = kwargs.get("game_name", "our new mobile game")
        params["game_genre"] = kwargs.get("game_genre", "RPG")
        params["game_platform"] = kwargs.get("game_platform", "Mobile")
        
        # 发件人信息
        sender_info = kwargs.get("sender_info", self.DEFAULT_SENDER)
        params["sender_name"] = sender_info.get("name", self.DEFAULT_SENDER["name"])
        params["sender_title"] = sender_info.get("title", self.DEFAULT_SENDER["title"])
        params["sender_company"] = sender_info.get("company", self.DEFAULT_SENDER["company"])
        params["sender_email"] = sender_info.get("email", self.DEFAULT_SENDER["email"])
        
        # 报价信息
        if context.pricing_card:
            params["anchor_price"] = context.pricing_card.get("anchor_price", 1000)
            params["target_price"] = context.pricing_card.get("target_price", 800)
        else:
            params["anchor_price"] = kwargs.get("anchor_price", 1000)
            params["target_price"] = kwargs.get("target_price", 800)
        
        # 个性化引用（从videos_data提取）
        params["video_reference"] = self._extract_video_reference(context, kwargs)
        
        # 表现数据
        if context.creator_profile and "recent_metrics" in context.creator_profile:
            metrics = context.creator_profile["recent_metrics"]
            params["baseline_views"] = metrics.get("baseline_views", 0)
        else:
            params["baseline_views"] = 0
        
        return params
    
    def _extract_video_reference(self, context: PipelineContext, kwargs: Dict) -> str:
        """提取视频引用（个性化点）"""
        # 如果提供了个性化点，直接使用
        if kwargs.get("personalization_note"):
            return kwargs["personalization_note"]
        
        # 从videos_data中提取
        if context.videos_data:
            # 找播放量最高的非商单视频
            best_video = None
            best_views = 0
            
            for video in context.videos_data:
                if not video.get("is_suspected_sponsored", False):
                    views = video.get("views", 0)
                    if views > best_views:
                        best_views = views
                        best_video = video
            
            # 如果没找到非商单，就用第一个
            if not best_video and context.videos_data:
                best_video = context.videos_data[0]
            
            if best_video:
                title = best_video.get("title", "")
                # 截断标题
                if len(title) > 50:
                    title = title[:47] + "..."
                return f'"{title}"'
        
        # 默认引用
        return "your recent content"
    
    def _generate_subjects(self, templates: List[str], params: Dict) -> List[str]:
        """生成邮件主题"""
        subjects = []
        for template in templates:
            try:
                subject = template.format(**params)
                subjects.append(subject)
            except KeyError:
                # 如果有缺失的参数，跳过或使用默认值
                continue
        return subjects if subjects else ["Collaboration Opportunity"]
    
    def _generate_body(self, template: str, params: Dict) -> str:
        """生成邮件正文"""
        try:
            body = template.format(**params)
            return body
        except KeyError as e:
            # 如果有缺失的参数，使用默认值填充
            return template.format(
                creator_name=params.get("creator_name", "Creator"),
                sender_name=params.get("sender_name", "Marketing Team"),
                company=params.get("sender_company", "Our Company"),
                game_name=params.get("game_name", "our game"),
                genre=params.get("game_genre", "RPG"),
                platform=params.get("game_platform", "Mobile"),
                video_reference=params.get("video_reference", "your recent videos"),
                anchor_price=params.get("anchor_price", 1000),
                sender_title=params.get("sender_title", ""),
                sender_email=params.get("sender_email", "cooperate@topuplive.com")
            )
    
    def _generate_cta(self, params: Dict) -> str:
        """生成CTA"""
        return "询问media kit / rate card，提供15分钟通话时间"
    
    def _add_chinese_translation(self, english_body: str, params: Dict) -> str:
        """添加中文翻译（双语版本）"""
        chinese_version = f"""
【中文翻译】

您好 {params.get('creator_name', 'Creator')}，

我是{params.get('sender_company', '我们公司')}的{params.get('sender_name', '市场团队')}。我们正在推广{params.get('game_name', '我们的新游戏')}，希望能与您探讨YouTube合作机会。

我观看了您最近的视频，特别是{params.get('video_reference', '您的近期内容')}，内容节奏和观众互动都很棒。基于您的典型表现，我们认为您的频道非常适合品牌曝光合作。

**合作形式（可协商）：**
- 1条YouTube长视频整合口播（片头或中插，由您选择）
- 视频描述区链接 + 置顶评论

**预算：** ${params.get('anchor_price', 1000)}（可协商，期待您的报价单）

如果您感兴趣，能否分享您的商务合作邮箱和60-90秒口播的报价？我们也可以安排一次15分钟的简短通话。

此致，
{params.get('sender_name', '市场团队')}
{params.get('sender_email', 'cooperate@topuplive.com')}

---

【English Version】
{english_body}"""
        
        return chinese_version
    
    def generate_follow_up(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        生成跟进邮件
        
        输入参数：
        - original_email: 原始邮件内容
        - follow_up_count: 跟进次数（1或2）
        """
        follow_up_count = kwargs.get("follow_up_count", 1)
        
        # 使用跟进模板
        kwargs["template_type"] = "follow_up"
        
        if follow_up_count == 2:
            # 第二次跟进，添加时间窗口
            kwargs["deadline"] = kwargs.get("deadline", "next Friday")
        
        return self.execute(context, **kwargs)


class NegotiationAgent(BaseAgent):
    """E. 回复处理与谈判推进Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的谈判专员。
负责处理对方回复并推进谈判。

规则：
1. 对方压价：给出两档方案（降价换条件/维持价加权益）
2. 对方要素材/brief：进入Brief流程
3. 对方要数据证明：提供基于median views的估算逻辑
4. 敏感条款（独家/永久授权/保证播放量）：标记NEED_HUMAN_APPROVAL
"""
    
    # 敏感条款关键词
    SENSITIVE_TERMS = [
        "exclusive", "permanent", "guarantee", "guaranteed",
        "独家", "永久", "保证", "保底", "对赌"
    ]
    
    # 谈判意图分类
    INTENT_TYPES = {
        "PRICE_TOO_HIGH": "price_too_high",      # 价格太高
        "ASKING_RATES": "asking_rates",          # 询问报价
        "REQUEST_BRIEF": "request_brief",        # 要素材/Brief
        "REQUEST_DATA": "request_data",          # 要数据证明
        "ACCEPT": "accept",                      # 接受报价
        "DECLINE": "decline",                    # 拒绝
        "COUNTER_OFFER": "counter_offer",        # 还盘
        "ASKING_CLARIFICATION": "asking_clarification",  # 询问细节
        "SENSITIVE_TERMS": "sensitive_terms",    # 敏感条款
    }
    
    def __init__(self):
        super().__init__("NegotiationAgent", self.SYSTEM_PROMPT)
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        执行谈判处理任务
        
        输入参数：
        - raw_reply: 对方邮件原文（必需）
        - budget_ceiling: 预算硬限制（可选）
        - sender_info: 发件人信息（可选）
        
        输出结果：
        - reply_draft: 拟回复邮件
        - updated_stage: 更新后的pipeline阶段
        - next_follow_up: 下次跟进时间
        - risks: 风险与审批项列表
        - need_human_approval: 是否需要人工审批
        """
        self.log_execution("start", f"开始处理回复: {context.creator_name}")
        
        raw_reply = kwargs.get("raw_reply", "")
        if not raw_reply:
            return self._handle_error("未提供对方回复内容")
        
        try:
            # 1. 分析对方意图
            intent_analysis = self._analyze_intent(raw_reply)
            
            # 2. 检查敏感条款
            sensitive_terms_found = self._check_sensitive_terms(raw_reply)
            
            # 3. 根据意图生成回复策略
            if sensitive_terms_found:
                reply_result = self._handle_sensitive_terms(context, raw_reply, sensitive_terms_found, kwargs)
            elif intent_analysis["intent"] == self.INTENT_TYPES["PRICE_TOO_HIGH"]:
                reply_result = self._handle_price_negotiation(context, raw_reply, kwargs)
            elif intent_analysis["intent"] == self.INTENT_TYPES["REQUEST_BRIEF"]:
                reply_result = self._handle_brief_request(context, raw_reply, kwargs)
            elif intent_analysis["intent"] == self.INTENT_TYPES["REQUEST_DATA"]:
                reply_result = self._handle_data_request(context, raw_reply, kwargs)
            elif intent_analysis["intent"] == self.INTENT_TYPES["ACCEPT"]:
                reply_result = self._handle_acceptance(context, raw_reply, kwargs)
            elif intent_analysis["intent"] == self.INTENT_TYPES["DECLINE"]:
                reply_result = self._handle_decline(context, raw_reply, kwargs)
            else:
                reply_result = self._handle_general_inquiry(context, raw_reply, kwargs)
            
            # 4. 构建结果
            result = {
                "status": "success",
                "intent_analysis": intent_analysis,
                "reply_draft": reply_result.get("reply_draft", {}),
                "updated_stage": reply_result.get("updated_stage", PipelineStage.NEGOTIATING.value),
                "next_follow_up": reply_result.get("next_follow_up"),
                "risks": reply_result.get("risks", []),
                "need_human_approval": reply_result.get("need_human_approval", False),
                "message": reply_result.get("message", "回复处理完成")
            }
            
            # 5. 记录到Context
            context.negotiation_log.append({
                "type": "reply_handled",
                "intent": intent_analysis["intent"],
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            result = self._handle_error(f"谈判处理失败: {str(e)}")
        
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _analyze_intent(self, raw_reply: str) -> Dict[str, Any]:
        """分析对方回复意图"""
        reply_lower = raw_reply.lower()
        
        # 关键词匹配
        intent_keywords = {
            self.INTENT_TYPES["PRICE_TOO_HIGH"]: [
                "too high", "expensive", "over budget", "can't afford", "lower", "reduce", "discount",
                "太贵", "超出预算", "价格太高", "便宜", "降价", "优惠"
            ],
            self.INTENT_TYPES["ASKING_RATES"]: [
                "rate", "pricing", "how much", "fee", "cost",
                "报价", "价格", "多少钱", "费用"
            ],
            self.INTENT_TYPES["REQUEST_BRIEF"]: [
                "brief", "materials", "assets", "information", "details",
                "素材", "资料", "brief", "详情"
            ],
            self.INTENT_TYPES["REQUEST_DATA"]: [
                "data", "metrics", "performance", "views", "statistics", "proof",
                "数据", "表现", "播放量", "证明"
            ],
            self.INTENT_TYPES["ACCEPT"]: [
                "interested", "let's do it", "sounds good", "agree", "accept", "confirm",
                "感兴趣", "可以", "同意", "确认"
            ],
            self.INTENT_TYPES["DECLINE"]: [
                "not interested", "pass", "decline", "busy", "schedule", "not now",
                "不感兴趣", "拒绝", "忙", "档期"
            ],
            self.INTENT_TYPES["COUNTER_OFFER"]: [
                "counter", "offer", "proposal", "alternative",
                "还盘", "方案", "建议"
            ],
        }
        
        scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in reply_lower)
            scores[intent] = score
        
        # 找出最高分的意图
        max_intent = max(scores, key=scores.get)
        max_score = scores[max_intent]
        
        if max_score == 0:
            max_intent = self.INTENT_TYPES["ASKING_CLARIFICATION"]
        
        return {
            "intent": max_intent,
            "confidence": min(max_score / 3, 1.0),  # 归一化置信度
            "all_scores": scores
        }
    
    def _check_sensitive_terms(self, raw_reply: str) -> List[str]:
        """检查敏感条款"""
        reply_lower = raw_reply.lower()
        found = []
        
        for term in self.SENSITIVE_TERMS:
            if term.lower() in reply_lower:
                found.append(term)
        
        return found
    
    def _handle_price_negotiation(self, context: PipelineContext, raw_reply: str, kwargs: Dict) -> Dict:
        """处理价格谈判（压价）"""
        pricing_card = context.pricing_card or {}
        budget_ceiling = kwargs.get("budget_ceiling")
        
        anchor_price = pricing_card.get("anchor_price", 1500)
        target_price = pricing_card.get("target_price", 1200)
        floor_price = pricing_card.get("floor_price", 1000)
        
        # 检查是否超出预算硬限制
        if budget_ceiling and floor_price > budget_ceiling:
            return {
                "reply_draft": {
                    "subject": f"Re: Partnership with your channel",
                    "body": self._generate_budget_exceeded_message(context, budget_ceiling),
                    "tone": "polite_decline"
                },
                "updated_stage": PipelineStage.CLOSED_LOST.value,
                "risks": ["底价超出预算硬限制"],
                "need_human_approval": False,
                "message": "底价超出预算，无法继续谈判"
            }
        
        # 生成两档方案
        option_a_price = int(target_price * 0.85)  # 降价15%
        option_b_price = target_price  # 维持价格但加权益
        
        reply_body = f"""Hi {context.creator_name},

Thanks for getting back to us! Totally understand the budget constraints.

To make this work, here are two options:

**Option A (Adjusted fee):** ${option_a_price}
- 45–60s integration (shorter mention)
- Description link only (no pinned comment)
- 1 round of revisions

**Option B (Keep scope):** ${option_b_price}
- 60–90s integration
- Description link + pinned comment
- Performance bonus: extra $200 if the video exceeds {int(pricing_card.get('baseline_views', 50000) * 1.5):,} views in 30 days

Let me know which option you prefer, or share your rate card and we'll align on the best package.

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        return {
            "reply_draft": {
                "subject": f"Re: Partnership options",
                "body": reply_body,
                "tone": "negotiation",
                "options": [
                    {"name": "Option A", "price": option_a_price, "scope": "reduced"},
                    {"name": "Option B", "price": option_b_price, "scope": "enhanced"}
                ]
            },
            "updated_stage": PipelineStage.NEGOTIATING.value,
            "next_follow_up": (datetime.now() + timedelta(days=3)).isoformat(),
            "risks": [],
            "need_human_approval": False,
            "message": f"提供两档方案: A=${option_a_price}, B=${option_b_price}"
        }
    
    def _handle_brief_request(self, context: PipelineContext, raw_reply: str, kwargs: Dict) -> Dict:
        """处理Brief/素材请求"""
        reply_body = f"""Hi {context.creator_name},

Great! Sharing the campaign brief and assets below:

- Brief (Google Doc): [Link to be added]
- Asset pack (drive link): [Link to be added]
- Tracking link (for description): [Link to be added]
- Key points: 60-90s integration, description link + pinned comment

Could you please confirm:
1) Your planned posting date/time
2) Whether you prefer intro or mid-roll placement

Once confirmed, we'll proceed with the agreement and timeline.

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        return {
            "reply_draft": {
                "subject": f"Brief & assets for your review",
                "body": reply_body,
                "tone": "brief_sent"
            },
            "updated_stage": PipelineStage.BRIEF_SENT.value,
            "next_follow_up": (datetime.now() + timedelta(days=5)).isoformat(),
            "risks": [],
            "need_human_approval": False,
            "message": "进入Brief发送阶段"
        }
    
    def _handle_data_request(self, context: PipelineContext, raw_reply: str, kwargs: Dict) -> Dict:
        """处理数据证明请求"""
        metrics = context.creator_profile.get("recent_metrics", {}) if context.creator_profile else {}
        baseline_views = metrics.get("baseline_views", 0)
        median_views = metrics.get("median_views", 0)
        
        reply_body = f"""Hi {context.creator_name},

Thanks for asking! Here's how we estimated the partnership value:

**Our Calculation Logic:**
- Your recent median views: {median_views:,}
- Baseline views (stable performance): {baseline_views:,}
- Estimated CPM range: $8-25 per 1,000 views (based on your region/content)
- Estimated reach value: ${baseline_views // 1000 * 8:,} - ${baseline_views // 1000 * 25:,}

This is based on your actual YouTube performance data, not third-party estimates. The final price also considers content match and your audience engagement quality.

Happy to discuss further or adjust based on your typical sponsorship rates.

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        return {
            "reply_draft": {
                "subject": f"Re: Performance data & pricing logic",
                "body": reply_body,
                "tone": "data_driven"
            },
            "updated_stage": PipelineStage.NEGOTIATING.value,
            "risks": [],
            "need_human_approval": False,
            "message": "提供数据估算逻辑"
        }
    
    def _handle_sensitive_terms(self, context: PipelineContext, raw_reply: str, sensitive_terms: List[str], kwargs: Dict) -> Dict:
        """处理敏感条款"""
        reply_body = f"""Hi {context.creator_name},

Thanks for your email. We'd like to clarify a few points:

Regarding {', '.join(sensitive_terms)}:
- We cannot include guaranteed views/conversions in the agreement since performance depends on many factors outside direct control.
- We don't offer exclusive/permanent rights as standard terms.

What we *can* do is define clear deliverables and quality standards:
- Integration length/placement
- Link placement (description + pinned comment)
- Posting window
- Performance bonus structure

Let me know if you'd like to discuss standard terms, or I can escalate to my manager for special arrangements.

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        risks = [f"对方提出敏感条款: {term}" for term in sensitive_terms]
        
        return {
            "reply_draft": {
                "subject": f"Re: Partnership terms clarification",
                "body": reply_body,
                "tone": "clarification"
            },
            "updated_stage": PipelineStage.NEGOTIATING.value,
            "risks": risks,
            "need_human_approval": True,
            "approval_reason": f"敏感条款需审批: {', '.join(sensitive_terms)}",
            "message": f"检测到敏感条款，需人工审批: {', '.join(sensitive_terms)}"
        }
    
    def _handle_acceptance(self, context: PipelineContext, raw_reply: str, kwargs: Dict) -> Dict:
        """处理接受报价"""
        reply_body = f"""Hi {context.creator_name},

Excellent! We're excited to work with you.

Next steps:
1. I'll send over the campaign brief and assets within 24 hours
2. Please review and confirm your planned posting date
3. We'll prepare the agreement based on our discussion

Looking forward to a great collaboration!

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        return {
            "reply_draft": {
                "subject": f"Confirmed! Next steps",
                "body": reply_body,
                "tone": "confirmation"
            },
            "updated_stage": PipelineStage.BRIEF_SENT.value,
            "next_follow_up": (datetime.now() + timedelta(days=2)).isoformat(),
            "risks": [],
            "need_human_approval": False,
            "message": "对方接受报价，进入Brief阶段"
        }
    
    def _handle_decline(self, context: PipelineContext, raw_reply: str, kwargs: Dict) -> Dict:
        """处理拒绝"""
        reply_body = f"""Hi {context.creator_name},

Thanks for letting us know. No worries at all.

If it's okay, I'll keep your contact for future campaigns that may fit your schedule better. Feel free to reach out anytime if your availability changes.

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        return {
            "reply_draft": {
                "subject": f"Re: Partnership",
                "body": reply_body,
                "tone": "polite_close"
            },
            "updated_stage": PipelineStage.CLOSED_LOST.value,
            "risks": [],
            "need_human_approval": False,
            "message": "对方拒绝，归档"
        }
    
    def _handle_general_inquiry(self, context: PipelineContext, raw_reply: str, kwargs: Dict) -> Dict:
        """处理一般询问"""
        reply_body = f"""Hi {context.creator_name},

Thanks for your reply! Happy to provide more details.

**Our proposal:**
- 1x YouTube long-form video integration (60-90s)
- Link in description + pinned comment
- Budget: ${context.pricing_card.get('target_price', 1200) if context.pricing_card else 1200}

**Timeline:**
- Brief delivery: Within 3 days of confirmation
- Video posting: Within 2 weeks of agreement
- Payment: Net 30 after video goes live

Let me know if you have any other questions or if you'd like to schedule a quick call.

Best regards,
{kwargs.get('sender_info', {}).get('name', 'Partnership Team')}
cooperate@topuplive.com"""
        
        return {
            "reply_draft": {
                "subject": f"Re: Partnership details",
                "body": reply_body,
                "tone": "informative"
            },
            "updated_stage": PipelineStage.NEGOTIATING.value,
            "next_follow_up": (datetime.now() + timedelta(days=3)).isoformat(),
            "risks": [],
            "need_human_approval": False,
            "message": "回复一般询问"
        }
    
    def _generate_budget_exceeded_message(self, context: PipelineContext, budget_ceiling: float) -> str:
        """生成预算超限的婉拒消息"""
        return f"""Hi {context.creator_name},

Thank you for your interest in partnering with us.

After reviewing, we realize our budget range may not align with your current rates. We respect your pricing and understand if this isn't the right fit at the moment.

We'd love to keep your channel in mind for future campaigns with larger budgets. Feel free to reach out if your rates change or if you're open to discussing other collaboration formats.

Best regards,
Partnership Team
cooperate@topuplive.com"""
    
    def _handle_error(self, message: str) -> Dict[str, Any]:
        """处理错误"""
        return {
            "status": "error",
            "error_type": "negotiation_failed",
            "message": message,
            "intent_analysis": {"intent": "error", "confidence": 0},
            "reply_draft": None,
            "updated_stage": PipelineStage.NEGOTIATING.value,
            "need_human_approval": True
        }


class BriefAgent(BaseAgent):
    """F. 曝光合作Brief + 素材对接Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的Brief专员。
负责生成可直接发给创作者的合作Brief。

Brief必须包含：
1. 合作目标与成功标准（可量化但不承诺结果）
2. 内容方向建议3条（贴近创作者风格）
3. 交付规格：视频类型、口播位置、链接放置
4. 时间线：脚本/初稿/定稿/上线
5. 审核机制：反馈时限、修改次数
6. 权益与素材清单
7. 合规与禁区（游戏类特殊要求）
"""
    
    def __init__(self):
        super().__init__("BriefAgent", self.SYSTEM_PROMPT)
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        执行Brief生成任务
        
        输入参数：
        - game_info: 产品信息（必需）
        - key_messages: 卖点（3-5条）
        - must_include: 必须露出点
        - restricted_claims: 禁用词/合规要求
        - landing_url: 落地页链接
        - utm: 跟踪参数
        - asset_pack_url: 素材包链接
        
        输出结果：
        - brief: 完整Brief文档
        - asset_email: 素材对接邮件
        """
        self.log_execution("start", f"开始生成Brief: {context.creator_name}")
        
        try:
            brief_data = self._generate_brief(context, kwargs)
            asset_email = self._generate_asset_email(context, brief_data, kwargs)
            
            context.brief_data = brief_data
            context.asset_pack_url = kwargs.get("asset_pack_url")
            
            result = {
                "status": "success",
                "brief": brief_data,
                "asset_email": asset_email,
                "message": "Brief生成完成"
            }
        except Exception as e:
            result = {
                "status": "error",
                "message": f"Brief生成失败: {str(e)}",
                "brief": {},
                "asset_email": {}
            }
        
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _generate_brief(self, context: PipelineContext, kwargs: Dict) -> Dict:
        """生成Brief文档"""
        game_info = kwargs.get("game_info", "A new mobile game")
        key_messages = kwargs.get("key_messages", ["Fun gameplay", "Great graphics", "Free to play"])
        must_include = kwargs.get("must_include", ["Game logo", "Download link"])
        restricted = kwargs.get("restricted_claims", ["No guarantee of winning"])
        landing_url = kwargs.get("landing_url", "https://example.com/game")
        utm = kwargs.get("utm", "utm_source=youtube")
        
        content_focus = context.creator_profile.get("content_focus", ["Gaming"]) if context.creator_profile else ["Gaming"]
        
        return {
            "campaign_info": {
                "game_name": game_info,
                "campaign_type": "Brand Awareness",
                "target_audience": content_focus,
            },
            "objectives": {
                "primary": "Increase brand awareness and drive game downloads",
                "success_metrics": [
                    "Video published within agreed timeframe",
                    "Brand link placed in description and pinned comment",
                    "Minimum 60s integration in video"
                ],
                "note": "Success metrics are for deliverable tracking only"
            },
            "content_directions": [
                {"title": "First Impressions", "description": f"Share genuine first experience with {game_info}"},
                {"title": "Gameplay Tips", "description": f"Play {game_info} and share tips for new players"},
                {"title": "Feature Showcase", "description": f"Highlight standout features of {game_info}"}
            ],
            "deliverables": {
                "video_type": "Long-form YouTube video",
                "integration_length": "60-90 seconds",
                "placement": "Mid-roll or intro",
                "description_link": f"{landing_url}?{utm}",
                "pinned_comment": True,
                "hashtags": ["#ad", "#sponsored"]
            },
            "timeline": {
                "brief_confirmation": "Within 2 days",
                "video_upload": "Within 14 days of agreement",
                "feedback_turnaround": "24-48 hours",
                "max_revisions": 1
            },
            "assets_provided": {
                "game_accounts": "Test accounts provided",
                "brand_assets": ["Logo pack", "Key art images"],
                "talking_points": key_messages,
                "tracking_link": f"{landing_url}?{utm}"
            },
            "compliance": {
                "required_disclosures": ["#ad or #sponsored"],
                "prohibited_content": restricted + ["No guarantee of rewards"],
                "regional_compliance": "Follow local advertising regulations"
            },
            "must_include": must_include,
            "contact_info": {
                "campaign_manager": "partnerships@topuplive.com",
                "response_time": "24-48 hours"
            },
            "created_at": datetime.now().isoformat()
        }
    
    def _generate_asset_email(self, context: PipelineContext, brief: Dict, kwargs: Dict) -> Dict:
        """生成素材对接邮件"""
        game_info = kwargs.get("game_info", "the game")
        asset_url = kwargs.get("asset_pack_url", "[Link to be shared]")
        
        body = f"""Hi {context.creator_name},

Great! Sharing the campaign brief and assets for {game_info}:

**Brief & Assets:**
- Campaign Brief: [Attached]
- Asset Pack: {asset_url}
- Tracking Link: {brief['deliverables']['description_link']}

**Quick Summary:**
- Integration: 60-90s in your next video
- Timeline: Video upload within 14 days
- Deliverables: Description link + pinned comment

**Next Steps:**
1. Review the brief and confirm your planned posting date
2. Download the game using the test account
3. Create your content
4. Share video preview 48h before publish

Questions? Just reply to this email.

Best regards,
Partnership Team
cooperate@topuplive.com"""
        
        return {
            "subject": f"{game_info} - Campaign Brief & Assets",
            "body": body,
            "attachments": ["Campaign Brief PDF"]
        }


class DailyReportAgent(BaseAgent):
    """G. 日报自动汇总Agent"""
    
    SYSTEM_PROMPT = """你是"网红经济营销岗 AI 分身"的日报专员。
负责生成每日合作进展报告。

日报必须包含：
1. 今日新增线索（名单+链接）
2. 今日触达与回复（数量+关键对话摘要）
3. 报价与谈判进度（按pipeline_stage分组）
4. Brief/素材交付进度
5. 风险与需审批事项
6. 明日计划（达人-动作-时间）
"""
    
    def __init__(self):
        super().__init__("DailyReportAgent", self.SYSTEM_PROMPT)
    
    def execute(self, contexts: List[PipelineContext], **kwargs) -> Dict[str, Any]:
        """
        执行日报生成任务
        
        输入参数：
        - contexts: 当日所有PipelineContext列表
        - date: 日期
        
        输出结果：
        - daily_report: 日报
        """
        self.log_execution("start", f"开始生成日报: {kwargs.get('date', 'today')}")
        
        try:
            report_date = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))
            
            # 1. 统计各阶段数量
            pipeline_stats = self._calculate_pipeline_stats(contexts)
            
            # 2. 汇总新增线索
            new_leads = self._extract_new_leads(contexts)
            
            # 3. 汇总邮件触达和回复
            outreach_stats = self._calculate_outreach_stats(contexts)
            
            # 4. 识别风险和需审批事项
            risks = self._identify_risks(contexts)
            
            # 5. 生成明日计划
            tomorrow_plan = self._generate_tomorrow_plan(contexts)
            
            # 6. 生成摘要
            summary = self._generate_summary(pipeline_stats, outreach_stats, risks)
            
            daily_report = {
                "date": report_date,
                "summary": summary,
                "new_leads": new_leads,
                "outreach": outreach_stats,
                "pipeline_breakdown": pipeline_stats,
                "risks": risks,
                "tomorrow_plan": tomorrow_plan
            }
            
            result = {
                "status": "success",
                "daily_report": daily_report,
                "message": f"日报生成完成: {len(contexts)}个线索, {len(risks)}个风险项"
            }
            
        except Exception as e:
            result = {
                "status": "error",
                "message": f"日报生成失败: {str(e)}",
                "daily_report": None
            }
        
        self.log_execution("complete", result.get("message", ""), result)
        return result
    
    def _calculate_pipeline_stats(self, contexts: List[PipelineContext]) -> List[Dict]:
        """统计Pipeline各阶段数量"""
        from collections import Counter
        
        stage_counts = Counter(ctx.current_stage.value for ctx in contexts)
        
        breakdown = []
        for stage, count in sorted(stage_counts.items()):
            items = [ctx.creator_name for ctx in contexts if ctx.current_stage.value == stage]
            breakdown.append({
                "stage": stage,
                "count": count,
                "items": items[:5]  # 最多显示5个
            })
        
        return breakdown
    
    def _extract_new_leads(self, contexts: List[PipelineContext]) -> List[Dict]:
        """提取新增线索"""
        # 简化处理：返回所有线索
        return [
            {
                "creator_name": ctx.creator_name,
                "channel_url": ctx.channel_url,
                "current_stage": ctx.current_stage.value
            }
            for ctx in contexts
        ]
    
    def _calculate_outreach_stats(self, contexts: List[PipelineContext]) -> Dict:
        """计算触达统计"""
        sent = sum(len(ctx.email_history) for ctx in contexts)
        replied = sum(len(ctx.negotiation_log) for ctx in contexts)
        
        return {
            "sent": sent,
            "replied": replied,
            "reply_rate": round(replied / sent, 2) if sent > 0 else 0
        }
    
    def _identify_risks(self, contexts: List[PipelineContext]) -> List[Dict]:
        """识别风险事项"""
        risks = []
        
        for ctx in contexts:
            # 检查是否需要人工审批
            if ctx.current_stage.value == "need_human_approval":
                risks.append({
                    "type": "need_approval",
                    "creator": ctx.creator_name,
                    "description": f"{ctx.creator_name} 需要人工审批"
                })
            
            # 检查谈判中的风险
            for log in ctx.negotiation_log:
                if log.get("result", {}).get("need_human_approval"):
                    risks.append({
                        "type": "negotiation_risk",
                        "creator": ctx.creator_name,
                        "description": f"{ctx.creator_name} 谈判中出现敏感条款"
                    })
        
        return risks
    
    def _generate_tomorrow_plan(self, contexts: List[PipelineContext]) -> List[Dict]:
        """生成明日计划"""
        plans = []
        
        for ctx in contexts:
            stage = ctx.current_stage.value
            
            if stage == "outreach_sent":
                plans.append({
                    "creator_name": ctx.creator_name,
                    "action": "Follow-up if no reply",
                    "time": "10:00 AM"
                })
            elif stage == "negotiating":
                plans.append({
                    "creator_name": ctx.creator_name,
                    "action": "Reply to negotiation",
                    "time": "2:00 PM"
                })
            elif stage == "brief_sent":
                plans.append({
                    "creator_name": ctx.creator_name,
                    "action": "Check brief confirmation",
                    "time": "11:00 AM"
                })
        
        return plans[:10]  # 最多10条
    
    def _generate_summary(self, pipeline_stats: List[Dict], outreach_stats: Dict, risks: List) -> str:
        """生成日报摘要"""
        total = sum(s["count"] for s in pipeline_stats)
        negotiating = next((s["count"] for s in pipeline_stats if s["stage"] == "negotiating"), 0)
        
        summary = f"今日共处理{total}个线索，"
        summary += f"其中{negotiating}个正在谈判中。"
        summary += f"发送邮件{outreach_stats['sent']}封，收到回复{outreach_stats['replied']}封。"
        
        if risks:
            summary += f"需关注风险项{len(risks)}个。"
        
        return summary


class ContactRefreshAgent(BaseAgent):
    """H. 联系方式刷新与验证Agent"""
    
    REFRESH_INTERVAL_DAYS = 30  # 刷新周期（天）
    
    SYSTEM_PROMPT = """你是联系方式刷新专员，负责定期检查和更新创作者联系方式，确保联系信息的有效性。"""
    
    def __init__(self):
        super().__init__("ContactRefreshAgent", self.SYSTEM_PROMPT)
        self.web_fetch = None
    
    def _init_tools(self):
        if self.web_fetch is None:
            from ..tools.web_fetch import WebFetchTool
            self.web_fetch = WebFetchTool()
    
    def is_stale(self, context: PipelineContext) -> bool:
        """检查联系方式是否需要刷新"""
        verification = context.contact_verification
        if not verification:
            return True
        
        last_update = verification.get("last_update")
        if not last_update:
            return True
        
        try:
            from datetime import timedelta
            last_dt = datetime.fromisoformat(last_update)
            return (datetime.now() - last_dt).days >= self.REFRESH_INTERVAL_DAYS
        except Exception:
            return True
    
    def execute(self, context: PipelineContext, **kwargs) -> Dict[str, Any]:
        """
        刷新并验证联系方式
        
        输入参数：
        - force: 是否强制刷新（忽略周期限制）
        - validate_emails: 是否进行邮箱验证（默认True）
        
        输出结果：
        - changes: 变更列表 {added, removed, unchanged}
        - validation_results: 邮箱验证结果
        - needs_notify: 是否有重要变更需通知
        """
        self._init_tools()
        force = kwargs.get("force", False)
        validate_emails = kwargs.get("validate_emails", True)
        
        if not force and not self.is_stale(context):
            return {
                "status": "skipped",
                "message": f"联系方式在 {self.REFRESH_INTERVAL_DAYS} 天内已更新，无需刷新",
                "changes": {"added": [], "removed": [], "unchanged": []}
            }
        
        self.log_execution("start", f"开始刷新联系方式: {context.creator_name}")
        
        try:
            old_contacts = {c.get("value", "").lower(): c for c in context.contact_candidates}
            
            # 重新运行联系方式查找
            contact_agent = ContactFindingAgent()
            contact_agent.web_fetch = self.web_fetch
            result = contact_agent.execute(context)
            
            new_contacts = {c.get("value", "").lower(): c for c in context.contact_candidates}
            
            # 检测变更
            old_keys = set(old_contacts.keys())
            new_keys = set(new_contacts.keys())
            
            added = [new_contacts[k] for k in (new_keys - old_keys)]
            removed = [old_contacts[k] for k in (old_keys - new_keys)]
            unchanged = [new_contacts[k] for k in (old_keys & new_keys)]
            
            changes = {
                "added": added,
                "removed": removed,
                "unchanged": unchanged
            }
            
            # 邮箱验证
            validation_results = {}
            if validate_emails:
                from ..tools.email_validator import EmailValidator
                validator = EmailValidator()
                
                for contact in context.contact_candidates:
                    if contact.get("type") in ["email", "business_email"]:
                        email = contact.get("value", "")
                        if email:
                            val_result = validator.validate(email, deep=False)
                            validation_results[email] = val_result
                            # 更新联系方式的置信度
                            if val_result["score"] > 0:
                                contact["confidence"] = min(
                                    contact.get("confidence", 0.5) * 0.5 + val_result["score"] * 0.5, 1.0
                                )
                            if val_result.get("disposable"):
                                contact["notes"] = contact.get("notes", "") + " [警告: 一次性邮箱]"
            
            # 更新验证记录
            context.contact_verification = {
                "last_update": datetime.now().isoformat(),
                "validation_results": validation_results,
                "refresh_count": context.contact_verification.get("refresh_count", 0) + 1
            }
            
            needs_notify = len(added) > 0 or len(removed) > 0
            
            return {
                "status": "success",
                "message": f"刷新完成: 新增{len(added)}个, 移除{len(removed)}个",
                "changes": changes,
                "validation_results": validation_results,
                "needs_notify": needs_notify
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": f"联系方式刷新失败: {str(e)}",
                "changes": {"added": [], "removed": [], "unchanged": []},
                "validation_results": {}
            }


class EmailSequenceManager:
    """邮件序列跟进管理器"""
    
    # 跟进序列定义
    SEQUENCE_STEPS = [
        {
            "step": 0,
            "name": "initial",
            "day_offset": 0,
            "subject_template": "Collaboration opportunity with {game_name}",
            "body_template": "initial_contact",
            "description": "首次联系"
        },
        {
            "step": 1,
            "name": "follow_up_1",
            "day_offset": 3,
            "subject_template": "Following up: {game_name} partnership",
            "body_template": "follow_up_1",
            "description": "第一次跟进（3天后）"
        },
        {
            "step": 2,
            "name": "follow_up_2",
            "day_offset": 7,
            "subject_template": "Last follow-up: {game_name} x {creator_name}",
            "body_template": "follow_up_2",
            "description": "第二次跟进（7天后）"
        },
        {
            "step": 3,
            "name": "final",
            "day_offset": 14,
            "subject_template": "Final note: {game_name} collaboration",
            "body_template": "final",
            "description": "最终尝试（14天后）"
        }
    ]
    
    BODY_TEMPLATES = {
        "follow_up_1": """Hi {creator_name},

Just following up in case my previous email got buried. We're still interested in exploring a paid YouTube integration for {game_name}.

Quick ask: a 60–90s integration + description link + pinned comment.
Budget: ${anchor_price} (open to your rates)

Would you have 5 minutes to chat or prefer I send more details via email?

Best,
{sender_name}
cooperate@topuplive.com""",
        
        "follow_up_2": """Hi {creator_name},

One more nudge — I know your inbox gets busy!

We'd love to partner with you for {game_name}. If now's not a good time, totally understand. But if you're open to it, just reply "yes" and I'll send everything over.

Best,
{sender_name}
cooperate@topuplive.com""",
        
        "final": """Hi {creator_name},

This will be my last email on this — I don't want to clutter your inbox!

If you're ever interested in a {game_name} collaboration in the future, feel free to reach out at cooperate@topuplive.com. We'd love to work with you.

Wishing you continued success with your channel!

Best,
{sender_name}
cooperate@topuplive.com"""
    }
    
    def start_sequence(self, context: PipelineContext, game_name: str, anchor_price: int) -> Dict:
        """启动邮件跟进序列"""
        context.email_sequence = {
            "game_name": game_name,
            "anchor_price": anchor_price,
            "current_step": 0,
            "started_at": datetime.now().isoformat(),
            "next_scheduled": datetime.now().isoformat(),
            "completed": False,
            "stopped_reason": None
        }
        return {"status": "started", "message": "邮件序列已启动", "sequence": context.email_sequence}
    
    def get_pending_follow_ups(self, contexts: List[PipelineContext]) -> List[Dict]:
        """获取所有待发送的跟进邮件"""
        pending = []
        now = datetime.now()
        
        for ctx in contexts:
            seq = ctx.email_sequence
            if not seq or seq.get("completed") or seq.get("stopped_reason"):
                continue
            
            # 检查是否到了下次发送时间
            next_scheduled_str = seq.get("next_scheduled")
            if not next_scheduled_str:
                continue
            
            try:
                next_scheduled = datetime.fromisoformat(next_scheduled_str)
            except Exception:
                continue
            
            if now >= next_scheduled:
                current_step = seq.get("current_step", 0)
                if current_step < len(self.SEQUENCE_STEPS):
                    step_info = self.SEQUENCE_STEPS[current_step]
                    pending.append({
                        "context": ctx,
                        "step": step_info,
                        "game_name": seq.get("game_name", "Our Game"),
                        "anchor_price": seq.get("anchor_price", 1000),
                        "overdue_hours": max(0, (now - next_scheduled).total_seconds() / 3600)
                    })
        
        return pending
    
    def advance_sequence(self, context: PipelineContext) -> Dict:
        """推进序列到下一步"""
        seq = context.email_sequence
        if not seq:
            return {"status": "error", "message": "序列未启动"}
        
        current_step = seq.get("current_step", 0)
        next_step = current_step + 1
        
        if next_step >= len(self.SEQUENCE_STEPS):
            # 序列完成
            seq["completed"] = True
            seq["stopped_reason"] = "序列全部发送完毕"
            return {"status": "completed", "message": "邮件序列已全部发送"}
        
        # 计算下次发送时间
        day_offset = self.SEQUENCE_STEPS[next_step]["day_offset"]
        started_at = datetime.fromisoformat(seq["started_at"])
        next_scheduled = started_at + timedelta(days=day_offset)
        
        seq["current_step"] = next_step
        seq["next_scheduled"] = next_scheduled.isoformat()
        
        return {
            "status": "advanced",
            "message": f"已推进到第{next_step + 1}步: {self.SEQUENCE_STEPS[next_step]['description']}",
            "next_step": self.SEQUENCE_STEPS[next_step],
            "next_scheduled": next_scheduled.isoformat()
        }
    
    def stop_sequence(self, context: PipelineContext, reason: str = "手动停止") -> Dict:
        """停止序列（如收到回复）"""
        if context.email_sequence:
            context.email_sequence["stopped_reason"] = reason
            context.email_sequence["stopped_at"] = datetime.now().isoformat()
        return {"status": "stopped", "message": f"序列已停止: {reason}"}
    
    def generate_follow_up_email(self, context: PipelineContext, step_info: Dict,
                                  game_name: str, anchor_price: int) -> Dict:
        """生成跟进邮件内容"""
        template_name = step_info.get("body_template")
        template = self.BODY_TEMPLATES.get(template_name)
        
        if not template:
            # 使用OutreachAgent的模板
            agent = OutreachAgent()
            return agent.generate_follow_up(context, game_name=game_name, follow_up_count=step_info.get("step", 1))
        
        body = template.format(
            creator_name=context.creator_name,
            game_name=game_name,
            anchor_price=anchor_price,
            sender_name="Partnership Team"
        )
        
        subject = step_info["subject_template"].format(
            game_name=game_name,
            creator_name=context.creator_name
        )
        
        return {
            "status": "success",
            "email_draft": {
                "subject": subject,
                "body": body,
                "step_name": step_info["name"],
                "description": step_info["description"]
            }
        }
