import html
import io
import math
import random
import re
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import qrcode
import requests
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
    ("17/09/2026", "➕➖ Mục \"Xem lịch sử\" của mỗi thành viên giờ có thêm 2 ô tổng kết ngay phía trên bảng: tổng số điểm ĐƯỢC CỘNG và tổng số điểm BỊ TRỪ (kèm số lần), khỏi cần tự cộng trừ từng dòng nữa."),
    ("17/09/2026", "🌦️ Mưa/giông bão chân thật hơn: mưa giờ có 2 lớp hạt (gần to rõ, xa nhỏ mờ) nhìn có chiều sâu hơn hẳn; trời mưa thì mây dày + xám đậm hơn, mặt trời mờ hẳn xuống, và tắt luôn nhật thực (mưa mù thì làm sao thấy được); riêng lúc GIÔNG BÃO còn tối hơn nữa, mây đen kịt và có chớp sét lóe sáng đều 20 lần/phút."),
    ("17/09/2026", "☀️ Nhật thực giờ vào trang chỉ 2 giây là bắt đầu che luôn (khỏi phải đợi lâu mới thấy), rồi tự chuyển động liên tục không dừng khựng giữa chừng: 2 phút che vào, 2 phút che ra, 2 phút nắng đẹp, rồi lặp lại đều đặn — đĩa che tròn y hệt mặt trăng, khuyết dần từ bên phải, che kín đúng khoảnh khắc thì lóe vành nhật hoa lên và cả bầu trời tối sầm như Chế độ tối, rồi đi tiếp luôn để sáng dần trở lại cũng từ bên phải (không quay đầu, giống mặt trăng thật đi ngang qua một lượt)."),
    ("16/09/2026", "🌌 Dải Ngân Hà (Chế độ tối) giờ hiện nhiều ngày hơn: Thứ 6, Thứ 7, Chủ Nhật và Thứ 2 — thay vì chỉ mỗi Thứ 2 như trước."),
    ("16/09/2026", "🔧 Sửa lỗi hiện chữ/code rối mắt phía trên thanh tab (do phần code vẽ dải Ngân Hà gây ra) — cảm ơn mọi người đã báo lỗi, giờ web hiện bình thường lại rồi."),
    ("16/09/2026", "🌌 Mỗi ngày trong tuần Chế độ tối có 1 hiện tượng thiên văn riêng: Thứ 2 là dải Ngân Hà sáng rực cả vùng trời, Thứ 4/6/CN là sao chổi (đầu sáng + đuôi dài ánh xanh, bay chậm và hiếm hơn), các ngày còn lại vẫn là sao băng như cũ. Chế độ sáng thì thêm nhật thực: cứ 5 phút web mở là có 3 phút mặt trăng che mặt trời rồi lại sáng ra, lặp lại đều đặn — tất cả đều vẽ bằng CSS thuần, không cần JavaScript nên điện thoại yếu vẫn chạy mượt."),
    ("16/09/2026", "🌙 Mặt trăng (Chế độ tối) giờ đổi hình dạng dần mỗi ngày theo đúng chu kỳ trăng thật (~29,5 ngày) thay vì luôn tròn y hệt. Mây/nắng/mưa (cả 2 chế độ) giờ cập nhật theo thời tiết THẬT ở Mỹ Tho, Tiền Giang (lấy miễn phí từ Open-Meteo, 30 phút mới gọi lại 1 lần nên không ảnh hưởng tốc độ): trời quang thì như cũ, nhiều mây thì mây dày/xám hơn và mặt trời/bầu trời sao mờ bớt, có mưa thì thêm hiệu ứng mưa rơi nhẹ nhàng bằng CSS (không dùng JavaScript nên điện thoại yếu vẫn mượt). Lỡ không lấy được thời tiết thì web tự quay về mây ngẫu nhiên như bản cũ, không lỗi gì cả."),
    ("16/09/2026", "🗣️ Admin giờ trả lời góp ý công khai được rồi: vào Hộp góp ý ở thanh bên → gõ câu trả lời ngay dưới góp ý đó → Lưu. Câu trả lời hiện ngay ở tab Góp ý cho mọi người xem (mục \"Admin đã trả lời\"), nhưng KHÔNG hiện tên người đã gửi góp ý — vẫn giữ ẩn danh như trước."),
    ("16/09/2026", "🎨 Làm đẹp lại giao diện bảng xếp hạng/thẻ thành viên: đổi font chữ mới (Be Vietnam Pro, rõ dấu tiếng Việt hơn), thẻ xếp hạng có viền màu riêng theo từng người, số hạng đổi thành khung tròn, điểm số có mũi tên ▲▼ tăng/giảm, bục top 3 có ánh sáng lướt nhẹ ở hạng Nhất, thẻ hiện lần lượt mượt mà khi tải trang, nút bấm/tab có hiệu ứng nhấn nhẹ khi rê chuột."),
    ("16/09/2026", "⏳ Thêm mục \"Đếm ngược lịch thi/kiểm tra\" ngay trong tab Thời khóa biểu — Admin bấm \"➕ Thêm lịch thi\", gõ tên bài thi + chọn ngày là xong, không cần vào GitHub. Web tự đếm ngược \"Còn X ngày nữa\" cho mọi người xem, đến sát ngày thì đổi thành \"Ngày mai!\" rồi \"🔥 Hôm nay!\" cho dễ chú ý, bài thi nào qua ngày rồi thì tự động biến mất khỏi danh sách. Lịch thi gần nhất còn hiện ngay banner trên Trang chủ luôn, khỏi cần bấm vào tab mới thấy."),
    ("15/09/2026", "📅 Banner \"Hôm nay học gì\" trên Trang chủ giờ thông minh hơn: sau 11h45 sáng (buổi học đã xong) tự động chuyển sang hiện lịch của NGÀY MAI luôn, để chuẩn bị trước cho hôm sau thay vì cứ hiện lịch hôm nay đã học xong."),
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
        # Thêm cột trả lời công khai vào bảng feedback đã có sẵn (ALTER an toàn — không mất
        # dữ liệu góp ý cũ, chỉ thêm cột mới nếu chưa có).
        s.execute(text("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS phan_hoi TEXT"))
        s.execute(text("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS ngay_phan_hoi TIMESTAMP"))
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
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS lich_thi (
                id SERIAL PRIMARY KEY,
                tieu_de TEXT NOT NULL,
                ngay_thi DATE NOT NULL,
                ghi_chu TEXT,
                ngay_dang TIMESTAMP NOT NULL DEFAULT now()
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
    """Chỉ Admin gọi hàm này để đọc góp ý (kèm cả trả lời nếu có) — tên người gửi không
    hiển thị công khai ở đâu khác."""
    return conn.query(
        'SELECT id, nguoi_gui, noi_dung, ngay, phan_hoi, ngay_phan_hoi FROM feedback ORDER BY ngay DESC', ttl=0,
    )


def delete_feedback(feedback_id):
    with conn.session as s:
        s.execute(text("DELETE FROM feedback WHERE id = :id"), {"id": feedback_id})
        s.commit()


def luu_phan_hoi_feedback(feedback_id, phan_hoi):
    """Chỉ Admin mới gọi hàm này (đã kiểm tra is_admin trước khi gọi). Lưu/ghi đè câu trả lời
    công khai cho 1 góp ý — không lưu tên người gửi kèm câu trả lời để giữ ẩn danh."""
    with conn.session as s:
        s.execute(
            text("UPDATE feedback SET phan_hoi = :ph, ngay_phan_hoi = now() WHERE id = :id"),
            {"ph": phan_hoi or None, "id": feedback_id},
        )
        s.commit()


def load_feedback_da_tra_loi():
    """Các góp ý ĐÃ có Admin trả lời — hiện công khai cho mọi người xem, KHÔNG kèm tên
    người gửi để giữ ẩn danh. Trả lời mới nhất lên đầu."""
    return conn.query(
        "SELECT id, noi_dung, phan_hoi, ngay_phan_hoi FROM feedback "
        "WHERE phan_hoi IS NOT NULL AND phan_hoi != '' ORDER BY ngay_phan_hoi DESC",
        ttl=0,
    )


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


def add_lich_thi(tieu_de, ngay_thi, ghi_chu):
    """Chỉ Admin mới gọi hàm này (đã kiểm tra is_admin trước khi gọi)."""
    with conn.session as s:
        s.execute(
            text("INSERT INTO lich_thi (tieu_de, ngay_thi, ghi_chu) VALUES (:td, :nt, :gc)"),
            {"td": tieu_de, "nt": ngay_thi, "gc": ghi_chu or None},
        )
        s.commit()


def load_lich_thi_sap_toi():
    """Chỉ lấy các mốc thi từ HÔM NAY (giờ Hà Nội) trở đi — cái nào qua rồi tự động không
    hiện nữa nữa, khỏi cần Admin nhớ vào xoá. Sắp xếp gần nhất lên đầu."""
    hom_nay = datetime.now(GIO_HA_NOI).date()
    return conn.query(
        "SELECT id, tieu_de, ngay_thi, ghi_chu FROM lich_thi WHERE ngay_thi >= :hn ORDER BY ngay_thi ASC",
        params={"hn": hom_nay}, ttl=0,
    )


def load_lich_thi_da_qua():
    """Các mốc thi đã qua ngày — chỉ để Admin xem lại/dọn dẹp nếu muốn, người thường không thấy."""
    hom_nay = datetime.now(GIO_HA_NOI).date()
    return conn.query(
        "SELECT id, tieu_de, ngay_thi, ghi_chu FROM lich_thi WHERE ngay_thi < :hn ORDER BY ngay_thi DESC",
        params={"hn": hom_nay}, ttl=0,
    )


def delete_lich_thi(id_):
    with conn.session as s:
        s.execute(text("DELETE FROM lich_thi WHERE id = :id"), {"id": id_})
        s.commit()


def _chuan_hoa_ngay(gia_tri):
    """Cột DATE trong Postgres tùy driver có lúc trả về datetime.date, có lúc trả về
    Timestamp/datetime — chuẩn hóa về date để so sánh/định dạng cho chắc ăn."""
    if isinstance(gia_tri, datetime):
        return gia_tri.date()
    return gia_tri


def _dem_nguoc_lich_thi(ngay_thi):
    """Trả về dòng chữ đếm ngược, ví dụ 'Còn 3 ngày nữa', tính theo NGÀY hôm nay ở Hà Nội
    (không tính giờ phút) — nên dù xem lúc nào trong ngày thi thì vẫn hiện đúng 'Hôm nay!'."""
    hom_nay = datetime.now(GIO_HA_NOI).date()
    so_ngay = (_chuan_hoa_ngay(ngay_thi) - hom_nay).days
    if so_ngay == 0:
        return "🔥 Hôm nay!"
    if so_ngay == 1:
        return "⏰ Ngày mai!"
    return f"Còn {so_ngay} ngày nữa"


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

GIO_CHUYEN_SANG_NGAY_MAI = (11, 45)  # (giờ, phút) — qua mốc này là buổi học sáng đã xong


def _ngay_hien_thi_tkb_ha_noi():
    """Trước 11h45: hiện lịch của HÔM NAY. Từ 11h45 trở đi (buổi sáng đã học xong, cần chuẩn bị
    cho hôm sau): tự chuyển sang hiện lịch của NGÀY MAI. Trả về (nhãn, "Thứ x"/"CN" của ngày đó)."""
    bay_gio = datetime.now(GIO_HA_NOI)
    gio_ct, phut_ct = GIO_CHUYEN_SANG_NGAY_MAI
    if (bay_gio.hour, bay_gio.minute) >= (gio_ct, phut_ct):
        ngay_hien_thi = bay_gio + timedelta(days=1)
        nhan = "Ngày mai"
    else:
        ngay_hien_thi = bay_gio
        nhan = "Hôm nay"
    return nhan, _TEN_THU_VN[ngay_hien_thi.weekday()]


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


# ---------------------------------------------------------------
# THỜI TIẾT MỸ THO, TIỀN GIANG — lấy từ Open-Meteo (miễn phí, không cần đăng ký API key)
# để mây/nắng/mưa trên giao diện đổi theo thời tiết THẬT ngoài đời, thay vì chỉ random.
# ---------------------------------------------------------------
TOA_DO_MY_THO = (10.35806, 106.36417)  # Mỹ Tho, Tiền Giang


@st.cache_data(ttl=1800, show_spinner=False)
def lay_thoi_tiet_my_tho():
    """Gọi Open-Meteo lấy thời tiết hiện tại ở Mỹ Tho. Cache 30 phút — nhiều người mở web
    cùng lúc cũng chỉ tốn 1 lượt gọi mạng, không ảnh hưởng tốc độ tải trang.
    Lỡ mạng lỗi/API sập thì trả về None một cách âm thầm — web tự chuyển sang mây ngẫu nhiên
    như trước, KHÔNG hiện lỗi gì cho người dùng thấy (đây chỉ là hiệu ứng trang trí)."""
    try:
        lat, lon = TOA_DO_MY_THO
        res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": "weather_code", "timezone": "Asia/Bangkok"},
            timeout=4,
        )
        res.raise_for_status()
        ma = res.json()["current"]["weather_code"]
        return _phan_loai_thoi_tiet(ma)
    except Exception:
        return None


