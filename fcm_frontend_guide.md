# Hướng dẫn Tích hợp FCM cho Frontend (Java/Android)

Dành cho người phát triển App Mobile bằng Java.

## Bước 1: Cấu hình Firebase SDK
1. Thêm tệp `google-services.json` vào thư mục `app/`.
2. Thêm dependency vào `build.gradle`:
   ```gradle
   implementation 'com.google.firebase:firebase-messaging:23.x.x'
   ```

## Bước 2: Lấy FCM Token và gửi lên Backend
Ngay sau khi người dùng **đăng nhập thành công**, hãy thực hiện:
```java
FirebaseMessaging.getInstance().getToken()
    .addOnCompleteListener(new OnCompleteListener<String>() {
        @Override
        public void onComplete(@NonNull Task<String> task) {
            if (!task.isSuccessful()) return;
            String token = task.getResult();
            
            // GỌI API BACKEND ĐỂ LƯU TOKEN
            // Endpoint: POST /api/v1/users/me/fcm-token
            // Body: {"fcm_token": token, "device_type": "android"}
        }
    });
```

## Bước 3: Xử lý nhận thông báo
Tạo một class kế thừa `FirebaseMessagingService`:
```java
public class MyFCMService extends FirebaseMessagingService {
    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        // 1. Thông báo hệ thống sẽ tự hiện nếu bạn cấu hình định dạng đúng
        // 2. Cập nhật số ở cái chuông (Badge) bằng cách gọi API:
        //    GET /api/v1/notifications/unread-count
    }
}
```

## Bước 4: Xử lý Đăng xuất (Quan trọng)
Khi người dùng bấm **Logout**, trước khi xóa Access Token cục bộ, hãy gọi API:
- `DELETE /api/v1/users/me/fcm-token/{token}`
- Điều này để đảm bảo người dùng khác dùng điện thoại này sau đó không nhận được thông báo của người cũ.

---
**Dữ liệu gửi kèm (Data Payload)**: Backend luôn gửi kèm `type` và `event_id` trong trường `data` để bạn có thể code logic chuyển màn hình khi người dùng bấm vào thông báo.
