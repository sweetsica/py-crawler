import asyncio
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def run():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled"
        ])
        context = await browser.new_context(
            viewport={"width": 414, "height": 896},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
            is_mobile=True,
            has_touch=True
        )
        
        try:
            with open('json/sp.json', 'r', encoding='utf-8') as f:
                cookies = json.load(f)
                formatted = []
                for c in cookies:
                    cc = c.copy()
                    ss = cc.get("sameSite", "Lax")
                    if not ss or ss == "no_restriction": ss = "None"
                    elif ss not in ["Lax", "None", "Strict"]: ss = "Lax"
                    cc["sameSite"] = ss
                    formatted.append(cc)
                await context.add_cookies(formatted)
        except Exception as e:
            pass

        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        url = "https://shopee.vn/shop/1717755486/item/52504882633/rating"
        print(f"Loading {url}")
        
        api_data_list = []
        
        async def handle_response(response):
            nonlocal api_data_list
            if "get_ratings" in response.url and response.status == 200:
                try:
                    js = await response.json()
                    if js.get("data") and js["data"].get("ratings"):
                        api_data_list.append(js)
                        print(f"Intercepted ratings API! (Total: {len(api_data_list)} trang)")
                except Exception as e:
                    print("Error parsing response:", e)

        page.on("response", handle_response)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            MAX_PAGES = 5 # Số trang tối đa muốn lấy
            for page_num in range(1, MAX_PAGES + 1):
                # scroll and wait
                for i in range(15):
                    await page.evaluate("window.scrollBy(0, 1000)")
                    await asyncio.sleep(0.5)
                    if len(api_data_list) >= page_num:
                        break
                
                # Next page click
                if page_num < MAX_PAGES:
                    # Shopee usually uses a button with class containing shopee-icon-button--right for next page
                    next_btn = page.locator('button.shopee-icon-button--right')
                    if await next_btn.count() > 0:
                        is_disabled = await next_btn.first.get_attribute("disabled")
                        if is_disabled is not None:
                            print("Đã hết trang (Nút Next bị disable).")
                            break
                        else:
                            print(f"Chuyển sang trang {page_num + 1}...")
                            await next_btn.first.click()
                            await asyncio.sleep(2)
                    else:
                        print("Không tìm thấy nút Next.")
                        await page.screenshot(path="debug_shopee_mobile.png", full_page=True)
                        break
            
            if api_data_list:
                count_img = 0
                count_vid = 0
                for data_chunk in api_data_list:
                    ratings = data_chunk["data"]["ratings"]
                    for r in ratings:
                        for img in r.get("images") or []:
                            count_img += 1
                            print("IMG: https://down-vn.img.susercontent.com/file/" + img)
                        for vid in r.get("videos") or []:
                            count_vid += 1
                            print("VID: " + vid.get("url", ""))
                print(f"Captured {count_img} imgs and {count_vid} vids from {len(api_data_list)} pages.")
            else:
                print("Did not intercept get_ratings API.")
                
        except Exception as e:
            print("Exception:", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
