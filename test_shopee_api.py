import httpx
import json

async def run():
    with open('json/sp.json', 'r', encoding='utf-8') as f:
        cookies = json.load(f)
        
    cookie_dict = {}
    for c in cookies:
        cookie_dict[c['name']] = c['value']
        
    shop_id = "422592365"
    item_id = "21122995713"
    api_url = f"https://shopee.vn/api/v2/item/get_ratings?filter=0&flag=1&itemid={item_id}&limit=50&offset=0&shopid={shop_id}&type=0"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": f"https://shopee.vn/shop/{shop_id}/item/{item_id}",
    }
    
    async with httpx.AsyncClient() as client:
        r = await client.get(api_url, headers=headers, cookies=cookie_dict)
        print("Status API:", r.status_code)
        
        try:
            data = r.json()
            if "data" in data and data["data"] and "ratings" in data["data"]:
                ratings = data["data"]["ratings"]
                print(f"Got {len(ratings)} ratings")
                img_count = 0
                vid_count = 0
                for rating in ratings:
                    # extract images
                    if "images" in rating and rating["images"]:
                        img_count += len(rating["images"])
                        for img in rating["images"]:
                            print(f"IMG: https://down-vn.img.susercontent.com/file/{img}")
                    if "videos" in rating and rating["videos"]:
                        vid_count += len(rating["videos"])
                        for vid in rating["videos"]:
                            print(f"VID: {vid.get('url')}")
                            
                print(f"Total Media: {img_count} imgs, {vid_count} videos")
            else:
                print("No data or ratings field in response.")
                print(data)
        except Exception as e:
            print("Failed to parse JSON:", e)
            print(r.text[:500])

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
