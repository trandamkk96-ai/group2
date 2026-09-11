import streamlit as st
from sqlalchemy import text

# ============================================================
#  QUẢN LÝ ĐIỂM NHÓM — phiên bản chạy trên web (mọi thiết bị,
#  mọi hệ điều hành, chỉ cần trình duyệt), dữ liệu lưu bền vững
#  trên database Postgres (Supabase) thay vì file JSON.
# ============================================================

st.set_page_config(page_title="Quản Lý Điểm Nhóm", layout="wide")

# --- Kết nối database ---------------------------------------------------
# Cấu hình kết nối nằm trong Streamlit Secrets (mục [connections.supabase_db]),
# KHÔNG được ghi cứng trong code. Xem secrets.toml.example để biết cách điền.
conn = st.connection("supabase_db", type="sql")


def init_db():
    """Tạo bảng nếu chưa có (chạy an toàn nhiều lần)."""
    with conn.session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS members (
                name TEXT PRIMARY KEY,
                diem INTEGER NOT NULL DEFAULT 0
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                ten TEXT NOT NULL REFERENCES members(name) ON DELETE CASCADE,
                ngay TIMESTAMP NOT NULL DEFAULT now(),
                so_diem INTEGER NOT NULL,
                ly_do TEXT,
                xac_nhan TEXT
            )
        """))
        s.commit()


init_db()


# --- Truy vấn dữ liệu -----------------------------------------------------
def load_members():
    return conn.query("SELECT name, diem FROM members ORDER BY name", ttl=0)


def load_history(name):
    return conn.query(
        """
        SELECT ngay AS "Ngày", so_diem AS "Điểm", ly_do AS "Lý do", xac_nhan AS "Xác nhận"
        FROM history WHERE ten = :ten ORDER BY ngay DESC
        """,
        params={"ten": name},
        ttl=0,
    )


def add_member(name):
    with conn.session as s:
        s.execute(
            text("INSERT INTO members (name, diem) VALUES (:name, 0) ON CONFLICT DO NOTHING"),
            {"name": name},
        )
        s.commit()


def update_score(name, so_diem, ly_do, nguoi_ky):
    with conn.session as s:
        s.execute(
            text("UPDATE members SET diem = diem + :d WHERE name = :name"),
            {"d": so_diem, "name": name},
        )
        s.execute(
            text("""
                INSERT INTO history (ten, so_diem, ly_do, xac_nhan)
                VALUES (:name, :d, :ly_do, :ky)
            """),
            {"name": name, "d": so_diem, "ly_do": ly_do, "ky": nguoi_ky},
        )
        s.commit()


def reset_all_scores(nguoi_ky):
    """Đưa điểm hiện tại của mọi người về 0 khi sang tuần mới.
    Vẫn ghi 1 dòng lịch sử cho mỗi người để biết vì sao điểm đổi,
    lịch sử các lần cộng/trừ trước đó không bị xoá."""
    members = load_members()
    with conn.session as s:
        for _, row in members.iterrows():
            ten = row["name"]
            diem_hien_tai = int(row["diem"])
            if diem_hien_tai != 0:
                s.execute(
                    text("UPDATE members SET diem = 0 WHERE name = :name"),
                    {"name": ten},
                )
                s.execute(
                    text("""
                        INSERT INTO history (ten, so_diem, ly_do, xac_nhan)
                        VALUES (:name, :d, :ly_do, :ky)
                    """),
                    {"name": ten, "d": -diem_hien_tai, "ly_do": "Reset điểm đầu tuần mới", "ky": nguoi_ky},
                )
        s.commit()


# --- THANH BÊN (SIDEBAR): ĐĂNG NHẬP & CÔNG CỤ ADMIN ---
st.sidebar.title("🔒 Quyền Admin")
password = st.sidebar.text_input("Nhập mật khẩu Admin:", type="password")

ADMIN_PASSWORD = st.secrets.get("admin_password", "")
is_admin = bool(password) and password == ADMIN_PASSWORD

if is_admin:
    st.sidebar.success("Khu vực dành riêng cho bạn!")
    st.sidebar.markdown("---")
    st.sidebar.subheader("➕ Thêm thành viên")
    ten_moi = st.sidebar.text_input("Tên thành viên mới:")
    if st.sidebar.button("Thêm thành viên"):
        ten_moi = ten_moi.strip()
        existing = load_members()["name"].tolist()
        if ten_moi and ten_moi not in existing:
            add_member(ten_moi)
            st.sidebar.success(f"Đã thêm {ten_moi}")
            st.rerun()
        elif ten_moi in existing:
            st.sidebar.error("Tên này đã tồn tại!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Reset điểm tuần mới")
    st.sidebar.caption(
        "Đưa điểm hiện tại của TẤT CẢ mọi người về 0 để bắt đầu tuần mới. "
        "Lịch sử các lần cộng/trừ điểm cũ vẫn được giữ lại, không bị mất."
    )
    xac_nhan_reset = st.sidebar.checkbox("Tôi chắc chắn muốn reset điểm")
    if st.sidebar.button("🔄 Reset điểm về 0", use_container_width=True, disabled=not xac_nhan_reset):
        reset_all_scores(nguoi_ky="Admin")
        st.sidebar.success("Đã reset điểm về 0 cho tuần mới!")
        st.rerun()
else:
    if password:
        st.sidebar.error("Mật khẩu chưa đúng")
    else:
        st.sidebar.info("Bạn đang ở chế độ Xem. Nhập mật khẩu để chỉnh sửa điểm.")

# --- TRANG CHÍNH ---
st.title("📊 Quản Lý Điểm Nhóm")

members_df = load_members()

# Form cộng / trừ điểm (chỉ hiển thị nếu đúng mật khẩu Admin)
if is_admin:
    with st.expander("📝 Form Cộng / Trừ Điểm", expanded=True):
        if members_df.empty:
            st.warning("Chưa có thành viên nào. Hãy thêm ở thanh bên trái!")
        else:
            col1, col2, col3, col4 = st.columns([2, 1, 3, 2])
            with col1:
                ten_duoc_chon = st.selectbox("Chọn thành viên:", members_df["name"].tolist())
            with col2:
                so_diem = st.number_input("Điểm (+/-):", value=0, step=1)
            with col3:
                ly_do = st.text_input("Lý do / Lỗi vi phạm:")
            with col4:
                nguoi_ky = st.text_input("Người ký tên:", value="Admin")

            if st.button("✅ Cập nhật điểm", use_container_width=True):
                if not ly_do.strip():
                    st.error("Vui lòng nhập lý do!")
                else:
                    update_score(ten_duoc_chon, int(so_diem), ly_do.strip(), nguoi_ky.strip())
                    st.success(f"Đã cập nhật {so_diem:+} điểm cho {ten_duoc_chon}!")
                    st.rerun()

st.markdown("---")

# --- HIỂN THỊ BẢNG ĐIỂM (Tất cả mọi người đều xem được) ---
st.subheader("📋 Bảng Tổng Hợp & Lịch Sử")

if members_df.empty:
    st.info("Chưa có dữ liệu thành viên.")
else:
    cols = st.columns(2)
    for idx, row in members_df.reset_index(drop=True).iterrows():
        ten = row["name"]
        diem = row["diem"]
        with cols[idx % 2]:
            with st.container(border=True):
                st.markdown(f"### **{ten}**")
                color = "green" if diem >= 0 else "red"
                st.markdown(
                    f"Điểm hiện tại: <h3 style='display:inline; color:{color};'>{diem}</h3>",
                    unsafe_allow_html=True,
                )
                hist_df = load_history(ten)
                if not hist_df.empty:
                    st.dataframe(hist_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("Chưa có lịch sử cộng/trừ điểm.")
