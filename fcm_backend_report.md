# Báo cáo Triển khai FCM (Backend)

Hệ thống thông báo đẩy (Push Notification) đã được tích hợp hoàn chỉnh vào Backend.

## 1. Thay đổi Database
- Đã tạo bảng `user_fcm_tokens`:
    - Lưu trữ danh sách mã Token của từng thiết bị người dùng.
    - Hỗ trợ một người dùng nhận thông báo trên nhiều thiết bị cùng lúc.

## 2. Dịch vụ FCM Service (`app/services/fcm.py`)
- Sử dụng thư viện `firebase-admin` chính thức từ Google.
- Cấu hình **High Priority** và **Default Sound** cho thông báo.
- Hỗ trợ gom nhóm thông báo (tagging) trên Android và Badge trên iOS.

## 3. Các API mới
- `POST /api/v1/users/me/fcm-token`: Đăng ký Token mới từ điện thoại.
- `DELETE /api/v1/users/me/fcm-token/{token}`: Xóa Token khi người dùng đăng xuất.

## 4. Tích hợp tự động
- Đã nhúng logic gửi Push vào hàm `create_notification` trong `crud.py`. 
- **Quy trình**: Khi có bất kỳ thông báo nào được tạo ra trong hệ thống -> Backend tự tìm Token của người nhận -> Gửi Push đến điện thoại ngay lập tức.

---
**Trạng thái**: Sẵn sàng kết nối.
