# Báo cáo Triển khai Chức năng Thông báo (Notification System)

Tôi đã hoàn thành việc triển khai hệ thống thông báo dựa trên bản đề xuất. Dưới đây là chi tiết các thay đổi:

## 1. Database & Models
- Đã thêm bảng `notifications` vào Database.
- Định nghĩa các loại thông báo (`NotificationType`):
    - `EXPENSE_CREATED`: Khi có khoản chi mới.
    - `MEMBER_ADDED`: Khi có thành viên mới gia nhập nhóm.
    - `SETTLEMENT_RECORDED`: Khi có giao dịch thanh toán nợ.

## 2. API Endpoints
Hệ thống cung cấp các API mới tại `/api/v1/notifications/`:
- `GET /`: Lấy danh sách thông báo của người dùng hiện tại (hỗ trợ phân trang `skip`, `limit`).
- `GET /unread-count`: Lấy số lượng thông báo chưa đọc để hiển thị trên giao diện.
- `PATCH /{id}/read`: Đánh dấu một thông báo là đã đọc.
- `POST /mark-all-read`: Đánh dấu tất cả thông báo của người dùng là đã đọc.

## 3. Logic Tự động (Triggers)
Thông báo sẽ được tự động tạo trong các trường hợp sau:
- **Tạo khoản chi**: Gửi thông báo đến tất cả thành viên trong nhóm (trừ người tạo). Nội dung bao gồm tên người chi và số tiền.
- **Thanh toán nợ**: Gửi thông báo đến người nhận tiền khi người trả tiền thực hiện ghi nhận giao dịch.
- **Gia nhập nhóm**: 
    - Gửi thông báo cho người được admin thêm vào nhóm bằng Email.
    - Gửi thông báo chào mừng cho người tự tham gia bằng mã mời (Invite Code).

## 4. Migration
- Đã tạo và áp dụng file migrate: `98e2cc94f7d3_add_notifications_table.py`.
- Bảng `notifications` đã sẵn sàng sử dụng trong Postgres.

## 5. Hướng dẫn cho Frontend
- Sử dụng `reference_id` trả về trong mỗi thông báo để điều hướng người dùng đến đúng trang chi tiết của Expense hoặc Settlement.
- Nên gọi API `/unread-count` định kỳ hoặc sau khi thực hiện các hành động quan trọng để cập nhật badge thông báo.