def _phan_loai_thoi_tiet(ma):
    """Quy đổi mã thời tiết WMO của Open-Meteo về 4 nhóm đơn giản để vẽ giao diện."""
    if ma == 0:
        return "nang"
    if ma in (95, 96, 99):
        return "mua_to"  # giông/sấm sét
    if ma >= 51:  # mưa phùn, mưa, mưa rào, tuyết... đều tính là có mưa
        return "mua"
    return "may"  # 1-3 (ít mây/nhiều mây), 45/48 (sương mù)


TRANG_THAI_THOI_TIET = lay_thoi_tiet_my_tho()  # None nếu không lấy được -> dùng mây ngẫu nhiên
DANG_MUA = TRANG_THAI_THOI_TIET in ("mua", "mua_to")


def pha_mat_trang(ngay):
    """Mặt trăng đổi hình dạng dần theo chu kỳ trăng thật (~29.53 ngày), tính từ 1 mốc
    trăng non đã biết (6/1/2000). Trả về số 0..1 (0 = trăng non, 0.5 = trăng tròn)."""
    tham_chieu = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    so_ngay = (ngay - tham_chieu).total_seconds() / 86400
    chu_ky = 29.530588853
    return (so_ngay % chu_ky) / chu_ky


_TEN_HIEN_TUONG_THEO_THU = {
    0: "ngan_ha",   # Thứ 2 — dải Ngân Hà sáng rực cả vùng trời
    1: "sao_bang",  # Thứ 3
    2: "sao_choi",  # Thứ 4
    3: "sao_bang",  # Thứ 5
    4: "ngan_ha",   # Thứ 6 — dải Ngân Hà sáng rực cả vùng trời
    5: "ngan_ha",   # Thứ 7 — dải Ngân Hà sáng rực cả vùng trời
    6: "ngan_ha",   # CN — dải Ngân Hà sáng rực cả vùng trời
}


def hien_tuong_thien_van_hom_nay():
    """Mỗi ngày trong tuần có 1 hiện tượng thiên văn riêng cho Chế độ tối — đổi đều đặn
    theo thứ trong tuần (giờ Hà Nội), ai mở web cùng ngày cũng thấy giống nhau:
    Thứ 2 = dải Ngân Hà, các ngày còn lại xen kẽ sao băng / sao chổi."""
    return _TEN_HIEN_TUONG_THEO_THU[datetime.now(GIO_HA_NOI).weekday()]


