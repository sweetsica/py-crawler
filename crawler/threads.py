from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import requests
import hashlib
import mimetypes

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Threads Media Scraper</title>
    <style>
        body {
            font-family: sans-serif;
            padding: 20px;
        }
        form {
            margin-bottom: 30px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 20px;
        }
        .media-card {
            text-align: center;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 10px;
            background: #f9f9f9;
        }
        .media-card img,
        .media-card video {
            width: 100%;
            height: auto;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        a.media-link {
            word-break: break-word;
            font-size: 12px;
            display: block;
            margin-top: 8px;
            color: #007bff;
            text-decoration: none;
        }
        a.media-link:hover {
            text-decoration: underline;
        }
        .raw-html {
            border: 1px solid #ccc;
            padding: 15px;
            margin: 20px 0;
            background-color: #f0f0f0;
        }
    </style>
</head>
<body>
    <h2>Nhập link bài viết Threads:</h2>
    <form method="POST">
        <input name="url" style="width: 400px;" required>
        <input type="submit" value="Lấy media">
    </form>

    {% if raw_div %}
        <h3>HTML của div đầu tiên:</h3>
        <div class="raw-html">
            {{ raw_div|safe }}
        </div>
    {% endif %}

    {% if media %}
        <h3>Media tìm thấy:</h3>
        <div class="grid">
            {% for item in media %}
            <div class="media-card">
                {% if item.type == 'image' %}
                    <img src="{{ item.local_url|safe }}" alt="Ảnh">
                {% elif item.type == 'video' %}
                    <video src="{{ item.url|safe }}" controls></video>
                {% endif %}
                <div><strong>Tiêu đề:</strong> {{ item.title }}</div>
                <div><strong>Account:</strong> <a href="https://www.threads.net/@{{ item.acc }}">{{ item.acc }}</a></div>
                <div><strong>Media:</strong><a href="{{ item.url|safe }}" target="_blank" class="media-link">Xem</a></div>
            </div>
            {% endfor %}
        </div>
    {% endif %}
</body>
</html>
'''

def download_and_save_media(url):
    try:
        filename = hashlib.md5(url.encode()).hexdigest()
        try:
            head = requests.head(url, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
            content_type = head.headers.get("Content-Type", "image/jpeg")
            ext = mimetypes.guess_extension(content_type.split(";")[0])
        except Exception as e:
            print(f"Lỗi HEAD: {e}")
            ext = ".jpg"

        if not ext:
            ext = ".jpg"

        filename += ext
        filepath = f"static/images/{filename}"

        if not os.path.exists(filepath):
            r = requests.get(url, stream=True, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
        return f"/static/images/{filename}"
    except Exception as e:
        print(f"Lỗi tải media: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    media = []
    raw_div = ""
    title = ""
    account = ""

    if request.method == "POST":
        url = request.form["url"]

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)

        try:
            driver.get(url)
            time.sleep(5)

            container = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]')
            # raw_div = container.get_attribute("outerHTML")

            try:
                account_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[2]/div[1]/div[1]/span[1]/div[1]/span[1]/div[1]/a/span[1]/span[1]')
                account = account_el.text.strip()
            except Exception as e:
                print("Không tìm thấy tài khoản:", e)
                account = ""

            try:
                title_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[3]/div/div[1]/span[1]')
                title_raw = title_el.text.strip()
                title = title_raw.replace("Translate", "").strip()
            except Exception as e:
                print("Không tìm thấy tiêu đề:", e)

            # Kiểm tra ảnh bên trong container
            img_elements = container.find_elements(By.XPATH, './/img[@draggable="false"]')
            for img in img_elements:
                srcset = img.get_attribute("srcset")
                if srcset:
                    try:
                        srcset_links = [item.strip().split(" ") for item in srcset.split(",") if " " in item]
                        largest = max(srcset_links, key=lambda x: int(x[1].replace('w', '')) if len(x) > 1 else 0)
                        original_url = largest[0]
                    except:
                        original_url = img.get_attribute("src")
                else:
                    original_url = img.get_attribute("src")

                if original_url:
                    local_url = download_and_save_media(original_url)
                    if local_url:
                        media.append({
                            'type': 'image',
                            'url': original_url,
                            'local_url': local_url,
                            'title': title or 'Ảnh từ bài viết',
                            'acc': account or 'Được lấy từ srcset hoặc src'
                        })

            # Tìm video có playsinline bên trong container
            video_elements = container.find_elements(By.XPATH, './/video[@playsinline]')
            for video in video_elements:
                src = video.get_attribute("src")
                if src:
                    media.append({
                        'type': 'video',
                        'url': src,
                        'local_url': src,
                        'title': title or 'Video từ bài viết',
                        'acc': account or 'Có playsinline'
                    })

        except Exception as e:
            print(f"Lỗi xử lý: {e}")

        finally:
            driver.quit()

    return render_template_string(HTML_TEMPLATE, media=media, raw_div=raw_div, title=title, account=account)    

if __name__ == '__main__':
    os.makedirs("static/images", exist_ok=True)
    app.run(debug=True)
