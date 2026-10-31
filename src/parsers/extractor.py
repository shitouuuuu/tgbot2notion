import re
from urllib.parse import urlparse, parse_qs, urlunparse
import httpx
from bs4 import BeautifulSoup
from src import config

URL_REGEX = re.compile(r'https?://[^\s<>\"\'`\(\)\[\]]+', re.IGNORECASE)

PLATFORMS = {
    'instagram.com': 'Instagram',
    'instagr.am': 'Instagram',
    'ig.me': 'Instagram',
    'threads.net': 'Threads',
    'threads.com': 'Threads',
    'facebook.com': 'Facebook',
    'fb.com': 'Facebook',
    'fb.watch': 'Facebook',
    'x.com': 'Twitter',
    'twitter.com': 'Twitter',
    't.co': 'Twitter',
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'tiktok.com': 'TikTok',
    'bilibili.com': 'Bilibili',
    'b23.tv': 'Bilibili',
    'xiaohongshu.com': '小红书',
    'xhslink.com': '小红书',
    'zhihu.com': '知乎',
}

def format_count(n: int) -> str:
    """格式化互动数字（如 12500 -> 12.5k, 1200000 -> 1.2M）"""
    if not n or n <= 0:
        return '0'
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)

def extract_hashtags(text: str) -> list[str]:
    """提取文本中的 #标签（兼容中英文、数字、下划线及全角＃）"""
    if not text:
        return []
    raw_tags = re.findall(r'[#＃]([\w\u4e00-\u9fa5]+)', text)
    seen = set()
    tags = []
    for t in raw_tags:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            tags.append(t)
    return tags

def extract_url_and_note(text: str):
    """从用户发送的文本中提取 URL、附带备注以及 #标签"""
    if not text:
        return None, '', []
    
    match = URL_REGEX.search(text)
    tags = extract_hashtags(text)
    
    if not match:
        return None, text.strip(), tags
    
    raw_url = match.group(0).rstrip('.,!?，。！？；;')
    
    # 清理备注：移除 URL 与 #标签，保留干净的个人想法
    note = text.replace(match.group(0), '')
    for t in tags:
        note = re.sub(rf'[#＃]{re.escape(t)}\b', '', note)
    note = re.sub(r'[#＃]([\w\u4e00-\u9fa5]+)', '', note)
    note = re.sub(r'\s+', ' ', note).strip()
    
    return raw_url, note, tags

def identify_platform(url: str) -> str:
    """根据 URL 域名识别社交平台（支持二级域名匹配）"""
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        for key, name in PLATFORMS.items():
            if domain == key or domain.endswith('.' + key):
                return name
    except Exception:
        pass
    return 'Web'

def clean_url(url: str) -> str:
    """清理 URL 中常见的追踪参数（如 utm_*, igsh, fbclid, psln 等）"""
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query, keep_blank_values=True)
        drop_prefixes = ('utm_', 'fbclid', 'igsh', 'share_id', 'si', 'psln', 'igshid', 'xmt', 'slof')
        filtered = {k: v for k, v in query.items() if not any(k.lower().startswith(p) for p in drop_prefixes)}
        query_str = '&'.join([f'{k}={item}' for k, vals in filtered.items() for item in vals])
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query_str, parsed.fragment))
    except Exception:
        return url

async def fetch_instagram_metadata(url: str):
    """
    针对 Instagram 的帖子和 Reels，通过官方 embed captioned 接口免登录抓取正文摘要、封面图与自带标签
    """
    match = re.search(r'instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_-]+)', url)
    if not match:
        return None
    shortcode = match.group(1)
    embed_url = f"https://www.instagram.com/reel/{shortcode}/embed/captioned/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=8.0, proxy=config.PROXY) as client:
            res = await client.get(embed_url)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                caption_elem = soup.find(class_='Caption')
                caption = ""
                if caption_elem:
                    for comment_tag in caption_elem.find_all(class_=re.compile(r'CaptionComments')):
                        comment_tag.decompose()
                    caption = caption_elem.get_text().strip()
                
                img_elem = soup.find('img', class_='EmbeddedMediaImage')
                img_url = img_elem.get('src', '') if img_elem else ''
                
                title = f"Instagram: {caption[:60]}" if caption else f"Instagram 帖子 ({shortcode})"
                tags = extract_hashtags(caption)
                extra_images = [img_url] if img_url else []
                
                return {
                    'title': title,
                    'description': caption,
                    'image_url': img_url,
                    'extra_images': extra_images,
                    'tags': tags,
                    'stats': ''
                }
    except Exception as e:
        print(f"[WARN] Instagram embed fetch failed: {e}")
    return None