def _make_starfield_html(hien_tuong):
    """Tạo nền bầu trời sao cho Chế độ tối: các chấm sao lấp lánh (kỹ thuật box-shadow,
    không cần JavaScript) + hiện tượng thiên văn riêng của ngày hôm đó (sao băng / sao chổi
    — dải Ngân Hà thì vẽ riêng bằng CSS, không cần HTML sinh ra ở đây).

    LƯU Ý HIỆU NĂNG: bản trước dùng 235 chấm sao + 60 sao băng chạy hoạt ảnh liên tục,
    trên điện thoại yếu (CPU/GPU chậm) sẽ khiến trang tải/cuộn ì. Đã giảm bớt số lượng
    xuống mức vừa phải (vẫn đẹp, vẫn có bầu trời sao + hiệu ứng bay) để nhẹ máy hơn hẳn —
    nếu máy vẫn yếu, có thể giảm thêm các số ở đây."""

    def _dots(n):
        return ", ".join(
            f"{round(random.uniform(0, 100), 2)}vw {round(random.uniform(0, 100), 2)}vh #fff"
            for _ in range(n)
        )

    stars_small, stars_medium, stars_large = _dots(70), _dots(30), _dots(12)

    if hien_tuong == "sao_choi":
        # Sao chổi: hiếm hơn sao băng hẳn (chỉ vài lần/phút), bay chậm và "nặng ký" hơn,
        # có đầu sáng rực + đuôi dài ánh xanh — khác hẳn vệt sao băng mảnh, nhanh, trắng.
        SO_SAO_CHOI = 4
        hien_tuong_html = "".join(
            '<div class="comet" style="top:{top}vh; left:{left}vw; animation-delay:{delay}s;"></div>'.format(
                top=round(random.uniform(4, 45), 1),
                left=round(random.uniform(20, 95), 1),
                delay=round(i * (90 / SO_SAO_CHOI), 2),
            )
            for i in range(SO_SAO_CHOI)
        )
    else:
        # Mặc định (kể cả ngày dải Ngân Hà): vẫn có sao băng như cũ, dải Ngân Hà sẽ vẽ
        # chồng thêm lên bên trên chứ không thay thế sao băng.
        SO_SAO_BANG = 24  # số sao băng/phút — chỉnh số này để dày/thưa hơn (càng cao càng tốn máy)
        hien_tuong_html = "".join(
            '<div class="shooting-star" style="top:{top}vh; left:{left}vw; animation-delay:{delay}s;"></div>'.format(
                top=round(random.uniform(2, 55), 1),
                left=round(random.uniform(15, 95), 1),
                delay=round(i * (60 / SO_SAO_BANG), 2),
            )
            for i in range(SO_SAO_BANG)
        )
    return stars_small, stars_medium, stars_large, hien_tuong_html


if dark_mode:
    HIEN_TUONG_DEM = hien_tuong_thien_van_hom_nay()
    ST_SMALL, ST_MEDIUM, ST_LARGE, HIEN_TUONG_HTML = _make_starfield_html(HIEN_TUONG_DEM)
    DANG_CO_NGAN_HA = HIEN_TUONG_DEM == "ngan_ha"
    NGAN_HA_HTML = '<div class="ngan-ha"></div>' if DANG_CO_NGAN_HA else ''

