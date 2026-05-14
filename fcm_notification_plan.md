# Kế hoạch Triển khai Thông báo Push (FCM)

Tài liệu này mô tả các bước để tích hợp Firebase Cloud Messaging (FCM) vào hệ thống Bill Split nhằm gửi thông báo trực tiếp đến điện thoại người dùng.

## 1. Yêu cầu chuẩn bị (Firebase Console)
- Tạo một dự án trên [Firebase Console](https://console.firebase.google.com/).
- Tải file cấu hình quản trị: `serviceAccountKey.json` (Firebase Settings -> Service Accounts -> Generate new private key).
- Kích hoạt tính năng Cloud Messaging.

## 2. Các bước thực hiện Backend (FastAPI)

### Bước 2.1: Cấu hình môi trường
- Cài đặt thư viện: `pip install firebase-admin`.
- Thêm biến môi trường vào `.env`:
    - `FIREBASE_CREDENTIALS_PATH`: Đường dẫn đến file JSON của Firebase.

### Bước 2.2: Cập nhật Database (Models)
- Thêm bảng `user_fcm_tokens` để lưu trữ Token của người dùng.
    - Một người dùng có thể đăng nhập trên nhiều thiết bị, nên cần quan hệ 1-N (One User - Many Tokens).
    - Các trường: `id`, `user_id`, `fcm_token`, `device_type` (ios/android), `created_at`.

### Bước 2.3: Xây dựng API quản lý Token
- `POST /api/v1/users/me/fcm-token`: FE gọi API này ngay sau khi lấy được Token từ Firebase trên điện thoại.
- `DELETE /api/v1/users/me/fcm-token/{token}`: Xóa Token khi người dùng đăng xuất.

### Bước 2.4: Xây dựng Notification Service
- Tạo file `app/services/fcm.py` sử dụng `firebase-admin` để gửi thông báo.
- Hàm chính: `send_push_notification(user_id, title, body, data_payload)`.

### Bước 2.5: Tích hợp vào Logic hiện có
- Cập nhật hàm `create_notification` trong `crud.py`.
- Ngoài việc lưu thông báo vào database để xem trong app, hệ thống sẽ đồng thời gọi `fcm_service` để đẩy thông báo ra ngoài màn hình khóa điện thoại.

## 3. Yêu cầu đối với Mobile Frontend (FE)
1. **Cấu hình SDK**: Tích hợp Firebase SDK vào dự án React Native/Flutter.
2. **Lấy Token**: Khi người dùng đăng nhập thành công, app cần lấy FCM Token.
3. **Đăng ký Token**: Gọi API Backend để lưu Token kèm theo `user_id`.
4. **Xử lý Foreground/Background**: Hiển thị Alert nếu người dùng đang dùng app, hoặc Notification Tray nếu app đang tắt.

## 4. Các trường hợp sẽ nhận thông báo Push
- [x] Có người thêm bạn vào nhóm mới.
- [x] Có người thêm khoản chi mới trong nhóm của bạn.
- [x] Có người xác nhận đã trả nợ cho bạn.
- [x] Có người nhắc nợ (tính năng sắp tới).

---
**Đánh giá**: Sau khi hoàn thành, ứng dụng sẽ có trải nghiệm như một ứng dụng tài chính chuyên nghiệp (momo, banking), giúp người dùng không bỏ lỡ bất kỳ giao dịch nào.
