import asyncio
import json
from scraper import MediaScraper

async def main():
    print("Khởi tạo scraper...")
    s = MediaScraper()
    print("Bắt đầu scrape url...")
    url = "https://www.instagram.com/p/DWV2gXUEw_7/"
    r = await s.scrape(url)
    print("Hoàn tất, ghi kết quả ra debug_output.json")
    with open("debug_output.json", "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    asyncio.run(main())