# ---------------------------------------------------------------
# CSS — giao diện
# ---------------------------------------------------------------
st.markdown(f"""
<style>
    /* --- Font chữ đẹp hơn, hỗ trợ tiếng Việt có dấu rõ nét (Be Vietnam Pro) --- */
    @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Be Vietnam Pro', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }}

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

    /* --- Thẻ đếm ngược lịch thi/kiểm tra --- */
    .lich-thi-tieu-de {{
        font-weight: 800; color: {C_TEXT}; font-size: 1rem; margin: 22px 0 12px 0;
    }}
    .lich-thi-the {{
        display: flex; align-items: center; justify-content: space-between; gap: 14px;
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-left: 4px solid #ef4444;
        border-radius: 12px; padding: 14px 18px; margin-bottom: 10px;
        animation: fadeInUp 0.4s ease both;
    }}
    .lich-thi-the.sap-toi {{ border-left: 4px solid #f59e0b; }}
    .lich-thi-the.hom-nay {{ border-left: 4px solid #ef4444; animation: goldGlow 1.8s ease-in-out infinite; }}
    .lich-thi-thong-tin {{ flex: 1 1 auto; min-width: 0; }}
    .lich-thi-ten {{ font-weight: 800; color: {C_TEXT}; font-size: 0.98rem; line-height: 1.4; }}
    .lich-thi-ngay {{ color: {C_MUTED}; font-size: 0.82rem; margin-top: 2px; }}
    .lich-thi-ghichu {{ color: {C_MUTED}; font-size: 0.85rem; margin-top: 4px; line-height: 1.4; white-space: pre-wrap; }}
    .lich-thi-dem-nguoc {{
        flex: 0 0 auto; text-align: center;
        background: linear-gradient(135deg, #ef4444, #f97316); color: white;
        font-weight: 800; font-size: 0.82rem; border-radius: 999px; padding: 7px 16px;
        white-space: nowrap;
    }}

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

    /* --- Banner "Lịch thi gần nhất" trên Trang chủ --- */
    .home-examen-banner {{
        display: flex; align-items: center; justify-content: space-between; gap: 14px;
        background: linear-gradient(135deg, #ef4444 0%, #f97316 100%);
        border-radius: 14px; padding: 14px 20px; margin-bottom: 20px; color: white;
        box-shadow: 0 6px 16px rgba(239, 68, 68, 0.25);
        animation: fadeInUp 0.4s ease both;
    }}
    .home-examen-banner.hom-nay {{ animation: fadeInUp 0.4s ease both, goldGlow 1.8s ease-in-out infinite; }}
    .home-examen-label {{ font-size: 0.72rem; font-weight: 800; text-transform: uppercase; opacity: 0.85; letter-spacing: 0.03em; }}
    .home-examen-text {{ font-size: 1rem; font-weight: 600; margin-top: 4px; line-height: 1.5; }}
    .home-examen-dem-nguoc {{
        flex: 0 0 auto; text-align: center; background: rgba(255, 255, 255, 0.22);
        font-weight: 800; font-size: 0.85rem; border-radius: 999px; padding: 8px 18px;
        white-space: nowrap;
    }}

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

    /* --- Góp ý đã được Admin trả lời công khai (ẩn danh người gửi) --- */
    .qa-tieu-de {{
        font-weight: 800; color: {C_TEXT}; font-size: 1rem; margin: 26px 0 12px 0;
    }}
    .qa-the {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-left: 4px solid #10b981;
        border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;
        animation: fadeInUp 0.4s ease both;
    }}
    .qa-cauhoi {{ color: {C_TEXT}; font-size: 0.92rem; line-height: 1.5; white-space: pre-wrap; }}
    .qa-cauhoi-nhan {{ font-weight: 800; color: {C_MUTED}; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; }}
    .qa-tra-loi-wrap {{
        margin-top: 10px; padding: 10px 14px; border-radius: 10px;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(14, 165, 233, 0.1));
    }}
    .qa-tra-loi-nhan {{ font-weight: 800; color: #0ea5e9; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.03em; }}
    .qa-tra-loi {{ color: {C_TEXT}; font-size: 0.92rem; margin-top: 3px; line-height: 1.5; white-space: pre-wrap; }}

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
        position: relative; overflow: hidden;
        flex: 1; max-width: 220px; border-radius: 16px 16px 6px 6px; padding: 14px 10px 18px;
        text-align: center; color: white; box-shadow: 0 6px 16px rgba(0,0,0,0.12);
        animation: fadeInUp 0.5s ease both;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .podium-block:hover {{ transform: translateY(-6px) scale(1.03); box-shadow: 0 12px 26px rgba(0,0,0,0.18); }}
    .podium-block.gold {{
        background: linear-gradient(180deg,#fde68a,#f59e0b); height: 200px; order: 2;
        animation: fadeInUp 0.5s ease both, goldGlow 2.4s ease-in-out infinite;
    }}
    .podium-block.silver {{ background: linear-gradient(180deg,#e5e7eb,#94a3b8); height: 160px; order: 1; }}
    .podium-block.bronze {{ background: linear-gradient(180deg,#fed7aa,#fb923c); height: 140px; order: 3; }}
    /* Ánh sáng lướt qua bục hạng Nhất cho lấp lánh nhẹ, không gây rối mắt */
    .podium-block.gold::after {{
        content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%;
        background: linear-gradient(120deg, transparent, rgba(255,255,255,0.55), transparent);
        transform: skewX(-20deg); animation: shine 3.2s ease-in-out infinite;
    }}
    @keyframes shine {{
        0% {{ left: -60%; }}
        45%, 100% {{ left: 130%; }}
    }}
    .podium-medal {{ font-size: 2rem; line-height: 1; filter: drop-shadow(0 2px 3px rgba(0,0,0,0.15)); }}
    .podium-avatar {{
        width: 52px; height: 52px; border-radius: 50%; background: rgba(255,255,255,0.3);
        display: flex; align-items: center; justify-content: center; font-weight: 800;
        font-size: 1.2rem; margin: 6px auto; border: 2px solid rgba(255,255,255,0.8);
        box-shadow: 0 0 0 4px rgba(255,255,255,0.2);
    }}
    .podium-name {{ font-weight: 800; font-size: 1rem; margin-top: 2px; word-break: break-word; }}
    .podium-score {{ font-weight: 800; font-size: 1.05rem; margin-top: 4px; }}

    /* --- Thẻ xếp hạng (hạng 4 trở đi, hoặc khi tìm kiếm) --- */
    .rank-card {{
        background: {C_CARD}; border: 1px solid {C_BORDER}; border-left: 4px solid var(--diem-mau, {C_BORDER});
        border-radius: 14px;
        padding: 14px 20px; margin-bottom: 10px; box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        animation: fadeInUp 0.4s ease both;
    }}
    .rank-card:hover {{ transform: translateY(-2px) scale(1.005); box-shadow: 0 8px 20px rgba(16, 24, 40, 0.1); }}
    .rank-card-top {{ display: flex; align-items: center; gap: 16px; }}

    .rank-badge {{
        width: 32px; height: 32px; min-width: 32px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        background: {C_TRACK}; font-size: 0.95rem; font-weight: 800; color: {C_MUTED};
    }}

    .avatar {{
        width: 42px; height: 42px; min-width: 42px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-weight: 800; font-size: 1rem; color: white;
        box-shadow: 0 0 0 3px {C_CARD}, 0 0 0 4px var(--diem-mau, transparent);
    }}

    .member-name {{ flex: 1; font-size: 1.05rem; font-weight: 600; color: {C_TEXT}; }}

    .score-pill {{
        display: inline-flex; align-items: center; gap: 4px;
        padding: 6px 16px; border-radius: 999px; font-weight: 800; font-size: 0.95rem; white-space: nowrap;
    }}
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
        display: inline-block; background: linear-gradient(135deg, #eef2ff, #e0e7ff); color: #4338ca;
        border-radius: 999px; box-shadow: 0 1px 2px rgba(67, 56, 202, 0.15);
        padding: 3px 10px; font-size: 0.72rem; font-weight: 700; margin: 3px 4px 0 0;
        transition: transform 0.15s ease;
    }}
    .badge-chip:hover {{ transform: translateY(-1px) scale(1.04); }}
    .podium-badges {{ margin-top: 6px; }}
    .podium-badges .badge-chip {{ background: rgba(255,255,255,0.28); color: #ffffff; box-shadow: none; }}

    div[data-testid="stExpander"] {{
        border: 1px solid {C_BORDER}; border-radius: 14px; overflow: hidden; background: {C_CARD};
    }}
    div[data-testid="stExpander"] summary {{ background-color: {C_CARD} !important; color: {C_TEXT} !important; }}
    button[kind="secondary"], button[kind="primary"], [data-testid^="stBaseButton"] {{ border-radius: 10px !important; }}
    .stButton button, .stDownloadButton button, [data-testid="stFormSubmitButton"] button {{
        background-color: {C_CARD}; color: {C_TEXT}; border: 1px solid {C_BORDER};
        transition: transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease;
    }}
    .stButton button:hover, .stDownloadButton button:hover, [data-testid="stFormSubmitButton"] button:hover {{
        transform: translateY(-1px); border-color: #8b5cf6;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.18);
    }}
    .stButton button:active, .stDownloadButton button:active, [data-testid="stFormSubmitButton"] button:active {{
        transform: translateY(0); box-shadow: none;
    }}

    /* --- Tab "Trang chủ" / "Cập nhật" dạng viên thuốc (pill) --- */
    [data-testid="stTab"] {{
        font-weight: 700; font-size: 1.02rem; border-radius: 999px !important;
        padding: 6px 20px !important; transition: background 0.2s ease, color 0.2s ease, transform 0.15s ease;
        cursor: pointer; color: {C_TEXT};
    }}
    [data-testid="stTab"] p {{ color: inherit; }}
    [data-testid="stTab"]:hover:not([aria-selected="true"]) {{
        background: {C_TRACK}; transform: translateY(-1px);
    }}
    [data-testid="stTab"][aria-selected="true"] {{
        background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
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
#
# CẬP NHẬT THEO THỜI TIẾT THẬT: mặt trăng đổi hình dạng dần mỗi ngày theo đúng chu kỳ trăng
# (~29,5 ngày, tính toán trong pha_mat_trang() — không cần gọi mạng). Bầu trời sao còn mờ đi
# nếu Mỹ Tho đang nhiều mây/mưa thật ngoài đời (lấy 1 lần/30 phút từ Open-Meteo, xem
# lay_thoi_tiet_my_tho() ở trên) — lỡ không lấy được thời tiết thì bầu trời vẫn hiện bình
# thường như cũ, không có gì thay đổi.
if dark_mode:
    pha_trang_hien_tai = pha_mat_trang(datetime.now(GIO_HA_NOI))
    DO_LECH_TRANG = round(50 * (1 - math.cos(2 * math.pi * pha_trang_hien_tai)), 1)  # 0..100%

    if TRANG_THAI_THOI_TIET in ("mua", "mua_to"):
        DO_MO_BAU_TROI = 0.32
    elif TRANG_THAI_THOI_TIET == "may":
        DO_MO_BAU_TROI = 0.6
    else:
        DO_MO_BAU_TROI = 1.0  # nắng, hoặc không lấy được thời tiết -> hiện như cũ

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
            .stars-small, .stars-medium, .stars-large, .shooting-star, .comet, .moon {{ animation: none !important; }}
            .shooting-star, .comet {{ opacity: 0 !important; }}
            .ngan-ha {{ animation: none !important; opacity: 0.6 !important; }}
        }}

        /* --- Sao chổi: hiện tượng riêng của Thứ 4/6/CN — đầu sáng rực + đuôi dài ánh xanh,
           bay chậm và hiếm hơn hẳn sao băng để cảm giác "đặc biệt" hơn. --- */
        .comet {{
            position: fixed; width: 220px; height: 3px; border-radius: 999px;
            background: linear-gradient(90deg, rgba(186,230,253,0.95), rgba(186,230,253,0));
            opacity: 0; transform: rotate(-28deg); animation: bay-sao-choi 90s ease-in infinite;
            will-change: opacity, transform;
        }}
        .comet::before {{
            content: ""; position: absolute; left: -3px; top: 50%; width: 9px; height: 9px;
            transform: translateY(-50%); border-radius: 50%;
            background: radial-gradient(circle, #ffffff 0%, #bae6fd 55%, transparent 100%);
            box-shadow: 0 0 12px 4px rgba(186,230,253,0.85);
        }}
        @keyframes bay-sao-choi {{
            0%, 93% {{ opacity: 0; transform: translate(0, 0) rotate(-28deg); }}
            94% {{ opacity: 1; }}
            98% {{ opacity: 1; transform: translate(-460px, 260px) rotate(-28deg); }}
            100% {{ opacity: 0; transform: translate(-500px, 285px) rotate(-28deg); }}
        }}
        @media (max-width: 640px) {{
            .comet {{ width: 150px; }}
        }}

        /* --- Dải Ngân Hà: chỉ hiện riêng vào Thứ 2, 1 dải sáng mờ chéo qua bầu trời, sáng mờ
           dần lên xuống nhẹ nhàng — chỉ 1 lớp phủ (không sinh nhiều phần tử) nên vẫn nhẹ máy. --- */
        .ngan-ha {{
            position: fixed; top: -25vh; left: -25vw; width: 170vw; height: 55vh;
            transform: rotate(-25deg); pointer-events: none;
            background: linear-gradient(90deg,
                transparent 0%, rgba(199,210,254,0.16) 15%, rgba(255,255,255,0.4) 38%,
                rgba(216,180,254,0.3) 55%, rgba(199,210,254,0.18) 75%, transparent 100%);
            filter: blur(5px);
            animation: ngan-ha-sang 7s ease-in-out infinite;
        }}
        @keyframes ngan-ha-sang {{
            0%, 100% {{ opacity: 0.55; }}
            50% {{ opacity: 0.9; }}
        }}

        /* --- Mặt trăng: hình tròn vẽ bằng CSS (radial-gradient + vài "miệng hố" bằng
           box-shadow), có quầng sáng nhẹ nhàng lên xuống cho sinh động. Phần khuyết
           (.moon-shadow) là 1 vòng tròn màu nền trời đè lên, trượt ngang theo pha trăng
           thật của ngày hôm đó — không cần ảnh/JavaScript gì cả, chỉ thuần CSS. --- */
        .moon {{
            position: fixed; top: 5vh; right: 8vw; width: 72px; height: 72px;
            border-radius: 50%; overflow: hidden;
            background: radial-gradient(circle at 35% 32%, #fffef4 0%, #fdf6d8 45%, #e9e0b0 75%, #d9d093 100%);
            animation: moonGlow 6s ease-in-out infinite;
        }}
        .moon-shadow {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 50%;
            background: {C_BG}; transform: translateX({DO_LECH_TRANG}%);
            transition: transform 1s ease; z-index: 2;
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
    <div class="starfield" style="opacity: {DO_MO_BAU_TROI};">{NGAN_HA_HTML}
        <div class="moon"><div class="moon-shadow"></div></div>
        <div class="stars-small"></div>
        <div class="stars-medium"></div>
        <div class="stars-large"></div>
        {HIEN_TUONG_HTML}
    </div>
    """, unsafe_allow_html=True)
