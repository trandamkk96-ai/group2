# Quản Lý Điểm Nhóm — bản Web (chạy trên mọi thiết bị)

App Streamlit gốc chỉ chạy trên 1 máy (vì lưu điểm vào file JSON trên ổ đĩa).
Bản này được sửa để:

1. **Chạy trên web** — deploy 1 lần, có 1 link, ai cũng bấm vào là dùng được
   trên điện thoại, laptop, iPad... không phân biệt hệ điều hành, không cần
   cài đặt gì.
2. **Lưu điểm vào database (Supabase/Postgres)** thay vì file JSON — dữ liệu
   không bao giờ mất dù app khởi động lại hay bro cập nhật code.

Toàn bộ đều **miễn phí**. Làm theo đúng thứ tự các bước dưới đây (khoảng
15-20 phút cho lần đầu, chỉ cần làm 1 lần).

---

## Bước 1 — Tạo database miễn phí trên Supabase

1. Vào https://supabase.com → **Start your project** → đăng nhập bằng GitHub.
2. **New project** → đặt tên tuỳ ý → đặt **Database Password** (nhớ lưu lại
   mật khẩu này, sẽ dùng ở Bước 4) → chọn Region gần Việt Nam (Singapore) →
   **Create new project**. Đợi khoảng 1-2 phút để Supabase khởi tạo.
3. Vào mục **SQL Editor** (biểu tượng bên trái) → **New query** → mở file
   `sql/schema.sql` trong bộ này, copy toàn bộ nội dung, dán vào → bấm **Run**.
   (Bước này thật ra không bắt buộc vì app tự tạo bảng khi chạy lần đầu, nhưng
   chạy trước cho chắc cũng không sao.)
4. Vào **Project Settings** (biểu tượng bánh răng) → **Database** →
   phần **Connection string** → chọn tab **URI** → copy chuỗi kết nối, dạng:
   `postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres`
   Thay `[YOUR-PASSWORD]` bằng mật khẩu database đã đặt ở bước 2.

Giữ lại chuỗi này, sẽ dùng ở Bước 4.

---

## Bước 2 — Đưa code lên GitHub

1. Nếu chưa có tài khoản GitHub: tạo miễn phí tại https://github.com.
2. Tạo repository mới, đặt **Private** (không cho người lạ xem code có chứa
   thông tin nhạy cảm), ví dụ tên `quan-ly-diem-nhom`.
3. Upload toàn bộ các file trong bộ này vào repo đó:
   - `app.py`
   - `requirements.txt`
   - `.gitignore`
   - `sql/schema.sql`
   - (KHÔNG upload file `.streamlit/secrets.toml.example` chứa mật khẩu thật
     nếu bro đã điền số thật vào — nếu chưa điền gì thì upload thoải mái,
     hoặc bỏ qua file này cũng được, không bắt buộc)

   Cách đơn giản nhất nếu không quen dùng git: vào trang repo trên GitHub →
   **Add file → Upload files** → kéo thả các file vào → **Commit changes**.

---

## Bước 3 — Deploy lên Streamlit Community Cloud (miễn phí)

1. Vào https://share.streamlit.io → **Sign in with GitHub** (dùng luôn tài
   khoản GitHub ở Bước 2).
2. Bấm **Create app** → **Deploy a public app from GitHub** (app vẫn deploy
   được dù repo Private, chỉ là không public code).
3. Chọn:
   - Repository: repo bro vừa tạo (`quan-ly-diem-nhom`)
   - Branch: `main`
   - Main file path: `app.py`
4. **TRƯỚC KHI** bấm Deploy, mở **Advanced settings** → mục **Secrets** →
   dán nội dung sau (điền đúng số thật của bro):

   ```
   admin_password = "Ken@100612"

   [connections.supabase_db]
   url = "postgresql+psycopg2://postgres:MAT_KHAU_THAT@db.xxxxxxxxxxxx.supabase.co:5432/postgres"
   ```

   Lưu ý: chuỗi kết nối copy từ Supabase bắt đầu bằng `postgresql://` —
   bro phải đổi thành `postgresql+psycopg2://` (thêm `+psycopg2`) thì mới
   chạy đúng.

5. Bấm **Deploy!**. Đợi khoảng 1-2 phút để Streamlit cài đặt và khởi động app.

Xong! Bro sẽ có 1 link dạng `https://ten-app-cua-ban.streamlit.app`.
Gửi link này cho bất kỳ ai — họ chỉ cần bấm vào, mở trên điện thoại, máy
tính, iPad, Windows, macOS, Linux, Android, iOS... đều chạy được ngay trên
trình duyệt, không cần cài gì cả.

---

## Sau khi đã chạy — dùng và sửa code

- **Sửa code**: sửa `app.py` trong GitHub (hoặc kéo repo về máy sửa rồi
  push lại) → Streamlit Cloud tự động phát hiện và redeploy lại app trong
  vài chục giây. Vì điểm đã lưu ở Supabase (không còn nằm trong app nữa)
  nên **redeploy/sửa code không làm mất dữ liệu điểm**.
- **Đổi mật khẩu Admin**: vào app trên share.streamlit.io → **Settings** →
  **Secrets** → sửa dòng `admin_password` → Save (app tự khởi động lại).
- **Xem/sửa dữ liệu trực tiếp**: vào Supabase → **Table Editor** → bảng
  `members` (điểm hiện tại từng người) và `history` (lịch sử từng lần
  cộng/trừ) — có thể sửa tay tại đây nếu cần.

## Chạy thử ở máy mình trước khi deploy (không bắt buộc)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# rồi sửa secrets.toml điền connection string + mật khẩu thật
streamlit run app.py
```
