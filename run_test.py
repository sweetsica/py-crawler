import asyncio
import sys
from scraper import MediaScraper

async def run():
    url = "https://shopee.vn/V%C3%A1y-Ng%E1%BB%A7-Th%E1%BA%AFt-N%C6%A1-Ng%E1%BB%B1c-Quy%E1%BA%BFn-R%C5%A9-G%E1%BB%A3i-C%E1%BA%A3m-8113-CWEAR.SEXY_%C4%90%E1%BB%92-NG%E1%BB%A6-N%E1%BB%98I-Y-CAO-C%E1%BA%A4P--i.422592365.21122995713"
    print(f"[*] Chạy test với URL: {url} ...")
    scraper = MediaScraper()
    result = await scraper.scrape(url)
    print("\n--- KẾT QUẢ ---")
    
    if "error" in result:
         print("LỖI:", result["error"])
    else:
         media = result.get("media", [])
         imgs = [m for m in media if m["type"] == "image"]
         vids = [m for m in media if m["type"] == "video"]
         print(f"Tổng cộng vớt được: {len(imgs)} IMG / {len(vids)} VIDEO")
         
    # Thêm tí timeout để user kịp nhìn màn hình 
    print("[*] Giữ màn hình vài giây trước khi tắt...")
    await asyncio.sleep(5)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run())