else:
    # --- Bầu trời ban ngày cho Chế độ sáng: mặt trời phát sáng + vài đám mây trôi nhẹ ---
    # đặt cùng vị trí với mặt trăng bên Chế độ tối cho hai giao diện "đối xứng" nhau.
    #
    # SỐ LƯỢNG/MÀU MÂY + ĐỘ SÁNG MẶT TRỜI đổi theo thời tiết THẬT ở Mỹ Tho (nắng: mây thưa
    # trắng, mặt trời rõ; nhiều mây: mây dày hơn, xám nhẹ, mặt trời mờ bớt; mưa: mây dày và
    # xám đậm hơn nữa, mặt trời mờ hẳn; GIÔNG BÃO thì mây dày nhất + xậm màu nhất + mặt trời
    # gần như tắt hẳn, có thêm chớp sét — xem khối "if DANG_MUA" bên dưới). Không lấy được thời
    # tiết (mạng lỗi/API sập) thì TỰ ĐỘNG quay về mây ngẫu nhiên như bản gốc — vị trí random nhẹ
    # mỗi lần tải trang cho đỡ nhàm.
    if TRANG_THAI_THOI_TIET == "nang":
        SO_MAY, MAU_MAY, DO_SANG_MAT_TROI = 2, "#ffffff", 1.0
    elif TRANG_THAI_THOI_TIET == "may":
        SO_MAY, MAU_MAY, DO_SANG_MAT_TROI = 5, "#e2e8f0", 0.5
    elif TRANG_THAI_THOI_TIET == "mua":
        SO_MAY, MAU_MAY, DO_SANG_MAT_TROI = 8, "#64748b", 0.08
    elif TRANG_THAI_THOI_TIET == "mua_to":
        SO_MAY, MAU_MAY, DO_SANG_MAT_TROI = 10, "#334155", 0.02
    else:
        SO_MAY, MAU_MAY, DO_SANG_MAT_TROI = 3, "#ffffff", 1.0  # không rõ thời tiết -> như cũ

    # Nhật thực chỉ hiện khi trời có thể nhìn thấy mặt trời (nắng/nhiều mây/không rõ) — trời
    # đang mưa thì mây đen kịt che kín rồi, chẳng ai thấy nhật thực được nên tắt hẳn cho hợp lý.
    HIEN_NHAT_THUC = TRANG_THAI_THOI_TIET not in ("mua", "mua_to")

    _may = [
        (round(random.uniform(5, 62), 1), round(random.uniform(3, 88), 1), round(random.uniform(16, 27), 1))
        for _ in range(SO_MAY)
    ]
    CLOUDS_HTML = "".join(
        f'<div class="cloud" style="top:{top}vh; left:{left}vw; animation-delay:{-i * 4}s; '
        f'transform: scale({scale / 22}); --mau-may: {MAU_MAY};"></div>'
        for i, (top, left, scale) in enumerate(_may)
    )
    # Nhật thực TẮT hẳn khi trời mưa (xem HIEN_NHAT_THUC ở trên) — dựng sẵn các mẩu HTML/CSS
    # thành biến Python trước, rồi ghép vào ngay trên 1 dòng có nội dung khác (không để riêng
    # 1 dòng trống khi rỗng) để tránh lỗi hiện chữ thô đã gặp phải trước đây.
    if HIEN_NHAT_THUC:
        NHAT_THUC_HTML = '<div class="nhat-thuc"></div>'
        TOI_TROI_HTML = '<div class="nhat-thuc-toi-troi"></div>'
        VANH_SANG_HTML = '<div class="nhat-thuc-vanh-sang"></div>'
        SUN_WRAP_ANIM = "sunGlow 5s ease-in-out infinite, sangToiNhatThuc 362s linear infinite"
    else:
        NHAT_THUC_HTML = ""
        TOI_TROI_HTML = ""
        VANH_SANG_HTML = ""
        SUN_WRAP_ANIM = "sunGlow 5s ease-in-out infinite"
    st.markdown(f"""
    <style>
        .daysky {{ position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none; }}

        /* --- Mặt trời: hình tròn vẽ bằng CSS, ánh sáng ấm, quầng sáng nhấp nháy nhẹ.
           Mờ bớt khi trời nhiều mây/mưa (opacity), không ẩn hẳn để tránh đổi cảnh đột ngột.
           .sun-wrap bo tròn + overflow:hidden để "cắt gọn" đĩa che nhật thực bên trong (xem
           phần Nhật thực bên dưới) — quầng sáng phải dùng filter: drop-shadow (thay vì
           box-shadow) vì box-shadow sẽ bị overflow:hidden của chính nó cắt mất, drop-shadow thì
           không bị cắt nên quầng sáng vẫn hiện ra ngoài viền tròn bình thường. --- */
        .sun-wrap {{
            position: fixed; top: 5vh; right: 8vw; width: 72px; height: 72px;
            border-radius: 50%; overflow: hidden; opacity: {DO_SANG_MAT_TROI};
            filter: drop-shadow(0 0 45px rgba(255, 200, 87, 0.45)) drop-shadow(0 0 90px rgba(255, 200, 87, 0.18));
            animation: {SUN_WRAP_ANIM};
        }}
        .sun {{
            position: absolute; inset: 0; border-radius: 50%;
            background: radial-gradient(circle at 35% 32%, #fffdf2 0%, #ffe89b 40%, #ffc857 75%, #ffb347 100%);
        }}
        @keyframes sunGlow {{
            0%, 100% {{ filter: drop-shadow(0 0 45px rgba(255, 200, 87, 0.45)) drop-shadow(0 0 90px rgba(255, 200, 87, 0.18)); }}
            50% {{ filter: drop-shadow(0 0 58px rgba(255, 200, 87, 0.6)) drop-shadow(0 0 110px rgba(255, 200, 87, 0.28)); }}
        }}
        /* Ánh sáng mặt trời TỰ CHUYỂN DẦN liên tục, không dừng/chờ ở giữa chừng cho giống
           thật: vào trang 2 giây thì bắt đầu che (mờ dần xuống tối hẳn trong 2 phút), rồi sáng
           dần trở lại trong 2 phút kế (che ra), xong giữ nắng đẹp bình thường 2 phút — rồi lặp
           lại y hệt (2 giây, che vào, che ra, nắng, lặp...). */
        @keyframes sangToiNhatThuc {{
            0%, 0.55% {{ opacity: {DO_SANG_MAT_TROI}; }}
            33.70% {{ opacity: 0.04; }}
            66.85% {{ opacity: {DO_SANG_MAT_TROI}; }}
            100% {{ opacity: {DO_SANG_MAT_TROI}; }}
        }}
        @media (max-width: 640px) {{
            .sun-wrap {{ width: 52px; height: 52px; top: 3vh; right: 6vw; }}
        }}

        /* --- Mây trôi: 1 khối bo tròn + 2 "cục bông" (::before/::after) ghép lại. Màu mây
           (--mau-may, đặt inline theo từng đám) tự truyền xuống 2 "cục bông" luôn nhờ dùng
           biến CSS, không cần lặp lại màu 3 lần. --- */
        .cloud {{
            position: fixed; width: 90px; height: 32px; border-radius: 999px;
            background: var(--mau-may, #ffffff); opacity: 0.85;
            box-shadow: 0 6px 14px rgba(148, 163, 184, 0.18);
            animation: troiMay 22s ease-in-out infinite alternate;
        }}
        .cloud::before, .cloud::after {{
            content: ""; position: absolute; border-radius: 50%; background: var(--mau-may, #ffffff);
        }}
        .cloud::before {{ width: 46px; height: 46px; top: -22px; left: 10px; }}
        .cloud::after {{ width: 36px; height: 36px; top: -15px; left: 44px; }}
        @keyframes troiMay {{ from {{ transform: translateX(-16px); }} to {{ transform: translateX(16px); }} }}
        @media (prefers-reduced-motion: reduce) {{
            .sun-wrap, .cloud {{ animation: none !important; }}
        }}

        /* --- Nhật thực: chu kỳ 362 giây (~6 phút), lặp vô tận, thuần CSS không cần
           JavaScript/hẹn giờ gì cả — vào trang 2 giây là bắt đầu che luôn (không phải đợi tới
           gần hết chu kỳ mới thấy), rồi TỰ CHUYỂN DẦN liên tục không dừng/chờ giữa chừng cho
           giống thật: 2 phút che vào + 2 phút che ra + 2 phút nắng đẹp, xong lặp lại (2 giây,
           che vào, che ra, nắng, lặp...). Đĩa tối là CON của .sun-wrap (cùng khung tròn với mặt
           trời) trượt ngang CÙNG MỘT CHIỀU từ đầu tới cuối (phải → trái) chứ không lùi lại giữa
           chừng — nhờ .sun-wrap có overflow:hidden nên phần đĩa trượt ra ngoài khung tròn bị CẮT
           ẨN hết, chỉ phần đè lên đúng mặt trời mới hiện ra → che dần từng miếng "khuyết" y như
           nhật thực thật, che kín đúng 1 khoảnh khắc rồi đi tiếp luôn (không dừng) nên lúc "nhả"
           ra ánh sáng cũng hiện lại bắt đầu từ bên phải giống hệt lúc che vào — y như mặt trăng
           thật đi ngang qua một lượt, không quay đầu. Bộ đếm chạy riêng từ lúc mở trang, không
           đồng bộ giờ thực giữa mọi người xem — chỉ là hiệu ứng trang trí cho vui. Tắt hẳn khi
           trời mưa (xem HIEN_NHAT_THUC). --- */
        .nhat-thuc {{
            position: absolute; inset: 0; border-radius: 50%; background: #1e293b;
            animation: nhat-thuc 362s linear infinite;
            will-change: transform;
        }}
        @keyframes nhat-thuc {{
            0%, 0.55% {{ transform: translateX(100%); }}
            33.70% {{ transform: translateX(0%); }}
            66.85%, 100% {{ transform: translateX(-100%); }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .nhat-thuc {{ animation: none !important; transform: translateX(100%); }}
        }}

        /* --- Vành nhật hoa: viền sáng vàng mảnh quanh mép hình tròn, mờ hẳn lúc bình thường,
           chỉ LÓE SÁNG lên đúng khoảnh khắc mặt trời bị che kín hoàn toàn (phút thứ 2 trong chu
           kỳ) rồi tắt liền — tách riêng khỏi .sun-wrap nên không bị mờ dần theo, nhờ vậy nó
           "nổi bật" lên giữa lúc tối nhất, giống hiệu ứng "vành nhật hoa"/"diamond ring" của
           nhật thực thật. --- */
        .nhat-thuc-vanh-sang {{
            position: fixed; top: 5vh; right: 8vw; width: 72px; height: 72px;
            border-radius: 50%; pointer-events: none;
            animation: vanhSangNhatThuc 362s linear infinite;
        }}
        @keyframes vanhSangNhatThuc {{
            0%, 28.37% {{ box-shadow: inset 0 0 0 2px rgba(255, 221, 156, 0); }}
            33.70% {{ box-shadow: inset 0 0 0 3px rgba(255, 224, 160, 0.95), 0 0 16px 3px rgba(255, 224, 160, 0.6); }}
            39.03%, 100% {{ box-shadow: inset 0 0 0 2px rgba(255, 221, 156, 0); }}
        }}
        @media (max-width: 640px) {{
            .nhat-thuc-vanh-sang {{ width: 52px; height: 52px; top: 3vh; right: 6vw; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .nhat-thuc-vanh-sang {{ animation: none !important; box-shadow: none; }}
        }}

        /* --- Lúc nhật thực che kín thì cả bầu trời tối sầm lại như Chế độ tối (không có sao,
           chỉ tối nền thôi) rồi từ từ sáng trở lại — 1 lớp phủ đen đổi opacity theo ĐÚNG nhịp độ
           che/mở của mặt trời ở trên (mờ dần 2 phút, sáng dần 2 phút) nên luôn khớp nhau, không
           có đoạn dừng/chờ. Chỉ dùng opacity nên rất nhẹ, điện thoại yếu vẫn chạy mượt. --- */
        .nhat-thuc-toi-troi {{
            position: fixed; inset: 0; background: #0f172a; opacity: 0;
            pointer-events: none; animation: nenToiNhatThuc 362s linear infinite;
        }}
        @keyframes nenToiNhatThuc {{
            0%, 0.55% {{ opacity: 0; }}
            33.70% {{ opacity: 0.9; }}
            66.85% {{ opacity: 0; }}
            100% {{ opacity: 0; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .nhat-thuc-toi-troi {{ animation: none !important; opacity: 0; }}
        }}
    </style>
    <div class="daysky">
        <div class="sun-wrap">
            <div class="sun"></div>{NHAT_THUC_HTML}
        </div>
        {CLOUDS_HTML}{TOI_TROI_HTML}{VANH_SANG_HTML}
    </div>
    """, unsafe_allow_html=True)

