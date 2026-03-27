import asyncio
import json
from scraper import MediaScraper

async def main():
    s = MediaScraper()
    await s.init_browser()
    c = await s.browser.new_context(viewport={'width': 1280, 'height': 720})
    await s.load_cookies(c, 'json/insta.json')
    page = await c.new_page()
    await page.goto('https://www.instagram.com/p/DVh9fevgclM/', wait_until='domcontentloaded', timeout=60000)
    await asyncio.sleep(6)
    
    print('Articles:', await page.locator('article').count())
    print('Next button (aria-label):', await page.locator('button[aria-label="Next"], button[aria-label="Tiếp"]').count())
    print('Next button (class _afxw):', await page.locator('button._afxw').count())
    print('Any button with right chevron SVG:', await page.locator('svg[aria-label="Next"], svg[aria-label="Tiếp"]').count())
    
    imgs = await page.locator('img').all()
    data = []
    
    for i in imgs:
        try:
            bounds = await i.bounding_box()
            src = await i.get_attribute('src') or ""
            if "fbcdn" in src or "cdninstagram" in src:
                 in_article = await i.evaluate('(el) => el.closest("article") !== null')
                 data.append({'src': src[:80] + '...', 'bounds': bounds, 'in_article': in_article})
        except:
            pass
            
    print('Total imgs:', len(data))
    for idx, d in enumerate(data):
        print(f"[{idx}] Bounds: {d['bounds']} | InArticle: {d['in_article']} | Src: {d['src']}")
        
    await c.close()
    await s.browser.close()
    await s.pw.stop()

if __name__ == "__main__":
    asyncio.run(main())
