import asyncio
import os
import sys

from scraper import MediaScraper

async def main():
    scraper = MediaScraper()
    url = "https://www.facebook.com/NoiySanvajulie/posts/pfbid07f3AvHSni8h4tLdxGWhCeKEwu7Ko5oH7fUGHC2B7p9DpS393tNjChMuWo6mzageAl"
    try:
        result = await scraper.scrape(url)
        import json
        with open("result.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("Done")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
