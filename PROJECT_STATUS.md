# Nhật Ký Dự Án (Project AI Diary)

_Tài liệu này được tạo ra dành cho các Agent AI tiếp quản dự án. Giúp nắm bắt nhanh tình trạng hệ thống, các luồng tiến trình đã hoàn thiện, và các lỗi (gotchas) đã từng gặp phải để tránh lặp lại (tiết kiệm token/context window)._

## 1. Tóm tắt dự án (Project Overview)
Dự án là một hệ thống Scraper đa nền tảng (Facebook, Instagram, Shopee, Threads, X...) làm nhiệm vụ cào và trích xuất dứ liệu media (hình ảnh, video bài viết, comment, rating).
Hệ thống sử dụng automation browser kết hợp cookie session tĩnh nhằm bypass các cơ chế chống bot và login wall.

## 2. Trạng thái các luồng Scraper (Scraper Status)
*   **Facebook (Posts/Reels):** 
    *   Đang hoạt động ổn. Đã phải tối ưu hóa logic lọc bài post bằng **bounding-box filtering** để loại bỏ các ảnh rác, icon, emoji, UI assets nhỏ lẫn lộn.
    *   Đã sửa lỗi không lấy được link từ tính năng Reel do cơ chế render thay đổi.
    *   \*(Cập nhật)\* Đã bỏ bắt ảnh tự động qua Network (loại trừ `fbcdn`) vì nó thu nhầm quá nhiều sticker/thumbnail gợi ý bất chấp kích thước DOM.
*   **Instagram:** 
    *   Hỗ trợ tốt trích xuất ảnh dạng carousel/album. Quá trình xử lý đã bổ sung module tính toán toạ độ (geometric) để không bốc nhầm video nền hay thumbnail dư thừa ở phần suggested posts.
*   **Shopee (Product Ratings):** 
    *   Đã chuyển sang chạy bằng **Desktop PC Browser** (trước kia dùng mobile emulate nhưng hay bị lỗi layout mảng đánh giá sản phẩm). 
    *   Đã load thành công PC cookies để vượt qua popup/chặn IP. Mục tiêu nhắm đúng vùng "ĐÁNH GIÁ SẢN PHẨM" lấy ảnh và video từ user review.
    *   \*(Cập nhật)\* Nâng cấp lấy data lên tới **50 trang đánh giá**. Fix các classes DOM bị Shopee thay đổi, dùng SVG Icon Button Selector cho việc chuyển trang Next.
    *   \*(Cập nhật)\* Đã tẩy hậu tố thẻ `_tn` (Thumbnail 320px) trong các link hình review của Shopee để chỉ lấy bản ảnh chuẩn nét trọn vẹn.
    *   \*(Cập nhật)\* Siết chặt bộ lọc: Loại bỏ các ảnh phân loại sản phẩm (variant thumbnails - thường bung ra cỡ 640px khi gỡ `_tn`) và ảnh bìa video (video-cover) bằng cách chỉ dò thẻ `img` nằm trong khối `rating-media`.
    *   \*(Cập nhật QUAN TRỌNG)\* Shopee hiện tại render ảnh rating bằng `<div style="background-image">` (tính năng lazy-load) thay vì thẻ `<img>`. Đã đổi thuật toán dò quét cả `div` lẩn `img`, kết hợp **chạy vòng lặp Scroll (cuộn)** sau mỗi lần bấm trang Next để Shopee nạp real URL cho ảnh (xoá bỏ data base64 trắng).
*   **Threads & X:** Tích hợp ổn định qua endpoint API trích xuất chung (`/api/extract`). Logic platform detection cho các URL này đã hoạt động chính xác.

## 3. Hệ thống & Backend (Backend Updates)
*   **Cookie Management (Endpoint `/import`):** Hệ thống có giao diện import cookie riêng cho phép update nhanh `x.json`, `insta.json`, `fb.json`. Backend lấy data đè vào file trên máy chủ mà không hiển thị nội dung trực tiếp ra browser (bảo mật token).
*   **Bắt Lỗi (Error Handling):** Đã sửa một lỗi nghiêm trọng: `Internal Server Error - Unexpected token 'I'`. Nguyên nhân do parse lỗi các file JSON cookies đọc từ môi trường Linux Production. Hiện tại đã có catch error an toàn hơn và trả msg về Frontend dể debug.

## 4. Các lỗi kinh điển đã khắc phục - Cần đặc biệt chú ý (Known Issues & Gotchas)
1.  **Dễ lấy nhầm "Rác" (Extraneous Content):** Do DOM của FB và IG lồng ghép rất nhiều thẻ `<img>` ẩn hoặc dùng làm icon, việc chỉ query thẻ `<img>` sẽ gặp lỗi rác. Bắt buộc phải check size/bounding box.
2.  **Anti-Bot & Emulation chặn:** Shopee ngầm phát hiện các header mobile ảo, việc dùng auth cookie PC và giao diện máy tính tỏ ra bền bỉ và ít rủi ro hơn.
3.  **Parsers / JSON Data:** Đừng bao giờ trust input hay format cookie mà không gài try-catch, file thường thi thoảng lỗi định dạng text gây sập server.
4.  **Cập nhật DOM của Shopee:** Shopee thường xuyên đổi mới cấu trúc Component DOM. Đừng phụ thuộc vào 1 class cứng ngắc mà hãy dùng Multiple Selectors (VD: `.product-ratings, div[data-sqe='rating']`).
5.  **Ảnh vỡ/nhòe:** Thường do link chứa params báo đó là Thumbnail. VD Shopee là `_tn`, trên Twitter là size `name=...`. Cần bóc/truy vết url để làm sạch param lấy ảnh gốc.

## 5. Hướng Dẫn cho Các Agent AI Mới (Agent Instructions)
*   Tránh tìm kiếm hay cào lại thông tin cũ nếu không cần thiết.
*   Trước khi sửa scraper cho một trang bị hỏng, khuyên bạn nên yêu cầu user in ra snapshot của phần mã DOM bị lỗi (vì UI MXH thay đổi hàng ngày).
*   Khi cần log hãy log ra terminal nhưng **KHÔNG BAO GIỜ log token cookie** đầy đủ lên màn hình vì lý do bảo mật.
*   **Dọn dẹp tệp tin tạm thờI:** Rất hay sinh ra các tệp tin script python để test, screenshot `*.png` hay `html` dump. Hãy LUÔN xóa sạch các tệp rác này trước khi hoàn thành một phiên sửa lỗi.
*   \*(Cập nhật 12/04)\* Đã dọn dẹp toàn bộ file rác (`debug.png`, `test_shopee.py`, `tmp_res.json`, `__pycache__`) để repo sạch sẽ.
