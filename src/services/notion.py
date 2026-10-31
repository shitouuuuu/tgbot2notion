from datetime import datetime, timezone
import logging
from notion_client import AsyncClient
from src import config

logger = logging.getLogger(__name__)

PLATFORM_ICONS = {
    'Instagram': '📸',
    'Threads': '🧵',
    'Facebook': '📘',
    'Twitter': '🐦',
    'YouTube': '▶️',
    'TikTok': '🎵',
    'Bilibili': '📺',
    '小红书': '📕',
    '知乎': '💡',
    'Web': '🌐',
}

class NotionService:
    def __init__(self):
        self.client = AsyncClient(auth=config.NOTION_TOKEN)
        self.database_id = config.NOTION_DATABASE_ID
        self._schema_cache = None
        self._data_source_id = None

    async def _resolve_data_source(self):
        """解析数据库对应的数据源 ID（新版 Notion API 支持）"""
        if self._data_source_id:
            return self._data_source_id
        try:
            db = await self.client.databases.retrieve(database_id=self.database_id)
            if 'data_sources' in db and db['data_sources']:
                self._data_source_id = db['data_sources'][0]['id']
            return self._data_source_id
        except Exception as e:
            logger.warning(f"解析 Data Source ID 失败: {e}")
            return None

    async def get_database_schema(self):
        """获取并缓存数据库字段结构，用于智能字段映射"""
        if self._schema_cache is not None:
            return self._schema_cache
        try:
            db = await self.client.databases.retrieve(database_id=self.database_id)
            props = db.get('properties', {})
            # 兼容新版 Notion Data Source 结构
            if not props:
                ds_id = await self._resolve_data_source()
                if ds_id:
                    ds = await self.client.data_sources.retrieve(data_source_id=ds_id)
                    props = ds.get('properties', {})
                
            self._schema_cache = props
            logger.info(f"已成功获取 Notion Database 字段结构: {list(props.keys())}")
            return self._schema_cache
        except Exception as e:
            logger.warning(f"获取 Notion 数据库结构失败，将使用默认字段名: {e}")
            return {}

    async def find_existing_bookmark(self, url: str):
        """
        查重检测：检查当前数据库中是否已经收藏过该 URL
        若存在则返回现有记录的元信息，否则返回 None
        """
        try:
            ds_id = await self._resolve_data_source()
            if not ds_id:
                return None
            
            schema = await self.get_database_schema()
            # 查找 URL 字段名
            url_prop = 'URL'
            for name, prop in schema.items():
                if prop.get('type') == 'url':
                    url_prop = name
                    break
            
            res = await self.client.data_sources.query(
                data_source_id=ds_id,
                filter={
                    "property": url_prop,
                    "url": {"equals": url}
                },
                page_size=1
            )
            results = res.get('results', [])
            if not results:
                return None
            
            page = results[0]
            props = page.get('properties', {})
            title = ""
            for name, prop in props.items():
                if prop.get('type') == 'title':
                    title = "".join([t.get('plain_text', '') for t in prop.get('title', [])])
                    break
            
            return {
                "id": page.get('id'),
                "url": page.get('url', f"https://notion.so/{page.get('id', '').replace('-', '')}"),
                "title": title or "已收藏记录",
                "created_time": page.get('created_time')
            }
        except Exception as e:
            logger.warning(f"查重检测失败（将继续执行正常保存流程）: {e}")
            return None

    async def get_stats(self):
        """获取灵感库统计数据（总数、各平台分布）"""
        try:
            ds_id = await self._resolve_data_source()
            if not ds_id:
                return 0, {}
            
            res = await self.client.data_sources.query(data_source_id=ds_id, page_size=100)
            results = res.get('results', [])
            total = len(results)
            platforms = {}
            for page in results:
                props = page.get('properties', {})
                plat_obj = props.get('Platform', {})
                if plat_obj.get('type') == 'select' and plat_obj.get('select'):
                    p_name = plat_obj['select']['name']
                    platforms[p_name] = platforms.get(p_name, 0) + 1
            return total, platforms
        except Exception as e:
            logger.warning(f"获取统计数据失败: {e}")
            return 0, {}

    async def save_bookmark(self, title: str, url: str, platform: str, summary: str = '', user_note: str = '', image_url: str = '', tags: list = None, extra_images: list = None, stats: str = ''):
        """
        美化版：将轻量元数据格式化为精美 Notion 页面（支持 #标签多选映射、专属 Emoji 图标、Callout 批注卡片、分割线、书签组件）
        """
        schema = await self.get_database_schema()
        
        # 1. 查找 Title 字段
        title_prop = 'Title'
        for name, prop in schema.items():
            if prop.get('type') == 'title':
                title_prop = name
                break
        
        properties = {
            title_prop: {
                "title": [{"type": "text", "text": {"content": (title or url)[:100]}}]
            }
        }
        
        def find_prop(names, expected_type):
            for name, prop in schema.items():
                if prop.get('type') == expected_type and (name.lower() in [n.lower() for n in names] or any(n in name for n in names)):
                    return name
            return None

        # 映射字段
        url_prop = find_prop(['URL', 'Url', 'Link', '链接', '原链接'], 'url')
        if url_prop:
            properties[url_prop] = {"url": url}
            
        plat_prop = find_prop(['Platform', '平台', '来源', 'Source'], 'select')
        if plat_prop:
            properties[plat_prop] = {"select": {"name": platform}}

        # 映射 Tags 标签字段 (multi_select)
        if tags:
            tag_prop = find_prop(['Tags', '标签', '分类', 'Tag'], 'multi_select')
            if tag_prop:
                tag_objs = [{"name": t[:50].replace(',', '')} for t in tags if t]
                if tag_objs:
                    properties[tag_prop] = {"multi_select": tag_objs}
                
        if user_note:
            note_prop = find_prop(['User Note', 'Note', '备注', '批注', '心得'], 'rich_text')
            if note_prop:
                properties[note_prop] = {
                    "rich_text": [{"type": "text", "text": {"content": user_note[:2000]}}]
                }

        if summary:
            sum_prop = find_prop(['Summary', 'Description', '摘要', '内容', '描述'], 'rich_text')
            if sum_prop:
                properties[sum_prop] = {
                    "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]
                }
                
        time_prop = find_prop(['Saved At', 'Date', 'Time', '保存时间', '时间', '创建日期'], 'date')
        if time_prop:
            properties[time_prop] = {
                "date": {"start": datetime.now(timezone.utc).isoformat()}
            }

        # 2. 构造精美正文排版（Page Children）
        children = []

        # 社交互动热度徽章（如果抓取到点赞/转发数据）
        if stats:
            children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "🔥"},
                    "color": "gray_background",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "社交热度："},
                            "annotations": {"bold": True}
                        },
                        {
                            "type": "text",
                            "text": {"content": stats}
                        }
                    ]
                }
            })

        # 个人灵感批注卡片（醒目黄色 Callout）
        if user_note:
            children.append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "icon": {"type": "emoji", "emoji": "💡"},
                    "color": "yellow_background",
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "灵感批注：\n"},
                            "annotations": {"bold": True}
                        },
                        {
                            "type": "text",
                            "text": {"content": user_note[:1900]}
                        }
                    ]
                }
            })
            children.append({"object": "block", "type": "divider", "divider": {}})

        # 内容摘要板块
        children.append({
            "object": "block",
            "type": "heading_3",
            "heading_3": {
                "rich_text": [{"type": "text", "text": {"content": "📌 内容摘要"}}]
            }
        })
        if summary:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": summary[:2000]}}]
                }
            })
        else:
            children.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "（无文本摘要或原帖为纯图文）"},
                            "annotations": {"italic": True, "color": "gray"}
                        }
                    ]
                }
            })

        # 附带多图图集（当推文或帖子包含多张图片时在正文完整展示）
        if extra_images and len(extra_images) > 1:
            children.append({"object": "block", "type": "divider", "divider": {}})
            children.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": "🖼️ 原帖图集"}}]
                }
            })
            for img in extra_images[1:7]:
                if img and img.startswith(('http://', 'https://')):
                    children.append({
                        "object": "block",
                        "type": "image",
                        "image": {
                            "type": "external",
                            "external": {"url": img}
                        }
                    })

        children.append({"object": "block", "type": "divider", "divider": {}})

        # 原帖书签链接
        children.append({
            "object": "block",
            "type": "bookmark",
            "bookmark": {"url": url}
        })

        # 3. 页面图标与外部封面
        icon_emoji = PLATFORM_ICONS.get(platform, '🌐')
        payload = {
            "parent": {"database_id": self.database_id},
            "icon": {"type": "emoji", "emoji": icon_emoji},
            "properties": properties,
            "children": children
        }

        if image_url and image_url.startswith(('http://', 'https://')):
            payload["cover"] = {
                "type": "external",
                "external": {"url": image_url}
            }

        page = await self.client.pages.create(**payload)
        return page.get('url', f"https://notion.so/{page.get('id', '').replace('-', '')}")
