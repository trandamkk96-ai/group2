import html
import io
import random
import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import qrcode
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

# Link app cố định — nếu sau này đổi sang link/tên miền khác, chỉ cần sửa đúng dòng này
# rồi cập nhật lại app.py trên GitHub là mã QR sẽ tự cập nhật theo.
APP_URL = "https://group2-bl2ar8lcntmbxvkpfxy4n7.streamlit.app/"

# Nhật ký cập nhật web — mỗi khi thêm tính năng mới, chỉ cần thêm 1 dòng (ngày, mô tả)
# vào ĐẦU danh sách này rồi cập nhật app.py; tab "🆕 Cập nhật" sẽ tự hiện ra.
UPDATES = [
    ("15/09/2026", "📅 Thêm banner \"Hôm nay học gì\" ngay trên Trang chủ — tự lấy đúng lịch của hôm đó từ tab Thời khóa biểu theo giờ Hà Nội, khỏi cần bấm qua tab riêng để xem."),
    ("15/09/2026", "📅 Thêm tab Thời khóa biểu (kế bên Trang chủ) — ai cũng xem được, Admin sửa thẳng trên web trong 10 giây (không cần vào GitHub nữa): mở tab này → bấm \"Sửa thời khóa biểu\" → gõ lại → Lưu là xong ngay."),
    ("15/09/2026", "⚡ Giảm tải cho điện thoại yếu: bớt bớt số sao/sao băng chạy hoạt ảnh ở Chế độ tối (trang mượt hơn hẳn), điện thoại màn nhỏ tự động bớt thêm một nửa sao băng, máy nào bật \"Giảm chuyển động\" thì web tự tắt hẳn hoạt ảnh trang trí."),
    ("15/09/2026", "🕒 Tự động đổi giao diện theo giờ Hà Nội — giờ BẬT SẴN mặc định, ai mở trang cũng tự đúng giờ luôn (sau 18h tối tự Chế độ tối, sau 6h sáng tự Chế độ sáng), không cần bấm gì; vẫn có thể tắt tự động để tự chọn thủ công. Chế độ sáng giờ cũng có \"bầu trời\" riêng cho hợp với Chế độ tối: nền trời xanh nhạt, mặt trời phát sáng, mây trôi nhẹ nhàng."),
    ("15/09/2026", "Chế độ tối giờ có giao diện bầu trời sao ✨ — nền đen lấp lánh sao, có mặt trăng phát sáng góc trên, sao băng bay ngang qua dày hơn hẳn. Thêm tab Tin tức (chỉ Admin đăng/xoá được, ai cũng xem được) — tin mới nhất còn hiện ngay trên Trang chủ. Giờ có 4 tab: Trang chủ / Tin tức / Cập nhật / Góp ý, mỗi tab có banner màu riêng. Thêm Chế độ tối (nút 🌙 ở thanh bên), sắp xếp theo tên A-Z, giao diện sinh động hơn. Mã QR mở nhanh, Nhật ký hoạt động chung."),
    ("14/09/2026", "Thêm bộ lọc lịch sử theo ngày, biểu đồ xu hướng điểm, huy hiệu thành tích, xuất file PDF."),
    ("12/09/2026", "Thêm hộp góp ý (chỉ Admin đọc), avatar, bục podium top 3, tìm kiếm thành viên, hoàn tác."),
]

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
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS news (
                id SERIAL PRIMARY KEY,
                noi_dung TEXT NOT NULL,
                ngay TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS thoikhoabieu (
                id SERIAL PRIMARY KEY,
                noi_dung TEXT NOT NULL,
                ngay TIMESTAMP NOT NULL DEFAULT now()
            )
        """))
        s.commit()


init_db()

# Thời khóa biểu mặc định — chỉ dùng để "gieo" 1 lần duy nhất lúc bảng thoikhoabieu còn trống
# (lần đầu chạy sau khi thêm tính năng này). Sau đó Admin có thể sửa thẳng trên web, không cần
# đụng vào đây nữa — xem hướng dẫn "cách đổi thời khóa biểu nhanh gọn" mình nhắn kèm bên dưới.
TKB_MAC_DINH = """THỜI KHÓA BIỂU LỚP 9/7 (ÁP DỤNG TỪ THỨ 2 NGÀY 14/9/2026)

Thứ 2: HĐTN (2T) • Toán • Ngữ văn (2T)
Thứ 3: KHTN Hóa (2T) • LS&ĐL • HĐTN • KHTN Sinh
Thứ 4: Mỹ thuật • Âm nhạc • Toán (2T) • Tin học
Thứ 5: LS&ĐL • GDCD • Tiếng Anh (2T) • KHTN Lý
Thứ 6: LS&ĐL • Ngữ văn (2T) • Tiếng Anh • Toán
Thứ 7: Công nghệ • SHL"""


def _gieo_tkb_neu_trong():
    """Nếu bảng thời khóa biểu chưa có dòng nào (mới thêm tính năng lần đầu), tự điền sẵn
    thời khóa biểu hiện tại vào — để tab không bị trống trơn ngay từ đầu."""
    so_dong = conn.query("SELECT COUNT(*) AS n FROM thoikhoabieu", ttl=0).iloc[0]["n"]
    if so_dong == 0:
        with conn.session as s:
            s.execute(text("INSERT INTO thoikhoabieu (noi_dung) VALUES (:nd)"), {"nd": TKB_MAC_DINH})
            s.commit()


_gieo_tkb_neu_trong()


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


def load_recent_all(limit_per_member=10):
    """Lấy tối đa `limit_per_member` lần cộng/trừ gần nhất của MỖI thành viên, gộp trong 1 lượt
    truy vấn database duy nhất (thay vì hỏi riêng từng người) — để trang mở nhanh hơn, đặc biệt
    trên điện thoại mạng chậm."""
    return conn.query(
        """
        SELECT ten, so_diem FROM (
            SELECT ten, so_diem,
                   ROW_NUMBER() OVER (PARTITION BY ten ORDER BY ngay DESC, id DESC) AS rn
            FROM history
        ) t
        WHERE rn <= :lim
        ORDER BY ten, rn
        """,
        params={"lim": limit_per_member},
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


def compute_badges(vals, diem, diem_max):
    """vals: danh sách so_diem gần nhất của người này (mới nhất trước), lấy sẵn từ load_recent_all."""
    badges = []
    if diem_max is not None and diem_max > 0 and diem == diem_max:
        badges.append("🏅 Đang dẫn đầu")
    if vals:
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


def load_recent_activity(limit=15):
    """Nhật ký hoạt động chung của CẢ NHÓM — các lần cộng/trừ điểm gần nhất, không phân biệt ai."""
    return conn.query(
        'SELECT ten AS "Thành viên", ngay AS "Ngày", so_diem AS "Điểm", '
        '       ly_do AS "Lý do", xac_nhan AS "Xác nhận" '
        'FROM history ORDER BY ngay DESC, id DESC LIMIT :lim',
        params={"lim": limit},
        ttl=0,
    )


def make_qr_bytes(url):
    """Tạo ảnh mã QR (PNG) từ 1 đường link."""
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


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


def add_news(noi_dung):
    """Chỉ Admin mới gọi hàm này (đã kiểm tra is_admin trước khi gọi)."""
    with conn.session as s:
        s.execute(text("INSERT INTO news (noi_dung) VALUES (:nd)"), {"nd": noi_dung})
        s.commit()


def load_news():
    """Tin tức công khai — ai cũng xem được, chỉ Admin mới đăng/xoá được."""
    return conn.query('SELECT id, noi_dung, ngay FROM news ORDER BY ngay DESC', ttl=0)


def load_latest_news():
    """Lấy đúng 1 tin mới nhất — để hiện lên Trang chủ (nếu chưa có tin nào thì trả về rỗng)."""
    return conn.query('SELECT id, noi_dung, ngay FROM news ORDER BY ngay DESC LIMIT 1', ttl=0)


def delete_news(news_id):
    with conn.session as s:
        s.execute(text("DELETE FROM news WHERE id = :id"), {"id": news_id})
        s.commit()


def add_thoikhoabieu(noi_dung):
    """Chỉ Admin mới gọi hàm này (đã kiểm tra is_admin trước khi gọi). Mỗi lần Admin lưu là
    thêm 1 bản ghi mới — nên tự nhiên có luôn "lịch sử" các bản thời khóa biểu cũ, không mất gì."""
    with conn.session as s:
        s.execute(text("INSERT INTO thoikhoabieu (noi_dung) VALUES (:nd)"), {"nd": noi_dung})
        s.commit()


def load_thoikhoabieu_hien_tai():
    """Lấy bản thời khóa biểu mới nhất (bản Admin lưu gần đây nhất)."""
    return conn.query('SELECT id, noi_dung, ngay FROM thoikhoabieu ORDER BY ngay DESC LIMIT 1', ttl=0)


_MAU_DONG_THU = re.compile(r"^\s*Thứ\s*(\d+|Bảy|bảy|CN|cn)\s*[:：]\s*(.+?)\s*$")


def _tach_dong_tkb(noi_dung):
    """Tách nội dung thời khóa biểu (dạng chữ, Admin gõ tự do) thành:
    - cac_dong_dau: những dòng KHÔNG theo mẫu "Thứ x: ..." (thường là dòng tiêu đề/ghi chú)
    - cac_ngay: list (tên thứ, nội dung) cho những dòng ĐÚNG mẫu "Thứ x: ..."
    Nhờ vậy Admin gõ sao cũng hiển thị được — đúng mẫu thì lên thẻ đẹp, không đúng mẫu thì
    vẫn hiện ra như một dòng ghi chú bình thường, không bao giờ mất nội dung."""
    cac_dong_dau, cac_ngay = [], []
    for dong_tho in (noi_dung or "").splitlines():
        dong = dong_tho.strip()
        if not dong:
            continue
        khop = _MAU_DONG_THU.match(dong)
        if khop:
            cac_ngay.append((f"Thứ {khop.group(1)}", khop.group(2)))
        else:
            cac_dong_dau.append(dong)
    return cac_dong_dau, cac_ngay


# ---------------------------------------------------------------
# CHẾ ĐỘ TỐI — đặt sớm (trước CSS) để tính màu cho toàn bộ giao diện bên dưới.
# Có thể bật thủ công (nút 🌙), hoặc để web TỰ ĐỘNG đổi theo giờ Hà Nội:
# sau 18h (6 giờ tối) tự bật Chế độ tối, sau 6h sáng tự chuyển lại Chế độ sáng.
# Việt Nam không đổi giờ theo mùa nên dùng thẳng UTC+7, không cần cài thêm gì.
# ---------------------------------------------------------------
GIO_HA_NOI = timezone(timedelta(hours=7))


def _dang_la_ban_dem_o_ha_noi() -> bool:
    gio = datetime.now(GIO_HA_NOI).hour
    return gio >= 18 or gio < 6


# Python: Thứ 2=0 ... Chủ nhật=6 (datetime.weekday()) — đổi sang đúng cách gọi thứ ở VN,
# để khớp với nhãn "Thứ x" trong Thời khóa biểu.
_TEN_THU_VN = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]


def _thu_hom_nay_ha_noi() -> str:
    return _TEN_THU_VN[datetime.now(GIO_HA_NOI).weekday()]


auto_theme = st.sidebar.toggle(
    "🕒 Tự động theo giờ Hà Nội",
    value=True,  # MẶC ĐỊNH BẬT — ai mở trang cũng tự đúng giờ luôn, không cần bấm gì cả.
    key="auto_theme",
    help="Bật lên: sau 18h tối web tự chuyển Chế độ tối, sau 6h sáng tự chuyển lại Chế độ sáng — không cần bấm tay. Tắt đi nếu muốn tự chọn Chế độ tối/sáng theo ý mình.",
)
dark_mode_thu_cong = st.sidebar.toggle(
    "🌙 Chế độ tối", key="dark_mode", disabled=auto_theme,
)

if auto_theme:
    dark_mode = _dang_la_ban_dem_o_ha_noi()
    gio_hien_tai = datetime.now(GIO_HA_NOI).strftime("%H:%M")
    st.sidebar.caption(f"🕒 Giờ Hà Nội: {gio_hien_tai} — đang tự bật {'🌙 Chế độ tối' if dark_mode else '☀️ Chế độ sáng'}")
else:
    dark_mode = dark_mode_thu_cong

if dark_mode:
    C_BG, C_CARD, C_BORDER, C_TEXT, C_MUTED, C_TRACK, C_SIDEBAR = (
        "#0f172a", "#1e293b", "#334155", "#e2e8f0", "#94a3b8", "#334155", "#111827",
    )
    C_BG_CSS = C_BG  # ban đêm: nền xanh than đặc, để bầu trời sao làm điểm nhấn
else:
    C_BG, C_CARD, C_BORDER, C_TEXT, C_MUTED, C_TRACK, C_SIDEBAR = (
        "#f8fafc", "#ffffff", "#eef0f3", "#111827", "#9ca3af", "#f1f5f9", "#ffffff",
    )
    # ban ngày: nền trời xanh nhạt đổ dần xuống trắng — hợp với mặt trời + mây ở dưới,
    # thay vì một màu xám trắng phẳng lì như trước.
    C_BG_CSS = "linear-gradient(180deg, #dbeafe 0%, #eff6ff 32%, #f8fafc 65%)"


def _make_starfield_html():
    """Tạo nền bầu trời sao cho Chế độ tối: các chấm sao lấp lánh (kỹ thuật box-shadow,
    không cần JavaScript) + sao băng bay ngang qua màn hình.

    LƯU Ý HIỆU NĂNG: bản trước dùng 235 chấm sao + 60 sao băng chạy hoạt ảnh liên tục,
    trên điện thoại yếu (CPU/GPU chậm) sẽ khiến trang tải/cuộn ì. Đã giảm bớt số lượng
    xuống mức vừa phải (vẫn đẹp, vẫn có bầu trời sao + sao băng) để nhẹ máy hơn hẳn —
    nếu máy vẫn yếu, có thể giảm thêm các số ở đây."""

    def _dots(n):
        return ", ".join(
            f"{round(random.uniform(0, 100), 2)}vw {round(random.uniform(0, 100), 2)}vh #fff"
            for _ in range(n)
        )

    stars_small, stars_medium, stars_large = _dots(70), _dots(30), _dots(12)

    SO_SAO_BANG = 24  # số sao băng/phút — chỉnh số này để dày/thưa hơn (càng cao càng tốn máy)
    shooting_stars = "".join(
        '<div class="shooting-star" style="top:{top}vh; left:{left}vw; animation-delay:{delay}s;"></div>'.format(
            top=round(random.uniform(2, 55), 1),
            left=round(random.uniform(15, 95), 1),
            delay=round(i * (60 / SO_SAO_BANG), 2),
        )
        for i in range(SO_SAO_BANG)
    )
    return stars_small, stars_medium, stars_large, shooting_stars


if dark_mode:
    ST_SMALL, ST_MEDIUM, ST_LARGE, SHOOTING_STARS_HTML = _make_starfield_html()

# ---------------------------------------------------------------
# CSS — giao diện
# ---------------------------------------------------------------
st.markdown(f"""
<style>
    html, body {{ background: {C_BG_CSS} !important; }}
    /* LƯU Ý: .stApp của Streamlit vốn đã là position: absolute; inset: 0 (để tự phủ kín màn hình).
       KHÔNG được ghi đè "position" ở đây — nếu đổi thành "relative" thì khung này sẽ co về
       chiều cao 0 (vì "inset" chỉ kéo giãn khi position là absolute/fixed), khiến toàn bộ
       trang bị cắt mất (overflow: hidden) và hiện trắng trơn. Chỉ cần z-index là đủ để tạo
       ngữ cảnh xếp lớp cho bầu trời sao / bầu trời ban ngày, vì .stApp vốn đã "positioned" sẵn rồi. */
    .stApp {{ background: {C_BG_CSS} !important; z-index: 0; }}
    [data-testid="stAppViewContainer"] {{ background: {C_BG_CSS} !important; }}
    [data-testid="stMain"] {{ background-color: transparent !important; }}
    .block-container {{ padding-top: 5rem; max-width: 960px; position: relative; z-index: 1; }}

    .hero {{
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        border-radius: 20px; padding: 28px 32px; margin-bottom: 24px; color: white;
        box-shadow: 0 8px 24px rgba(99, 102, 241, 0.25);
    }}
    .hero-title {{ font-size: 1.9rem; font-weight: 800; margin: 0; }}
    .hero-subtitle {{ opacity: 0.9; font-size: 0.95rem; margin-top: 4px; }}

    /* --- Banner nhỏ đầu mỗi tab (Tin tức / Cập nhật / Góp ý) --- */
    .tab-hero {{
        border-radius: 16px; padding: 18px 24px; margin-bottom: 20px; color: white;
        animation: fadeInUp 0.4s ease both;
    }}
    .tab-hero.news {{
        background: linear-gradient(135deg, #ef4444 0%, #ec4899 100%);
        box-shadow: 0 8px 20px rgba(239, 68, 68, 0.25);
    }}
    .tab-hero.update {{
        background: linear-gradient(135deg, #f59e0b 0%, #f97316 100%);
        box-shadow: 0 8px 20px rgba(245, 158, 11, 0.25);
    }}
    .tab-hero.feedback {{
        background: linear-gradient(135deg, #10b981 0%, #0ea5e9 100%);
        box-shadow: 0 8px 20px rgba(16, 185, 129, 0.25);
    }}
    .tab-hero.schedule {{
        background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
        box-shadow: 0 8px 20px rgba(14, 165, 233, 0.25);
    }}
    .tab-hero-title {{ font-size: 1.3rem; font-weight: 800; margin: 0; }}
    .tab-hero-subtitle {{ opacity: 0.92; font-size: 0.88rem; margin-top: 4px; }}

    /* --- Tab "Thời khóa biểu": dòng tiêu đề + từng thứ trong tuần --- */
    .tkb-tieu-de {{
        font-weight: 800; color: {C_TEXT}; font-size: 0.95rem; margin-bottom: 14px;
        line-height: 1.5;
    }}
    .tkb-dong {{
        display: flex; align-items: center; gap: 14px;
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-left: 4px solid #0ea5e9;
        border-radius: 12px; padding: 12px 18px; margin-bottom: 10px;
        animation: fadeInUp 0.4s ease both;
    }}
    .tkb-thu {{
        flex: 0 0 auto; min-width: 62px; text-align: center;
        background: linear-gradient(135deg, #0ea5e9, #6366f1); color: white;
        font-weight: 800; font-size: 0.82rem; border-radius: 999px; padding: 5px 12px;
    }}
    .tkb-mon {{ color: {C_TEXT}; font-size: 0.95rem; line-height: 1.5; }}

    /* --- Banner "Tin mới nhất" hiện gọn trên Trang chủ (khi Admin có đăng tin) --- */
    .home-news-banner {{
        background: linear-gradient(135deg, #ef4444 0%, #ec4899 100%);
        border-radius: 14px; padding: 14px 20px; margin-bottom: 20px; color: white;
        box-shadow: 0 6px 16px rgba(239, 68, 68, 0.25);
        animation: fadeInUp 0.4s ease both;
    }}
    .home-news-label {{ font-size: 0.72rem; font-weight: 800; text-transform: uppercase; opacity: 0.85; letter-spacing: 0.03em; }}
    .home-news-text {{ font-size: 1rem; font-weight: 600; margin-top: 4px; line-height: 1.5; white-space: pre-wrap; }}

    /* --- Banner "Hôm nay học gì" trên Trang chủ, tự lấy theo thứ hôm nay --- */
    .home-tkb-banner {{
        background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%);
        border-radius: 14px; padding: 14px 20px; margin-bottom: 20px; color: white;
        box-shadow: 0 6px 16px rgba(14, 165, 233, 0.25);
        animation: fadeInUp 0.4s ease both;
    }}
    .home-tkb-banner.nghi {{
        background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%);
        box-shadow: 0 6px 16px rgba(100, 116, 139, 0.2);
    }}
    .home-tkb-label {{ font-size: 0.72rem; font-weight: 800; text-transform: uppercase; opacity: 0.85; letter-spacing: 0.03em; }}
    .home-tkb-text {{ font-size: 1rem; font-weight: 600; margin-top: 4px; line-height: 1.5; }}

    /* --- Danh sách "Cập nhật mới nhất" dạng timeline --- */
    .update-item {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-left: 4px solid #f59e0b;
        border-radius: 12px; padding: 12px 18px; margin-bottom: 12px;
        animation: fadeInUp 0.4s ease both;
    }}
    .update-date {{ font-weight: 800; color: {C_TEXT}; font-size: 0.95rem; }}
    .update-desc {{ color: {C_MUTED}; font-size: 0.9rem; margin-top: 3px; line-height: 1.5; }}
    .badge-chip.update-badge {{
        background: #fed7aa; color: #9a3412; font-size: 0.65rem; vertical-align: middle;
        margin-left: 6px;
    }}

    /* --- Từng tin trong tab "Tin tức" --- */
    .news-item {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-left: 4px solid #ef4444;
        border-radius: 12px; padding: 12px 18px; margin-bottom: 12px;
        animation: fadeInUp 0.4s ease both;
    }}
    .news-item-date {{ font-weight: 700; color: {C_MUTED}; font-size: 0.78rem; }}
    .news-item-text {{ color: {C_TEXT}; font-size: 0.95rem; margin-top: 3px; line-height: 1.5; white-space: pre-wrap; }}

    div[data-testid="stMetric"] {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 14px;
        padding: 12px 16px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {{ color: {C_TEXT}; }}

    /* --- Hiệu ứng xuất hiện nhẹ nhàng cho các thẻ --- */
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(14px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes goldGlow {{
        0%, 100% {{ box-shadow: 0 6px 16px rgba(245, 158, 11, 0.35); }}
        50% {{ box-shadow: 0 10px 30px rgba(245, 158, 11, 0.65); }}
    }}

    /* --- Podium top 3 --- */
    .podium-wrap {{ display: flex; align-items: flex-end; justify-content: center; gap: 14px; margin: 8px 0 26px; }}
    .podium-block {{
        flex: 1; max-width: 220px; border-radius: 16px 16px 6px 6px; padding: 14px 10px 18px;
        text-align: center; color: white; box-shadow: 0 6px 16px rgba(0,0,0,0.12);
        animation: fadeInUp 0.5s ease both;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .podium-block:hover {{ transform: translateY(-6px) scale(1.03); }}
    .podium-block.gold {{
        background: linear-gradient(180deg,#fde68a,#f59e0b); height: 200px; order: 2;
        animation: fadeInUp 0.5s ease both, goldGlow 2.4s ease-in-out infinite;
    }}
    .podium-block.silver {{ background: linear-gradient(180deg,#e5e7eb,#94a3b8); height: 160px; order: 1; }}
    .podium-block.bronze {{ background: linear-gradient(180deg,#fed7aa,#fb923c); height: 140px; order: 3; }}
    .podium-medal {{ font-size: 2rem; line-height: 1; }}
    .podium-avatar {{
        width: 52px; height: 52px; border-radius: 50%; background: rgba(255,255,255,0.3);
        display: flex; align-items: center; justify-content: center; font-weight: 800;
        font-size: 1.2rem; margin: 6px auto; border: 2px solid rgba(255,255,255,0.7);
    }}
    .podium-name {{ font-weight: 800; font-size: 1rem; margin-top: 2px; word-break: break-word; }}
    .podium-score {{ font-weight: 800; font-size: 1.05rem; margin-top: 4px; }}

    /* --- Thẻ xếp hạng (hạng 4 trở đi, hoặc khi tìm kiếm) --- */
    .rank-card {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-radius: 16px;
        padding: 14px 20px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        animation: fadeInUp 0.4s ease both;
    }}
    .rank-card:hover {{ transform: translateY(-2px) scale(1.005); box-shadow: 0 6px 16px rgba(16, 24, 40, 0.08); }}
    .rank-card-top {{ display: flex; align-items: center; gap: 16px; }}

    .rank-badge {{ width: 34px; min-width: 34px; text-align: center; font-size: 1.1rem; font-weight: 800; color: {C_MUTED}; }}

    .avatar {{
        width: 42px; height: 42px; min-width: 42px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1rem; color: white;
    }}

    .member-name {{ flex: 1; font-size: 1.05rem; font-weight: 600; color: {C_TEXT}; }}

    .score-pill {{ padding: 6px 16px; border-radius: 999px; font-weight: 800; font-size: 0.95rem; white-space: nowrap; }}
    .score-pill.positive {{ background: #dcfce7; color: #15803d; }}
    .score-pill.negative {{ background: #fee2e2; color: #b91c1c; }}
    .score-pill.zero {{ background: #f1f5f9; color: #475569; }}

    .progress-track {{ width: 100%; height: 7px; background: {C_TRACK}; border-radius: 999px; margin-top: 10px; overflow: hidden; }}
    .progress-fill {{
        height: 100%; border-radius: 999px; background: linear-gradient(90deg,#6366f1,#8b5cf6);
        transition: width 0.8s ease;
    }}

    .badge-row {{ margin-top: 8px; }}
    .badge-chip {{
        display: inline-block; background: #eef2ff; color: #4338ca; border-radius: 999px;
        padding: 3px 10px; font-size: 0.72rem; font-weight: 700; margin: 3px 4px 0 0;
    }}
    .podium-badges {{ margin-top: 6px; }}
    .podium-badges .badge-chip {{ background: rgba(255,255,255,0.28); color: #ffffff; }}

    div[data-testid="stExpander"] {{
        border: 1px solid {C_BORDER}; border-radius: 14px; overflow: hidden; background: {C_CARD};
    }}
    div[data-testid="stExpander"] summary {{ background-color: {C_CARD} !important; color: {C_TEXT} !important; }}
    button[kind="secondary"], button[kind="primary"], [data-testid^="stBaseButton"] {{ border-radius: 10px !important; }}
    .stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {{
        background-color: {C_CARD}; color: {C_TEXT}; border: 1px solid {C_BORDER};
    }}

    /* --- Tab "Trang chủ" / "Cập nhật" dạng viên thuốc (pill) --- */
    [data-testid="stTab"] {{
        font-weight: 700; font-size: 1.02rem; border-radius: 999px !important;
        padding: 6px 20px !important; transition: background 0.2s ease, color 0.2s ease;
        cursor: pointer; color: {C_TEXT};
    }}
    [data-testid="stTab"] p {{ color: inherit; }}
    [data-testid="stTab"][aria-selected="true"] {{
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: #ffffff !important;
    }}
    [data-testid="stTab"] .react-aria-SelectionIndicator {{ display: none; }}
    [data-testid="stTabs"] [role="tablist"] {{
        background: {C_BG}; gap: 8px; padding-bottom: 6px; border-bottom: 1px solid {C_BORDER};
    }}

    /* Thanh công cụ trên cùng của Streamlit (chỗ có nút ☰) mặc định trong suốt,
       nên khi cuộn trang, chữ của trang bị "lộ" xuyên qua gây cảm giác chồng chữ.
       Tô nền đặc cho thanh này để che hẳn phần nội dung cuộn qua bên dưới. */
    header[data-testid="stHeader"] {{
        background: {C_BG} !important;
        box-shadow: 0 1px 0 rgba(16, 24, 40, 0.06);
    }}

    /* --- Chế độ tối: nền/chữ của sidebar, tiêu đề, chú thích, ô nhập liệu ---
       (đặt màu chữ trên chính khung chứa để chữ bên trong tự kế thừa màu — nhiều
       thẻ tiêu đề/nhãn của Streamlit dùng color: inherit nên phải làm theo cách này). */
    section[data-testid="stSidebar"] {{ background-color: {C_SIDEBAR}; color: {C_TEXT}; }}
    [data-testid="stMarkdownContainer"] {{ color: {C_TEXT}; }}
    [data-testid="stCaptionContainer"] {{ color: {C_MUTED}; }}
    [data-testid="stWidgetLabel"] {{ color: {C_TEXT}; }}
    .stApp input, .stApp textarea {{
        background-color: {C_CARD} !important; color: {C_TEXT} !important; border-color: {C_BORDER} !important;
    }}
    [data-testid="stSelectbox"] > div {{
        background-color: {C_CARD}; color: {C_TEXT}; border-color: {C_BORDER};
    }}
</style>
""", unsafe_allow_html=True)

# --- Bầu trời sao cho Chế độ tối (sao lấp lánh + sao băng dày đặc + mặt trăng) ---
# Chỉ hiện khi bật Chế độ tối; ở giao diện thường (sáng) không có gì thay đổi ở đây.
if dark_mode:
    st.markdown(f"""
    <style>
        .starfield {{ position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }}
        .stars-small, .stars-medium, .stars-large {{
            position: absolute; top: 0; left: 0; width: 1px; height: 1px;
            background: transparent; border-radius: 50%; will-change: opacity;
        }}
        .stars-small {{ box-shadow: {ST_SMALL}; animation: twinkle 3s ease-in-out infinite alternate; }}
        .stars-medium {{
            width: 2px; height: 2px; box-shadow: {ST_MEDIUM};
            animation: twinkle 4s ease-in-out infinite alternate-reverse;
        }}
        .stars-large {{
            width: 3px; height: 3px; box-shadow: {ST_LARGE};
            animation: twinkle 5s ease-in-out infinite;
        }}
        @keyframes twinkle {{ from {{ opacity: 0.35; }} to {{ opacity: 1; }} }}

        .shooting-star {{
            position: fixed; width: 140px; height: 2px; border-radius: 999px;
            background: linear-gradient(90deg, rgba(255,255,255,0.95), rgba(255,255,255,0));
            opacity: 0; transform: rotate(-35deg); animation: shoot 60s linear infinite;
            will-change: opacity, transform;
        }}
        @keyframes shoot {{
            0%, 96% {{ opacity: 0; transform: translate(0, 0) rotate(-35deg); }}
            96.5% {{ opacity: 1; }}
            98.5% {{ opacity: 1; transform: translate(-340px, 240px) rotate(-35deg); }}
            100% {{ opacity: 0; transform: translate(-380px, 270px) rotate(-35deg); }}
        }}
        /* Máy/điện thoại yếu: bớt một nửa số sao băng đang chạy hoạt ảnh cùng lúc cho nhẹ máy
           (nth-child ẩn hẳn — trình duyệt không phải vẽ/tính khung hình cho phần bị ẩn). */
        @media (max-width: 640px) {{
            .shooting-star:nth-child(n+17) {{ display: none; }}
        }}
        /* Ai bật "giảm chuyển động" trong máy (Reduce Motion / Giảm chuyển động) thì tắt hẳn
           các hoạt ảnh trang trí này — vừa nhẹ máy vừa đúng ý người dùng. */
        @media (prefers-reduced-motion: reduce) {{
            .stars-small, .stars-medium, .stars-large, .shooting-star, .moon {{ animation: none !important; }}
            .shooting-star {{ opacity: 0 !important; }}
        }}

        /* --- Mặt trăng: hình tròn vẽ bằng CSS (radial-gradient + vài "miệng hố" bằng
           box-shadow), có quầng sáng nhẹ nhàng lên xuống cho sinh động. --- */
        .moon {{
            position: fixed; top: 5vh; right: 8vw; width: 72px; height: 72px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 32%, #fffef4 0%, #fdf6d8 45%, #e9e0b0 75%, #d9d093 100%);
            animation: moonGlow 6s ease-in-out infinite;
        }}
        .moon::before, .moon::after {{
            content: ""; position: absolute; border-radius: 50%; background: rgba(120, 110, 70, 0.18);
        }}
        .moon::before {{ width: 16px; height: 16px; top: 13px; left: 15px; }}
        .moon::after {{
            width: 10px; height: 10px; top: 40px; left: 42px;
            box-shadow: -22px 6px 0 -2px rgba(120, 110, 70, 0.16);
        }}
        @keyframes moonGlow {{
            0%, 100% {{ box-shadow: 0 0 45px 12px rgba(255, 250, 224, 0.5), 0 0 90px 35px rgba(255, 250, 224, 0.2); }}
            50% {{ box-shadow: 0 0 55px 16px rgba(255, 250, 224, 0.7), 0 0 110px 42px rgba(255, 250, 224, 0.32); }}
        }}
        @media (max-width: 640px) {{
            .moon {{ width: 52px; height: 52px; top: 3vh; right: 6vw; }}
            .moon::before {{ width: 12px; height: 12px; top: 9px; left: 11px; }}
            .moon::after {{ width: 7px; height: 7px; top: 29px; left: 30px; box-shadow: -16px 4px 0 -2px rgba(120, 110, 70, 0.16); }}
        }}
    </style>
    <div class="starfield">
        <div class="moon"></div>
        <div class="stars-small"></div>
        <div class="stars-medium"></div>
        <div class="stars-large"></div>
        {SHOOTING_STARS_HTML}
    </div>
    """, unsafe_allow_html=True)
else:
    # --- Bầu trời ban ngày cho Chế độ sáng: mặt trời phát sáng + vài đám mây trôi nhẹ ---
    # đặt cùng vị trí với mặt trăng bên Chế độ tối cho hai giao diện "đối xứng" nhau.
    # Vị trí mây random nhẹ mỗi lần tải trang, cho đỡ nhàm khi ai cũng thấy y hệt nhau.
    _may = [
        (round(random.uniform(8, 16), 1), round(random.uniform(5, 25), 1), 22),
        (round(random.uniform(28, 40), 1), round(random.uniform(60, 80), 1), 26),
        (round(random.uniform(48, 60), 1), round(random.uniform(15, 35), 1), 18),
    ]
    CLOUDS_HTML = "".join(
        f'<div class="cloud" style="top:{top}vh; left:{left}vw; animation-delay:{-i * 4}s; '
        f'transform: scale({scale / 22});"></div>'
        for i, (top, left, scale) in enumerate(_may)
    )
    st.markdown(f"""
    <style>
        .daysky {{ position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }}

        /* --- Mặt trời: hình tròn vẽ bằng CSS, ánh sáng ấm, quầng sáng nhấp nháy nhẹ --- */
        .sun {{
            position: fixed; top: 5vh; right: 8vw; width: 72px; height: 72px;
            border-radius: 50%;
            background: radial-gradient(circle at 35% 32%, #fffdf2 0%, #ffe89b 40%, #ffc857 75%, #ffb347 100%);
            animation: sunGlow 5s ease-in-out infinite;
        }}
        @keyframes sunGlow {{
            0%, 100% {{ box-shadow: 0 0 45px 14px rgba(255, 200, 87, 0.45), 0 0 90px 38px rgba(255, 200, 87, 0.18); }}
            50% {{ box-shadow: 0 0 58px 18px rgba(255, 200, 87, 0.6), 0 0 110px 46px rgba(255, 200, 87, 0.28); }}
        }}
        @media (max-width: 640px) {{
            .sun {{ width: 52px; height: 52px; top: 3vh; right: 6vw; }}
        }}

        /* --- Mây trôi: 1 khối bo tròn + 2 "cục bông" (::before/::after) ghép lại --- */
        .cloud {{
            position: fixed; width: 90px; height: 32px; border-radius: 999px;
            background: #ffffff; opacity: 0.8;
            box-shadow: 0 6px 14px rgba(148, 163, 184, 0.18);
            animation: troiMay 22s ease-in-out infinite alternate;
        }}
        .cloud::before, .cloud::after {{
            content: ""; position: absolute; border-radius: 50%; background: #ffffff;
        }}
        .cloud::before {{ width: 46px; height: 46px; top: -22px; left: 10px; }}
        .cloud::after {{ width: 36px; height: 36px; top: -15px; left: 44px; }}
        @keyframes troiMay {{ from {{ transform: translateX(-16px); }} to {{ transform: translateX(16px); }} }}
        @media (prefers-reduced-motion: reduce) {{
            .sun, .cloud {{ animation: none !important; }}
        }}
    </style>
    <div class="daysky">
        <div class="sun"></div>
        {CLOUDS_HTML}
    </div>
    """, unsafe_allow_html=True)


AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#10b981", "#0ea5e9", "#eab308"]


def avatar_color(name):
    return AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]


def progress_pct(diem, diem_max):
    if diem_max is None or diem_max <= 0 or diem <= 0:
        return 0
    return max(0, min(100, round(diem / diem_max * 100)))


def badges_html(name, diem, diem_max, recent_map, extra_class=""):
    badges = compute_badges(recent_map.get(name, []), diem, diem_max)
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
# 5 TAB CHÍNH: Trang chủ / Thời khóa biểu / Tin tức / Cập nhật / Góp ý
# ---------------------------------------------------------------
tab_home, tab_tkb, tab_news, tab_update, tab_feedback = st.tabs(
    ["🏠 Trang chủ", "📅 Thời khóa biểu", "📰 Tin tức", "🆕 Cập nhật", "💬 Góp ý"]
)

# =================================================================
# TAB 1 — TRANG CHỦ (toàn bộ nội dung cũ: điểm, xếp hạng, form, v.v.)
# =================================================================
with tab_home:
    st.markdown(
        '<div class="hero">'
        '<div class="hero-title">🏆 Quản Lý Điểm Nhóm</div>'
        '<div class="hero-subtitle">Bảng xếp hạng điểm — cập nhật trực tiếp, mọi lúc mọi nơi</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # --- "Hôm nay học gì" — tự lấy từ tab Thời khóa biểu theo đúng thứ hôm nay (giờ Hà Nội) ---
    thu_hom_nay = _thu_hom_nay_ha_noi()
    tkb_now_df = load_thoikhoabieu_hien_tai()
    noi_dung_tkb_now = tkb_now_df.iloc[0]["noi_dung"] if not tkb_now_df.empty else TKB_MAC_DINH
    _, cac_ngay_hom_nay = _tach_dong_tkb(noi_dung_tkb_now)
    mon_hoc_hom_nay = next((mon for thu, mon in cac_ngay_hom_nay if thu == thu_hom_nay), None)

    if mon_hoc_hom_nay:
        st.markdown(
            '<div class="home-tkb-banner">'
            f'<div class="home-tkb-label">📅 Hôm nay ({html.escape(thu_hom_nay)}) học:</div>'
            f'<div class="home-tkb-text">{html.escape(mon_hoc_hom_nay)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="home-tkb-banner nghi">'
            f'<div class="home-tkb-label">📅 Hôm nay ({html.escape(thu_hom_nay)})</div>'
            '<div class="home-tkb-text">🎉 Không có lịch học trong Thời khóa biểu.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # --- Tin mới nhất (nếu Admin có đăng ở tab "📰 Tin tức") ---
    # Không đăng gì thì không hiện gì ở đây cả — trang chủ vẫn như bình thường.
    tin_moi_nhat = load_latest_news()
    if not tin_moi_nhat.empty:
        tin = tin_moi_nhat.iloc[0]
        thoi_gian_tin = tin["ngay"].strftime("%d/%m/%Y %H:%M") if pd.notna(tin["ngay"]) else ""
        st.markdown(
            '<div class="home-news-banner">'
            f'<div class="home-news-label">📰 Tin mới nhất — {thoi_gian_tin}</div>'
            f'<div class="home-news-text">{html.escape(tin["noi_dung"])}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    members_df = load_members()

    # --- Mã QR mở nhanh ---
    with st.expander("📱 Mã QR mở nhanh (để chia sẻ cho mọi người quét)"):
        st.image(
            make_qr_bytes(APP_URL),
            caption="Quét mã này bằng camera điện thoại để mở app ngay",
            width=200,
        )
        st.caption(APP_URL)

    # --- Lọc lịch sử theo khoảng thời gian ---
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

        muon_xuat_file = st.checkbox(
            "Chuẩn bị file để xuất (Excel / PDF) — chỉ tạo file khi bấm vào đây, giúp trang mở nhanh hơn",
            key="muon_xuat_file",
        )
        if muon_xuat_file:
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

    # --- Form Cộng / Trừ điểm (chỉ Admin) + Hoàn tác ---
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

    # --- Tìm kiếm + Sắp xếp + Bảng xếp hạng ---
    col_tim, col_sapxep = st.columns([2, 1.4])
    with col_tim:
        tu_khoa = st.text_input("🔍 Tìm thành viên:", placeholder="Nhập tên cần tìm...")
    with col_sapxep:
        sap_xep = st.radio(
            "Sắp xếp:",
            ["🏆 Theo điểm", "🔤 Theo tên (A-Z)"],
            horizontal=True,
            key="sap_xep_mode",
        )

    st.subheader("📋 Bảng xếp hạng")

    MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}

    if members_df.empty:
        st.info("Chưa có dữ liệu thành viên.")
    else:
        ranked = list(members_df.reset_index(drop=True).iterrows())
        diem_max = int(members_df["diem"].max())

        # Lấy sẵn lịch sử gần đây của TẤT CẢ thành viên trong 1 lượt truy vấn duy nhất
        # (thay vì mỗi thẻ xếp hạng tự hỏi database riêng) để trang mở nhanh hơn trên điện thoại,
        # và tránh làm hết chỗ (pool) kết nối database khi có nhiều thành viên / nhiều người xem
        # cùng lúc (đây là nguyên nhân gây lỗi "TimeoutError" trước đó).
        recent_all_df = load_recent_all(limit_per_member=10)
        recent_map = {}
        if not recent_all_df.empty:
            for ten_gr, grp in recent_all_df.groupby("ten", sort=False):
                recent_map[ten_gr] = grp["so_diem"].tolist()

        # Lấy sẵn TOÀN BỘ lịch sử (đã áp dụng lọc ngày nếu có) trong 1 lượt truy vấn duy nhất,
        # rồi chia theo từng thành viên — thay vì mỗi ô "Xem lịch sử" tự hỏi database riêng.
        all_hist_df = load_all_history(start_dt, end_dt)
        hist_by_member = {}
        if not all_hist_df.empty:
            for ten_h, grp in all_hist_df.groupby("Thành viên", sort=False):
                hist_by_member[ten_h] = grp.drop(columns=["Thành viên"])

        dang_az = sap_xep.startswith("🔤")

        if tu_khoa.strip() or dang_az:
            # --- Có tìm kiếm HOẶC chọn sắp xếp A-Z: bỏ podium, hiện danh sách phẳng
            # (thứ hạng 🥇🥈🥉/số hiển thị vẫn giữ đúng theo điểm gốc, chỉ thay đổi thứ tự hiện) ---
            loc = tu_khoa.strip().lower()
            if loc:
                ranked = [(idx, row) for idx, row in ranked if loc in str(row["name"]).lower()]
            if dang_az:
                ranked = sorted(ranked, key=lambda item: str(item[1]["name"]).lower())
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
                    f'{badges_html(ten, diem, diem_max, recent_map)}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                with st.expander(f"Xem lịch sử của {ten}"):
                    hist_df = hist_by_member.get(ten, pd.DataFrame())
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
                        f'{badges_html(ten, diem, diem_max, recent_map, "podium-badges")}'
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
                    f'{badges_html(ten, diem, diem_max, recent_map)}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                with st.expander(f"Xem lịch sử của {ten}"):
                    hist_df = hist_by_member.get(ten, pd.DataFrame())
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
                        hist_df = hist_by_member.get(ten, pd.DataFrame())
                        if not hist_df.empty:
                            st.dataframe(hist_df, use_container_width=True, hide_index=True)
                        else:
                            st.caption("Chưa có lịch sử cộng/trừ điểm.")

    # --- Nhật ký hoạt động chung ---
    if not members_df.empty:
        st.markdown("---")
        st.subheader("🗞️ Nhật ký hoạt động gần đây")
        recent_activity_df = load_recent_activity(limit=15)
        if recent_activity_df.empty:
            st.caption("Chưa có hoạt động cộng/trừ điểm nào.")
        else:
            st.dataframe(recent_activity_df, use_container_width=True, hide_index=True)

    # --- Xu hướng điểm ---
    if not members_df.empty:
        st.markdown("---")
        st.subheader("📈 Xu hướng điểm")
        hien_bieu_do = st.checkbox(
            "Hiện biểu đồ xu hướng (chỉ tải khi bấm vào đây, giúp trang mở nhanh hơn trên điện thoại)",
            key="hien_trend",
        )
        if hien_bieu_do:
            trend_options = ["Cả nhóm"] + members_df["name"].tolist()
            trend_pick = st.selectbox("Xem xu hướng của:", trend_options, key="trend_select")
            trend_df = load_trend_series(None if trend_pick == "Cả nhóm" else trend_pick)
            if trend_df.empty:
                st.caption("Chưa có dữ liệu để vẽ biểu đồ.")
            else:
                st.line_chart(trend_df)


# =================================================================
# TAB 2 — THỜI KHÓA BIỂU (chỉ Admin sửa được — ai cũng xem được)
#
# CÁCH ĐỔI THỜI KHÓA BIỂU NHANH GỌN — KHÔNG CẦN ĐỘNG VÀO CODE NỮA:
# đăng nhập Admin ở thanh bên → vào tab này → sửa thẳng trong khung chữ (vẫn theo
# đúng mẫu "Thứ 2: ...", mỗi thứ 1 dòng) → bấm "Lưu thời khóa biểu" là xong ngay,
# không cần vào GitHub, không cần dán code, không cần chờ Streamlit deploy lại gì cả.
# =================================================================
with tab_tkb:
    st.markdown(
        '<div class="tab-hero schedule">'
        '<div class="tab-hero-title">📅 Thời khóa biểu</div>'
        '<div class="tab-hero-subtitle">Lịch học trong tuần của lớp</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    tkb_hien_tai = load_thoikhoabieu_hien_tai()
    noi_dung_tkb_hien_tai = tkb_hien_tai.iloc[0]["noi_dung"] if not tkb_hien_tai.empty else TKB_MAC_DINH

    if is_admin:
        with st.expander("✏️ Sửa thời khóa biểu (chỉ Admin thấy mục này)"):
            st.caption(
                "Gõ mỗi thứ 1 dòng, theo mẫu **Thứ 2: Toán • Ngữ văn (2T)** — dấu chấm tròn "
                "\"•\" chỉ để cho đẹp, không bắt buộc, gõ dấu phẩy hay gạch ngang cũng được. "
                "Dòng đầu (tiêu đề) muốn ghi gì cũng được."
            )
            with st.form("form_sua_tkb"):
                noi_dung_tkb_moi = st.text_area(
                    "Nội dung thời khóa biểu:", value=noi_dung_tkb_hien_tai, height=260,
                )
                da_luu_tkb = st.form_submit_button("💾 Lưu thời khóa biểu", use_container_width=True)
                if da_luu_tkb:
                    if noi_dung_tkb_moi.strip():
                        add_thoikhoabieu(noi_dung_tkb_moi.strip())
                        st.success("Đã lưu thời khóa biểu mới!")
                        st.rerun()
                    else:
                        st.error("Nội dung không được để trống.")
        st.write("")

    cac_dong_dau, cac_ngay_hoc = _tach_dong_tkb(noi_dung_tkb_hien_tai)

    for dong in cac_dong_dau:
        st.markdown(f'<div class="tkb-tieu-de">{html.escape(dong)}</div>', unsafe_allow_html=True)

    if not cac_ngay_hoc:
        st.caption("Chưa có thời khóa biểu.")
    else:
        for thu, mon_hoc in cac_ngay_hoc:
            st.markdown(
                '<div class="tkb-dong">'
                f'<div class="tkb-thu">{html.escape(thu)}</div>'
                f'<div class="tkb-mon">{html.escape(mon_hoc)}</div>'
                '</div>',
                unsafe_allow_html=True,
            )


# =================================================================
# TAB 3 — TIN TỨC (chỉ Admin đăng/xoá được — ai cũng xem được)
# =================================================================
with tab_news:
    st.markdown(
        '<div class="tab-hero news">'
        '<div class="tab-hero-title">📰 Tin tức</div>'
        '<div class="tab-hero-subtitle">Thông báo từ Admin cho cả nhóm</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if is_admin:
        with st.form("form_dang_tin", clear_on_submit=True):
            noi_dung_tin = st.text_area("Viết tin mới:", placeholder="Nhập nội dung thông báo...")
            da_dang_tin = st.form_submit_button("📰 Đăng tin", use_container_width=True)
            if da_dang_tin:
                if noi_dung_tin.strip():
                    add_news(noi_dung_tin.strip())
                    st.success("Đã đăng tin!")
                    st.rerun()
                else:
                    st.error("Vui lòng nhập nội dung tin.")
        st.write("")

    news_df = load_news()
    if news_df.empty:
        st.caption("Chưa có tin tức nào.")
    else:
        for _, tin in news_df.iterrows():
            thoi_gian = tin["ngay"].strftime("%d/%m/%Y %H:%M") if pd.notna(tin["ngay"]) else ""
            card_html = (
                f'<div class="news-item"><div class="news-item-date">{thoi_gian}</div>'
                f'<div class="news-item-text">{html.escape(tin["noi_dung"])}</div></div>'
            )
            if is_admin:
                col_tin, col_xoa = st.columns([6, 1])
                with col_tin:
                    st.markdown(card_html, unsafe_allow_html=True)
                with col_xoa:
                    if st.button("🗑️", key=f"del_news_{tin['id']}", help="Xoá tin này"):
                        delete_news(int(tin["id"]))
                        st.rerun()
            else:
                st.markdown(card_html, unsafe_allow_html=True)


# =================================================================
# TAB 4 — CẬP NHẬT (nhật ký các tính năng mới của web)
# =================================================================
with tab_update:
    st.markdown(
        '<div class="tab-hero update">'
        '<div class="tab-hero-title">🆕 Cập nhật mới nhất trên web</div>'
        '<div class="tab-hero-subtitle">Mỗi khi web có tính năng mới, thông tin sẽ được thêm vào đây</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    for i, (ngay_cn, noi_dung_cn) in enumerate(UPDATES):
        moi_nhat = ' <span class="badge-chip update-badge">Mới nhất</span>' if i == 0 else ""
        st.markdown(
            f'<div class="update-item"><div class="update-date">{ngay_cn}{moi_nhat}</div>'
            f'<div class="update-desc">{noi_dung_cn}</div></div>',
            unsafe_allow_html=True,
        )


# =================================================================
# TAB 5 — GÓP Ý (công khai gửi, chỉ Admin đọc — ở sidebar)
# =================================================================
with tab_feedback:
    st.markdown(
        '<div class="tab-hero feedback">'
        '<div class="tab-hero-title">💬 Góp ý cho nhóm</div>'
        '<div class="tab-hero-subtitle">Góp ý của bạn chỉ Admin đọc được, không hiển thị công khai cho người khác xem</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    with st.form("form_gop_y", clear_on_submit=True):
        nguoi_gui_fb = st.text_input("Tên bạn (để trống nếu muốn ẩn danh):")
        noi_dung_fb = st.text_area("Nội dung góp ý:")
        da_gui = st.form_submit_button("📨 Gửi góp ý", use_container_width=True)
        if da_gui:
            if noi_dung_fb.strip():
                add_feedback(nguoi_gui_fb.strip() or "Ẩn danh", noi_dung_fb.strip())
                st.success("Cảm ơn bạn đã góp ý!")
            else:
                st.error("Vui lòng nhập nội dung góp ý.")
