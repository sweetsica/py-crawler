import asyncio
from playwright.async_api import async_playwright
import json

async def main():
    p = await async_playwright().start()
    b = await p.chromium.launch(headless=True)
    c = await b.new_context(viewport={'width': 1280, 'height': 720})
    
    cookies = json.load(open('json/insta.json'))
    if isinstance(cookies, dict) and 'cookies' in cookies:
        cookies = cookies['cookies']
    await c.add_cookies(cookies)
    
    page = await c.new_page()
    await page.goto('https://www.instagram.com/p/DVh9fevgclM/', wait_until='networkidle')
    await asyncio.sleep(5)
    
    print('Articles:', await page.locator('article').count())
    print('Next button (aria-label):', await page.locator('button[aria-label="Next"], button[aria-label="Tiếp"]').count())
    print('Next button (class _afxw):', await page.locator('button._afxw').count())
    
    imgs = await page.locator('img').all()
    data = []
    import urllib.parse
    for i in imgs:
        try:
            bounds = await i.bounding_box()
            src = await i.get_attribute('src') or ""
            # Make sure it's valid
            if "fbcdn" in src or "cdninstagram" in src:
                 data.append({'src': src[:80] + '...', 'bounds': bounds})
        except:
            pass
            
    print('Total imgs:', len(data))
    for idx, d in enumerate(data):
        print(f"[{idx}] Bounds: {d['bounds']} | Src: {d['src']}")
        
    await b.close()
    await p.stop()

if __name__ == "__main__":
    asyncio.run(main())