async def fetch_twitter_metadata(url: str):
    """
    针对 Twitter/X 推文：
    1. 优先通过 FxTwitter API v2 深度抓取高清多图图集、点赞/转发热度、完整未截断正文及自带标签
    2. 优雅降级：若 API 不可用，使用官方 oEmbed 与 OpenGraph 解析
    """
    # 1. 尝试从 URL 中匹配推文 Status ID
    id_match = re.search(r'(?:twitter\.com|x\.com)/[^/]+/status/(\d+)', url)
    if id_match:
        tweet_id = id_match.group(1)
        api_url = f"https://api.fxtwitter.com/2/status/{tweet_id}"
        api_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            async with httpx.AsyncClient(headers=api_headers, follow_redirects=True, timeout=8.0, proxy=config.PROXY) as client:
                res = await client.get(api_url)
                if res.status_code == 200:
                    data = res.json()
                    st = data.get('status', {})
                    text = st.get('text', '').strip()
                    author = st.get('author', {})
                    author_name = author.get('name', 'Twitter').strip()
                    screen_name = author.get('screen_name', '').strip()
                    
                    title = f"{author_name} (@{screen_name}): {text[:50]}" if screen_name else f"{author_name}: {text[:50]}"
                    if not text:
                        title = f"{author_name} 的推文"

                    likes = st.get('likes') or 0
                    reposts = st.get('reposts') or 0
                    bookmarks = st.get('bookmarks') or 0
                    stats_items = []
                    if likes:
                        stats_items.append(f"❤️ {format_count(likes)}")
                    if reposts:
                        stats_items.append(f"🔁 {format_count(reposts)}")
                    if bookmarks:
                        stats_items.append(f"🔖 {format_count(bookmarks)}")
                    stats_str = " · ".join(stats_items)

                    # 提取多图及媒体
                    media = st.get('media', {})
                    photos = [p.get('url') for p in media.get('photos', []) if p.get('url')]
                    videos = [v.get('thumbnail_url') for v in media.get('videos', []) if v.get('thumbnail_url')]
                    extra_images = photos + [v for v in videos if v not in photos]
                    cover_img = extra_images[0] if extra_images else ''

                    tags = extract_hashtags(text)

                    return {
                        'title': title,
                        'description': text,
                        'image_url': cover_img,
                        'extra_images': extra_images,
                        'tags': tags,
                        'stats': stats_str
                    }
        except Exception as e:
            print(f"[WARN] FxTwitter deep fetch failed, fallback to oEmbed: {e}")

    # 2. 降级方案：Twitter 官方 oEmbed API + OpenGraph
    headers = {
        'User-Agent': 'facebookexternalhit/1.1 (+https://www.facebook.com/externalhit_uatext.php) Mozilla/5.0'
    }
    title = ""
    description = ""
    image_url = ""
    
    try:
        oembed_url = f"https://publish.x.com/oembed?url={url}"
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=8.0, proxy=config.PROXY) as client:
            res = await client.get(oembed_url)
            if res.status_code == 200:
                data = res.json()
                author = data.get("author_name", "Twitter")
                html_raw = data.get("html", "")
                soup = BeautifulSoup(html_raw, "html.parser")
                p = soup.find("p")
                if p:
                    text = p.get_text().strip()
                    title = f"{author}: {text[:60]}"
                    description = text
    except Exception as e:
        print(f"[WARN] Twitter oEmbed fetch failed: {e}")

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=8.0, proxy=config.PROXY) as client:
            res = await client.get(url)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                if og_img and og_img.get("content"):
                    img_src = og_img["content"].strip()
                    if img_src.startswith("http") and not img_src.endswith("default-og.a2e144f0cf66.jpg"):
                        image_url = img_src
                if not title:
                    og_title = soup.find("meta", property="og:title")
                    if og_title and og_title.get("content"):
                        title = og_title["content"].strip()
    except Exception as e:
        print(f"[WARN] Twitter OG fetch failed: {e}")

    tags = extract_hashtags(description)
    return {
        'title': title or "Twitter / X 推文",
        'description': description,
        'image_url': image_url,
        'extra_images': [image_url] if image_url else [],
        'tags': tags,
        'stats': ''
    }

async def fetch_metadata(url: str):
    """
    异步轻量抓取页面的 OpenGraph 元数据（仅提取标题、描述、封面 URL 及标签，绝不下载大文件媒体）
    """
    platform = identify_platform(url)
    cleaned_url = clean_url(url)
    
    result = {
        'url': cleaned_url,
        'platform': platform,
        'title': '',
        'description': '',
        'image_url': '',
        'extra_images': [],
        'tags': [],
        'stats': '',
    }
    
    # 针对 Instagram 深度解析
    if platform == 'Instagram':
        ig_data = await fetch_instagram_metadata(url)
        if ig_data:
            result.update(ig_data)
            return result

    # 针对 Twitter/X 深度解析
    if platform == 'Twitter':
        tw_data = await fetch_twitter_metadata(cleaned_url)
        if tw_data:
            result.update(tw_data)
            return result

    # 通用 OpenGraph 抓取
    headers = {
        'User-Agent': 'facebookexternalhit/1.1 (+https://www.facebook.com/externalhit_uatext.php) Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True, headers=headers, proxy=config.PROXY) as client:
            res = await client.get(cleaned_url)
            
            # 根据最终跳转后的 URL 域名二次校验（处理短链跳转）
            final_platform = identify_platform(str(res.url))
            if final_platform != 'Web':
                result['platform'] = final_platform
                platform = final_platform

            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # 1. Title
                og_title = soup.find('meta', property='og:title') or soup.find('meta', attrs={'name': 'og:title'})
                if og_title and og_title.get('content'):
                    result['title'] = og_title['content'].strip()
                elif soup.title and soup.title.string:
                    result['title'] = soup.title.string.strip()
                
                # 2. Description
                og_desc = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'og:description'}) or soup.find('meta', attrs={'name': 'description'})
                if og_desc and og_desc.get('content'):
                    result['description'] = og_desc['content'].strip()
                
                # 3. Image URL
                og_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
                if og_img and og_img.get('content'):
                    img_url = og_img['content'].strip()
                    if img_url.startswith(('http://', 'https://')):
                        result['image_url'] = img_url
                        result['extra_images'] = [img_url]
    except Exception as e:
        print(f"[WARN] Generic OpenGraph fetch failed: {e}")

    # 从描述中提取标签
    if not result['tags'] and result['description']:
        result['tags'] = extract_hashtags(result['description'])
        
    return result
