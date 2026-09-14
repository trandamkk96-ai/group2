import io
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import text
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# ============================================================
#  QUẢN LÝ ĐIỂM NHÓM — phiên bản chạy trên web (mọi thiết bị,
#  mọi hệ điều hành, chỉ cần trình duyệt), dữ liệu lưu bền vững
#  trên database Postgres (Supabase) thay vì file JSON.
# ============================================================

st.set_page_config(page_title="Quản Lý Điểm Nhóm", page_icon="🏆", layout="wide")

# --- Kết nối database ---------------------------------------------------
conn = st.connection("supabase_db", type="sql")


def init_db():
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
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                nguoi_gui TEXT,
                noi_dung TEXT NOT NULL,
                ngay TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        s.commit()


init_db()


# --- Truy vấn dữ liệu -----------------------------------------------------
def load_members():
    return conn.query("SELECT name, diem FROM members ORDER BY diem DESC, name", ttl=0)


def load_history(name, start=None, end=None):
    """start/end: đối tượng date (Python). end được hiểu là bao gồm luôn cả ngày đó."""
    query = (
        'SELECT ngay AS "Ngày", so_diem AS "Điểm", ly_do AS "Lý do", xac_nhan AS "Xác nhận" '
        'FROM history WHERE ten = :ten'
    )
    params = {"ten": name}
    if start is not None:
        query += ' AND ngay >= :start'
        params["start"] = start
    if end is not None:
        query += ' AND ngay < :end'
        params["end"] = end + timedelta(days=1)
    query += ' ORDER BY ngay DESC'
    return conn.query(query, params=params, ttl=0)


def load_all_history(start=None, end=None):
    query = (
        'SELECT ten AS "Thành viên", ngay AS "Ngày", so_diem AS "Điểm", '
        '       ly_do AS "Lý do", xac_nhan AS "Xác nhận" FROM history WHERE 1=1'
    )
    params = {}
    if start is not None:
        query += ' AND ngay >= :start'
        params["start"] = start
    if end is not None:
        query += ' AND ngay < :end'
        params["end"] = end + timedelta(days=1)
    query += ' ORDER BY ngay DESC'
    return conn.query(query, params=params, ttl=0)


def load_recent_entries(name, limit=10):
    """Lấy vài lần cộng/trừ gần nhất của 1 người (không áp dụng lọc ngày) — dùng để tính huy hiệu."""
    return conn.query(
        'SELECT so_diem FROM history WHERE ten = :ten ORDER BY ngay DESC, id DESC LIMIT :lim',
        params={"ten": name, "lim": limit},
        ttl=0,
    )


def load_trend_series(name=None):
    """Điểm cộng dồn theo thời gian — cho 1 người, hoặc cả nhóm nếu name=None."""
    if name:
        df = conn.query(
            'SELECT ngay AS "Ngày", so_diem FROM history WHERE ten = :ten ORDER BY ngay ASC',
            params={"ten": name},
            ttl=0,
        )
    else:
        df = conn.query('SELECT ngay AS "Ngày", so_diem FROM history ORDER BY ngay ASC', ttl=0)
    if df.empty:
        return df
    df["Điểm cộng dồn"] = df["so_diem"].cumsum()
    return df.set_index("Ngày")[["Điểm cộng dồn"]]


def compute_badges(name, diem, diem_max):
    badges = []
    if diem_max is not None and diem_max > 0 and diem == diem_max:
        badges.append("🏅 Đang dẫn đầu")
    recent = load_recent_entries(name, limit=10)
    if not recent.empty:
        vals = recent["so_diem"].tolist()
        streak_up = 0
        for v in vals:
            if v > 0:
                streak_up += 1
            else:
                break
        if streak_up >= 3:
            badges.append(f"🔥 {streak_up} lần liên tiếp được cộng điểm")
        streak_down = 0
        for v in vals:
            if v < 0:
                streak_down += 1
            else:
                break
        if streak_down >= 3:
            badges.append(f"⚠️ {streak_down} lần liên tiếp bị trừ điểm")
    return badges


def load_last_entry():
    """Lấy lần cộng/trừ điểm gần nhất (để có thể hoàn tác)."""
    return conn.query(
        'SELECT id, ten, so_diem, ly_do, ngay FROM history ORDER BY ngay DESC, id DESC LIMIT 1',
        ttl=0,
    )


def to_excel_bytes(members_df, history_df):
    bang_diem = members_df.rename(columns={"name": "Thành viên", "diem": "Điểm hiện tại"})
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        bang_diem.to_excel(writer, index=False, sheet_name="Bang diem")
        history_df.to_excel(writer, index=False, sheet_name="Lich su")
    return buffer.getvalue()


