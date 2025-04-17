from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os
import re
import requests

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
        <h3>Facebook Video:</h3>
        <video src="{{ fb_video_url|safe }}" controls></video>
    {% endif %}
</body>
</html>
'''

def extract_facebook_video_url(page_source):
    match = re.search(r'"browser_native_hd_url":"(https:\\/\\/[^\"]+\.mp4.*?)"', page_source)
    if match:
        return match.group(1).replace('\\/', '/')
    return None

@app.route("/", methods=["GET", "POST"])
def index():
    title = ""
    account = ""
    fb_video_url = ""

    if request.method == "POST":
        url = request.form["url"]

        if "facebook.com" in url:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)

            try:
                driver.get(url)
                time.sleep(5)
                fb_video_url = extract_facebook_video_url(driver.page_source)
            except Exception as e:
                print("Lỗi khi xử lý Facebook:", e)
            finally:
                driver.quit()
        else:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)

            try:
                driver.get(url)
                time.sleep(5)

                try:
                    title_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[3]/div/div[1]/span[1]')
                    title = title_el.text.strip()
                    if title == 'Translate':
                        title = ""
                except Exception as e:
                    print("Không tìm thấy tiêu đề:", e)

                try:
                    account_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[2]/div[1]/div[1]/span[1]/div[1]/span[1]/div[1]/a/span[1]/span[1]')
                    account = account_el.text.strip()
                except Exception as e:
                    print("Không tìm thấy account:", e)

            except Exception as e:
                print(f"Lỗi xử lý: {e}")

            finally:
                driver.quit()

    return render_template_string(HTML_TEMPLATE, title=title, account=account, fb_video_url=fb_video_url)

if __name__ == '__main__':
    app.run(debug=True)
