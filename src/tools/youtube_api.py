"""
工具接口 - YouTube API
实现真实的YouTube Data API调用
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
import requests


class YouTubeAPITool:
    """
    YouTube Data API 工具
    
    需要配置API Key才能使用
    文档: https://developers.google.com/youtube/v3
    """
    
    API_BASE = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
    
    def is_available(self) -> bool:
        """检查API是否可用"""
        return self.api_key is not None
    
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送API请求"""
        params['key'] = self.api_key
        url = f"{self.API_BASE}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": str(e),
                "error_type": "request_failed"
            }
    
    def _extract_handle_from_url(self, channel_url: str) -> Optional[str]:
        """从频道URL中提取handle"""
        # 支持格式: @username, channel/UC..., c/username, user/username
        patterns = [
            r'youtube\.com/@([\w-]+)',  # @handle
            r'youtube\.com/c/([\w-]+)',  # c/customname
            r'youtube\.com/user/([\w-]+)',  # user/username
            r'youtube\.com/channel/([\w-]+)',  # channel/UC...
        ]
        
        for pattern in patterns:
            match = re.search(pattern, channel_url)
            if match:
                return match.group(1)
        return None
    
    def get_channel_by_url(self, channel_url: str) -> Dict[str, Any]:
        """
        通过频道URL获取频道信息
        """
        if not self.is_available():
            return {
                "status": "error",
                "error": "YouTube API Key未配置",
                "error_type": "api_not_configured"
            }
        
        handle = self._extract_handle_from_url(channel_url)
        if not handle:
            return {
                "status": "error",
                "error": "无法从URL提取频道标识",
                "error_type": "invalid_url"
            }
        
        # 判断是handle还是channel ID
        if handle.startswith('UC') and len(handle) == 24:
            # 这是channel ID
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': handle
            }
        else:
            # 这是handle (@username)
            params = {
                'part': 'snippet,statistics,contentDetails',
                'forHandle': handle
            }
        
        data = self._make_request('channels', params)
        
        if 'error' in data:
            return {
                "status": "error",
                "error": data.get('error', {}).get('message', 'API请求失败'),
                "error_type": "api_error"
            }
        
        items = data.get('items', [])
        if not items:
            return {
                "status": "error",
                "error": "未找到频道",
                "error_type": "channel_not_found"
            }
        
        channel = items[0]
        snippet = channel.get('snippet', {})
        statistics = channel.get('statistics', {})
        content_details = channel.get('contentDetails', {})
        
        return {
            "status": "success",
            "channel_id": channel.get('id'),
            "channel_title": snippet.get('title'),
            "description": snippet.get('description', ''),
            "custom_url": snippet.get('customUrl', ''),
            "published_at": snippet.get('publishedAt'),
            "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url'),
            "country": snippet.get('country'),
            "language": snippet.get('defaultLanguage'),
            "subscriber_count": int(statistics.get('subscriberCount', 0)),
            "view_count": int(statistics.get('viewCount', 0)),
            "video_count": int(statistics.get('videoCount', 0)),
            "hidden_subscriber_count": statistics.get('hiddenSubscriberCount', False),
            "uploads_playlist_id": content_details.get('relatedPlaylists', {}).get('uploads'),
            "raw_data": channel,
            "about_description": "",  # 需要通过About页面获取
            "about_links": []  # 需要通过About页面获取
        }
    
    def list_videos(self, channel_id: str, max_results: int = 30) -> List[Dict[str, Any]]:
        """
        获取频道视频列表
        """
        if not self.is_available():
            return []
        
        # 首先获取频道的uploads playlist ID
        channel_data = self._make_request('channels', {
            'part': 'contentDetails',
            'id': channel_id
        })
        
        items = channel_data.get('items', [])
        if not items:
            return []
        
        uploads_playlist_id = items[0].get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
        if not uploads_playlist_id:
            return []
        
        # 获取playlist中的视频
        videos = []
        next_page_token = None
        
        while len(videos) < max_results:
            params = {
                'part': 'snippet,contentDetails',
                'playlistId': uploads_playlist_id,
                'maxResults': min(50, max_results - len(videos))
            }
            if next_page_token:
                params['pageToken'] = next_page_token
            
            playlist_data = self._make_request('playlistItems', params)
            
            if 'error' in playlist_data:
                break
            
            items = playlist_data.get('items', [])
            if not items:
                break
            
            # 获取视频ID列表
            video_ids = [item['contentDetails']['videoId'] for item in items if 'contentDetails' in item]
            
            # 批量获取视频详情（包含统计信息）
            if video_ids:
                video_details = self.get_video_details(video_ids)
                videos.extend(video_details)
            
            next_page_token = playlist_data.get('nextPageToken')
            if not next_page_token:
                break
        
        return videos[:max_results]
    
    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """
        获取视频详情
        """
        if not self.is_available() or not video_ids:
            return []
        
        # API限制：每次最多50个ID
        chunk_size = 50
        all_videos = []
        
        for i in range(0, len(video_ids), chunk_size):
            chunk = video_ids[i:i + chunk_size]
            
            params = {
                'part': 'snippet,statistics,contentDetails',
                'id': ','.join(chunk)
            }
            
            data = self._make_request('videos', params)
            
            if 'error' in data:
                continue
            
            for video in data.get('items', []):
                snippet = video.get('snippet', {})
                statistics = video.get('statistics', {})
                content_details = video.get('contentDetails', {})
                
                # 解析时长 (ISO 8601格式 PT4M13S)
                duration_str = content_details.get('duration', 'PT0S')
                duration_seconds = self._parse_duration(duration_str)
                
                all_videos.append({
                    "video_id": video.get('id'),
                    "title": snippet.get('title'),
                    "description": snippet.get('description', ''),
                    "published_at": snippet.get('publishedAt'),
                    "thumbnail": snippet.get('thumbnails', {}).get('high', {}).get('url'),
                    "channel_id": snippet.get('channelId'),
                    "channel_title": snippet.get('channelTitle'),
                    "tags": snippet.get('tags', []),
                    "category_id": snippet.get('categoryId'),
                    "duration": duration_seconds,
                    "duration_formatted": self._format_duration(duration_seconds),
                    "view_count": int(statistics.get('viewCount', 0)),
                    "like_count": int(statistics.get('likeCount', 0)) if 'likeCount' in statistics else None,
                    "comment_count": int(statistics.get('commentCount', 0)) if 'commentCount' in statistics else None,
                    "raw_data": video
                })
        
        return all_videos
    
    def _parse_duration(self, duration_str: str) -> int:
        """解析ISO 8601时长格式"""
        import re
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return 0
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def _format_duration(self, seconds: int) -> str:
        """格式化时长为可读字符串"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    def search_videos(self, query: str, max_results: int = 50, 
                      order: str = "relevance",
                      published_after: Optional[str] = None,
                      region_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        搜索YouTube视频
        
        Args:
            query: 搜索关键词
            max_results: 最大结果数
            order: 排序方式 (relevance/date/rating/viewCount/title)
            published_after: 只返回此日期之后发布的视频 (ISO 8601格式)
            region_code: 地区代码 (如 US, CN, JP)
            
        Returns:
            视频列表，包含频道信息
        """
        if not self.is_available():
            return []
        
        all_results = []
        next_page_token = None
        
        while len(all_results) < max_results:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': min(50, max_results - len(all_results)),
                'order': order
            }
            
            if published_after:
                params['publishedAfter'] = published_after
            if region_code:
                params['regionCode'] = region_code
            if next_page_token:
                params['pageToken'] = next_page_token
            
            data = self._make_request('search', params)
            
            if 'error' in data:
                break
            
            items = data.get('items', [])
            if not items:
                break
            
            # 提取视频和频道信息
            for item in items:
                snippet = item.get('snippet', {})
                
                result = {
                    'video_id': item.get('id', {}).get('videoId'),
                    'title': snippet.get('title'),
                    'description': snippet.get('description', ''),
                    'published_at': snippet.get('publishedAt'),
                    'channel_id': snippet.get('channelId'),
                    'channel_title': snippet.get('channelTitle'),
                    'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                    'live_broadcast_content': snippet.get('liveBroadcastContent'),
                    'channel_url': f"https://www.youtube.com/channel/{snippet.get('channelId')}"
                }
                all_results.append(result)
            
            next_page_token = data.get('nextPageToken')
            if not next_page_token:
                break
        
        return all_results[:max_results]
    
    def search_creators(self, query: str, max_results: int = 20,
                        min_subscriber_count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        搜索创作者（基于视频搜索，然后获取频道详情）
        
        Args:
            query: 搜索关键词
            max_results: 最大创作者数
            min_subscriber_count: 最小订阅数筛选
            
        Returns:
            创作者列表，包含频道详情
        """
        # 先搜索视频
        videos = self.search_videos(query, max_results=max_results * 3)
        
        if not videos:
            return []
        
        # 去重频道
        seen_channels = set()
        unique_channels = []
        
        for video in videos:
            channel_id = video.get('channel_id')
            if channel_id and channel_id not in seen_channels:
                seen_channels.add(channel_id)
                unique_channels.append({
                    'channel_id': channel_id,
                    'channel_title': video.get('channel_title'),
                    'channel_url': video.get('channel_url'),
                    'sample_video': video
                })
        
        # 获取频道详情
        creators = []
        for channel_info in unique_channels[:max_results]:
            channel_data = self._make_request('channels', {
                'part': 'snippet,statistics',
                'id': channel_info['channel_id']
            })
            
            if 'error' in channel_data:
                continue
            
            items = channel_data.get('items', [])
            if not items:
                continue
            
            channel = items[0]
            snippet = channel.get('snippet', {})
            stats = channel.get('statistics', {})
            
            subscriber_count = int(stats.get('subscriberCount', 0))
            
            # 筛选订阅数
            if min_subscriber_count and subscriber_count < min_subscriber_count:
                continue
            
            creators.append({
                'channel_id': channel_info['channel_id'],
                'channel_title': snippet.get('title'),
                'channel_url': channel_info['channel_url'],
                'custom_url': snippet.get('customUrl', ''),
                'description': snippet.get('description', ''),
                'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url'),
                'country': snippet.get('country'),
                'published_at': snippet.get('publishedAt'),
                'subscriber_count': subscriber_count,
                'view_count': int(stats.get('viewCount', 0)),
                'video_count': int(stats.get('videoCount', 0)),
                'sample_video_title': channel_info['sample_video'].get('title'),
                'sample_video_id': channel_info['sample_video'].get('video_id')
            })
        
        # 按订阅数排序
        creators.sort(key=lambda x: x['subscriber_count'], reverse=True)
        
        return creators