@st.cache_resource
def _register_pdf_fonts():
    pdfmetrics.registerFont(TTFont("DejaVuSans", "fonts/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", "fonts/DejaVuSans-Bold.ttf"))
    return True


def _pdf_table(data, col_widths, header_bold=True):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "DejaVuSans"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header_bold:
        style.append(("FONTNAME", (0, 0), (-1, 0), "DejaVuSans-Bold"))
    t.setStyle(TableStyle(style))
    return t


def to_pdf_bytes(members_df, history_df, tieu_de="Bao cao diem nhom"):
    _register_pdf_fonts()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm, leftMargin=1.5 * cm, rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("VNTitle", parent=styles["Title"], fontName="DejaVuSans-Bold", fontSize=18)
    heading_style = ParagraphStyle("VNHeading", parent=styles["Heading2"], fontName="DejaVuSans-Bold", fontSize=13)
    normal_style = ParagraphStyle("VNNormal", parent=styles["Normal"], fontName="DejaVuSans", fontSize=10)

    elements = [Paragraph("Báo Cáo Điểm Nhóm", title_style), Spacer(1, 14)]

    elements.append(Paragraph("Bảng điểm hiện tại", heading_style))
    elements.append(Spacer(1, 6))
    diem_data = [["Thành viên", "Điểm hiện tại"]] + [
        [str(r["name"]), str(int(r["diem"]))] for _, r in members_df.iterrows()
    ]
    elements.append(_pdf_table(diem_data, [10 * cm, 5 * cm]))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Lịch sử cộng / trừ điểm", heading_style))
    elements.append(Spacer(1, 6))
    if history_df.empty:
        elements.append(Paragraph("Chưa có lịch sử.", normal_style))
    else:
        hist_data = [["Thành viên", "Ngày", "Điểm", "Lý do", "Xác nhận"]]
        for _, r in history_df.iterrows():
            ngay_str = r["Ngày"].strftime("%d/%m/%Y %H:%M") if pd.notna(r["Ngày"]) else ""
            hist_data.append([
                str(r["Thành viên"]), ngay_str, f'{int(r["Điểm"]):+d}',
                str(r["Lý do"] or ""), str(r["Xác nhận"] or ""),
            ])
        elements.append(_pdf_table(hist_data, [3 * cm, 3 * cm, 1.7 * cm, 5.3 * cm, 2.5 * cm]))

    doc.build(elements)
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


def undo_entry(history_id, ten, so_diem):
    """Hoàn tác 1 lần cộng/trừ điểm: trừ ngược lại điểm đã cộng và xoá dòng lịch sử đó."""
    with conn.session as s:
        s.execute(text("UPDATE members SET diem = diem - :d WHERE name = :name"), {"d": so_diem, "name": ten})
        s.execute(text("DELETE FROM history WHERE id = :id"), {"id": history_id})
        s.commit()


def delete_member(name):
    with conn.session as s:
        s.execute(text("DELETE FROM members WHERE name = :name"), {"name": name})
        s.commit()


def reset_all_scores():
    with conn.session as s:
        s.execute(text("UPDATE members SET diem = 0"))
        s.execute(text("DELETE FROM history"))
        s.commit()


def add_feedback(nguoi_gui, noi_dung):
    with conn.session as s:
        s.execute(
            text("INSERT INTO feedback (nguoi_gui, noi_dung) VALUES (:ng, :nd)"),
            {"ng": nguoi_gui, "nd": noi_dung},
        )
        s.commit()


def load_feedback():
    """Chỉ Admin gọi hàm này để đọc góp ý — không hiển thị công khai ở đâu khác."""
    return conn.query('SELECT id, nguoi_gui, noi_dung, ngay FROM feedback ORDER BY ngay DESC', ttl=0)


def delete_feedback(feedback_id):
    with conn.session as s:
        s.execute(text("DELETE FROM feedback WHERE id = :id"), {"id": feedback_id})
        s.commit()


