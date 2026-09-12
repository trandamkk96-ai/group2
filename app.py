import io

import pandas as pd
import streamlit as st
from sqlalchemy import text

# ============================================================
#  QUẢN LÝ ĐIỂM NHÓM — phiên bản chạy trên web (mọi thiết bị,
#  mọi hệ điều hành, chỉ cần trình duyệt), dữ liệu lưu bền vững
#  trên database Postgres (Supabase) thay vì file JSON.
# ============================================================

st.set_page_config(page_title="Quản Lý Điểm Nhóm", page_icon="🏆", layout="wide")

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
    return conn.query("SELECT name, diem FROM members ORDER BY diem DESC, name", ttl=0)


def load_history(name):
    return conn.query(
        """
        SELECT ngay AS "Ngày", so_diem AS "Điểm", ly_do AS "Lý do", xac_nhan AS "Xác nhận"
        FROM history WHERE ten = :ten ORDER BY ngay DESC
        """,
        params={"ten": name},
        ttl=0,
    )


def load_all_history():
    return conn.query(
        """
        SELECT ten AS "Thành viên", ngay AS "Ngày", so_diem AS "Điểm",
               ly_do AS "Lý do", xac_nhan AS "Xác nhận"
        FROM history ORDER BY ngay DESC
        """,
        ttl=0,
    )


def to_excel_bytes(members_df, history_df):
    bang_diem = members_df.rename(columns={"name": "Thành viên", "diem": "Điểm hiện tại"})
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        bang_diem.to_excel(writer, index=False, sheet_name="Bang diem")
        history_df.to_excel(writer, index=False, sheet_name="Lich su")
    return buffer.getvalue()


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


def delete_member(name):
    """Xoá 1 thành viên khỏi bảng — lịch sử cộng/trừ của người đó cũng
    tự động bị xoá theo (nhờ ON DELETE CASCADE), không thể hoàn tác."""
    with conn.session as s:
        s.execute(text("DELETE FROM members WHERE name = :name"), {"name": name})
        s.commit()


def reset_all_scores():
    """Đưa điểm hiện tại của mọi người về 0 VÀ xoá sạch lịch sử cộng/trừ
    cũ để bắt đầu tuần mới hoàn toàn sạch sẽ. Không thể hoàn tác."""
    with conn.session as s:
        s.execute(text("UPDATE members SET diem = 0"))
        s.execute(text("DELETE FROM history"))
        s.commit()


