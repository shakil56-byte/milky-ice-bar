import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="🍦 মিল্কি আইস বার", page_icon="🍦", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Hind Siliguri', sans-serif; }
.stApp { background: #0d1b2a; }
[data-testid="stSidebar"] { background: #112236 !important; border-right: 1px solid #1e3a52; }
[data-testid="stSidebar"] * { color: #a8d5c2 !important; }
h1 { color: #00e5b0 !important; }
h2, h3 { color: #7ecfb8 !important; }
[data-testid="metric-container"] { background: #112236; border: 1px solid #1e3a52; border-radius: 10px; padding: 10px 16px; }
[data-testid="metric-container"] label { color: #7ecfb8 !important; font-size: 0.8rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: #00e5b0 !important; font-weight: 700 !important; }
input[type="number"], input[type="text"] { background: #1a2f45 !important; color: #e0f0ea !important; border: 1px solid #2a4a65 !important; border-radius: 6px !important; }
.stButton button { background: #00e5b0 !important; color: #0d1b2a !important; border: none !important; border-radius: 8px !important; font-weight: 700 !important; font-family: 'Hind Siliguri', sans-serif !important; }
.stButton button:hover { opacity: 0.85; }
[data-baseweb="select"] > div { background: #1a2f45 !important; border-color: #2a4a65 !important; color: #e0f0ea !important; }
input[type="date"] { background: #1a2f45 !important; color: #e0f0ea !important; border: 1px solid #2a4a65 !important; border-radius: 6px !important; }
hr { border-color: #1e3a52 !important; }
p, label, .stText { color: #c8e6dc !important; }
div[data-testid="stForm"] { background: #112236; border: 1px solid #1e3a52; border-radius: 10px; padding: 16px; }

/* Excel-style table */
.excel-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.excel-table th {
    background: #0a2540;
    color: #00e5b0;
    font-weight: 700;
    text-align: center;
    padding: 8px 6px;
    border: 1px solid #1e3a52;
    white-space: nowrap;
}
.excel-table th.col-product { text-align: left; min-width: 120px; }
.excel-table td {
    border: 1px solid #1e3a52;
    padding: 4px 4px;
    text-align: center;
    background: #112236;
    color: #e0f0ea;
}
.excel-table tr:nth-child(odd) td { background: #0d1b2a; }
.excel-table td.col-product {
    text-align: left;
    font-weight: 600;
    color: #e0f0ea;
    padding-left: 10px;
    white-space: nowrap;
}
.excel-table td.closing-pos { color: #00e5b0; font-weight: 700; font-size: 1rem; }
.excel-table td.closing-neg { color: #e05c5c; font-weight: 700; font-size: 1rem; }
.group-header th {
    background: #0a3050;
    color: #7ecfb8;
    font-size: 0.75rem;
    padding: 4px;
}
</style>
""", unsafe_allow_html=True)

# ── DB ───────────────────────────────────────────────────────────────────────
DB = "icecream_stock.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    c = get_conn()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL, product_id INTEGER NOT NULL,
        opening INTEGER DEFAULT 0, stock_in INTEGER DEFAULT 0,
        delivery INTEGER DEFAULT 0, returned INTEGER DEFAULT 0,
        retail INTEGER DEFAULT 0, damaged INTEGER DEFAULT 0,
        closing INTEGER DEFAULT 0,
        UNIQUE(entry_date, product_id),
        FOREIGN KEY(product_id) REFERENCES products(id))""")
    c.commit(); c.close()

init_db()

def get_products():
    c = get_conn(); r = c.execute("SELECT id,name FROM products ORDER BY name").fetchall(); c.close(); return r

def add_product(name):
    c = get_conn()
    try: c.execute("INSERT INTO products(name) VALUES(?)",(name,)); c.commit(); return True
    except: return False
    finally: c.close()

def del_product(pid):
    c = get_conn()
    c.execute("DELETE FROM stock WHERE product_id=?",(pid,))
    c.execute("DELETE FROM products WHERE id=?",(pid,))
    c.commit(); c.close()

def get_last_closing(pid, before_date):
    c = get_conn()
    r = c.execute("SELECT closing FROM stock WHERE product_id=? AND entry_date<? ORDER BY entry_date DESC LIMIT 1",(pid,before_date)).fetchone()
    c.close(); return r[0] if r else 0

def get_row(entry_date, pid):
    c = get_conn()
    r = c.execute("SELECT opening,stock_in,delivery,returned,retail,damaged,closing FROM stock WHERE entry_date=? AND product_id=?",(entry_date,pid)).fetchone()
    c.close(); return r

def save_row(entry_date, pid, opening, stock_in, delivery, returned, retail, damaged):
    closing = opening + stock_in + returned - delivery - retail - damaged
    c = get_conn()
    c.execute("""INSERT INTO stock(entry_date,product_id,opening,stock_in,delivery,returned,retail,damaged,closing)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(entry_date,product_id) DO UPDATE SET
        opening=excluded.opening, stock_in=excluded.stock_in,
        delivery=excluded.delivery, returned=excluded.returned,
        retail=excluded.retail, damaged=excluded.damaged, closing=excluded.closing""",
        (entry_date,pid,opening,stock_in,delivery,returned,retail,damaged,closing))
    c.commit(); c.close()
    return closing

def get_report(f, t):
    c = get_conn()
    rows = c.execute("""
        SELECT s.entry_date, p.name, s.opening, s.stock_in,
               s.delivery, s.returned, s.retail, s.damaged, s.closing
        FROM stock s JOIN products p ON s.product_id=p.id
        WHERE s.entry_date BETWEEN ? AND ?
        ORDER BY s.entry_date, p.name
    """, (f, t)).fetchall()
    c.close()
    return rows

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🍦 মিল্কি আইস বার")
st.sidebar.markdown("---")
page = st.sidebar.radio("মেনু", ["📦 দৈনিক এন্ট্রি","📊 রিপোর্ট","🛒 পণ্য তালিকা"], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown("<small style='color:#4a7a6a'>ক্লোজিং = ওপেনিং + স্টক ইন + রিটার্ন − ডেলিভারি − খুচরা − নষ্ট</small>", unsafe_allow_html=True)

# ══ PAGE 1: দৈনিক এন্ট্রি ════════════════════════════════════════════════════
if page == "📦 দৈনিক এন্ট্রি":
    st.title("📦 দৈনিক স্টক এন্ট্রি")

    col1, _ = st.columns([2, 5])
    with col1:
        sel_date = st.date_input("তারিখ", value=date.today())
    edate = str(sel_date)

    products = get_products()
    if not products:
        st.warning("⚠️ আগে **🛒 পণ্য তালিকা** পেজে গিয়ে পণ্য যোগ করুন।")
        st.stop()

    # ── Excel-style HTML table header ────────────────────────────────────────
    st.markdown(f"""
    <table class="excel-table">
      <thead>
        <tr>
          <th class="col-product" rowspan="2">পণ্য</th>
          <th rowspan="2">ওপেনিং<br>স্টক</th>
          <th rowspan="2">স্টক ইন</th>
          <th rowspan="2">ডেলিভারি</th>
          <th rowspan="2">রিটার্ন</th>
          <th rowspan="2">খুচরা</th>
          <th rowspan="2">নষ্ট</th>
          <th rowspan="2">ক্লোজিং<br>স্টক</th>
        </tr>
      </thead>
    </table>
    """, unsafe_allow_html=True)

    # ── Input rows ────────────────────────────────────────────────────────────
    # col widths: পণ্য, ওপেনিং, স্টক ইন, ডেলিভারি, রিটার্ন, খুচরা, নষ্ট, ক্লোজিং
    W = [2.2, 1, 1, 1, 1, 1, 1, 1.2]
    headers = ["পণ্য","ওপেনিং","স্টক ইন","ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"]

    # Header row via columns
    hc = st.columns(W)
    for i, h in enumerate(headers):
        hc[i].markdown(
            f"<div style='background:#0a2540;color:#00e5b0;font-weight:700;"
            f"font-size:0.8rem;text-align:center;padding:6px 2px;"
            f"border:1px solid #1e3a52;border-radius:4px;'>{h}</div>",
            unsafe_allow_html=True)

    entry_data = {}

    for idx, (pid, pname) in enumerate(products):
        r = get_row(edate, pid)
        lc = get_last_closing(pid, edate)
        op  = r[0] if r else lc
        si  = r[1] if r else 0
        de  = r[2] if r else 0
        re_ = r[3] if r else 0
        rt  = r[4] if r else 0
        da  = r[5] if r else 0

        bg = "#112236" if idx % 2 == 0 else "#0d1b2a"
        rc = st.columns(W)

        rc[0].markdown(
            f"<div style='background:{bg};color:#e0f0ea;font-weight:600;"
            f"padding:8px 8px;border:1px solid #1e3a52;border-radius:4px;"
            f"font-size:0.9rem;white-space:nowrap;overflow:hidden;'>{pname}</div>",
            unsafe_allow_html=True)

        opening  = rc[1].number_input("", value=op,  min_value=0, key=f"op_{pid}", label_visibility="collapsed")
        stock_in = rc[2].number_input("", value=si,  min_value=0, key=f"si_{pid}", label_visibility="collapsed")
        delivery = rc[3].number_input("", value=de,  min_value=0, key=f"de_{pid}", label_visibility="collapsed")
        returned = rc[4].number_input("", value=re_, min_value=0, key=f"re_{pid}", label_visibility="collapsed")
        retail   = rc[5].number_input("", value=rt,  min_value=0, key=f"rt_{pid}", label_visibility="collapsed")
        damaged  = rc[6].number_input("", value=da,  min_value=0, key=f"da_{pid}", label_visibility="collapsed")

        closing = opening + stock_in + returned - delivery - retail - damaged
        cl_color = "#00e5b0" if closing >= 0 else "#e05c5c"
        rc[7].markdown(
            f"<div style='background:{bg};color:{cl_color};font-weight:700;"
            f"font-size:1.05rem;text-align:center;padding:8px 4px;"
            f"border:1px solid #1e3a52;border-radius:4px;'>{closing}</div>",
            unsafe_allow_html=True)

        entry_data[pid] = (opening, stock_in, delivery, returned, retail, damaged)

    st.markdown("")
    if st.button("💾  সব সেভ করুন"):
        for pid, (op, si, de, re_, rt, da) in entry_data.items():
            save_row(edate, pid, op, si, de, re_, rt, da)
        st.success(f"✅ {edate} তারিখের ডেটা সেভ হয়েছে!")
        st.balloons()

# ══ PAGE 2: রিপোর্ট ══════════════════════════════════════════════════════════
elif page == "📊 রিপোর্ট":
    st.title("📊 স্টক রিপোর্ট")
    c1, c2, c3 = st.columns([2,2,2])
    with c1: fd = st.date_input("শুরু", value=date.today()-timedelta(days=6))
    with c2: td = st.date_input("শেষ",  value=date.today())
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🔍 দেখুন", use_container_width=True)

    rows = get_report(str(fd), str(td))
    if not rows:
        st.info("এই সময়ের কোনো ডেটা নেই।")
    else:
        df = pd.DataFrame(rows, columns=["তারিখ","পণ্য","ওপেনিং","স্টক ইন","ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"])

        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("মোট স্টক ইন",  int(df["স্টক ইন"].sum()))
        m2.metric("মোট ডেলিভারি", int(df["ডেলিভারি"].sum()))
        m3.metric("মোট রিটার্ন",  int(df["রিটার্ন"].sum()))
        m4.metric("মোট খুচরা",    int(df["খুচরা"].sum()))
        m5.metric("মোট নষ্ট",     int(df["নষ্ট"].sum()))

        st.markdown("---")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Product summary
        st.markdown("### পণ্য ভিত্তিক সারসংক্ষেপ")
        summary = df.groupby("পণ্য").agg(
            স্টক_ইন=("স্টক ইন","sum"),
            ডেলিভারি=("ডেলিভারি","sum"),
            রিটার্ন=("রিটার্ন","sum"),
            খুচরা=("খুচরা","sum"),
            নষ্ট=("নষ্ট","sum"),
            শেষ_ক্লোজিং=("ক্লোজিং","last")
        ).reset_index()
        st.dataframe(summary, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Excel CSV ডাউনলোড", data=csv,
            file_name=f"report_{fd}_{td}.csv", mime="text/csv")

# ══ PAGE 3: পণ্য তালিকা ══════════════════════════════════════════════════════
elif page == "🛒 পণ্য তালিকা":
    st.title("🛒 পণ্য তালিকা")
    with st.form("prod_form", clear_on_submit=True):
        c1, c2 = st.columns([4,1])
        new_prod = c1.text_input("নতুন পণ্যের নাম", placeholder="যেমন: চকোলেট কাপ")
        if c2.form_submit_button("+ যোগ", use_container_width=True):
            if new_prod.strip():
                if add_product(new_prod.strip()): st.rerun()
                else: st.error("এই নাম আগেই আছে!")
            else: st.warning("নাম লিখুন।")
    st.markdown("---")
    products = get_products()
    if not products:
        st.info("এখনো কোনো পণ্য নেই। উপরে যোগ করুন।")
    else:
        st.markdown(f"**মোট পণ্য: {len(products)}টি**")
        for pid, pname in products:
            c1, c2 = st.columns([6,1])
            c1.markdown(f"<p style='padding-top:6px;color:#e0f0ea;font-size:1rem'>🍦 {pname}</p>", unsafe_allow_html=True)
            if c2.button("🗑", key=f"dp_{pid}"):
                del_product(pid); st.rerun()
