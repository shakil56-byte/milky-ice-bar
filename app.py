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
thead tr th { background: #112236 !important; color: #00e5b0 !important; font-weight: 700; text-align: center !important; }
tbody tr:nth-child(even) { background: #112236 !important; }
tbody tr:nth-child(odd) { background: #0d1b2a !important; }
tbody tr td { color: #e0f0ea !important; text-align: center !important; }
.stDataFrame { border: 1px solid #1e3a52; border-radius: 10px; }
div[data-testid="stForm"] { background: #112236; border: 1px solid #1e3a52; border-radius: 10px; padding: 16px; }
</style>
""", unsafe_allow_html=True)

# ── DB ──────────────────────────────────────────────────────────────────────
DB = "icecream_stock.db"

def conn():
    return sqlite3.connect(DB, check_same_thread=False)

def init_db():
    c = conn()
    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS agents (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL, product_id INTEGER NOT NULL,
        opening INTEGER DEFAULT 0, stock_in INTEGER DEFAULT 0,
        retail INTEGER DEFAULT 0, damaged INTEGER DEFAULT 0,
        closing INTEGER DEFAULT 0,
        UNIQUE(entry_date, product_id),
        FOREIGN KEY(product_id) REFERENCES products(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entry_date TEXT NOT NULL, product_id INTEGER NOT NULL, agent_id INTEGER NOT NULL,
        delivered INTEGER DEFAULT 0, returned INTEGER DEFAULT 0,
        UNIQUE(entry_date, product_id, agent_id),
        FOREIGN KEY(product_id) REFERENCES products(id),
        FOREIGN KEY(agent_id) REFERENCES agents(id))""")
    c.commit()
    c.close()

init_db()

def get_products():
    c = conn(); r = c.execute("SELECT id,name FROM products ORDER BY name").fetchall(); c.close(); return r

def get_agents():
    c = conn(); r = c.execute("SELECT id,name FROM agents ORDER BY name").fetchall(); c.close(); return r

def add_product(name):
    c = conn()
    try: c.execute("INSERT INTO products(name) VALUES(?)",(name,)); c.commit(); return True
    except: return False
    finally: c.close()

def del_product(pid):
    c = conn()
    c.execute("DELETE FROM deliveries WHERE product_id=?",(pid,))
    c.execute("DELETE FROM stock WHERE product_id=?",(pid,))
    c.execute("DELETE FROM products WHERE id=?",(pid,))
    c.commit(); c.close()

def add_agent(name):
    c = conn()
    try: c.execute("INSERT INTO agents(name) VALUES(?)",(name,)); c.commit(); return True
    except: return False
    finally: c.close()

def del_agent(aid):
    c = conn()
    c.execute("DELETE FROM deliveries WHERE agent_id=?",(aid,))
    c.execute("DELETE FROM agents WHERE id=?",(aid,))
    c.commit(); c.close()

def get_last_closing(pid, before_date):
    c = conn()
    r = c.execute("SELECT closing FROM stock WHERE product_id=? AND entry_date<? ORDER BY entry_date DESC LIMIT 1",(pid,before_date)).fetchone()
    c.close(); return r[0] if r else 0

def get_stock_row(entry_date, pid):
    c = conn()
    r = c.execute("SELECT opening,stock_in,retail,damaged,closing FROM stock WHERE entry_date=? AND product_id=?",(entry_date,pid)).fetchone()
    c.close(); return r

def get_delivery_row(entry_date, pid, aid):
    c = conn()
    r = c.execute("SELECT delivered,returned FROM deliveries WHERE entry_date=? AND product_id=? AND agent_id=?",(entry_date,pid,aid)).fetchone()
    c.close(); return r

def save_stock(entry_date, pid, opening, stock_in, retail, damaged, closing):
    c = conn()
    c.execute("""INSERT INTO stock(entry_date,product_id,opening,stock_in,retail,damaged,closing)
        VALUES(?,?,?,?,?,?,?) ON CONFLICT(entry_date,product_id) DO UPDATE SET
        opening=excluded.opening,stock_in=excluded.stock_in,retail=excluded.retail,
        damaged=excluded.damaged,closing=excluded.closing""",
        (entry_date,pid,opening,stock_in,retail,damaged,closing))
    c.commit(); c.close()

def save_delivery(entry_date, pid, aid, delivered, returned):
    c = conn()
    c.execute("""INSERT INTO deliveries(entry_date,product_id,agent_id,delivered,returned)
        VALUES(?,?,?,?,?) ON CONFLICT(entry_date,product_id,agent_id) DO UPDATE SET
        delivered=excluded.delivered,returned=excluded.returned""",
        (entry_date,pid,aid,delivered,returned))
    c.commit(); c.close()

def get_report(f, t):
    c = conn()
    agents = get_agents()
    products = get_products()
    rows = []
    for ed in pd.date_range(f, t):
        edate = str(ed.date())
        for pid, pname in products:
            sr = get_stock_row(edate, pid)
            if not sr: continue
            opening,stock_in,retail,damaged,closing = sr
            total_del = total_ret = 0
            agent_cols = {}
            for aid, aname in agents:
                dr = get_delivery_row(edate, pid, aid)
                d,r = (dr[0],dr[1]) if dr else (0,0)
                agent_cols[f"{aname}_ডেলি"] = d
                agent_cols[f"{aname}_রিটার্ন"] = r
                total_del += d; total_ret += r
            row = {"তারিখ":edate,"পণ্য":pname,"ওপেনিং":opening,"স্টক ইন":stock_in}
            row.update(agent_cols)
            row.update({"মোট ডেলিভারি":total_del,"মোট রিটার্ন":total_ret,
                        "খুচরা":retail,"নষ্ট":damaged,"ক্লোজিং":closing})
            rows.append(row)
    c.close()
    return pd.DataFrame(rows) if rows else pd.DataFrame()

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.markdown("## 🍦 মিল্কি আইস বার")
st.sidebar.markdown("---")
page = st.sidebar.radio("মেনু", ["📦 দৈনিক এন্ট্রি","📊 রিপোর্ট","🚴 ডেলিভারিম্যান","🛒 পণ্য তালিকা"], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.markdown("<small style='color:#4a7a6a'>ক্লোজিং = ওপেনিং + স্টক ইন + মোট রিটার্ন − মোট ডেলিভারি − খুচরা − নষ্ট</small>", unsafe_allow_html=True)

# ══ PAGE 1: দৈনিক এন্ট্রি ════════════════════════════════════════════════════
if page == "📦 দৈনিক এন্ট্রি":
    st.title("📦 দৈনিক স্টক এন্ট্রি")
    col1, _ = st.columns([2,5])
    with col1:
        sel_date = st.date_input("তারিখ", value=date.today())
    edate = str(sel_date)

    products = get_products()
    agents   = get_agents()

    if not products:
        st.warning("⚠️ আগে **🛒 পণ্য তালিকা** পেজে গিয়ে পণ্য যোগ করুন।")
        st.stop()
    if not agents:
        st.warning("⚠️ আগে **🚴 ডেলিভারিম্যান** পেজে গিয়ে ডেলিভারিম্যান যোগ করুন।")
        st.stop()

    # Build table header
    agent_headers = []
    for _, aname in agents:
        agent_headers += [f"{aname} ডেলিভারি", f"{aname} রিটার্ন"]

    all_headers = ["পণ্য","ওপেনিং","স্টক ইন"] + agent_headers + ["খুচরা","নষ্ট","ক্লোজিং"]
    col_widths = [2] + [1]*(len(all_headers)-1)

    # Header row
    hcols = st.columns(col_widths)
    for i, h in enumerate(all_headers):
        hcols[i].markdown(f"<p style='color:#00e5b0;font-weight:700;font-size:0.8rem;margin:0;text-align:center'>{h}</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:4px 0'>", unsafe_allow_html=True)

    # Data rows
    entry_data = {}
    for pid, pname in products:
        sr = get_stock_row(edate, pid)
        last_close = get_last_closing(pid, edate)
        op  = sr[0] if sr else last_close
        si  = sr[1] if sr else 0
        ret = sr[2] if sr else 0
        dam = sr[3] if sr else 0

        rcols = st.columns(col_widths)
        rcols[0].markdown(f"<p style='color:#e0f0ea;font-weight:600;padding-top:8px;font-size:0.9rem'>{pname}</p>", unsafe_allow_html=True)
        opening  = rcols[1].number_input("", value=op,  min_value=0, key=f"op_{pid}", label_visibility="collapsed")
        stock_in = rcols[2].number_input("", value=si,  min_value=0, key=f"si_{pid}", label_visibility="collapsed")

        agent_vals = {}
        ci = 3
        for aid, aname in agents:
            dr = get_delivery_row(edate, pid, aid)
            d_val = dr[0] if dr else 0
            r_val = dr[1] if dr else 0
            d = rcols[ci].number_input("", value=d_val, min_value=0, key=f"d_{pid}_{aid}", label_visibility="collapsed")
            r = rcols[ci+1].number_input("", value=r_val, min_value=0, key=f"r_{pid}_{aid}", label_visibility="collapsed")
            agent_vals[aid] = (d, r)
            ci += 2

        retail  = rcols[ci].number_input("",   value=ret, min_value=0, key=f"rt_{pid}", label_visibility="collapsed")
        damaged = rcols[ci+1].number_input("", value=dam, min_value=0, key=f"da_{pid}", label_visibility="collapsed")

        total_del = sum(v[0] for v in agent_vals.values())
        total_ret = sum(v[1] for v in agent_vals.values())
        closing = opening + stock_in + total_ret - total_del - retail - damaged
        color = "#00e5b0" if closing >= 0 else "#e05c5c"
        rcols[ci+2].markdown(f"<p style='color:{color};font-weight:700;font-size:1.1rem;text-align:center;padding-top:8px'>{closing}</p>", unsafe_allow_html=True)

        entry_data[pid] = {
            "opening":opening,"stock_in":stock_in,"retail":retail,
            "damaged":damaged,"closing":closing,"agents":agent_vals
        }
        st.markdown("<hr style='margin:2px 0;border-color:#1e3a52'>", unsafe_allow_html=True)

    st.markdown("")
    if st.button("💾  সব সেভ করুন", use_container_width=False):
        for pid, v in entry_data.items():
            save_stock(edate, pid, v["opening"], v["stock_in"], v["retail"], v["damaged"], v["closing"])
            for aid, (d, r) in v["agents"].items():
                save_delivery(edate, pid, aid, d, r)
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
        show = st.button("🔍 দেখুন", use_container_width=True)

    df = get_report(str(fd), str(td))
    if df.empty:
        st.info("এই সময়ের কোনো ডেটা নেই।")
    else:
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("মোট স্টক ইন",    int(df["স্টক ইন"].sum()) if "স্টক ইন" in df else 0)
        m2.metric("মোট ডেলিভারি",   int(df["মোট ডেলিভারি"].sum()) if "মোট ডেলিভারি" in df else 0)
        m3.metric("মোট রিটার্ন",    int(df["মোট রিটার্ন"].sum()) if "মোট রিটার্ন" in df else 0)
        m4.metric("মোট খুচরা",      int(df["খুচরা"].sum()) if "খুচরা" in df else 0)
        m5.metric("মোট নষ্ট",       int(df["নষ্ট"].sum()) if "নষ্ট" in df else 0)
        st.markdown("---")
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ CSV ডাউনলোড", data=csv,
            file_name=f"report_{fd}_{td}.csv", mime="text/csv")

# ══ PAGE 3: ডেলিভারিম্যান ════════════════════════════════════════════════════
elif page == "🚴 ডেলিভারিম্যান":
    st.title("🚴 ডেলিভারিম্যান তালিকা")
    with st.form("agent_form", clear_on_submit=True):
        c1,c2 = st.columns([4,1])
        new_agent = c1.text_input("নতুন ডেলিভারিম্যানের নাম", placeholder="যেমন: সাজ্জাদ")
        if c2.form_submit_button("+ যোগ", use_container_width=True):
            if new_agent.strip():
                if add_agent(new_agent.strip()): st.rerun()
                else: st.error("এই নাম আগেই আছে!")
            else: st.warning("নাম লিখুন।")
    st.markdown("---")
    agents = get_agents()
    if not agents:
        st.info("এখনো কেউ নেই। উপরে যোগ করুন।")
    else:
        for aid, aname in agents:
            c1,c2 = st.columns([6,1])
            c1.markdown(f"<p style='padding-top:6px;color:#e0f0ea;font-size:1rem'>🚴 {aname}</p>", unsafe_allow_html=True)
            if c2.button("🗑", key=f"da_{aid}"):
                del_agent(aid); st.rerun()

# ══ PAGE 4: পণ্য তালিকা ══════════════════════════════════════════════════════
elif page == "🛒 পণ্য তালিকা":
    st.title("🛒 পণ্য তালিকা")
    with st.form("prod_form", clear_on_submit=True):
        c1,c2 = st.columns([4,1])
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
            c1,c2 = st.columns([6,1])
            c1.markdown(f"<p style='padding-top:6px;color:#e0f0ea;font-size:1rem'>🍦 {pname}</p>", unsafe_allow_html=True)
            if c2.button("🗑", key=f"dp_{pid}"):
                del_product(pid); st.rerun()