# ---------------------------------------------------------------
# CSS — giao diện đẹp hơn
# ---------------------------------------------------------------
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; max-width: 960px; }

    .hero {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 20px;
        padding: 28px 32px;
        margin-bottom: 24px;
        color: white;
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
    }
    .hero-title { font-size: 1.9rem; font-weight: 800; margin: 0; }
    .hero-subtitle { opacity: 0.9; font-size: 0.95rem; margin-top: 4px; }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #eef0f3;
        border-radius: 14px;
        padding: 12px 16px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }

    .rank-card {
        display: flex; align-items: center; gap: 16px;
        background: #ffffff; border: 1px solid #eef0f3; border-radius: 16px;
        padding: 14px 20px; margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .rank-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(16, 24, 40, 0.08); }
    .rank-card.top1 { border: 1px solid #fde68a; background: linear-gradient(90deg,#fffbeb,#ffffff); }
    .rank-card.top2 { border: 1px solid #e5e7eb; background: linear-gradient(90deg,#f9fafb,#ffffff); }
    .rank-card.top3 { border: 1px solid #fed7aa; background: linear-gradient(90deg,#fff7ed,#ffffff); }

    .rank-badge { width: 40px; min-width: 40px; text-align: center; font-size: 1.2rem; font-weight: 800; color: #9ca3af; }
    .rank-badge.medal { font-size: 1.7rem; }

    .avatar {
        width: 42px; height: 42px; min-width: 42px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1rem; color: white;
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
    }

    .member-name { flex: 1; font-size: 1.05rem; font-weight: 600; color: #111827; }

    .score-pill { padding: 6px 16px; border-radius: 999px; font-weight: 800; font-size: 0.95rem; white-space: nowrap; }
    .score-pill.positive { background: #dcfce7; color: #15803d; }
    .score-pill.negative { background: #fee2e2; color: #b91c1c; }
    .score-pill.zero { background: #f1f5f9; color: #475569; }

    div[data-testid="stExpander"] { border: none; border-radius: 14px; overflow: hidden; }
    button[kind="secondary"], button[kind="primary"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#10b981", "#0ea5e9", "#eab308"]


def avatar_color(name):
    return AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]


# ---------------------------------------------------------------
# SIDEBAR — Admin
# ---------------------------------------------------------------
st.sidebar.title("🔒 Quyền Admin")
password = st.sidebar.text_input("Nhập mật khẩu Admin:", type="password")

ADMIN_PASSWORD = st.secrets.get("admin_password", "")
is_admin = bool(password) and password == ADMIN_PASSWORD

if is_admin:
    st.sidebar.success("Khu vực dành riêng cho bạn!")
    st.sidebar.markdown("---")
    st.sidebar.subheader("➕ Thêm thành viên")
    ten_moi = st.sidebar.text_input("Tên thành viên mới:")
    if st.sidebar.button("Thêm thành viên", use_container_width=True):
        ten_moi = ten_moi.strip()
        existing = load_members()["name"].tolist()
        if ten_moi and ten_moi not in existing:
            add_member(ten_moi)
            st.sidebar.success(f"Đã thêm {ten_moi}")
            st.rerun()
        elif ten_moi in existing:
            st.sidebar.error("Tên này đã tồn tại!")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🗑️ Xoá thành viên")
    existing_for_delete = load_members()["name"].tolist()
    if existing_for_delete:
        ten_xoa = st.sidebar.selectbox("Chọn thành viên cần xoá:", existing_for_delete, key="ten_xoa_select")
        st.sidebar.caption("⚠️ Xoá luôn cả lịch sử cộng/trừ điểm của người này. Không thể hoàn tác.")
        xac_nhan_xoa = st.sidebar.checkbox("Tôi chắc chắn muốn xoá thành viên này", key="xac_nhan_xoa_thanh_vien")
        if st.sidebar.button("🗑️ Xoá thành viên", use_container_width=True, disabled=not xac_nhan_xoa):
            delete_member(ten_xoa)
            st.sidebar.success(f"Đã xoá {ten_xoa}!")
            st.rerun()
    else:
        st.sidebar.caption("Chưa có thành viên nào để xoá.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Reset điểm tuần mới")
    st.sidebar.caption(
        "⚠️ Đưa điểm TẤT CẢ mọi người về 0 VÀ XOÁ VĨNH VIỄN toàn bộ lịch sử "
        "cộng/trừ điểm cũ. Không thể hoàn tác, hãy chắc chắn trước khi bấm."
    )
    xac_nhan_reset = st.sidebar.checkbox("Tôi chắc chắn muốn xoá hết và reset điểm")
    if st.sidebar.button("🔄 Reset điểm về 0", use_container_width=True, disabled=not xac_nhan_reset):
        reset_all_scores()
        st.sidebar.success("Đã reset điểm về 0 và xoá sạch lịch sử cũ!")
        st.rerun()
else:
    if password:
        st.sidebar.error("Mật khẩu chưa đúng")
    else:
        st.sidebar.info("Bạn đang ở chế độ Xem. Nhập mật khẩu để chỉnh sửa điểm.")


# ---------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">🏆 Quản Lý Điểm Nhóm</div>
        <div class="hero-subtitle">Bảng xếp hạng điểm — cập nhật trực tiếp, mọi lúc mọi nơi</div>
    </div>
    """,
    unsafe_allow_html=True,
)

members_df = load_members()

if not members_df.empty:
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Số thành viên", len(members_df))
    kpi2.metric("Điểm cao nhất", int(members_df["diem"].max()))
    kpi3.metric("Tổng điểm", int(members_df["diem"].sum()))

    excel_bytes = to_excel_bytes(members_df, load_all_history())
    st.download_button(
        "⬇️ Xuất file Excel",
        data=excel_bytes,
        file_name="diem_nhom.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.write("")


# ---------------------------------------------------------------
# FORM CỘNG / TRỪ ĐIỂM (chỉ Admin)
# ---------------------------------------------------------------
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
    st.write("")


# ---------------------------------------------------------------
# BẢNG XẾP HẠNG
# ---------------------------------------------------------------
st.subheader("📋 Bảng xếp hạng")

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

if members_df.empty:
    st.info("Chưa có dữ liệu thành viên.")
else:
    for idx, row in members_df.reset_index(drop=True).iterrows():
        rank = idx + 1
        ten = row["name"]
        diem = int(row["diem"])

        top_class = f"top{rank}" if rank <= 3 else ""
        badge = MEDALS.get(rank, str(rank))
        badge_class = "medal" if rank <= 3 else ""
        pill_class = "positive" if diem > 0 else ("negative" if diem < 0 else "zero")
        chu_cai_dau = ten.strip()[0].upper() if ten.strip() else "?"

        st.markdown(
            f"""
            <div class="rank-card {top_class}">
                <div class="rank-badge {badge_class}">{badge}</div>
                <div class="avatar" style="background: {avatar_color(ten)};">{chu_cai_dau}</div>
                <div class="member-name">{ten}</div>
                <div class="score-pill {pill_class}">{diem:+d} điểm</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(f"Xem lịch sử của {ten}"):
            hist_df = load_history(ten)
            if not hist_df.empty:
                st.dataframe(hist_df, use_container_width=True, hide_index=True)
            else:
                st.caption("Chưa có lịch sử cộng/trừ điểm.")
