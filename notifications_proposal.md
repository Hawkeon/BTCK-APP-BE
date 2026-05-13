# Đề xuất Chức năng Thông báo (Notification System)

Hệ thống thông báo giúp người dùng cập nhật kịp thời các hoạt động trong nhóm chi tiêu (ví dụ: khi có người thêm khoản chi mới, khi được mời vào nhóm, hoặc khi nợ đã được thanh toán).

## 1. Cấu trúc Bảng dữ liệu (Database Schema)

Chúng ta cần thêm bảng `notifications` để lưu trữ lịch sử thông báo.

### Bảng `notifications`
| Trường | Kiểu dữ liệu | Mô tả |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Định danh duy nhất cho thông báo. |
| `recipient_id` | UUID (FK) | Người nhận thông báo (trỏ đến `users.id`). |
| `sender_id` | UUID (FK, Nullable) | Người gây ra thông báo (ví dụ: người tạo khoản chi). |
| `event_id` | UUID (FK, Nullable) | Sự kiện liên quan đến thông báo. |
| `title` | String | Tiêu đề ngắn gọn (ví dụ: "Khoản chi mới"). |
| `content` | Text | Nội dung chi tiết (ví dụ: "A đã thêm khoản chi 50k"). |
| `type` | Enum/String | Loại thông báo: `EXPENSE_CREATED`, `MEMBER_ADDED`, `SETTLEMENT_RECORDED`. |
| `reference_id` | UUID (Nullable) | ID của đối tượng gây ra thông báo (Dùng để dẫn người dùng đến đúng trang chi tiết của Expense hoặc Settlement đó). |
| `is_read` | Boolean | Trạng thái đã đọc (mặc định: `false`). |
| `created_at` | DateTime | Thời gian gửi thông báo. |

## 2. Các chức năng chính (Features)

1.  **Lấy danh sách thông báo**: Người dùng có thể xem danh sách thông báo của mình (phân trang).
2.  **Đánh dấu đã đọc**: Chuyển trạng thái `is_read` thành `true` cho từng thông báo hoặc "Đọc tất cả".
3.  **Số lượng chưa đọc**: API trả về số lượng thông báo mới để hiển thị icon (badge) trên giao diện.
4.  **Tự động xóa**: Tự động xóa thông báo cũ sau 30 ngày để làm nhẹ database.

## 3. Các loại thông báo và Luồng hoạt động (Workflow)

### A. Luồng tạo khoản chi mới (`EXPENSE_CREATED`)
1.  **Trigger**: Thành viên A tạo một khoản chi trong nhóm X.
2.  **Xử lý Backend**: Hệ thống lưu khoản chi vào bảng `expenses`.
3.  **Tạo thông báo**: Hệ thống tìm tất cả thành viên trong nhóm X (trừ thành viên A) và tạo các bản ghi vào bảng `notifications`. `reference_id` sẽ lưu ID của Expense vừa tạo.
4.  **Giao diện**: Khi các thành viên khác nhấn vào thông báo, ứng dụng sẽ dùng `reference_id` để dẫn họ đến xem chi tiết khoản chi đó.

### B. Luồng mời vào nhóm (`MEMBER_ADDED`)
1.  **Trigger**: Người dùng dùng mã mời hoặc được admin thêm vào nhóm.
2.  **Xử lý Backend**: Lưu bản ghi vào `event_members`.
3.  **Tạo thông báo**: Hệ thống gửi thông báo cho người vừa tham gia: "Chào mừng bạn đến với nhóm X". `reference_id` ở đây có thể lưu ID của Event.

### C. Luồng ghi nhận thanh toán (`SETTLEMENT_RECORDED`)
1.  **Trigger**: Thành viên A xác nhận đã trả tiền cho thành viên B.
2.  **Xử lý Backend**: Lưu bản ghi vào bảng `settlements`.
3.  **Tạo thông báo**: Gửi thông báo cho thành viên B: "A đã gửi cho bạn 100k". `reference_id` lưu ID của Settlement.

## 4. Công nghệ đề xuất tích hợp thêm

Để thông báo mượt mà hơn (thời gian thực), có thể nâng cấp thêm:
*   **WebSockets (FastAPI)**: Đẩy thông báo ngay lập tức lên màn hình người dùng mà không cần họ phải load lại trang.
*   **Firebase Cloud Messaging (FCM)**: Nếu sau này bạn làm App Mobile để đẩy thông báo lên điện thoại (Push Notification).