# --- Mưa (dùng chung cho cả Chế độ tối lẫn sáng) — chỉ hiện khi Mỹ Tho đang có mưa thật,
# vẽ hoàn toàn bằng CSS (1 lớp phủ full màn hình, chạy animation dịch chuyển nền — rất nhẹ,
# không dùng JavaScript, chỉ opacity/background-position/vài phần tử tĩnh nên không ảnh hưởng
# gì đến tốc độ, kể cả trên điện thoại yếu). Giờ vẽ 2 LỚP MƯA chồng nhau (lớp gần: hạt to, rơi
# nhanh, rõ nét; lớp xa: hạt nhỏ, rơi chậm, mờ hơn) cho có chiều sâu giống mưa thật thay vì 1
# lớp phẳng đơn điệu như trước. Giông bão (mua_to) thì mưa dày + rơi nhanh hơn hẳn, kèm CHỚP SÉT
# (một lớp phủ trắng chớp sáng rồi tắt liền, lặp đều 20 lần/phút — thuần CSS, chỉ đổi opacity
# nên vẫn rất nhẹ). ---
if DANG_MUA:
    _mua_day = TRANG_THAI_THOI_TIET == "mua_to"
    if _mua_day:
        SET_HTML = '<div class="set-chop"></div>'
    else:
        SET_HTML = ""
    st.markdown(f"""
    <style>
        .mua-overlay {{ position: fixed; inset: 0; z-index: -1; pointer-events: none; }}
        /* Lớp mưa GẦN: hạt to, đậm nét, rơi nhanh — nổi bật ở tiền cảnh. */
        .mua-overlay::before {{
            content: ""; position: absolute; inset: -30px;
            background-image: repeating-linear-gradient(
                112deg, transparent 0px, transparent 2px,
                rgba(255,255,255,0.55) 2px, rgba(255,255,255,0.55) 3px,
                transparent 3px, transparent {26 if _mua_day else 40}px
            );
            opacity: {0.7 if _mua_day else 0.5};
            animation: mua-roi-gan {0.32 if _mua_day else 0.55}s linear infinite;
        }}
        /* Lớp mưa XA: hạt nhỏ, mờ hơn, rơi chậm hơn — tạo chiều sâu phía sau lớp gần. */
        .mua-overlay::after {{
            content: ""; position: absolute; inset: -30px;
            background-image: repeating-linear-gradient(
                118deg, transparent 0px, transparent 1px,
                rgba(255,255,255,0.3) 1px, rgba(255,255,255,0.3) 2px,
                transparent 2px, transparent {18 if _mua_day else 28}px
            );
            opacity: {0.55 if _mua_day else 0.35};
            animation: mua-roi-xa {0.5 if _mua_day else 0.8}s linear infinite;
        }}
        @keyframes mua-roi-gan {{
            from {{ background-position: 0 0; }}
            to {{ background-position: -45px 140px; }}
        }}
        @keyframes mua-roi-xa {{
            from {{ background-position: 0 0; }}
            to {{ background-position: -20px 75px; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .mua-overlay::before, .mua-overlay::after {{ animation: none !important; opacity: 0.3; }}
        }}

        /* --- Chớp sét (chỉ khi giông bão): 1 lớp phủ trắng toàn màn hình, LÓE lên rồi tắt liền
           trong tích tắc đầu mỗi chu kỳ 3 giây — lặp đều 20 lần/phút, thuần CSS opacity. --- */
        .set-chop {{
            position: fixed; inset: 0; z-index: -1; pointer-events: none;
            background: #f5f8ff; opacity: 0;
            animation: chop-set 3s linear infinite;
        }}
        @keyframes chop-set {{
            0% {{ opacity: 0; }}
            0.6% {{ opacity: 0.65; }}
            1.4% {{ opacity: 0.05; }}
            2.2% {{ opacity: 0.45; }}
            4% {{ opacity: 0; }}
            100% {{ opacity: 0; }}
        }}
        @media (prefers-reduced-motion: reduce) {{
            .set-chop {{ animation: none !important; opacity: 0; }}
        }}
    </style>
    <div class="mua-overlay"></div>{SET_HTML}
    """, unsafe_allow_html=True)


