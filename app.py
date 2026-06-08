import streamlit as st
import sqlite3
import pandas as pd
import hashlib
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
input[type="number"], input[type="text"], input[type="password"] {
    background: #1a2f45 !important; color: #e0f0ea !important;
    border: 1px solid #2a4a65 !important; border-radius: 6px !important; }
.stButton button { background: #00e5b0 !important; color: #0d1b2a !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important; font-family: 'Hind Siliguri', sans-serif !important; }
.stButton button:hover { opacity: 0.85; }
[data-baseweb="select"] > div { background: #1a2f45 !important; border-color: #2a4a65 !important; color: #e0f0ea !important; }
hr { border-color: #1e3a52 !important; }
p, label, .stText { color: #c8e6dc !important; }
div[data-testid="stForm"] { background: #112236; border: 1px solid #1e3a52; border-radius: 10px; padding: 16px; }
.role-badge-admin { background: #00e5b0; color: #0d1b2a; padding: 2px 10px;
    border-radius: 20px; font-size: 0.75rem; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ── DB ───────────────────────────────────────────────────────────────────────
DB = "icecream_stock.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    c = get_conn()
    c.execute("PRAGMA journal_mode=WAL")

    # Users
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        display_name TEXT)""")

    # Products
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL)""")

    # Drop old stock table if it has wrong schema
    old_cols = [r[1] for r in c.execute("PRAGMA table_info(stock)").fetchall()]
    bad_schema = old_cols and ("user_id" not in old_cols or "stock_in" not in old_cols)

    if bad_schema:
        # Save old data
        try:
            old_rows = c.execute("SELECT * FROM stock").fetchall()
            old_names = old_cols
        except:
            old_rows, old_names = [], []
        c.execute("DROP TABLE stock")

    if bad_schema or not old_cols:
        c.execute("""CREATE TABLE IF NOT EXISTS stock (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date  TEXT    NOT NULL,
            product_id  INTEGER NOT NULL,
            user_id     INTEGER NOT NULL DEFAULT 1,
            opening     INTEGER DEFAULT 0,
            stock_in    INTEGER DEFAULT 0,
            delivery    INTEGER DEFAULT 0,
            returned    INTEGER DEFAULT 0,
            retail      INTEGER DEFAULT 0,
            damaged     INTEGER DEFAULT 0,
            closing     INTEGER DEFAULT 0)""")

        if bad_schema:
            for row in old_rows:
                try:
                    d = dict(zip(old_names, row))
                    closing = (d.get("opening",0) + d.get("stock_in", d.get("input_qty",0))
                               + d.get("returned",0) - d.get("delivery",0)
                               - d.get("retail",0) - d.get("damaged",0))
                    c.execute("""INSERT INTO stock
                        (entry_date,product_id,user_id,opening,stock_in,delivery,returned,retail,damaged,closing)
                        VALUES(?,?,?,?,?,?,?,?,?,?)""", (
                        d.get("entry_date",""), d.get("product_id",1),
                        d.get("user_id",1), d.get("opening",0),
                        d.get("stock_in", d.get("input_qty",0)),
                        d.get("delivery",0), d.get("returned",0),
                        d.get("retail",0), d.get("damaged",0), closing))
                except: pass

    # Default admin
    try:
        c.execute("INSERT INTO users(username,password,role,display_name) VALUES(?,?,?,?)",
                  ("admin", hash_pw("admin123"), "admin", "মালিক"))
    except: pass

    c.commit()
    c.close()

init_db()

# ── Auth ─────────────────────────────────────────────────────────────────────
def login(username, password):
    c = get_conn()
    r = c.execute("SELECT id,username,role,display_name FROM users WHERE username=? AND password=?",
                  (username, hash_pw(password))).fetchone()
    c.close(); return r

def get_all_users():
    c = get_conn()
    r = c.execute("SELECT id,username,role,display_name FROM users ORDER BY role DESC,display_name").fetchall()
    c.close(); return r

def add_user(username, password, role, display_name):
    c = get_conn()
    try:
        c.execute("INSERT INTO users(username,password,role,display_name) VALUES(?,?,?,?)",
                  (username, hash_pw(password), role, display_name))
        c.commit(); return True
    except: return False
    finally: c.close()

def del_user(uid):
    c = get_conn()
    c.execute("DELETE FROM users WHERE id=?", (uid,))
    c.commit(); c.close()

def reset_password(uid, new_pw):
    c = get_conn()
    c.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_pw), uid))
    c.commit(); c.close()

# ── Products ─────────────────────────────────────────────────────────────────
def get_products():
    c = get_conn()
    r = c.execute("SELECT id,name FROM products ORDER BY name").fetchall()
    c.close(); return r

def add_product(name):
    c = get_conn()
    try: c.execute("INSERT INTO products(name) VALUES(?)", (name,)); c.commit(); return True
    except: return False
    finally: c.close()

def del_product(pid):
    c = get_conn()
    c.execute("DELETE FROM stock WHERE product_id=?", (pid,))
    c.execute("DELETE FROM products WHERE id=?", (pid,))
    c.commit(); c.close()

# ── Stock ─────────────────────────────────────────────────────────────────────
def get_last_closing(pid, before_date, user_id):
    c = get_conn()
    r = c.execute("""SELECT closing FROM stock
        WHERE product_id=? AND entry_date<? AND user_id=?
        ORDER BY entry_date DESC LIMIT 1""", (pid, before_date, user_id)).fetchone()
    c.close(); return r[0] if r else 0

def get_row(entry_date, pid, user_id):
    c = get_conn()
    r = c.execute("""SELECT opening,stock_in,delivery,returned,retail,damaged,closing
        FROM stock WHERE entry_date=? AND product_id=? AND user_id=?""",
        (entry_date, pid, user_id)).fetchone()
    c.close(); return r

def save_row(entry_date, pid, user_id, opening, stock_in, delivery, returned, retail, damaged):
    closing = opening + stock_in + returned - delivery - retail - damaged
    c = get_conn()
    c.execute("""DELETE FROM stock
        WHERE entry_date=? AND product_id=? AND user_id=?""",
        (entry_date, pid, user_id))
    c.execute("""INSERT INTO stock
        (entry_date,product_id,user_id,opening,stock_in,delivery,returned,retail,damaged,closing)
        VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (entry_date, pid, user_id, opening, stock_in, delivery, returned, retail, damaged, closing))
    c.commit(); c.close()
    return closing

def get_combined_report(f, t):
    c = get_conn()
    rows = c.execute("""
        SELECT s.entry_date, p.name,
            SUM(s.opening), SUM(s.stock_in), SUM(s.delivery),
            SUM(s.returned), SUM(s.retail), SUM(s.damaged), SUM(s.closing)
        FROM stock s JOIN products p ON s.product_id=p.id
        WHERE s.entry_date BETWEEN ? AND ?
        GROUP BY s.entry_date, p.name
        ORDER BY s.entry_date, p.name""", (f, t)).fetchall()
    c.close(); return rows

def get_employee_report(f, t):
    c = get_conn()
    rows = c.execute("""
        SELECT s.entry_date, p.name, u.display_name,
            s.opening, s.stock_in, s.delivery,
            s.returned, s.retail, s.damaged, s.closing
        FROM stock s
        JOIN products p ON s.product_id=p.id
        JOIN users u ON s.user_id=u.id
        WHERE s.entry_date BETWEEN ? AND ?
        ORDER BY s.entry_date, p.name, u.display_name""", (f, t)).fetchall()
    c.close(); return rows

# ══════════════════════════════════════════════════════════════════════════════
# LOGIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.markdown("""
    <div style='text-align:center;padding-top:60px'>
      <div style='font-size:4rem'>🍦</div>
      <h1 style='color:#00e5b0;margin:0'>মিল্কি আইস বার</h1>
      <p style='color:#7ecfb8'>স্টক ম্যানেজমেন্ট সিস্টেম</p>
    </div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1,2,1])
    with col:
        with st.form("login_form"):
            st.markdown("### 🔐 লগিন করুন")
            uname = st.text_input("ইউজারনেম", placeholder="username")
            pw    = st.text_input("পাসওয়ার্ড", type="password", placeholder="password")
            if st.form_submit_button("লগিন করুন", use_container_width=True):
                u = login(uname, pw)
                if u:
                    st.session_state.user = {"id":u[0],"username":u[1],"role":u[2],"name":u[3]}
                    st.rerun()
                else:
                    st.error("ইউজারনেম বা পাসওয়ার্ড ভুল!")
        st.markdown("<small style='color:#4a7a6a'>ডিফল্ট: username=admin | password=admin123</small>",
                    unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════════
user     = st.session_state.user
is_admin = user["role"] == "admin"

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🍦 মিল্কি আইস বার")
st.sidebar.markdown(f"**{user['name']}**")
if is_admin:
    st.sidebar.markdown("<span class='role-badge-admin'>মালিক ✓</span>", unsafe_allow_html=True)
st.sidebar.markdown("---")

if is_admin:
    pages = ["🏠 ড্যাশবোর্ড","📦 দৈনিক এন্ট্রি","📊 সম্মিলিত রিপোর্ট","👥 কর্মচারী রিপোর্ট","🛒 পণ্য তালিকা","⚙️ ইউজার ম্যানেজমেন্ট"]
else:
    pages = ["📦 দৈনিক এন্ট্রি","📊 আমার রিপোর্ট"]

default_page = 0  # admin এর জন্য ড্যাশবোর্ড, কর্মচারীর জন্য এন্ট্রি
page = st.sidebar.radio("মেনু", pages, index=default_page, label_visibility="collapsed")
st.sidebar.markdown("---")
if st.sidebar.button("🚪 লগআউট"):
    st.session_state.user = None
    st.rerun()

# ── Helper: entry table ───────────────────────────────────────────────────────
def draw_entry_table(edate, uid):
    products = get_products()
    if not products:
        st.warning("⚠️ মালিক এখনো পণ্য যোগ করেননি।")
        st.stop()

    W = [2.2, 1, 1, 1, 1, 1, 1, 1.2]
    headers = ["পণ্য","ওপেনিং","স্টক ইন","ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"]
    hc = st.columns(W)
    for i,h in enumerate(headers):
        hc[i].markdown(
            f"<div style='background:#0a2540;color:#00e5b0;font-weight:700;"
            f"font-size:0.8rem;text-align:center;padding:6px 2px;"
            f"border:1px solid #1e3a52;border-radius:4px'>{h}</div>",
            unsafe_allow_html=True)

    data = {}
    for idx,(pid,pname) in enumerate(products):
        r  = get_row(edate, pid, uid)
        lc = get_last_closing(pid, edate, uid)
        op  = r[0] if r else lc
        si  = r[1] if r else 0
        de  = r[2] if r else 0
        re_ = r[3] if r else 0
        rt  = r[4] if r else 0
        da  = r[5] if r else 0

        bg = "#112236" if idx%2==0 else "#0d1b2a"
        rc = st.columns(W)
        rc[0].markdown(
            f"<div style='background:{bg};color:#e0f0ea;font-weight:600;"
            f"padding:8px;border:1px solid #1e3a52;border-radius:4px;"
            f"font-size:0.9rem'>{pname}</div>", unsafe_allow_html=True)

        opening  = rc[1].number_input("", value=op,  min_value=0, key=f"op_{pid}_{uid}", label_visibility="collapsed")
        stock_in = rc[2].number_input("", value=si,  min_value=0, key=f"si_{pid}_{uid}", label_visibility="collapsed")
        delivery = rc[3].number_input("", value=de,  min_value=0, key=f"de_{pid}_{uid}", label_visibility="collapsed")
        returned = rc[4].number_input("", value=re_, min_value=0, key=f"re_{pid}_{uid}", label_visibility="collapsed")
        retail   = rc[5].number_input("", value=rt,  min_value=0, key=f"rt_{pid}_{uid}", label_visibility="collapsed")
        damaged  = rc[6].number_input("", value=da,  min_value=0, key=f"da_{pid}_{uid}", label_visibility="collapsed")

        closing = opening + stock_in + returned - delivery - retail - damaged
        clr = "#00e5b0" if closing >= 0 else "#e05c5c"
        rc[7].markdown(
            f"<div style='background:{bg};color:{clr};font-weight:700;"
            f"font-size:1.05rem;text-align:center;padding:8px 4px;"
            f"border:1px solid #1e3a52;border-radius:4px'>{closing}</div>",
            unsafe_allow_html=True)

        data[pid] = (opening, stock_in, delivery, returned, retail, damaged)
    return data

# ══ ড্যাশবোর্ড (Admin) ═══════════════════════════════════════════════════════
if page == "🏠 ড্যাশবোর্ড":
    st.title(f"🏠 ড্যাশবোর্ড — আজকের রিপোর্ট")

    today = str(date.today())
    st.markdown(f"<p style='color:#7ecfb8'>📅 তারিখ: {today}</p>", unsafe_allow_html=True)
    st.markdown("---")

    # আজকের সম্মিলিত ডেটা
    rows = get_combined_report(today, today)

    if not rows:
        st.info("আজকে এখনো কোনো এন্ট্রি হয়নি।")
    else:
        df_today = pd.DataFrame(rows, columns=["তারিখ","পণ্য","ওপেনিং","স্টক ইন",
                                                "ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"])

        # Summary metrics
        m1,m2,m3,m4,m5,m6 = st.columns(6)
        m1.metric("📥 স্টক ইন",   int(df_today["স্টক ইন"].sum()))
        m2.metric("🚚 ডেলিভারি",  int(df_today["ডেলিভারি"].sum()))
        m3.metric("↩️ রিটার্ন",   int(df_today["রিটার্ন"].sum()))
        m4.metric("🛒 খুচরা",     int(df_today["খুচরা"].sum()))
        m5.metric("❌ নষ্ট",      int(df_today["নষ্ট"].sum()))
        m6.metric("📦 ক্লোজিং",   int(df_today["ক্লোজিং"].sum()))

        st.markdown("---")
        st.markdown("### পণ্যভিত্তিক আজকের স্টক")

        # Table header
        W = [2.2, 1, 1, 1, 1, 1, 1, 1.2]
        headers = ["পণ্য","ওপেনিং","স্টক ইন","ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"]
        hc = st.columns(W)
        for i,h in enumerate(headers):
            hc[i].markdown(
                f"<div style='background:#0a2540;color:#00e5b0;font-weight:700;"
                f"font-size:0.8rem;text-align:center;padding:6px 2px;"
                f"border:1px solid #1e3a52;border-radius:4px'>{h}</div>",
                unsafe_allow_html=True)

        for idx, row in df_today.iterrows():
            bg = "#112236" if idx%2==0 else "#0d1b2a"
            rc = st.columns(W)
            rc[0].markdown(
                f"<div style='background:{bg};color:#e0f0ea;font-weight:600;"
                f"padding:8px;border:1px solid #1e3a52;border-radius:4px;"
                f"font-size:0.9rem'>{row['পণ্য']}</div>", unsafe_allow_html=True)
            for ci, col_name in enumerate(["ওপেনিং","স্টক ইন","ডেলিভারি","রিটার্ন","খুচরা","নষ্ট"]):
                rc[ci+1].markdown(
                    f"<div style='background:{bg};color:#c8e6dc;text-align:center;"
                    f"padding:8px 4px;border:1px solid #1e3a52;border-radius:4px'>{int(row[col_name])}</div>",
                    unsafe_allow_html=True)
            cl = int(row["ক্লোজিং"])
            clr = "#00e5b0" if cl >= 0 else "#e05c5c"
            rc[7].markdown(
                f"<div style='background:{bg};color:{clr};font-weight:700;"
                f"font-size:1.05rem;text-align:center;padding:8px 4px;"
                f"border:1px solid #1e3a52;border-radius:4px'>{cl}</div>",
                unsafe_allow_html=True)

    # কর্মচারী এন্ট্রি স্ট্যাটাস
    st.markdown("---")
    st.markdown("### কর্মচারী এন্ট্রি স্ট্যাটাস")
    all_users = get_all_users()
    workers = [(uid,un,dn) for uid,un,r,dn in all_users if r=="user"]
    if workers:
        c = get_conn()
        for uid,un,dn in workers:
            has_entry = c.execute(
                "SELECT COUNT(*) FROM stock WHERE entry_date=? AND user_id=?",
                (today, uid)).fetchone()[0]
            status = "✅ এন্ট্রি দিয়েছে" if has_entry else "⏳ এখনো দেয়নি"
            color  = "#00e5b0" if has_entry else "#e0a040"
            c1,c2 = st.columns([3,2])
            c1.markdown(f"<p style='padding-top:4px;color:#e0f0ea'>👤 {dn}</p>", unsafe_allow_html=True)
            c2.markdown(f"<p style='padding-top:4px;color:{color}'>{status}</p>", unsafe_allow_html=True)
        c.close()
    else:
        st.info("কোনো কর্মচারী নেই।")

# ══ দৈনিক এন্ট্রি ════════════════════════════════════════════════════════════
elif page == "📦 দৈনিক এন্ট্রি":
    st.title(f"📦 দৈনিক স্টক এন্ট্রি — {user['name']}")
    c1,_ = st.columns([2,5])
    with c1:
        sel_date = st.date_input("তারিখ", value=date.today())
    edate = str(sel_date)

    data = draw_entry_table(edate, user["id"])
    st.markdown("")
    if st.button("💾  সেভ করুন"):
        for pid,(op,si,de,re_,rt,da) in data.items():
            save_row(edate, pid, user["id"], op, si, de, re_, rt, da)
        st.success(f"✅ {edate} তারিখের ডেটা সেভ হয়েছে!")
        st.balloons()

# ══ সম্মিলিত রিপোর্ট ═════════════════════════════════════════════════════════
elif page == "📊 সম্মিলিত রিপোর্ট":
    st.title("📊 সম্মিলিত স্টক রিপোর্ট")
    c1,c2 = st.columns(2)
    with c1: fd = st.date_input("শুরু", value=date.today()-timedelta(days=6))
    with c2: td = st.date_input("শেষ",  value=date.today())

    rows = get_combined_report(str(fd), str(td))
    if not rows:
        st.info("এই সময়ের কোনো ডেটা নেই।")
    else:
        df = pd.DataFrame(rows, columns=["তারিখ","পণ্য","ওপেনিং","স্টক ইন",
                                          "ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"])
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("মোট স্টক ইন",  int(df["স্টক ইন"].sum()))
        m2.metric("মোট ডেলিভারি", int(df["ডেলিভারি"].sum()))
        m3.metric("মোট রিটার্ন",  int(df["রিটার্ন"].sum()))
        m4.metric("মোট খুচরা",    int(df["খুচরা"].sum()))
        m5.metric("মোট নষ্ট",     int(df["নষ্ট"].sum()))
        st.markdown("---")
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV ডাউনলোড", data=csv,
            file_name=f"combined_{fd}_{td}.csv", mime="text/csv")

# ══ কর্মচারী রিপোর্ট ══════════════════════════════════════════════════════════
elif page == "👥 কর্মচারী রিপোর্ট":
    st.title("👥 কর্মচারী ভিত্তিক রিপোর্ট")
    c1,c2 = st.columns(2)
    with c1: fd = st.date_input("শুরু", value=date.today()-timedelta(days=6))
    with c2: td = st.date_input("শেষ",  value=date.today())

    rows = get_employee_report(str(fd), str(td))
    if not rows:
        st.info("এই সময়ের কোনো ডেটা নেই।")
    else:
        df = pd.DataFrame(rows, columns=["তারিখ","পণ্য","কর্মচারী","ওপেনিং",
                                          "স্টক ইন","ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"])
        emps = ["সবাই"] + sorted(df["কর্মচারী"].unique().tolist())
        sel  = st.selectbox("কর্মচারী বেছে নিন", emps)
        if sel != "সবাই":
            df = df[df["কর্মচারী"] == sel]
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV ডাউনলোড", data=csv,
            file_name=f"employee_report.csv", mime="text/csv")

