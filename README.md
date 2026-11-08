# XAUDesk – cập nhật phân tích tin VNWallstreet (chỉ mã nguồn)

Bản này dựa trên `news_monitor.py` của gói XAUDesk-GitHub-Cloud-Ready trước đó, **không phải bản đồng bộ đã kiểm tra với HEAD của GitHub**. Không cần thay bộ cài MT5.

## Tương thích
Giữ nguyên giao diện API `MONITOR.get(force=False)` và dữ liệu `items`, `last_checked`, `last_success`, `telegram_status`, `website_status`, `interval_seconds`. Bổ sung trường `source`, `relevance`, `needs_confirmation` cho từng bài. Lọc trùng bài theo ID. Phân tích theo quy tắc, không tiêu hao AI token.

## Đưa lên GitHub
1. Mở repo `sunnynguyen196/xaudesk-forxbusiness`, xem file `news_monitor.py` có ở thư mục gốc hay không.
2. Sao lưu file hiện tại. Nếu phiên bản repo vẫn tương thích với `cloud_server.py` dùng `from news_monitor import MONITOR`, thay **chỉ** `news_monitor.py` bằng bản này rồi Commit changes. Không tải các file MT5, .venv, .env hoặc token lên repo.
3. Nếu dashboard chạy trên máy Windows và không có `git pull`/auto-update, GitHub commit **không tự đổi code localhost**. Cần đồng bộ mã một lần hoặc có sẵn cơ chế update. Không cần cài lại bộ MT5.
4. Chạy `python test_news.py` (kiểm thử offline). Sau đó chạy dashboard và mở tab 04.

## Giới hạn
- Trang công khai `https://t.me/s/vnwallstreet` có thể thay đổi HTML hoặc giới hạn truy cập. Tự kiểm tra 120 giây **khi server nhận yêu cầu** tới `/api/news`, không phải tiến trình 24/7 nếu dashboard không được truy cập.
- Website `https://vnwallstreet.com/#/home` dùng ứng dụng động; chưa xác minh feed/API công khai nên **không thu thập bài trực tiếp từ website**. Chỉ hiển thị liên kết và trạng thái nguồn, không bịa bài.
- Tin Telegram là nguồn thứ cấp, phải đối chiếu nguồn chính thức và biến động XAUUSD trước khi kết luận.