AVATAR_COLORS = ["#6366f1", "#8b5cf6", "#ec4899", "#f97316", "#10b981", "#0ea5e9", "#eab308"]


def avatar_color(name):
    return AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]


def progress_pct(diem, diem_max):
    if diem_max is None or diem_max <= 0 or diem <= 0:
        return 0
    return max(0, min(100, round(diem / diem_max * 100)))


def mui_ten_diem(diem):
    """Mũi tên nhỏ trước điểm số cho dễ nhìn tăng/giảm — chỉ để trang trí, không đổi số liệu."""
    if diem > 0:
        return "▲ "
    if diem < 0:
        return "▼ "
    return ""


def do_tre_the(idx, buoc=0.045, toi_da=0.4):
    """Độ trễ (giây) để các thẻ xếp hạng hiện lên lần lượt từ trên xuống thay vì cùng lúc,
    tạo cảm giác mượt mà hơn khi tải trang — giới hạn độ trễ tối đa để danh sách dài không
    bị chờ quá lâu mới hiện hết."""
    return min(idx * buoc, toi_da)


def tong_ket_diem(hist_df):
    """Từ bảng lịch sử của 1 thành viên (cột "Điểm"), tính tổng số điểm ĐƯỢC CỘNG và tổng số
    điểm BỊ TRỪ riêng biệt (kèm số lần) — để hiện gọn "bạn này được cộng bao nhiêu, bị trừ bao
    nhiêu" thay vì phải tự cộng trừ từng dòng trong bảng."""
    if hist_df.empty or "Điểm" not in hist_df.columns:
        return 0, 0, 0, 0
    diem_col = hist_df["Điểm"]
    cong = diem_col[diem_col > 0]
    tru = diem_col[diem_col < 0]
    return int(cong.sum()), int(len(cong)), int(tru.sum()), int(len(tru))


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
    st.sidebar.caption(
        "Gõ câu trả lời rồi bấm Lưu — câu trả lời sẽ hiện CÔNG KHAI ở tab Góp ý cho mọi người "
        "xem, nhưng KHÔNG hiện tên người gửi góp ý (giữ ẩn danh). Để trống + Lưu để gỡ câu trả lời."
    )
    if feedback_df.empty:
        st.sidebar.caption("Chưa có góp ý nào.")
    else:
        for _, fb in feedback_df.iterrows():
            thoi_gian = fb["ngay"].strftime("%d/%m %H:%M") if pd.notna(fb["ngay"]) else ""
            nguoi = fb["nguoi_gui"] or "Ẩn danh"
            da_tra_loi = bool(fb["phan_hoi"] and str(fb["phan_hoi"]).strip())
            nhan_da_tra_loi = " ✅" if da_tra_loi else ""
            with st.sidebar.expander(f"{nguoi} — {thoi_gian}{nhan_da_tra_loi}"):
                st.write(fb["noi_dung"])
                phan_hoi_moi = st.text_area(
                    "Trả lời công khai (không bắt buộc):",
                    value=fb["phan_hoi"] or "",
                    key=f"phan_hoi_{fb['id']}",
                )
                cot_luu, cot_xoa = st.columns(2)
                with cot_luu:
                    if st.button("💾 Lưu trả lời", key=f"luu_ph_{fb['id']}", use_container_width=True):
                        luu_phan_hoi_feedback(int(fb["id"]), phan_hoi_moi.strip())
                        st.success("Đã lưu!")
                        st.rerun()
                with cot_xoa:
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

    # --- "Hôm nay / Ngày mai học gì" — tự lấy từ tab Thời khóa biểu theo giờ Hà Nội.
    # Sau 11h45 sáng (buổi học đã xong) thì tự chuyển sang hiện lịch của NGÀY MAI luôn,
    # để chuẩn bị trước cho hôm sau thay vì cứ hiện lịch hôm nay đã học xong rồi.
    nhan_ngay_tkb, thu_hien_thi_tkb = _ngay_hien_thi_tkb_ha_noi()
    tkb_now_df = load_thoikhoabieu_hien_tai()
    noi_dung_tkb_now = tkb_now_df.iloc[0]["noi_dung"] if not tkb_now_df.empty else TKB_MAC_DINH
    _, cac_ngay_hien_thi_tkb = _tach_dong_tkb(noi_dung_tkb_now)
    mon_hoc_hien_thi = next((mon for thu, mon in cac_ngay_hien_thi_tkb if thu == thu_hien_thi_tkb), None)

    if mon_hoc_hien_thi:
        st.markdown(
            '<div class="home-tkb-banner">'
            f'<div class="home-tkb-label">📅 {html.escape(nhan_ngay_tkb)} ({html.escape(thu_hien_thi_tkb)}) học:</div>'
            f'<div class="home-tkb-text">{html.escape(mon_hoc_hien_thi)}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="home-tkb-banner nghi">'
            f'<div class="home-tkb-label">📅 {html.escape(nhan_ngay_tkb)} ({html.escape(thu_hien_thi_tkb)})</div>'
            '<div class="home-tkb-text">🎉 Không có lịch học trong Thời khóa biểu.</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # --- Lịch thi gần nhất (nếu Admin có thêm ở tab "📅 Thời khóa biểu") ---
    # Chỉ hiện lịch thi GẦN NHẤT sắp tới — không thêm gì thì không hiện gì ở đây cả.
    lich_thi_gan_nhat_df = load_lich_thi_sap_toi()
    if not lich_thi_gan_nhat_df.empty:
        lich_thi_gan_nhat = lich_thi_gan_nhat_df.iloc[0]
        ngay_thi_gan_nhat = _chuan_hoa_ngay(lich_thi_gan_nhat["ngay_thi"])
        lop_examen_css = "hom-nay" if ngay_thi_gan_nhat == datetime.now(GIO_HA_NOI).date() else ""
        st.markdown(
            f'<div class="home-examen-banner {lop_examen_css}">'
            '<div>'
            '<div class="home-examen-label">⏳ Lịch thi gần nhất</div>'
            f'<div class="home-examen-text">{html.escape(lich_thi_gan_nhat["tieu_de"])} '
            f'— {ngay_thi_gan_nhat.strftime("%d/%m/%Y")} ({_TEN_THU_VN[ngay_thi_gan_nhat.weekday()]})</div>'
            '</div>'
            f'<div class="home-examen-dem-nguoc">{html.escape(_dem_nguoc_lich_thi(lich_thi_gan_nhat["ngay_thi"]))}</div>'
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

            for hang_hien_thi, (idx, row) in enumerate(ranked):
                rank = idx + 1
                ten = row["name"]
                diem = int(row["diem"])
                top_class = ""
                badge = MEDALS.get(rank, str(rank))
                pill_class = "positive" if diem > 0 else ("negative" if diem < 0 else "zero")
                chu_cai_dau = ten.strip()[0].upper() if ten.strip() else "?"
                pct = progress_pct(diem, diem_max)
                mau_ten = avatar_color(ten)

                card_html = (
                    f'<div class="rank-card {top_class}" style="--diem-mau: {mau_ten}; animation-delay: {do_tre_the(hang_hien_thi)}s;">'
                    f'<div class="rank-card-top">'
                    f'<div class="rank-badge">{badge}</div>'
                    f'<div class="avatar" style="background: {mau_ten};">{chu_cai_dau}</div>'
                    f'<div class="member-name">{ten}</div>'
                    f'<div class="score-pill {pill_class}">{mui_ten_diem(diem)}{diem:+d} điểm</div>'
                    f'</div>'
                    f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div>'
                    f'{badges_html(ten, diem, diem_max, recent_map)}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                with st.expander(f"Xem lịch sử của {ten}"):
                    hist_df = hist_by_member.get(ten, pd.DataFrame())
                    if not hist_df.empty:
                        tong_cong, lan_cong, tong_tru, lan_tru = tong_ket_diem(hist_df)
                        c_tk1, c_tk2 = st.columns(2)
                        c_tk1.metric("➕ Tổng được cộng", f"+{tong_cong}", f"{lan_cong} lần")
                        c_tk2.metric("➖ Tổng bị trừ", f"{tong_tru}", f"{lan_tru} lần")
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
                        f'<div class="podium-block {classes[i]}" style="animation-delay: {i * 0.1}s;">'
                        f'<div class="podium-medal">{MEDALS.get(rank, "")}</div>'
                        f'<div class="podium-avatar">{chu_cai_dau}</div>'
                        f'<div class="podium-name">{ten}</div>'
                        f'<div class="podium-score">{mui_ten_diem(diem)}{diem:+d} điểm</div>'
                        f'{badges_html(ten, diem, diem_max, recent_map, "podium-badges")}'
                        f'</div>'
                    )
                st.markdown(f'<div class="podium-wrap">{blocks_html}</div>', unsafe_allow_html=True)

            for hang_hien_thi, (idx, row) in enumerate(rest):
                rank = idx + 1
                ten = row["name"]
                diem = int(row["diem"])
                pill_class = "positive" if diem > 0 else ("negative" if diem < 0 else "zero")
                chu_cai_dau = ten.strip()[0].upper() if ten.strip() else "?"
                pct = progress_pct(diem, diem_max)
                mau_ten = avatar_color(ten)

                card_html = (
                    f'<div class="rank-card" style="--diem-mau: {mau_ten}; animation-delay: {do_tre_the(hang_hien_thi)}s;">'
                    f'<div class="rank-card-top">'
                    f'<div class="rank-badge">{rank}</div>'
                    f'<div class="avatar" style="background: {mau_ten};">{chu_cai_dau}</div>'
                    f'<div class="member-name">{ten}</div>'
                    f'<div class="score-pill {pill_class}">{mui_ten_diem(diem)}{diem:+d} điểm</div>'
                    f'</div>'
                    f'<div class="progress-track"><div class="progress-fill" style="width:{pct}%;"></div></div>'
                    f'{badges_html(ten, diem, diem_max, recent_map)}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                with st.expander(f"Xem lịch sử của {ten}"):
                    hist_df = hist_by_member.get(ten, pd.DataFrame())
                    if not hist_df.empty:
                        tong_cong, lan_cong, tong_tru, lan_tru = tong_ket_diem(hist_df)
                        c_tk1, c_tk2 = st.columns(2)
                        c_tk1.metric("➕ Tổng được cộng", f"+{tong_cong}", f"{lan_cong} lần")
                        c_tk2.metric("➖ Tổng bị trừ", f"{tong_tru}", f"{lan_tru} lần")
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
                            tong_cong, lan_cong, tong_tru, lan_tru = tong_ket_diem(hist_df)
                            c_tk1, c_tk2 = st.columns(2)
                            c_tk1.metric("➕ Tổng được cộng", f"+{tong_cong}", f"{lan_cong} lần")
                            c_tk2.metric("➖ Tổng bị trừ", f"{tong_tru}", f"{lan_tru} lần")
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

    # -------------------------------------------------------------
    # ĐẾM NGƯỢC LỊCH THI/KIỂM TRA
    #
    # CÁCH THÊM/XOÁ LỊCH THI NHANH GỌN — KHÔNG CẦN ĐỘNG VÀO CODE:
    # đăng nhập Admin ở thanh bên → vào tab này → mở mục "➕ Thêm lịch thi"
    # bên dưới → điền tên bài thi + ngày thi → bấm Lưu. Lịch thi đã qua ngày
    # sẽ TỰ ĐỘNG biến mất khỏi danh sách, không cần vào xoá tay.
    # -------------------------------------------------------------
    st.markdown('<div class="lich-thi-tieu-de">⏳ Đếm ngược lịch thi / kiểm tra</div>', unsafe_allow_html=True)

    if is_admin:
        with st.expander("➕ Thêm lịch thi (chỉ Admin thấy mục này)"):
            with st.form("form_them_lich_thi", clear_on_submit=True):
                tieu_de_lich_thi = st.text_input("Tên bài thi/kiểm tra:", placeholder="VD: Kiểm tra giữa kỳ Toán")
                ngay_thi_moi = st.date_input(
                    "Ngày thi:", value=datetime.now(GIO_HA_NOI).date(),
                )
                ghi_chu_lich_thi = st.text_input("Ghi chú (không bắt buộc):", placeholder="VD: Phòng A3, mang máy tính")
                da_luu_lich_thi = st.form_submit_button("💾 Lưu lịch thi", use_container_width=True)
                if da_luu_lich_thi:
                    if tieu_de_lich_thi.strip():
                        add_lich_thi(tieu_de_lich_thi.strip(), ngay_thi_moi, ghi_chu_lich_thi.strip())
                        st.success("Đã lưu lịch thi mới!")
                        st.rerun()
                    else:
                        st.error("Vui lòng nhập tên bài thi/kiểm tra.")

        cac_lich_thi_da_qua = load_lich_thi_da_qua()
        if not cac_lich_thi_da_qua.empty:
            with st.expander("🗑️ Lịch thi đã qua (chỉ Admin thấy mục này)"):
                for _, dong in cac_lich_thi_da_qua.iterrows():
                    cot_ten, cot_xoa = st.columns([5, 1])
                    with cot_ten:
                        st.caption(f"{_chuan_hoa_ngay(dong['ngay_thi']).strftime('%d/%m/%Y')} — {dong['tieu_de']}")
                    with cot_xoa:
                        if st.button("Xoá", key=f"xoa_lich_thi_qua_{dong['id']}"):
                            delete_lich_thi(dong["id"])
                            st.rerun()
        st.write("")

    cac_lich_thi_sap_toi = load_lich_thi_sap_toi()
    if cac_lich_thi_sap_toi.empty:
        st.caption("🎉 Hiện chưa có lịch thi/kiểm tra nào sắp tới.")
    else:
        for _, dong in cac_lich_thi_sap_toi.iterrows():
            ngay_thi_chuan = _chuan_hoa_ngay(dong["ngay_thi"])
            so_ngay_con_lai = (ngay_thi_chuan - datetime.now(GIO_HA_NOI).date()).days
            lop_css = "hom-nay" if so_ngay_con_lai == 0 else ("sap-toi" if so_ngay_con_lai <= 3 else "")
            ghi_chu_html = (
                f'<div class="lich-thi-ghichu">📌 {html.escape(dong["ghi_chu"])}</div>'
                if dong["ghi_chu"] else ""
            )
            cot_the, cot_xoa_the = (st.columns([20, 1]) if is_admin else (st.container(), None))
            with cot_the:
                st.markdown(
                    f'<div class="lich-thi-the {lop_css}">'
                    '<div class="lich-thi-thong-tin">'
                    f'<div class="lich-thi-ten">{html.escape(dong["tieu_de"])}</div>'
                    f'<div class="lich-thi-ngay">📅 {ngay_thi_chuan.strftime("%d/%m/%Y")} ({_TEN_THU_VN[ngay_thi_chuan.weekday()]})</div>'
                    f'{ghi_chu_html}'
                    '</div>'
                    f'<div class="lich-thi-dem-nguoc">{html.escape(_dem_nguoc_lich_thi(dong["ngay_thi"]))}</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
            if is_admin:
                with cot_xoa_the:
                    if st.button("✖", key=f"xoa_lich_thi_{dong['id']}", help="Xoá lịch thi này"):
                        delete_lich_thi(dong["id"])
                        st.rerun()


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
        '<div class="tab-hero-subtitle">Chỉ Admin đọc được góp ý của bạn. Nếu Admin trả lời, câu trả lời sẽ hiện công khai bên dưới — nhưng KHÔNG kèm tên người gửi</div>'
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

    # --- Các góp ý Admin đã trả lời — hiện công khai cho mọi người xem, KHÔNG hiện tên
    # người gửi (giữ ẩn danh dù lúc gửi có ghi tên hay không). ---
    da_tra_loi_df = load_feedback_da_tra_loi()
    if not da_tra_loi_df.empty:
        st.markdown('<div class="qa-tieu-de">🗣️ Admin đã trả lời</div>', unsafe_allow_html=True)
        for _, qa in da_tra_loi_df.iterrows():
            st.markdown(
                '<div class="qa-the">'
                '<div class="qa-cauhoi-nhan">💬 Góp ý</div>'
                f'<div class="qa-cauhoi">{html.escape(qa["noi_dung"])}</div>'
                '<div class="qa-tra-loi-wrap">'
                '<div class="qa-tra-loi-nhan">✅ Admin trả lời</div>'
                f'<div class="qa-tra-loi">{html.escape(qa["phan_hoi"])}</div>'
                '</div>'
                '</div>',
                unsafe_allow_html=True,
            )
