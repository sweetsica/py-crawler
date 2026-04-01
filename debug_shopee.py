import asyncio
from playwright.async_api import async_playwright
import json

async def test():
    with open('json/sp.json', 'r', encoding='utf-8') as f:
        cookies = json.load(f)
        formatted_cookies = []
        for cSoft in cookies:
            c = cSoft.copy()
            same_site = c.get("sameSite", "Lax")
            if same_site == "no_restriction":
                c["sameSite"] = "None"
            elif same_site not in ["Lax", "None", "Strict"]:
                c["sameSite"] = "Lax"
            formatted_cookies.append(c)

    url = 'https://shopee.vn/V%C3%A1y-Ng%E1%BB%A7-Th%E1%BA%AFt-N%C6%A1-Ng%E1%BB%B1c-Quy%E1%BA%BFn-R%C5%A9-G%E1%BB%A3i-C%E1%BA%A3m-8113-CWEAR.SEXY_%C4%90%E1%BB%92-NG%E1%BB%A6-N%E1%BB%98I-Y-CAO-C%E1%BA%A4P--i.422592365.21122995713'
    
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        ctx = await b.new_context(viewport={'width': 1280, 'height': 720})
        await ctx.add_cookies(formatted_cookies)
        page = await ctx.new_page()
        print("Visiting URL...")
        await page.goto(url, wait_until='domcontentloaded', timeout=90000)
        await asyncio.sleep(5)
        
        # Click Vietnamese button if it exists
        loc = page.locator('text="Tiếng Việt"').first
        if await loc.is_visible():
            print("Clicking Tiếng Việt...")
            await loc.click()
            await asyncio.sleep(2)
        
        # Scroll down to load ratings
        print("Scrolling...")
        for i in range(12):
             await page.evaluate('window.scrollBy(0, 1000)')
             await asyncio.sleep(1)
        
        rating = await page.query_selector('div.product-detail.page-product__detail + div')
        if rating:
             html = await rating.inner_html()
             with open('rating_dump.html', 'w', encoding='utf-8') as f: 
                 f.write(html)
             print('Dumped HTML to rating_dump.html.')
             
             imgs = await rating.query_selector_all('img')
             print(f'Direct imgs found: {len(imgs)}')
             
             bg_divs = await rating.query_selector_all('div[style*="background-image"]')
             print(f'Divs with bg image found: {len(bg_divs)}')
             
             for el in bg_divs:
                 style = await el.get_attribute("style")
                 print("Found BG:", style)
        else:
             print('No rating section found based on selector.')
        await b.close()

if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(test())