# ---------------------------------------------------------------
# CSS — giao diện
# ---------------------------------------------------------------
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; max-width: 960px; }

    .hero {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 20px; padding: 28px 32px; margin-bottom: 24px; color: white;
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
    }
    .hero-title { font-size: 1.9rem; font-weight: 800; margin: 0; }
    .hero-subtitle { opacity: 0.9; font-size: 0.95rem; margin-top: 4px; }

    div[data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #eef0f3; border-radius: 14px;
        padding: 12px 16px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }

    /* --- Podium top 3 --- */
    .podium-wrap { display: flex; align-items: flex-end; justify-content: center; gap: 14px; margin: 8px 0 26px; }
    .podium-block {
        flex: 1; max-width: 220px; border-radius: 16px 16px 6px 6px; padding: 14px 10px 18px;
        text-align: center; color: white; box-shadow: 0 6px 16px rgba(0,0,0,0.12);
    }
    .podium-block.gold { background: linear-gradient(180deg,#fde68a,#f59e0b); height: 200px; order: 2; }
    .podium-block.silver { background: linear-gradient(180deg,#e5e7eb,#94a3b8); height: 160px; order: 1; }
    .podium-block.bronze { background: linear-gradient(180deg,#fed7aa,#fb923c); height: 140px; order: 3; }
    .podium-medal { font-size: 2rem; line-height: 1; }
    .podium-avatar {
        width: 52px; height: 52px; border-radius: 50%; background: rgba(255,255,255,0.3);
        display: flex; align-items: center; justify-content: center; font-weight: 800;
        font-size: 1.2rem; margin: 6px auto; border: 2px solid rgba(255,255,255,0.7);
    }
    .podium-name { font-weight: 800; font-size: 1rem; margin-top: 2px; word-break: break-word; }
    .podium-score { font-weight: 800; font-size: 1.05rem; margin-top: 4px; }

    /* --- Thẻ xếp hạng (hạng 4 trở đi, hoặc khi tìm kiếm) --- */
    .rank-card {
        background: #ffffff; border: 1px solid #eef0f3; border-radius: 16px;
        padding: 14px 20px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .rank-card:hover { transform: translateY(-2px); box-shadow: 0 6px 16px rgba(16, 24, 40, 0.08); }
    .rank-card-top { display: flex; align-items: center; gap: 16px; }

    .rank-badge { width: 34px; min-width: 34px; text-align: center; font-size: 1.1rem; font-weight: 800; color: #9ca3af; }

    .avatar {
        width: 42px; height: 42px; min-width: 42px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1rem; color: white;
    }

    .member-name { flex: 1; font-size: 1.05rem; font-weight: 600; color: #111827; }

    .score-pill { padding: 6px 16px; border-radius: 999px; font-weight: 800; font-size: 0.95rem; white-space: nowrap; }
    .score-pill.positive { background: #dcfce7; color: #15803d; }
    .score-pill.negative { background: #fee2e2; color: #b91c1c; }
    .score-pill.zero { background: #f1f5f9; color: #475569; }

    .progress-track { width: 100%; height: 7px; background: #f1f5f9; border-radius: 999px; margin-top: 10px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg,#6366f1,#8b5cf6); }

    .badge-row { margin-top: 8px; }
    .badge-chip {
        display: inline-block; background: #eef2ff; color: #4338ca; border-radius: 999px;
        padding: 3px 10px; font-size: 0.72rem; font-weight: 700; margin: 3px 4px 0 0;
    }
    .podium-badges { margin-top: 6px; }
    .podium-badges .badge-chip { background: rgba(255,255,255,0.28); color: #ffffff; }

    div[data-testid="stExpander"] { border: none; border-radius: 14px; overflow: hidden; }
    button[kind="secondary"], button[kind="primary"] { border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)


AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#10b981", "#0ea5e9", "#eab308"]


def avatar_color(name):
    return AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]


def progress_pct(diem, diem_max):
    if diem_max is None or diem_max <= 0 or diem <= 0:
        return 0
    return max(0, min(100, round(diem / diem_max * 100)))


def badges_html(name, diem, diem_max, extra_class=""):
    badges = compute_badges(name, diem, diem_max)
    if not badges:
        return ""
    chips = "".join(f'<span class="badge-chip">{b}</span>' for b in badges)
    cls = f"badge-row {extra_class}".strip()
    return f'<div class="{cls}">{chips}</div>'


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

    st.sidebar.markdown("---")
    feedback_df = load_feedback()
    st.sidebar.subheader(f"📬 Hộp góp ý ({len(feedback_df)})")
    if feedback_df.empty:
        st.sidebar.caption("Chưa có góp ý nào.")
    else:
        for _, fb in feedback_df.iterrows():
            thoi_gian = fb["ngay"].strftime("%d/%m %H:%M") if pd.notna(fb["ngay"]) else ""
            nguoi = fb["nguoi_gui"] or "Ẩn danh"
            with st.sidebar.expander(f"{nguoi} — {thoi_gian}"):
                st.write(fb["noi_dung"])
                if st.button("🗑️ Xoá góp ý này", key=f"del_fb_{fb['id']}", use_container_width=True):
                    delete_feedback(int(fb["id"]))
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
    '<div class="hero">'
    '<div class="hero-title">🏆 Quản Lý Điểm Nhóm</div>'
    '<div class="hero-subtitle">Bảng xếp hạng điểm — cập nhật trực tiếp, mọi lúc mọi nơi</div>'
    '</div>',
    unsafe_allow_html=True,
)

members_df = load_members()

# ---------------------------------------------------------------
# LỌC LỊCH SỬ THEO KHOẢNG THỜI GIAN (áp dụng cho lịch sử xem + xuất file)
# ---------------------------------------------------------------
with st.expander("📅 Lọc lịch sử theo khoảng thời gian"):
    loc_theo_ngay = st.checkbox("Chỉ xem lịch sử trong khoảng ngày cụ thể")
    if loc_theo_ngay:
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            start_dt = st.date_input("Từ ngày:", value=date.today() - timedelta(days=7))
        with col_d2:
            end_dt = st.date_input("Đến ngày:", value=date.today())
    else:
        start_dt, end_dt = None, None
        st.caption("Đang hiển thị toàn bộ lịch sử (chưa lọc theo ngày).")

if not members_df.empty:
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Số thành viên", len(members_df))
    kpi2.metric("Điểm cao nhất", int(members_df["diem"].max()))
    kpi3.metric("Tổng điểm", int(members_df["diem"].sum()))

    excel_bytes = to_excel_bytes(members_df, load_all_history(start_dt, end_dt))
    pdf_bytes = to_pdf_bytes(members_df, load_all_history(start_dt, end_dt))
    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        st.download_button(
            "⬇️ Xuất file Excel",
            data=excel_bytes,
            file_name="diem_nhom.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_exp2:
        st.download_button(
            "⬇️ Xuất file PDF",
            data=pdf_bytes,
            file_name="diem_nhom.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    st.write("")


# ---------------------------------------------------------------
# FORM CỘNG / TRỪ ĐIỂM (chỉ Admin) + Hoàn tác
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

        # --- Hoàn tác lần gần nhất ---
        last_entry = load_last_entry()
        if not last_entry.empty:
            e = last_entry.iloc[0]
            st.markdown("---")
            st.caption(
                f"Thao tác gần nhất: **{e['ten']}** {int(e['so_diem']):+d} điểm — "
                f"{e['ly_do'] or '(không có lý do)'}"
            )
            if st.button("↩️ Hoàn tác thao tác này", use_container_width=True):
                undo_entry(int(e["id"]), e["ten"], int(e["so_diem"]))
                st.success("Đã hoàn tác!")
                st.rerun()
    st.write("")


# ---------------------------------------------------------------
# TÌM KIẾM
# ---------------------------------------------------------------
tu_khoa = st.text_input("🔍 Tìm thành viên:", placeholder="Nhập tên cần tìm...")

st.subheader("📋 Bảng xếp hạng")

MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

if members_df.empty:
    st.info("Chưa có dữ liệu thành viên.")
else:
    ranked = list(members_df.reset_index(drop=True).iterrows())
    diem_max = int(members_df["diem"].max())

    if tu_khoa.strip():
        # --- Có tìm kiếm: bỏ podium, hiện danh sách khớp kèm đúng thứ hạng gốc ---
        loc = tu_khoa.strip().lower()
        ranked = [(idx, row) for idx, row in ranked if loc in str(row["name"]).lower()]
        if not ranked:
            st.info("Không tìm thấy thành viên nào khớp.")

        for idx, row in ranked:
            rank = idx + 1
            ten = row["name"]
            diem = int(row["diem"])
            top_class = ""
            badge = MEDALS.get(rank, str(rank))
            pill_class = "positive" if diem > 0 else ("negative" if diem < 0 else "zero")
            chu_cai_dau = ten.strip()[0].upper() if ten.strip() else "?"
            pct = progress_pct(diem, diem_max)

            card_html = (
                f'<div class="rank-card {top_class}">'
                f'<div class="rank-card-top">'
                f'<div class="rank-badge">{badge}</div>'
                f'<div class="avatar" style="background: {avatar_color(ten)};">{chu_cai_dau}</div>'
                f'<div class="member-name">{ten}</div>'
                f'<div class="score-pill {pill_class}">{diem:+d} điểm</div>'
                f'</div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div>'
                f'{badges_html(ten, diem, diem_max)}'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            with st.expander(f"Xem lịch sử của {ten}"):
                hist_df = load_history(ten, start_dt, end_dt)
                if not hist_df.empty:
                    st.dataframe(hist_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("Chưa có lịch sử cộng/trừ điểm.")
    else:
        # --- Không tìm kiếm: hiện bục podium top 3 + danh sách hạng 4 trở đi ---
        top3 = ranked[:3]
        rest = ranked[3:]

        if top3:
            blocks_html = ""
            classes = ["gold", "silver", "bronze"]
            for i, (idx, row) in enumerate(top3):
                rank = idx + 1
                ten = row["name"]
                diem = int(row["diem"])
                chu_cai_dau = ten.strip()[0].upper() if ten.strip() else "?"
                blocks_html += (
                    f'<div class="podium-block {classes[i]}">'
                    f'<div class="podium-medal">{MEDALS.get(rank, "")}</div>'
                    f'<div class="podium-avatar">{chu_cai_dau}</div>'
                    f'<div class="podium-name">{ten}</div>'
                    f'<div class="podium-score">{diem:+d} điểm</div>'
                    f'{badges_html(ten, diem, diem_max, "podium-badges")}'
                    f'</div>'
                )
            st.markdown(f'<div class="podium-wrap">{blocks_html}</div>', unsafe_allow_html=True)

        for idx, row in rest:
            rank = idx + 1
            ten = row["name"]
            diem = int(row["diem"])
            pill_class = "positive" if diem > 0 else ("negative" if diem < 0 else "zero")
            chu_cai_dau = ten.strip()[0].upper() if ten.strip() else "?"
            pct = progress_pct(diem, diem_max)

            card_html = (
                f'<div class="rank-card">'
                f'<div class="rank-card-top">'
                f'<div class="rank-badge">{rank}</div>'
                f'<div class="avatar" style="background: {avatar_color(ten)};">{chu_cai_dau}</div>'
                f'<div class="member-name">{ten}</div>'
                f'<div class="score-pill {pill_class}">{diem:+d} điểm</div>'
                f'</div>'
                f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div>'
                f'{badges_html(ten, diem, diem_max)}'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)
            with st.expander(f"Xem lịch sử của {ten}"):
                hist_df = load_history(ten, start_dt, end_dt)
                if not hist_df.empty:
                    st.dataframe(hist_df, use_container_width=True, hide_index=True)
                else:
                    st.caption("Chưa có lịch sử cộng/trừ điểm.")

        # Lịch sử của top 3 (đặt dưới cùng để bục podium không quá dài)
        if top3:
            st.markdown("##### Lịch sử của top 3")
            for idx, row in top3:
                ten = row["name"]
                with st.expander(f"Xem lịch sử của {ten}"):
                    hist_df = load_history(ten, start_dt, end_dt)
                    if not hist_df.empty:
                        st.dataframe(hist_df, use_container_width=True, hide_index=True)
                    else:
                        st.caption("Chưa có lịch sử cộng/trừ điểm.")


# ---------------------------------------------------------------
# XU HƯỚNG ĐIỂM
# ---------------------------------------------------------------
if not members_df.empty:
    st.markdown("---")
    st.subheader("📈 Xu hướng điểm")
    trend_options = ["Cả nhóm"] + members_df["name"].tolist()
    trend_pick = st.selectbox("Xem xu hướng của:", trend_options, key="trend_select")
    trend_df = load_trend_series(None if trend_pick == "Cả nhóm" else trend_pick)
    if trend_df.empty:
        st.caption("Chưa có dữ liệu để vẽ biểu đồ.")
    else:
        st.line_chart(trend_df)


# ---------------------------------------------------------------
# GÓP Ý (ai cũng gửi được — chỉ Admin mới đọc được, ở sidebar)
# ---------------------------------------------------------------
st.markdown("---")
st.subheader("💬 Gửi góp ý")
st.caption("Góp ý của bạn chỉ Admin đọc được, không hiển thị công khai cho người khác xem.")
with st.form("form_gop_y", clear_on_submit=True):
    nguoi_gui_fb = st.text_input("Tên bạn (để trống nếu muốn ẩn danh):")
    noi_dung_fb = st.text_area("Nội dung góp ý:")
    da_gui = st.form_submit_button("Gửi góp ý", use_container_width=True)
    if da_gui:
        if noi_dung_fb.strip():
            add_feedback(nguoi_gui_fb.strip() or "Ẩn danh", noi_dung_fb.strip())
            st.success("Cảm ơn bạn đã góp ý!")
        else:
            st.error("Vui lòng nhập nội dung góp ý.")
