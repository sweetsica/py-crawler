from flask import Flask, request, render_template_string
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

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

    {% if account %}
        <h3>Tiêu đề:</h3>
        <div>{{ account }}</div>
    {% endif %}
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def index():
    # title = ""
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

            # try:
            #     title_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[3]/div/div[1]/span[1]')
            #     title_raw = title_el.text.strip()
            #     title = title_raw.replace("Translate", "").strip()
            # except Exception as e:
            #     print("Không tìm thấy tiêu đề:", e)

            try:
                account_el = driver.find_element(By.XPATH, '(//div[@data-pressable-container])[1]/div[1]/div[2]/div[1]/div[1]/span[1]/div[1]/span[1]/div[1]/a/span[1]/span[1]')
                account = account_el.text.strip()
            except Exception as e:
                print("Không tìm thấy tài khoản:", e)
                account = ""


        except Exception as e:
            print(f"Lỗi xử lý: {e}")

        finally:
            driver.quit()

    return render_template_string(HTML_TEMPLATE, account=account)

if __name__ == '__main__':
    app.run(debug=True)