# ══ আমার রিপোর্ট (কর্মচারী) ══════════════════════════════════════════════════
elif page == "📊 আমার রিপোর্ট":
    st.title(f"📊 আমার রিপোর্ট — {user['name']}")
    c1,c2 = st.columns(2)
    with c1: fd = st.date_input("শুরু", value=date.today()-timedelta(days=6))
    with c2: td = st.date_input("শেষ",  value=date.today())

    c = get_conn()
    rows = c.execute("""
        SELECT s.entry_date, p.name, s.opening, s.stock_in,
               s.delivery, s.returned, s.retail, s.damaged, s.closing
        FROM stock s JOIN products p ON s.product_id=p.id
        WHERE s.entry_date BETWEEN ? AND ? AND s.user_id=?
        ORDER BY s.entry_date, p.name""",
        (str(fd), str(td), user["id"])).fetchall()
    c.close()
    if not rows:
        st.info("এই সময়ের কোনো ডেটা নেই।")
    else:
        df = pd.DataFrame(rows, columns=["তারিখ","পণ্য","ওপেনিং","স্টক ইন",
                                          "ডেলিভারি","রিটার্ন","খুচরা","নষ্ট","ক্লোজিং"])
        st.dataframe(df, use_container_width=True, hide_index=True)

# ══ পণ্য তালিকা ═══════════════════════════════════════════════════════════════
elif page == "🛒 পণ্য তালিকা":
    st.title("🛒 পণ্য তালিকা")
    with st.form("prod_form", clear_on_submit=True):
        c1,c2 = st.columns([4,1])
        np_ = c1.text_input("নতুন পণ্যের নাম", placeholder="যেমন: চকোলেট কাপ")
        if c2.form_submit_button("+ যোগ", use_container_width=True):
            if np_.strip():
                if add_product(np_.strip()): st.rerun()
                else: st.error("এই নাম আগেই আছে!")
            else: st.warning("নাম লিখুন।")
    st.markdown("---")
    for pid,pname in get_products():
        c1,c2 = st.columns([6,1])
        c1.markdown(f"<p style='padding-top:6px;color:#e0f0ea'>🍦 {pname}</p>", unsafe_allow_html=True)
        if c2.button("🗑", key=f"dp_{pid}"):
            del_product(pid); st.rerun()

