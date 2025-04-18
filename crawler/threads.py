from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import re

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Threads Title Scraper</title>
    <style>
        body {
            font-family: sans-serif;
            padding: 20px;
        }
        form {
            margin-bottom: 30px;
        }
    </style>
</head>
<body>
    <h2>Nhập link bài viết Threads hoặc Facebook:</h2>
    <form method="POST">
        <input name="url" style="width: 400px;" required>
        <input type="submit" value="Lấy thông tin">
    </form>

    {% if title %}
        <h3>Tiêu đề:</h3>
        <div>{{ title }}</div>
    {% endif %}

    {% if account %}
        <h3>Tài khoản:</h3>
        <div>{{ account }}</div>
    {% endif %}

    {% if fb_video_url %}
        <h3>Link video Facebook:</h3>
        <div><a href="{{ fb_video_url }}" target="_blank">{{ fb_video_url }}</a></div>
    {% endif %}

    {% if fb_images %}
        <h3>Ảnh Facebook:</h3>
        {% for img in fb_images %}
            <img src="{{ img }}" style="max-width: 300px; margin: 10px;">
        {% endfor %}
    {% endif %}
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def index():
    title = ""
    account = ""
    fb_video_url = ""
    fb_images = []

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
            html = driver.page_source

            if "facebook.com" in url:
                # Tìm video Facebook
                match = re.search(r'"browser_native_hd_url":"(https:\\/\\/[^\"]+\\.mp4.*?)"', html)
                if match:
                    fb_video_url = match.group(1).replace('\\/', '/')

                # Tìm ảnh Facebook
                try:
                    img_elements = driver.find_elements(
                        By.XPATH,
                        '//img[@referrerpolicy="origin-when-cross-origin" and not(@height) and not(@width)]'
                    )
                    for img in img_elements:
                        src = img.get_attribute('src')
                        if src:
                            fb_images.append(src)
                except Exception as e:
                    print("Lỗi lấy ảnh Facebook:", str(e))
            else:
                # Threads xử lý
                try:
                    title_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[3]/div/div[1]/span[1]')
                    title = title_el.text.strip()
                    if "Translate" in title:
                        title = title.replace("Translate", "").strip()
                except Exception as e:
                    print("Không tìm thấy tiêu đề:", e)

                try:
                    acc_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[2]/div[1]/div[1]/span[1]/div[1]/span[1]/div[1]/a/span[1]/span[1]')
                    account = acc_el.text.strip()
                except Exception as e:
                    print("Không tìm thấy tài khoản:", e)

        except Exception as e:
            print(f"Lỗi xử lý: {e}")

        finally:
            driver.quit()

    return render_template_string(HTML_TEMPLATE, title=title, account=account, fb_video_url=fb_video_url, fb_images=fb_images)

if __name__ == '__main__':
    app.run(debug=True)
