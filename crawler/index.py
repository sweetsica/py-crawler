# import os

# orbita_path = r"F:\AAA-Sweetsica\python_project\second_website\crawler\orbita-browser\ob.exe"
# chromedriver_path = r"F:\AAA-Sweetsica\python_project\second_website\crawler\chromedriver.exe"

# print("[Orbita tồn tại?]", os.path.isfile(orbita_path))
# print("[ChromeDriver tồn tại?]", os.path.isfile(chromedriver_path))
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

orbita_path = r"F:\AAA-Sweetsica\python_project\second_website\crawler\orbita-browser\ob.exe"
chromedriver_path = r"F:\AAA-Sweetsica\python_project\second_website\crawler\chromedriver.exe"

assert os.path.exists(orbita_path), "ob.exe không tồn tại"
assert os.path.exists(chromedriver_path), "chromedriver.exe không tồn tại"

options = Options()
options.binary_location = orbita_path

service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=options)

driver.get("https://whoer.net")

try:
    print("🚀 Trình duyệt Orbita đang mở. Nhấn Ctrl + C để thoát...")
    while True:
        pass
except KeyboardInterrupt:
    print("\n⛔ Script bị dừng. Đóng trình duyệt...")
    driver.quit()
