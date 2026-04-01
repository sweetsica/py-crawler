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
        
        api_data = None
        
        async def handle_response(response):
            nonlocal api_data
            if "get_ratings" in response.url and response.status == 200:
                try:
                    js = await response.json()
                    if js.get("data") and js["data"].get("ratings"):
                        api_data = js
                        print("Intercepted ratings API!")
                except Exception as e:
                    print("Error parsing response:", e)

        page.on("response", handle_response)
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # scroll and wait
            for i in range(10):
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(1)
                if api_data:
                    break
            
            if api_data:
                ratings = api_data["data"]["ratings"]
                count_img = 0
                count_vid = 0
                for r in ratings:
                    for img in r.get("images") or []:
                        count_img += 1
                        print("IMG: https://down-vn.img.susercontent.com/file/" + img)
                    for vid in r.get("videos") or []:
                        count_vid += 1
                        print("VID: " + vid.get("url", ""))
                print(f"Captured {count_img} imgs and {count_vid} vids")
            else:
                print("Did not intercept get_ratings API.")
                
        except Exception as e:
            print("Exception:", e)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
