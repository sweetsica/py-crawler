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
                args=[
                    "--no-sandbox", 
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            print("[*] Trình duyệt đã sẵn sàng.")

    async def load_cookies(self, context, cookie_file):
        # Đảm bảo đường dẫn file chuẩn xác trên mọi OS (Windows/Linux)
        filename = os.path.basename(cookie_file)
        cookie_file = os.path.join("json", filename)
            
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
                    
                    try:
                        await context.add_cookies(formatted_cookies)
                        print(f"[*] Đã tải {len(formatted_cookies)} cookies thành công.")
                        return True
                    except Exception as cookie_err:
                        print(f"[!] Playwright không chấp nhận định dạng cookie từ {cookie_file}: {cookie_err}")
                        return False
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
        elif "threads.net" in url or "threads.com" in url:
            return "threads", "json/threads.json"
        elif "shopee.vn" in url:
            return "shopee", "json/sp.json"
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

        try:
            await self.init_browser()
        except Exception as e:
            msg = f"Lỗi khởi động trình duyệt trên Host: {str(e)}. Hãy thử chạy 'playwright install' trên server."
            print(f"[!] {msg}")
            return {"error": msg}
        
        # Create a new context for each request to avoid cookie bleeding
        is_mobile = False
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            is_mobile=is_mobile,
            has_touch=is_mobile
        )
        
        await self.load_cookies(context, cookie_file)
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        media_list = []
        network_media = []

        async def handle_request(request):
            req_url = request.url
            if any(ext in req_url.lower() for ext in [".mp4", ".m4v", ".mov"]):
                 # Check if it's an audio dash chunk via efg param
                 is_audio = False
                 if "efg=" in req_url:
                     import urllib.parse
                     import base64
                     m = re.search(r'efg=([^&]+)', req_url)
                     if m:
                         efg_str = urllib.parse.unquote(m.group(1))
                         pad = len(efg_str) % 4
                         if pad: efg_str += '=' * (4 - pad)
                         try:
                             dec = base64.b64decode(efg_str.replace('-', '+').replace('_', '/')).decode('utf-8', errors='ignore')
                             if "audi" in dec.lower() or "audio" in dec.lower():
                                 is_audio = True
                         except:
                             pass
                 if not is_audio:
                     network_media.append({"type": "video", "url": req_url})
            elif any(ext in req_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                 # Không lấy ảnh từ network đối với Instagram để tránh rác (icon, tracking pixels, avatar)
                 if platform in ["instagram", "threads"]:
                     pass
                 elif "twimg.com/media" in req_url or "pbs.twimg.com" in req_url or "fbcdn" in req_url:
                       if "/profile_images/" not in req_url:
                            network_media.append({"type": "image", "url": req_url})

        page.on("request", handle_request)

        if platform == "shopee":
            # Khởi chạy ở chế độ Desktop, không cưỡng ép lấy link /rating của mobile.
            print(f"[*] Shopee detected. Dùng nguyên URL PC để cào: {url}")

        try:
            print(f"[*] Đang truy cập URL: {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=90000)
            print("[*] Đã nhận dữ liệu sơ bộ, đang chờ trang render thêm...")
            
            # Instagram chỉ cần 4s là đủ lấy mạng cho main video. Đợi lâu nó tải luôn video gợi ý rác.
            if platform in ["instagram", "threads"]:
                await asyncio.sleep(4)
            else:
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
            elif platform == "threads":
                media_list = await self._scrape_threads(page)
            elif platform == "shopee":
                media_list = await self._scrape_shopee(page)

            # Gộp network media (chỉ cho FB/IG, Twitter đã dùng API)
            if platform != "twitter":
                # Kiểm tra xem TRÊN TRANG (DOM) có thực sự chứa thẻ <video> không
                # Reel thường có thẻ video nhưng src có thể bị ẩn hoặc là blob: lúc cào bước 1
                if platform in ["threads", "instagram"]:
                    has_dom_video = any(m.get("type") == "video" for m in media_list)
                else:
                    has_dom_video = await page.locator("video").count() > 0
                
                filtered_network_media = []
                for net_item in network_media:
                    # Nếu bài đăng thuần là album ảnh (DOM không có thẻ <video>)
                    # Mọi video mồi từ network (như reels gợi ý, video nền đăng nhập) đều bị chặn 100%
                    if net_item.get("type") == "video" and not has_dom_video:
                        continue
                    filtered_network_media.append(net_item)
                    
                media_list.extend(filtered_network_media)

        except Exception as e:
            await context.close()
            return {"error": f"Lỗi truy cập: {str(e)}"}

        await context.close()

        if not media_list:
            return {"error": "Không tìm thấy media hoặc link không hợp lệ"}

        return {
            "platform": platform,
            "url": url,
            "media": self._deduplicate(media_list, platform)
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

        # Cơ chế cào Album ưu việt:
        # IG xoá ảnh khỏi DOM khi lướt sang trang mới (chống lag), nên phải bắt ảnh TỪNG KHUNG HÌNH một.
        # IG bỏ thẻ <article> ở UI mới, nên ta dùng Toán Học (Bounding Box) để chặn grid thumbnails (rộng ~310px)
        collected_srcs = set()
        
        async def extract_visible_images():
            imgs = await page.query_selector_all("img")
            for img in imgs:
                try:
                    bounds = await img.bounding_box()
                    if not bounds: continue
                    # Main image (kể cả dọc/ngang) trên viewport 1280x720 luôn có width >= 400px.
                    # Khung ảnh "More posts" lưới 3 cột dưới màn hình luôn tự bóp width về khoảng 310px.
                    if bounds["width"] >= 330 and bounds["height"] >= 330:
                        src = await img.get_attribute("src")
                        if src and "150x150" not in src and "100x100" not in src and "profile_pic" not in src:
                            if "cdninstagram" in src or "fbcdn" in src or "instagram" in src:
                                if src not in collected_srcs:
                                    res.append({"type": "image", "url": src})
                                    collected_srcs.add(src)
                except Exception:
                    pass

        # Quét khung hình mặc định đầu tiên
        await extract_visible_images()

        # Click nút "Next" để lazy-load và quét liên tiếp các khung hình bị ẩn
        try:
            next_btn = page.locator('button[aria-label="Next"], button[aria-label="Tiếp"]')
            click_count = 0
            while await next_btn.count() > 0 and await next_btn.first.is_visible() and click_count < 15:
                await next_btn.first.click()
                await asyncio.sleep(0.5)
                # Quét lại sau mỗi lần lật sang trang mới
                await extract_visible_images()
                click_count += 1
            if click_count > 0:
                print(f"[*] Đã lật trang {click_count} lần để mở khóa toàn bộ {len(collected_srcs)} ảnh album")
        except Exception as e:
            pass
        
        return self._deduplicate(res)

    async def _scrape_threads(self, page):
        res = []
        print("[*] Đang cào Threads...")
        
        # Tìm toạ độ Y của bài viết (Target Post) để không lấy nhầm ảnh/video từ Comments
        import re
        post_id = None
        match = re.search(r'/post/([^/?]+)', page.url)
        if match:
            post_id = match.group(1)

        target_y = -1
        if post_id:
            links = await page.query_selector_all(f'a[href*="{post_id}"]')
            for link in links:
                try:
                    bounds = await link.bounding_box()
                    if bounds and bounds["y"] > 0:
                        target_y = bounds["y"]
                        print(f"[*] Tìm thấy toạ độ bài viết gốc: Y={target_y}")
                        break
                except:
                    pass
        
        videos = await page.query_selector_all("video")
        print(f"[*] Tìm thấy {len(videos)} thẻ video trên toàn trang")
        for v in videos:
            try:
                bounds = await v.bounding_box()
                if bounds and target_y > 0 and (bounds["y"] < target_y - 300 or bounds["y"] > target_y + 850):
                    print(f"    - Bỏ qua video ngoài vùng mục tiêu (Y={bounds['y']})")
                    continue
                    
                src = await v.get_attribute("src")
                if src:
                    res.append({"type": "video", "url": src})
            except Exception:
                pass

        imgs = await page.query_selector_all("img")
        print(f"[*] Tìm thấy {len(imgs)} thẻ img trên toàn trang")
        for img in imgs:
            try:
                bounds = await img.bounding_box()
                if not bounds: continue
                
                # Bỏ qua hình ảnh từ comment (toạ độ quá xa so với thẻ post chính)
                if target_y > 0 and (bounds["y"] < target_y - 300 or bounds["y"] > target_y + 850):
                    continue
                    
                # Check if it's a main image (Threads posts are usually large)
                if bounds["width"] >= 200 and bounds["height"] >= 200:
                    src = await img.get_attribute("src")
                    if src and "profile_pic" not in src:
                        if "cdninstagram" in src or "fbcdn" in src or "threads" in src:
                            res.append({"type": "image", "url": src})
            except Exception:
                pass
                
        return self._deduplicate(res)

    async def _scrape_shopee(self, page):
        res = []
        print("[*] Đang cào Shopee Rating (PC Version)...")
        
        # Xử lý popup chọn ngôn ngữ nếu có
        try:
            lang_btn = page.locator('button:has-text("Tiếng Việt"), div:has-text("Tiếng Việt"), span:has-text("Tiếng Việt")').first
            if await lang_btn.is_visible(timeout=3000):
                print("[*] Phát hiện popup chọn ngôn ngữ, đang tự động click 'Tiếng Việt'...")
                await lang_btn.click()
                await asyncio.sleep(2)
        except Exception:
            pass
            
        # Shopee lazy loads rating, scroll down a bit
        try:
            for i in range(12):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1)
                
            rating_section = await page.query_selector("div.product-detail.page-product__detail + div")
            if rating_section:
                print("[*] Đã tìm thấy khu vực ĐÁNH GIÁ SẢN PHẨM")
                for page_num in range(1, 6): # Lấy tối đa 5 trang đánh giá
                    print(f"[*] Đang lấy dữ liệu trang {page_num}...")
                    imgs = await page.query_selector_all("div.product-detail.page-product__detail + div img")
                    vids = await page.query_selector_all("div.product-detail.page-product__detail + div video")

                    print(f"    - Tìm thấy {len(imgs)} thẻ img trong khu vực")
                    for img in imgs:
                        src = await img.get_attribute("src")
                        if src and ("susercontent" in src or "shopee" in src):
                            if "avatar" not in src and "profile" not in src:
                                res.append({"type": "image", "url": src})
                                
                    print(f"    - Tìm thấy {len(vids)} thẻ video trong khu vực")
                    for v in vids:
                        src = await v.get_attribute("src")
                        if src and src.startswith("http"):
                            res.append({"type": "video", "url": src})
                            
                    # Thử tìm và click nút Next
                    next_btn = await page.query_selector(".shopee-page-controller button.shopee-icon-button--right")
                    if next_btn:
                        is_disabled = await next_btn.get_attribute("disabled")
                        if is_disabled is not None:
                            print("[*] Đã đến trang đánh giá cuối cùng.")
                            break
                        else:
                            print(f"[*] Chuyển sang trang {page_num + 1}...")
                            await next_btn.click()
                            await asyncio.sleep(2) # Chờ Shopee tải trang mới
                    else:
                        print("[*] Không tìm thấy nút chuyển trang.")
                        break
            else:
                print("[!] Không tìm thấy khu vực ĐÁNH GIÁ SẢN PHẨM, fallback tìm toàn trang")
                imgs = await page.query_selector_all("img")
                vids = await page.query_selector_all("video")
                print(f"[*] Tìm thấy {len(imgs)} thẻ img trên toàn trang")
                for img in imgs:
                    src = await img.get_attribute("src")
                    if src and ("susercontent" in src or "shopee" in src):
                        if "avatar" not in src and "profile" not in src:
                            res.append({"type": "image", "url": src})
                            
                print(f"[*] Tìm thấy {len(vids)} thẻ video trên toàn trang")
                for v in vids:
                    src = await v.get_attribute("src")
                    if src and src.startswith("http"):
                        res.append({"type": "video", "url": src})
                        
        except Exception as e:
            print(f"[!] Lỗi khi cuộn/cào DOM Shopee: {e}")
            
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

    def _clean_url(self, url):
        """Clean URLs by removing bytestart and byteend parameters to get full videos"""
        if not url or not isinstance(url, str):
            return url
        url = re.sub(r'([?&])bytestart=\d+&?', r'\1', url)
        url = re.sub(r'([?&])byteend=\d+&?', r'\1', url)
        # Cleanup any resulting empty or redundant parameters
        url = url.replace('?&', '?').replace('&&', '&').rstrip('?&')
        return url

    def _deduplicate(self, media_list, platform=None):
        import urllib.parse
        import base64
        import json
        seen_keys = set()
        unique = []
        
        # Nhóm video theo xpv_asset_id để lấy bitrate cao nhất, tránh trùng lặp do đa độ phân giải
        asset_videos = {}
        processed_list = []
        
        for item in media_list:
            cleaned_url = self._clean_url(item["url"])
            if cleaned_url and cleaned_url.startswith("blob:"):
                # Bỏ qua blob URLs vì không dùng được ở ngoài trình duyệt
                continue
                
            item_copy = item.copy()
            item_copy["url"] = cleaned_url
            
            asset_id = None
            bitrate = -1
            
            if item.get("type") == "video" and "efg=" in cleaned_url:
                m = re.search(r'efg=([^&]+)', cleaned_url)
                if m:
                    efg_str = urllib.parse.unquote(m.group(1))
                    pad = len(efg_str) % 4
                    if pad: efg_str += '=' * (4 - pad)
                    try:
                        dec = base64.b64decode(efg_str.replace('-', '+').replace('_', '/')).decode('utf-8', errors='ignore')
                        efg_data = json.loads(dec)
                        # IG thường dùng xpv_asset_id, FB có thể dùng video_id
                        asset_id = str(efg_data.get("xpv_asset_id", efg_data.get("video_id", "")))
                        if not asset_id or asset_id == "None":
                            asset_id = None
                        bitrate = int(efg_data.get("bitrate", -1))
                    except Exception:
                        pass
                        
            if asset_id:
                # Nếu Asset ID đã tồn tại, chỉ giữ lại bản có bitrate cao nhất
                if asset_id not in asset_videos or bitrate > asset_videos[asset_id]["bitrate"]:
                    asset_videos[asset_id] = {"item": item_copy, "bitrate": bitrate}
            else:
                # Ảnh hoặc video ko có efg đưa vào danh sách chung
                processed_list.append(item_copy)
                
        # Lấy các video duy nhất có chất lượng cao nhất đã được gộp
        for v in asset_videos.values():
            processed_list.append(v["item"])
            
        # Lọc trùng lặp thông thường dựa theo path (phòng hờ backup)
        for item in processed_list:
            cleaned_url = item["url"]
            try:
                parsed = urllib.parse.urlparse(cleaned_url)
                if item.get("type") == "video" and ("fbcdn" in cleaned_url or "cdninstagram" in cleaned_url):
                    key = parsed.path
                else:
                    key = parsed.path if parsed.path else cleaned_url
            except Exception:
                key = cleaned_url
                
            if key not in seen_keys:
                unique.append(item)
                seen_keys.add(key)
                
        # Giới hạn số lượng trả về (cắt video lọt vào do mạng load ngầm)
        final_unique = []
        ig_video_count = 0
        for item in unique:
            if platform in ["instagram", "threads"] and item.get("type") == "video":
                if ig_video_count >= 1:
                    continue
                ig_video_count += 1
            final_unique.append(item)
            
        return final_unique
