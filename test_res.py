import asyncio
import re
from playwright.async_api import async_playwright
import json

async def test_find_large_urls():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        with open("json/fb.json", "r", encoding="utf-8") as f:
            c = json.load(f)["cookies"]
            await context.add_cookies(c)
        page = await context.new_page()
        await page.goto("https://www.facebook.com/NoiySanvajulie/posts/pfbid07f3AvHSni8h4tLdxGWhCeKEwu7Ko5oH7fUGHC2B7p9DpS393tNjChMuWo6mzageAl", wait_until="networkidle")
        content = await page.content()
        urls = set()
        for match in re.finditer(r'https:\/\/[^\"\']+?_n\.jpg[^\"\']*', content):
            u = match.group(0).replace('\\/', '/')
            if 'stp=' not in u and ('s2048' in u or 's1080' in u or 'p2048' in u or 'p1080' in u or 's960' in u or 's590' in u or 's720' in u or 'p720' in u or ('stp=' not in u and '_nc_cat' in u)):
                urls.add(u)
        
        print("Found possible URLs:", len(urls))
        for u in list(urls)[:5]:
            print(u)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_find_large_urls())
