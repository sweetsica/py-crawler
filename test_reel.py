import asyncio
import json
from scraper import MediaScraper

async def main():
    s = MediaScraper()
    url = "https://www.instagram.com/_huyn.hng/reel/DWIyFDGgZqj/"
    r = await s.scrape(url)
    with open("test_reel_out.json", "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
