from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from scraper import MediaScraper
import uvicorn
import httpx
import os
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")
scraper = MediaScraper()

# Đảm bảo thư mục lưu trữ cookie tồn tại
if not os.path.exists("json"):
    os.makedirs("json")

@app.get("/import", response_class=HTMLResponse)
async def import_page(request: Request):
    return templates.TemplateResponse(request, "import.html", {"request": request})

@app.post("/import")
async def import_cookie(source: str = Form(...), content: str = Form(...)):
    """Lưu cookie JSON vào file tưng ứng: x.json, insta.json, fb.json"""
    valid_sources = {
        "x": "x.json",
        "insta": "insta.json",
        "fb": "fb.json",
        "threads": "threads.json",
        "shopee": "sp.json"
    }
    
    if source not in valid_sources:
        return JSONResponse(content={"error": "Nguồn không hợp lệ"}, status_code=400)
    
    try:
        # Kiểm tra xem có đúng định dạng JSON không
        cookie_data = json.loads(content)
        
        file_path = os.path.join("json", valid_sources[source])
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(cookie_data, f, indent=4, ensure_ascii=False)
            
        return JSONResponse(content={"status": "success", "message": "Đã nạp"})
    except json.JSONDecodeError:
        return JSONResponse(content={"error": "Dữ liệu không phải JSON hợp lệ"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"error": f"Lỗi: {str(e)}"}, status_code=500)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    error_trace = traceback.format_exc()
    print(f"[!] Lỗi server: {error_trace}")
    return JSONResponse(
        status_code=500,
        content={
            "error": f"Lỗi máy chủ nội bộ: {str(exc)}",
            "detail": error_trace
        }
    )

@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    return templates.TemplateResponse(request, "index.html", {"request": request})

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})

@app.get("/proxy")
async def proxy_media(url: str, request: Request):
    """Proxy để vượt lỗi 403/CORS. Hỗ trợ Range request cho video player."""
    
    upstream_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Connection": "keep-alive",
    }
    
    # Copy Range header từ browser gửi lên (nếu có)
    range_header = request.headers.get("Range")
    if range_header:
        upstream_headers["Range"] = range_header

    # Phân loại và set Referer + cookie file
    cookies = {}
    if "twimg.com" in url or "x.com" in url:
        upstream_headers["Referer"] = "https://x.com/"
        cookie_file = os.path.join("json", "x.json")
    elif "fbcdn" in url:
        upstream_headers["Referer"] = "https://www.facebook.com/"
        cookie_file = os.path.join("json", "fb.json")
    elif "cdninstagram" in url:
        upstream_headers["Referer"] = "https://www.instagram.com/"
        cookie_file = os.path.join("json", "insta.json")
    elif "threads.net" in url or "threads.com" in url:
        upstream_headers["Referer"] = "https://www.threads.net/"
        cookie_file = os.path.join("json", "threads.json")
    elif "shopee" in url or "susercontent.com" in url or "cv.shopee.vn" in url:
        upstream_headers["Referer"] = "https://shopee.vn/"
        cookie_file = os.path.join("json", "sp.json")
    else:
        upstream_headers["Referer"] = url
        cookie_file = None

    # Load Cookies (quan trọng đối với 1 số video Twitter/X)
    if cookie_file:
        if os.path.exists(cookie_file):
            try:
                with open(cookie_file, "r", encoding='utf-8') as f:
                    c_data = json.load(f)
                    if isinstance(c_data, dict) and "cookies" in c_data:
                        c_data = c_data["cookies"]
                    for c in c_data:
                        cookies[c["name"]] = c["value"]
                # print(f"[Proxy] Đã nạp {len(cookies)} cookies từ {cookie_file}")
            except Exception as e:
                print(f"[Proxy] Lỗi load cookies từ {cookie_file}: {e}")
        else:
            # Chỉ log warn cho Twitter vì nó cần cookie hơn FB/IG khi proxy 
            if "x.json" in cookie_file:
                print(f"[Proxy] Cảnh báo: Không tìm thấy {cookie_file}, có thể không tải được video Twitter.")

    # Dùng 1 client duy nhất - mở GET stream và lấy headers từ chính response đó
    client = httpx.AsyncClient(follow_redirects=True, timeout=60.0)
    
    try:
        upstream_resp = await client.send(
            client.build_request("GET", url, headers=upstream_headers, cookies=cookies if cookies else None),
            stream=True
        )
    except Exception as e:
        await client.aclose()
        return JSONResponse(content={"error": str(e)}, status_code=502)

    if upstream_resp.status_code >= 400:
        await upstream_resp.aclose()
        await client.aclose()
        return JSONResponse(
            content={"error": f"Upstream {upstream_resp.status_code}"}, 
            status_code=upstream_resp.status_code
        )

    # Lấy headers trực tiếp từ upstream response (đảm bảo nhất quán)
    content_type = upstream_resp.headers.get("Content-Type", "application/octet-stream")
    res_headers = {}
    for key in ["Content-Length", "Accept-Ranges", "Content-Range"]:
        if key in upstream_resp.headers:
            res_headers[key] = upstream_resp.headers[key]
    
    status_code = upstream_resp.status_code  # 200 hoặc 206

    async def stream_and_close():
        try:
            async for chunk in upstream_resp.aiter_bytes():
                yield chunk
        finally:
            await upstream_resp.aclose()
            await client.aclose()

    return StreamingResponse(
        stream_and_close(), 
        media_type=content_type, 
        headers=res_headers,
        status_code=status_code
    )

@app.post("/test")
async def test_url(url: str = Form(...)):
    print(f"\n[!] Nhận yêu cầu test URL: {url}")
    # Trả về kết quả cho giao diện test (dùng JSON để frontend xử lý)
    result = await scraper.scrape(url)
    return JSONResponse(content=result)

@app.post("/api/extract")
async def api_extract(request: Request):
    # Hỗ trợ cả JSON và form-data
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
        url = data.get("url")
    else:
        # form-data hoặc x-www-form-urlencoded
        form = await request.form()
        url = form.get("url")
    
    if not url:
        raise HTTPException(status_code=400, detail="Thiếu trường 'url'")
    
    result = await scraper.scrape(url)
    return JSONResponse(content=result)

if __name__ == "__main__":
    print("\n" + "="*50)
    print("[!] SERVER ĐANG KHỞI CHẠY - CẬP NHẬT 19:10 (12/04)")
    print("[!] Đã dọn dẹp file rác và cập nhật nhật ký dự án")
    print(f"[!] Branch: main050426-01")
    print("="*50 + "\n")
    port = int(os.environ.get("PORT", 2603))
    uvicorn.run(app, host="0.0.0.0", port=port)
