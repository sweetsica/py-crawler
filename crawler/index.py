from flask import Flask, request, render_template
from seleniumwire import webdriver
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import time

app = Flask(__name__)

def remove_bytestart_and_byteend(url):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params.pop('bytestart', None)
    query_params.pop('byteend', None)
    new_query = urlencode(query_params, doseq=True)
    new_url = parsed_url._replace(query=new_query)
    return urlunparse(new_url)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []

    if request.method == 'POST':
        video_url = request.form['video_url']

        # Cấu hình Selenium
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--headless")  # Chạy ngầm không bật trình duyệt

        driver = webdriver.Chrome(options=options)
        driver.get(video_url)
        time.sleep(10)

        for request_ in driver.requests:
            if request_.response:
                content_type = request_.response.headers.get('content-type', '')
                content_length = request_.response.headers.get('content-length', '0')
                try:
                    content_length_int = int(content_length)
                except ValueError:
                    continue

                if 'video/mp4' in content_type and content_length_int > 10000:
                    clean_url = remove_bytestart_and_byteend(request_.url)
                    results.append({
                        'url': clean_url,
                        'status': request_.response.status_code,
                        'content_type': content_type,
                        'content_length': content_length
                    })

        driver.quit()

    return render_template('index.html', results=results)

if __name__ == '__main__':
    app.run(debug=True)
