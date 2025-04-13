from flask import Flask, request, render_template_string, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re
import time

app = Flask(__name__)

# HTML đơn giản để nhập URL từ form
form_template = """
<!doctype html>
<title>Facebook Video Extractor</title>
<h2>Nhập link Facebook video:</h2>
<form method="post">
  <input type="text" name="url" style="width:500px">
  <input type="submit">
</form>
{% if video_url %}
  <h3>Video HD URL:</h3>
  <p><a href="{{ video_url }}" target="_blank">{{ video_url }}</a></p>
{% elif error %}
  <p style="color:red">{{ error }}</p>
{% endif %}
"""

def get_browser_native_hd_url(fb_url):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(fb_url)

    time.sleep(5)  # Đợi trang tải

    html = driver.page_source
    driver.quit()

    # Tìm đoạn chứa URL video
    match = re.search(r'"browser_native_hd_url":"(https:\\/\\/[^"]+\.mp4.*?)"', html)
    if match:
        return match.group(1).replace('\\/', '/')
    return None

# Trang web với form
@app.route("/", methods=["GET", "POST"])
def index():
    video_url = None
    error = None
    if request.method == "POST":
        fb_url = request.form.get("url")
        if not fb_url:
            error = "Vui lòng nhập URL Facebook."
        else:
            try:
                video_url = get_browser_native_hd_url(fb_url)
                if not video_url:
                    error = "Không tìm thấy video HD."
            except Exception as e:
                error = f"Lỗi: {str(e)}"
    return render_template_string(form_template, video_url=video_url, error=error)

# API endpoint
@app.route("/api/fb", methods=["POST"])
def extract_fb_video():
    data = request.get_json()
    fb_url = data.get("url")

    if not fb_url:
        return jsonify({"error": "Thiếu URL"}), 400

    try:
        video_url = get_browser_native_hd_url(fb_url)
        if video_url:
            return jsonify({"hd_video_url": video_url})
        else:
            return jsonify({"error": "Không tìm thấy browser_native_hd_url"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
