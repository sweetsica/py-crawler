from seleniumwire import webdriver  #cho phép bạn chặn, ghi lại, can thiệp vào các request và response HTTP khi trình duyệt hoạt động
import time #dùng để thao tác với thời gian.
import json #làm việc với dữ liệu JSON trong Python.
import os #tương tác với hệ điều hành: tạo thư mục, lấy biến môi trường, xử lý đường dẫn,...
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    #urlparse(url) → phân tích URL thành các thành phần: scheme, netloc, path, params, query, fragment.
    #parse_qs(query_string) → chuyển query string thành dictionary.
    #urlencode(dict) → tạo query string từ dictionary.
    #urlunparse() → lắp ráp lại URL từ các thành phần.


# Tạo danh sách để lưu kết quả
results = []

# Cấu hình driver
options = webdriver.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")

# Khởi tạo trình duyệt với selenium-wire
driver = webdriver.Chrome(options=options)

# Truy cập link video Facebook
url = 'https://www.facebook.com/stories/1912229028852168/UzpfSVNDOjk2NDg4NjYyMjQ2NDYyOA==/?bucket_count=9&source=story_tray'
driver.get(url)

# Chờ vài giây cho các request được gửi đi
time.sleep(10)

# Duyệt qua các request đã bắt được
for request in driver.requests:
    if request.response:
        print("URL:", request.url)
        print("Status Code:", request.response.status_code)
        print("Response Headers:")
        for header, value in request.response.headers.items():
            print(f"  {header}: {value}")
        print("-" * 50)

# sleep(15)


# Duyệt qua các request đã bắt được
for request in driver.requests:
    if request.response:
        # Kiểm tra content-type và content-length
        content_type = request.response.headers.get('content-type', '')
        content_length = request.response.headers.get('content-length', '0')

        # Chuyển content-length về kiểu số nguyên để so sánh
        try:
            content_length = int(content_length)
        except ValueError:
            content_length = 0

        # Lọc theo điều kiện
        if 'video/mp4' in content_type and content_length > 10000:
            result = {
                "URL": request.url,
                "Status Code": request.response.status_code,
                "Content-Type": content_type,
                "Content-Length": content_length
            }
            results.append(result)

# input("Nhấn Enter để tiếp tục...")

# Tạo nội dung HTML từ kết quả
html_content = """
<html>
<head>
    <title>Video Requests (MP4)</title>
    <style>
        body { font-family: Arial, sans-serif; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
        th { background-color: #f2f2f2; }
        h1 { text-align: center; }
    </style>
</head>
<body>
    <h1>Video Requests (MP4)</h1>
    <table>
        <tr><th>URL</th><th>Status Code</th><th>Content-Type</th><th>Content-Length</th></tr>"""
# Hàm để loại bỏ tham số bytestart và byteend khỏi URL
def remove_bytestart_and_byteend(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    
    # Loại bỏ các tham số 'bytestart' và 'byteend'
    query_params.pop('bytestart', None)
    query_params.pop('byteend', None)
    
    # Tạo lại URL không có tham số 'bytestart' và 'byteend'
    new_query = urlencode(query_params, doseq=True)
    new_url = parsed_url._replace(query=new_query)
    
    return urlunparse(new_url)

# Thêm các kết quả vào bảng HTML với liên kết
for result in results:
    clean_url = remove_bytestart_and_byteend(result['URL'])
    html_content += f"""
        <tr>
            <td><a href="{clean_url}" target="_blank">{clean_url}</a></td>
            <td>{result['Status Code']}</td>
            <td>{result['Content-Type']}</td>
            <td>{result['Content-Length']}</td>
        </tr>"""

html_content += """
    </table>
</body>
</html>
"""

# Thêm các kết quả vào bảng HTML
for result in results:
    html_content += f"""
        <tr>
            <td>{result['URL']}</td>
            <td>{result['Status Code']}</td>
            <td>{result['Content-Type']}</td>
            <td>{result['Content-Length']}</td>
        </tr>"""

html_content += """
    </table>
</body>
</html>
"""

# Lưu HTML vào file result.html
file_path = "result.html"
with open(file_path, "w") as f:
    f.write(html_content)

# Mở tab mới và hiển thị nội dung từ file HTML
driver.execute_script("window.open('');")  # Mở tab mới
driver.switch_to.window(driver.window_handles[-1])  # Chuyển đến tab mới

# Mở file HTML trong tab mới
driver.get(f"file:///{os.path.abspath(file_path)}")

# Chờ vài giây trước khi đóng trình duyệt
time.sleep(10)

# Đóng trình duyệt
# driver.quit()

input("Nhấn Enter để tiếp tục...")

# pip install selenium-wire selenium
# pip install packaging setuptools
# pip install blinker