# ══ ইউজার ম্যানেজমেন্ট ════════════════════════════════════════════════════════
elif page == "⚙️ ইউজার ম্যানেজমেন্ট":
    st.title("⚙️ ইউজার ম্যানেজমেন্ট")

    with st.form("user_form", clear_on_submit=True):
        st.markdown("### নতুন ইউজার যোগ করুন")
        c1,c2 = st.columns(2)
        nn = c1.text_input("নাম (বাংলায়)", placeholder="যেমন: সাজ্জাদ")
        nu = c2.text_input("ইউজারনেম",     placeholder="যেমন: sajjad")
        c3,c4 = st.columns(2)
        np2  = c3.text_input("পাসওয়ার্ড", type="password")
        role = c4.selectbox("ভূমিকা", ["user","admin"],
                            format_func=lambda x: "কর্মচারী" if x=="user" else "মালিক")
        if st.form_submit_button("✅ ইউজার যোগ করুন", use_container_width=True):
            if nn and nu and np2:
                if add_user(nu, np2, role, nn):
                    st.success(f"✅ '{nn}' যোগ হয়েছে! লগিন: {nu} / {np2}")
                    st.rerun()
                else: st.error("এই ইউজারনেম আগেই আছে!")
            else: st.warning("সব তথ্য পূরণ করুন।")

    st.markdown("---")
    st.markdown("### বর্তমান ইউজার তালিকা")
    for uid,uname,urole,dname in get_all_users():
        c1,c2,c3,c4 = st.columns([3,2,2,1])
        c1.markdown(f"<p style='padding-top:6px;color:#e0f0ea;font-weight:600'>{dname}</p>", unsafe_allow_html=True)
        c2.markdown(f"<p style='padding-top:6px;color:#7ecfb8'>@{uname}</p>", unsafe_allow_html=True)
        badge = "মালিক" if urole=="admin" else "কর্মচারী"
        c3.markdown(f"<p style='padding-top:6px;color:#a8d5c2'>{badge}</p>", unsafe_allow_html=True)
        if uname != "admin":
            if c4.button("🗑", key=f"du_{uid}"):
                del_user(uid); st.rerun()

    st.markdown("---")
    st.markdown("### কর্মচারীর পাসওয়ার্ড রিসেট")
    all_users = get_all_users()
    others = [(uid,f"{dn} (@{un})") for uid,un,r,dn in all_users if un != "admin"]
    if others:
        sel = st.selectbox("কর্মচারী বেছে নিন", [u[0] for u in others],
                           format_func=lambda x: next(u[1] for u in others if u[0]==x))
        rp = st.text_input("নতুন পাসওয়ার্ড", type="password", key="reset_pw")
        if st.button("🔑 পাসওয়ার্ড রিসেট করুন"):
            if rp: reset_password(sel, rp); st.success("✅ রিসেট হয়েছে!")
            else: st.warning("পাসওয়ার্ড দিন।")
    else:
        st.info("কোনো কর্মচারী নেই।")

    st.markdown("---")
    st.markdown("### 🔐 আমার (Admin) পাসওয়ার্ড পরিবর্তন")
    with st.form("admin_pw_form", clear_on_submit=True):
        old_pw  = st.text_input("বর্তমান পাসওয়ার্ড", type="password")
        new_pw1 = st.text_input("নতুন পাসওয়ার্ড", type="password")
        new_pw2 = st.text_input("নতুন পাসওয়ার্ড আবার লিখুন", type="password")
        if st.form_submit_button("✅ পাসওয়ার্ড পরিবর্তন করুন", use_container_width=True):
            if not old_pw or not new_pw1 or not new_pw2:
                st.warning("সব ঘর পূরণ করুন।")
            elif new_pw1 != new_pw2:
                st.error("নতুন পাসওয়ার্ড দুটো মিলছে না!")
            elif not login(user["username"], old_pw):
                st.error("বর্তমান পাসওয়ার্ড ভুল!")
            else:
                reset_password(user["id"], new_pw1)
                st.success("✅ পাসওয়ার্ড পরিবর্তন হয়েছে!")
