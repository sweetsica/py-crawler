import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        
        # load cookie
        import os
        if os.path.exists("json/fb.json"):
            with open("json/fb.json", "r") as f:
                cookies = json.load(f)
                if "cookies" in cookies: cookies = cookies["cookies"]
                formatted = []
                for c in cookies:
                    formatted_c = {
                        "name": c.get("name"),
                        "value": c.get("value"),
                        "domain": c.get("domain"),
                        "path": c.get("path", "/"),
                    }
                    formatted.append(formatted_c)
                await context.add_cookies(formatted)
                
        page = await context.new_page()
        await page.goto("https://www.facebook.com/photo/?fbid=1371200565035992&set=a.465576188931772", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(10)
        await page.screenshot(path="fb_debug.png")
        
        imgs = await page.query_selector_all("img")
        print(f"Total imgs: {len(imgs)}")
        for img in imgs:
            try:
                bounds = await img.bounding_box()
                if not bounds: continue
                src = await img.get_attribute("src")
                if "fbcdn" in src:
                    print(f"[{bounds['width']}x{bounds['height']}] src: {src[:80]}...")
            except:
                pass
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
