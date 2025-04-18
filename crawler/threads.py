from flask import Flask, request, render_template_string, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from datetime import datetime
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
    <h2>Nhập link bài viết Threads:</h2>
    <form method="POST">
        <input name="url" style="width: 400px;" required>
        <input type="submit" value="Lấy tiêu đề">
    </form>

    {% if title %}
        <h3>Tiêu đề:</h3>
        <div>{{ title }}</div>
    {% endif %}
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def index():
    title = ""
    error = ""

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            url = data.get("url", "")
        else:
            url = request.form.get("url", "")

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
                if "Translate" in title:
                    title = title.replace("Translate", "").strip()
            except Exception as e:
                print("Không tìm thấy tiêu đề:", e)

        except Exception as e:
            print(f"Lỗi xử lý: {e}")

        finally:
            driver.quit()

    return render_template_string(HTML_TEMPLATE, title=title)

@app.route("/api/scrape", methods=["POST"])
def api_scrape():
    if not request.is_json:
        return jsonify({
            "status": 400,
            "message": "Invalid JSON request",
            "created_at": datetime.utcnow().isoformat()
        }), 400

    data = request.get_json()
    url = data.get("url", "")
    if not url:
        return jsonify({
            "status": 400,
            "message": "Missing URL",
            "created_at": datetime.utcnow().isoformat()
        }), 400

    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)

        driver.get(url)
        time.sleep(5)

        results = {}

        if "facebook.com" in url:
            html = driver.page_source
            match = re.search(r'"browser_native_hd_url":"(https:\\/\\/[^\"]+\.mp4.*?)"', html)
            if match:
                results["1"] = match.group(1).replace('\\/', '/')
            else:
                img_elements = driver.find_elements(
                    By.XPATH,
                    '//img[@referrerpolicy="origin-when-cross-origin" and not(@height) and not(@width)]'
                )
                for idx, img in enumerate(img_elements):
                    src = img.get_attribute("src")
                    if src:
                        results[str(idx + 1)] = src

        elif "threads.net" in url:
            try:
                title_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[3]/div/div[1]/span[1]')
                title = title_el.text.strip()
                if "Translate" in title:
                    title = title.replace("Translate", "").strip()
                results["1"] = title
            except Exception:
                pass

        driver.quit()

        if not results:
            return jsonify({
                "status": 404,
                "message": "No data found",
                "data": {},
                "created_at": datetime.utcnow().isoformat()
            }), 404

        return jsonify({
            "status": 200,
            "data": results,
            "created_at": datetime.utcnow().isoformat()
        })

    except Exception as e:
        return jsonify({
            "status": 400,
            "message": str(e),
            "created_at": datetime.utcnow().isoformat()
        }), 400

if __name__ == '__main__':
    app.run(debug=True)
