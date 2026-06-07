import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, timedelta
import os

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🍦 আইসক্রিম স্টক",
    page_icon="🍦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@400;600;700&family=Tiro+Bangla&display=swap');

html, body, [class*="css"] {
    font-family: 'Hind Siliguri', sans-serif;
}

/* Dark background */
.stApp { background: #0d1b2a; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #112236 !important;
    border-right: 1px solid #1e3a52;
}
[data-testid="stSidebar"] * { color: #a8d5c2 !important; }

/* Main headings */
h1 { color: #00e5b0 !important; font-size: 2rem !important; }
h2 { color: #00e5b0 !important; }
h3 { color: #7ecfb8 !important; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #112236;
    border: 1px solid #1e3a52;
    border-radius: 12px;
    padding: 12px 18px;
}
[data-testid="metric-container"] label { color: #7ecfb8 !important; font-size: 0.82rem !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #00e5b0 !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* Number inputs */
input[type="number"] {
    background: #1a2f45 !important;
    color: #e0f0ea !important;
    border: 1px solid #2a4a65 !important;
    border-radius: 8px !important;
}

/* Tables */
[data-testid="stDataFrame"] {
    border: 1px solid #1e3a52;
    border-radius: 10px;
    overflow: hidden;
}

/* Buttons */
.stButton button {
    background: #00e5b0 !important;
    color: #0d1b2a !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-family: 'Hind Siliguri', sans-serif !important;
    padding: 0.4rem 1.4rem !important;
    transition: all 0.2s;
}
.stButton button:hover { opacity: 0.85; transform: translateY(-1px); }

/* Delete button */
.del-btn button {
    background: #e05c5c !important;
    color: white !important;
}

/* Success / error */
.stSuccess { background: #0d2e22 !important; border-left: 4px solid #00e5b0 !important; }
.stError   { background: #2e0d0d !important; border-left: 4px solid #e05c5c !important; }

/* Selectbox */
[data-baseweb="select"] > div {
    background: #1a2f45 !important;
    border-color: #2a4a65 !important;
    color: #e0f0ea !important;
}

/* Date input */
input[type="date"] {
    background: #1a2f45 !important;
    color: #e0f0ea !important;
    border: 1px solid #2a4a65 !important;
    border-radius: 8px !important;
}

/* Divider */
hr { border-color: #1e3a52 !important; }

p, label, .stText { color: #c8e6dc !important; }
</style>
""", unsafe_allow_html=True)

# ── Database ────────────────────────────────────────────────────────────────
DB = "icecream_stock.db"

def get_conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    con = get_conn()
    con.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL,
        product_id INTEGER NOT NULL,
        opening INTEGER DEFAULT 0,
        input_qty INTEGER DEFAULT 0,
        delivery INTEGER DEFAULT 0,
        returned INTEGER DEFAULT 0,
        damaged INTEGER DEFAULT 0,
        retail INTEGER DEFAULT 0,
        closing INTEGER DEFAULT 0,
        UNIQUE(entry_date, product_id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )""")
    con.commit()
    con.close()

init_db()

def get_products():
    con = get_conn()
    rows = con.execute("SELECT id, name FROM products ORDER BY name").fetchall()
    con.close()
    return rows

def add_product(name):
    con = get_conn()
    try:
        con.execute("INSERT INTO products(name) VALUES(?)", (name.strip(),))
        con.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        con.close()

def delete_product(pid):
    con = get_conn()
    con.execute("DELETE FROM stock WHERE product_id=?", (pid,))
    con.execute("DELETE FROM products WHERE id=?", (pid,))
    con.commit()
    con.close()

def get_last_closing(product_id, before_date):
    con = get_conn()
    row = con.execute(
        "SELECT closing FROM stock WHERE product_id=? AND entry_date<? ORDER BY entry_date DESC LIMIT 1",
        (product_id, before_date)
    ).fetchone()
    con.close()
    return row[0] if row else 0

def get_entry(entry_date, product_id):
    con = get_conn()
    row = con.execute(
        "SELECT opening,input_qty,delivery,returned,damaged,retail,closing FROM stock WHERE entry_date=? AND product_id=?",
        (entry_date, product_id)
    ).fetchone()
    con.close()
    return row

def save_entry(entry_date, product_id, opening, input_qty, delivery, returned, damaged, retail):
    closing = opening + input_qty + returned - delivery - damaged - retail
    con = get_conn()
    con.execute("""INSERT INTO stock(entry_date,product_id,opening,input_qty,delivery,returned,damaged,retail,closing)
        VALUES(?,?,?,?,?,?,?,?,?)
        ON CONFLICT(entry_date,product_id) DO UPDATE SET
        opening=excluded.opening, input_qty=excluded.input_qty, delivery=excluded.delivery,
        returned=excluded.returned, damaged=excluded.damaged, retail=excluded.retail, closing=excluded.closing
    """, (entry_date, product_id, opening, input_qty, delivery, returned, damaged, retail, closing))
    con.commit()
    con.close()
    return closing

def get_report(from_date, to_date):
    con = get_conn()
    rows = con.execute("""
        SELECT s.entry_date, p.name, s.opening, s.input_qty, s.delivery,
               s.returned, s.damaged, s.retail, s.closing
        FROM stock s JOIN products p ON s.product_id=p.id
        WHERE s.entry_date BETWEEN ? AND ?
        ORDER BY s.entry_date, p.name
    """, (from_date, to_date)).fetchall()
    con.close()
    return rows

# ── Sidebar Navigation ──────────────────────────────────────────────────────
st.sidebar.markdown("## 🍦 আইসক্রিম স্টক")
st.sidebar.markdown("---")
page = st.sidebar.radio("মেনু", ["📦 দৈনিক এন্ট্রি", "📊 রিপোর্ট", "🛒 প্রোডাক্ট তালিকা"],
                         label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown("<small style='color:#4a7a6a'>ক্লোজিং = ওপেনিং + ইনপুট + রিটার্ন − ডেলিভারি − নষ্ট − খুচরা</small>",
                    unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 — দৈনিক এন্ট্রি
# ══════════════════════════════════════════════════════════════════════════════
if page == "📦 দৈনিক এন্ট্রি":
    st.title("📦 দৈনিক স্টক এন্ট্রি")

    col1, col2 = st.columns([2, 5])
    with col1:
        selected_date = st.date_input("তারিখ", value=date.today(), label_visibility="visible")

    products = get_products()
    if not products:
        st.warning("⚠️ আগে **প্রোডাক্ট তালিকা** পেজে গিয়ে প্রোডাক্ট যোগ করুন।")
        st.stop()

    st.markdown("---")

    # Column headers
    cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.8])
    headers = ["প্রোডাক্ট", "ওপেনিং", "ইনপুট", "ডেলিভারি", "রিটার্ন", "নষ্ট", "খুচরা", "ক্লোজিং"]
    for c, h in zip(cols, headers):
        c.markdown(f"<p style='color:#00e5b0;font-weight:700;font-size:0.85rem;margin-bottom:4px'>{h}</p>",
                   unsafe_allow_html=True)

    entry_data = {}
    date_str = str(selected_date)

    for pid, pname in products:
        existing = get_entry(date_str, pid)
        last_closing = get_last_closing(pid, date_str)

        if existing:
            def_opening  = existing[0]
            def_input    = existing[1]
            def_delivery = existing[2]
            def_returned = existing[3]
            def_damaged  = existing[4]
            def_retail   = existing[5]
        else:
            def_opening  = last_closing
            def_input = def_delivery = def_returned = def_damaged = def_retail = 0

        cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.8])
        cols[0].markdown(f"<p style='padding-top:8px;color:#e0f0ea;font-weight:600'>{pname}</p>",
                         unsafe_allow_html=True)

        opening  = cols[1].number_input("ওপেনিং",  value=def_opening,  min_value=0, key=f"op_{pid}",  label_visibility="collapsed")
        input_   = cols[2].number_input("ইনপুট",   value=def_input,    min_value=0, key=f"in_{pid}",  label_visibility="collapsed")
        delivery = cols[3].number_input("ডেলিভারি",value=def_delivery, min_value=0, key=f"de_{pid}",  label_visibility="collapsed")
        returned = cols[4].number_input("রিটার্ন",  value=def_returned, min_value=0, key=f"re_{pid}",  label_visibility="collapsed")
        damaged  = cols[5].number_input("নষ্ট",    value=def_damaged,  min_value=0, key=f"da_{pid}",  label_visibility="collapsed")
        retail   = cols[6].number_input("খুচরা",   value=def_retail,   min_value=0, key=f"rt_{pid}",  label_visibility="collapsed")

        closing = opening + input_ + returned - delivery - damaged - retail
        color = "#00e5b0" if closing >= 0 else "#e05c5c"
        cols[7].markdown(f"<p style='padding-top:8px;font-size:1.2rem;font-weight:700;color:{color}'>{closing}</p>",
                         unsafe_allow_html=True)

        entry_data[pid] = (opening, input_, delivery, returned, damaged, retail)

    st.markdown("---")
    if st.button("💾  সব সেভ করুন", use_container_width=False):
        for pid, (opening, input_, delivery, returned, damaged, retail) in entry_data.items():
            save_entry(date_str, pid, opening, input_, delivery, returned, damaged, retail)
        st.success(f"✅ {date_str} তারিখের ডেটা সেভ হয়েছে!")
        st.balloons()

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 — রিপোর্ট
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊 রিপোর্ট":
    st.title("📊 স্টক রিপোর্ট")

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        from_date = st.date_input("শুরুর তারিখ", value=date.today() - timedelta(days=6))
    with c2:
        to_date = st.date_input("শেষ তারিখ", value=date.today())
    with c3:
        st.markdown("<br>", unsafe_allow_html=True)
        show = st.button("🔍 রিপোর্ট দেখুন", use_container_width=True)

    if show or True:
        rows = get_report(str(from_date), str(to_date))
        if not rows:
            st.info("এই সময়ের কোনো ডেটা নেই।")
        else:
            df = pd.DataFrame(rows, columns=[
                "তারিখ", "প্রোডাক্ট", "ওপেনিং", "ইনপুট",
                "ডেলিভারি", "রিটার্ন", "নষ্ট", "খুচরা", "ক্লোজিং"
            ])

            # Summary metrics
            st.markdown("### সারসংক্ষেপ")
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("মোট ইনপুট",    int(df["ইনপুট"].sum()))
            m2.metric("মোট ডেলিভারি", int(df["ডেলিভারি"].sum()))
            m3.metric("মোট রিটার্ন",  int(df["রিটার্ন"].sum()))
            m4.metric("মোট নষ্ট",     int(df["নষ্ট"].sum()))
            m5.metric("মোট খুচরা",    int(df["খুচরা"].sum()))
            m6.metric("শেষ ক্লোজিং",  int(df["ক্লোজিং"].iloc[-1]))

            st.markdown("---")
            st.markdown("### বিস্তারিত")
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Product-wise summary
            st.markdown("### প্রোডাক্ট ভিত্তিক সারসংক্ষেপ")
            summary = df.groupby("প্রোডাক্ট").agg(
                ইনপুট=("ইনপুট","sum"),
                ডেলিভারি=("ডেলিভারি","sum"),
                রিটার্ন=("রিটার্ন","sum"),
                নষ্ট=("নষ্ট","sum"),
                খুচরা=("খুচরা","sum"),
                শেষ_ক্লোজিং=("ক্লোজিং","last")
            ).reset_index()
            st.dataframe(summary, use_container_width=True, hide_index=True)

            # CSV Download
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "⬇️ Excel-এ ডাউনলোড (CSV)",
                data=csv,
                file_name=f"stock_report_{from_date}_{to_date}.csv",
                mime="text/csv"
            )

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 — প্রোডাক্ট তালিকা
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛒 প্রোডাক্ট তালিকা":
    st.title("🛒 প্রোডাক্ট তালিকা")

    # Add product
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns([4, 1])
        new_name = col1.text_input("নতুন প্রোডাক্টের নাম", placeholder="যেমন: চকোলেট কাপ ৫০মিলি")
        submitted = col2.form_submit_button("+ যোগ করুন", use_container_width=True)
        if submitted:
            if new_name.strip():
                if add_product(new_name):
                    st.success(f"✅ '{new_name}' যোগ হয়েছে!")
                    st.rerun()
                else:
                    st.error("এই নামে প্রোডাক্ট আগেই আছে!")
            else:
                st.warning("প্রোডাক্টের নাম লিখুন।")

    st.markdown("---")

    products = get_products()
    if not products:
        st.info("এখনো কোনো প্রোডাক্ট নেই। উপরে যোগ করুন।")
    else:
        st.markdown(f"**মোট প্রোডাক্ট: {len(products)}টি**")
        st.markdown("")
        for pid, pname in products:
            col1, col2 = st.columns([6, 1])
            col1.markdown(f"<p style='padding-top:6px;color:#e0f0ea;font-size:1rem'>🍦 {pname}</p>",
                          unsafe_allow_html=True)
            with col2:
                if st.button("🗑 মুছুন", key=f"del_{pid}"):
                    delete_product(pid)
                    st.rerun()
