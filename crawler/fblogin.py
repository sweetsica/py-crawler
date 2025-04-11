from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from time import sleep
from selenium.webdriver.common.by import By


service = Service(r"F:\AAA-Sweetsica\python_project\second_website\crawler\chromedriver.exe")

browser = webdriver.Chrome(service=service)
# browser.get("https://www.facebook.com/")
browser.get("https://fsave.net/vi")

txtUser = browser.find_element("xpath", '//*[@id="postUrl"]')
txtUser.send_keys("https://www.facebook.com/reel/1884776129003551")

confirm = browser.find_element(By.ID, "loadVideos")
confirm.click()

# 1. Tìm phần tử media-body
try:
    result = browser.find_element(By.CLASS_NAME, 'resolution-badge')

    # 2. Tìm tất cả các thẻ con có class 'resolution-badge'
    badges = result.find_elements(By.CLASS_NAME, 'resolution-badge')

    # 3. Duyệt từng badge, kiểm tra nội dung
    for badge in badges:
        if '1080' in badge.text:
            print("Tìm thấy badge 1080p:", badge.text)
            # 👉 Thực hiện hành động gì đó tại đây, ví dụ:
            # badge.click()
            break
    else:
        print("Không tìm thấy badge 1080p")
        
except Exception as e:
    print("Không tìm thấy phần tử media-body:", e)

# sleep(15)
input("Nhấn Enter để tiếp tục...")


browser.close()