import json
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import os
import re
import httpx

class MediaScraper:
    def __init__(self):
        self.browser = None
        self.context = None
        self.pw = None

    async def init_browser(self):
        if not self.browser:
            print("[*] Đang khởi tạo Playwright...")
            self.pw = await async_playwright().start()
            print("[*] Đang chạy trình duyệt Chromium...")
            self.browser = await self.pw.chromium.launch(
                headless=True,
                channel="chrome", # Try to use the real Chrome if available
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            print("[*] Trình duyệt đã sẵn sàng.")

    async def load_cookies(self, context, cookie_file):
        # Normalize cookie path to be inside 'json' folder if not already
        if not cookie_file.startswith("json/"):
            cookie_file = os.path.join("json", cookie_file)
            
        print(f"[*] Đang tải cookie từ file: {cookie_file}")
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    cookies = json.load(f)
                    # Playwright expects a list of dicts. 
                    if isinstance(cookies, dict) and "cookies" in cookies:
                        cookies = cookies["cookies"]
                    
                    formatted_cookies = []
                    for c in cookies:
                        formatted_c = {
                            "name": c.get("name"),
                            "value": c.get("value"),
                            "domain": c.get("domain"),
                            "path": c.get("path", "/"),
                            "expires": c.get("expires", -1),
                            "httpOnly": c.get("httpOnly", False),
                            "secure": c.get("secure", False),
                            "sameSite": c.get("sameSite", "Lax")
                        }
                        same_site = formatted_c["sameSite"]
                        if same_site == "no_restriction":
                            formatted_c["sameSite"] = "None"
                        elif same_site not in ["Lax", "None", "Strict"]:
                            formatted_c["sameSite"] = "Lax"
                        formatted_cookies.append(formatted_c)
                    
                    await context.add_cookies(formatted_cookies)
                    print(f"[*] Đã tải {len(formatted_cookies)} cookies thành công.")
                    return True
            except Exception as e:
                print(f"[!] Lỗi khi đọc file cookie {cookie_file}: {e}")
        else:
            print(f"[!] Cảnh báo: File cookie '{cookie_file}' không tồn tại. Trình duyệt sẽ chạy mà không có đăng nhập.")
        return False

    def get_platform(self, url):
        if "facebook.com" in url or "fb.com" in url or "fb.watch" in url:
            return "facebook", "json/fb.json"
        elif "instagram.com" in url:
            return "instagram", "json/insta.json"
        elif "twitter.com" in url or "x.com" in url:
            return "twitter", "json/x.json"
        return None, None

    async def scrape(self, url):
        platform, cookie_file = self.get_platform(url)
        if not platform:
            return {"error": "link không hỗ trợ"}

        # Twitter: Thử API trước (nhanh, không cần browser)
        if platform == "twitter":
            print(f"[*] Twitter detected, thử API trước...")
            api_media = await self._scrape_twitter_api(url, cookie_file)
            if api_media:
                return {
                    "platform": platform,
                    "url": url,
                    "media": self._deduplicate(api_media)
                }
            print("[!] API không trả về media, fallback sang browser...")

        await self.init_browser()
        
        # Create a new context for each request to avoid cookie bleeding
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        
        await self.load_cookies(context, cookie_file)
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        media_list = []
        network_media = []

        async def handle_request(request):
            req_url = request.url
            if any(ext in req_url.lower() for ext in [".mp4", ".m4v", ".mov"]):
                 network_media.append({"type": "video", "url": req_url})
            elif any(ext in req_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                 if "twimg.com/media" in req_url or "pbs.twimg.com" in req_url or "fbcdn" in req_url or "cdninstagram" in req_url:
                       if "/profile_images/" not in req_url:
                            network_media.append({"type": "image", "url": req_url})

        page.on("request", handle_request)

        try:
            print(f"[*] Đang truy cập URL: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            print("[*] Đã nhận dữ liệu sơ bộ, đang chờ trang render thêm...")
            await asyncio.sleep(15)
            
            title = await page.title()
            print(f"[*] Tiêu đề trang: {title}")
            await page.screenshot(path="debug.png")
            
            print("[*] Đã chờ xong, bắt đầu cào media...")

            if platform == "facebook":
                media_list = await self._scrape_facebook(page)
            elif platform == "instagram":
                media_list = await self._scrape_instagram(page)
            elif platform == "twitter":
                media_list = await self._scrape_twitter(page)

            # Gộp network media (chỉ cho FB/IG, Twitter đã dùng API)
            if platform != "twitter":
                media_list.extend(network_media)

        except Exception as e:
            await context.close()
            return {"error": f"Lỗi truy cập: {str(e)}"}

        await context.close()

        if not media_list:
            return {"error": "Không tìm thấy media hoặc link không hợp lệ"}

        return {
            "platform": platform,
            "url": url,
            "media": self._deduplicate(media_list)
        }

    async def _scrape_facebook(self, page):
        res = []
        print("[*] Đang cào Facebook...")
        # Try to find videos first
        videos = await page.query_selector_all("video")
        print(f"[*] Tìm thấy {len(videos)} thẻ video")
        for v in videos:
            src = await v.get_attribute("src")
            if src and src.startswith("http"):
                res.append({"type": "video", "url": src})

        # Try to find images in posts
        imgs = await page.query_selector_all("img")
        print(f"[*] Tìm thấy {len(imgs)} thẻ img")
        for img in imgs:
            src = await img.get_attribute("src")
            # Filter out small icons or profile pics
            if src and src.startswith("http") and "emoji" not in src and "fbcdn" in src:
                res.append({"type": "image", "url": src})
        
        return self._deduplicate(res)

    async def _scrape_instagram(self, page):
        res = []
        print("[*] Đang cào Instagram...")
        videos = await page.query_selector_all("video")
        print(f"[*] Tìm thấy {len(videos)} thẻ video")
        for v in videos:
            src = await v.get_attribute("src")
            if src:
                res.append({"type": "video", "url": src})

        # Xử lý ảnh trong bài viết
        imgs = await page.query_selector_all("div._aagv img")
        if not imgs:
             imgs = await page.query_selector_all("img")
        
        print(f"[*] Tìm thấy {len(imgs)} thẻ img")
        for img in imgs:
            src = await img.get_attribute("src")
            if src and "cdninstagram" in src:
                res.append({"type": "image", "url": src})
        
        return self._deduplicate(res)

    def _get_tweet_id(self, url):
        """Extract tweet ID from a Twitter/X URL."""
        match = re.search(r'/status/(\d+)', url)
        return match.group(1) if match else None

    async def _scrape_twitter_api(self, url, cookie_file="json/x.json"):
        """Use Twitter GraphQL API to get video variants with bitrate info."""
        tweet_id = self._get_tweet_id(url)
        if not tweet_id:
            print("[!] Không thể lấy tweet ID từ URL")
            return []

        # Load cookies from file
        cookies = {}
        # Ensure path is correct
        if not cookie_file.startswith("json/"):
            cookie_file = os.path.join("json", cookie_file)

        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    c_data = json.load(f)
                    if isinstance(c_data, dict) and "cookies" in c_data:
                        c_data = c_data["cookies"]
                    for c in c_data:
                        cookies[c["name"]] = c["value"]
                print(f"[*] Đã tải cookies từ {cookie_file} cho API.")
            except Exception as e:
                print(f"[!] Lỗi đọc cookie cho API: {e}")
        else:
            print(f"[!] Cảnh báo: Không tìm thấy file cookie {cookie_file}. API có thể bị từ chối.")

        csrf_token = cookies.get("ct0", "")
        if not csrf_token:
            print("[!] Không tìm thấy csrf token (ct0) trong cookies")
            return []

        # Twitter public bearer token (used by the web app)
        bearer_token = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

        # GraphQL TweetDetail endpoint
        variables = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "rankingMode": "Relevance",
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True
        }
        features = {
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "rweb_video_timestamps_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_enhance_cards_enabled": False
        }

        import urllib.parse
        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(features),
        }
        api_url = "https://x.com/i/api/graphql/nBS-WpgA6ZG0CyNHD517JQ/TweetDetail?" + urllib.parse.urlencode(params)

        headers = {
            "authorization": f"Bearer {bearer_token}",
            "x-csrf-token": csrf_token,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Referer": "https://x.com/",
            "Accept": "*/*",
        }

        # Build cookie header string
        cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
        headers["Cookie"] = cookie_str

        print(f"[*] Gọi Twitter API cho tweet ID: {tweet_id}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(api_url, headers=headers, follow_redirects=True, timeout=30.0)
                print(f"[*] API response status: {response.status_code}")

                if response.status_code != 200:
                    print(f"[!] API trả về lỗi: {response.status_code}")
                    print(f"[!] Response body: {response.text[:500]}")
                    return []

                data = response.json()
                return self._extract_media_from_api(data)

        except Exception as e:
            print(f"[!] Lỗi gọi Twitter API: {e}")
            return []

    def _extract_media_from_api(self, data):
        """Extract media items from Twitter API response, selecting highest-bitrate mp4."""
        media_list = []
        
        try:
            instructions = data.get("data", {}).get("tweetResult", {}).get("result", {})
            # Navigate the nested response structure
            # Try timeline approach first (TweetDetail returns timeline entries)
            timeline_instructions = (data.get("data", {})
                .get("threaded_conversation_with_injections_v2", {})
                .get("instructions", []))
            
            entries = []
            for instruction in timeline_instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    break
            
            for entry in entries:
                tweet_results = None
                # Navigate to tweet result
                content = entry.get("content", {})
                if content.get("entryType") == "TimelineTimelineItem":
                    item_content = content.get("itemContent", {})
                    tweet_results = item_content.get("tweet_results", {}).get("result", {})
                
                if not tweet_results:
                    continue
                
                # Handle tweets with "tweet" wrapper (for visibility-filtered tweets)
                if "tweet" in tweet_results:
                    tweet_results = tweet_results["tweet"]
                
                legacy = tweet_results.get("legacy", {})
                extended_entities = legacy.get("extended_entities", {})
                media_items = extended_entities.get("media", [])

                for media in media_items:
                    media_type = media.get("type", "")
                    
                    if media_type == "video" or media_type == "animated_gif":
                        video_info = media.get("video_info", {})
                        variants = video_info.get("variants", [])
                        
                        # Filter only mp4 variants and sort by bitrate (highest first)
                        mp4_variants = [
                            v for v in variants 
                            if v.get("content_type") == "video/mp4" and v.get("bitrate") is not None
                        ]
                        
                        if mp4_variants:
                            mp4_variants.sort(key=lambda v: v.get("bitrate", 0), reverse=True)
                            best = mp4_variants[0]
                            print(f"[*] Tìm thấy video MP4 - Bitrate: {best.get('bitrate')} bps, URL: {best['url']}")
                            media_list.append({
                                "type": "video",
                                "url": best["url"],
                                "bitrate": best.get("bitrate", 0)
                            })
                    
                    elif media_type == "photo":
                        img_url = media.get("media_url_https", "")
                        if img_url:
                            # Get original/large size
                            img_url = re.sub(r'(\?|&)name=\w+', '', img_url)
                            img_url += "?name=large" if "?" not in img_url else "&name=large"
                            media_list.append({"type": "image", "url": img_url})

        except Exception as e:
            print(f"[!] Lỗi parse API response: {e}")
            import traceback
            traceback.print_exc()

        return media_list

    async def _scrape_twitter(self, page):
        res = []
        print("[*] Đang cào X/Twitter...")
        
        # PRIMARY: Dùng Twitter API để lấy video variants với bitrate
        current_url = page.url
        api_media = await self._scrape_twitter_api(current_url)
        if api_media:
            print(f"[*] API trả về {len(api_media)} media items")
            return api_media
        
        print("[!] API không trả về media, fallback sang DOM/Network...")
        
        # FALLBACK: DOM scraping
        # Cuộn trang một chút để kích hoạt lazy loading
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(3)
        
        # Thử lấy lại ảnh từ DOM bài viết
        imgs = await page.query_selector_all("article img")
        if not imgs:
            imgs = await page.query_selector_all("img")
            
        for img in imgs:
            src = await img.get_attribute("src")
            if src and ("twimg.com/media" in src or "pbs.twimg.com" in src):
                if "/profile_images/" not in src and "/candidate_v2/" not in src:
                    if "name=" in src:
                        src = re.sub(r"name=\w+", "name=large", src)
                    res.append({"type": "image", "url": src})

        # Thử lấy video từ DOM
        video_selectors = [
            "video",
            "[data-testid='videoPlayer'] video",
            "article video"
        ]
        for selector in video_selectors:
            videos = await page.query_selector_all(selector)
            for v in videos:
                src = await v.get_attribute("src")
                if src and src.startswith("http"):
                    res.append({"type": "video", "url": src})
                elif src and src.startswith("blob:"):
                    print(f"[*] Tìm thấy blob video: {src}")

        return self._deduplicate(res)

    def _deduplicate(self, media_list):
        seen = set()
        unique = []
        for item in media_list:
            if item["url"] not in seen:
                unique.append(item)
                seen.add(item["url"])
        return unique
