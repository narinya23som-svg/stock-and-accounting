import streamlit as st, pandas as pd, sqlite3

st.set_page_config(page_title="ระบบสหกรณ์โรงเรียน", page_icon="🏫", layout="wide")

# --- 1. Database Helper ---
def run_sql(query, params=(), fetch=False):
    with sqlite3.connect("coop_database.db") as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()
        return pd.read_sql_query(query, conn, params=params) if fetch else None

# สร้างตาราง
run_sql("CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, name TEXT, cost REAL, price REAL, qty INT)")
run_sql("CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT, product_name TEXT, qty INT, price_per_unit REAL, total_price REAL, total_cost REAL, sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
run_sql("CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT, amount REAL, expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

# ดึงข้อมูล
df_products = run_sql("SELECT * FROM products", fetch=True)
df_sales = run_sql("SELECT * FROM sales ORDER BY id DESC", fetch=True)
df_expenses = run_sql("SELECT * FROM expenses ORDER BY id DESC", fetch=True)

# --- 2. เมนูหลัก ---
st.title("🏫 โปรแกรมสหกรณ์ร้านค้าโรงเรียน")
menu = st.sidebar.radio("เมนูหลัก", ["📊 หน้าแรก (Dashboard)", "📦 จัดการสินค้าในสต็อก", "🛒 ขายสินค้า", "💸 บันทึกค่าใช้จ่าย", "📊 สรุปยอดและแบ่งปันผล"])

# --- 3. หน้า Dashboard ---
if menu == "📊 หน้าแรก (Dashboard)":
    st.header("📊 สรุปภาพรวมของร้านค้า")
    rev = df_sales["total_price"].sum() if not df_sales.empty else 0.0
    cogs = df_sales["total_cost"].sum() if not df_sales.empty else 0.0
    exp = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
    stock = df_products["qty"].sum() if not df_products.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ยอดขายรวม", f"฿{rev:,.2f}"); c2.metric("ค่าใช้จ่ายรวม", f"฿{(cogs+exp):,.2f}")
    c3.metric("กำไรสุทธิ", f"฿{(rev-cogs-exp):,.2f}"); c4.metric("สินค้าเหลือในคลัง", f"{stock:,}")
    st.divider()
    
    col_l, col_r = st.columns([2, 1])
    with col_l:
        st.subheader("📦 จำนวนสินค้าคงเหลือ")
        if not df_products.empty:
            st.bar_chart(df_products.set_index("name")["qty"])
        else:
            st.info("ไม่มีข้อมูลสินค้า")
            
    with col_r:
        st.subheader("⚠️ สินค้าเหลือน้อย (< 10)")
        if not df_products.empty:
            alert = df_products[df_products["qty"] < 10][["id", "name", "qty"]]
            if not alert.empty:
                st.dataframe(alert, hide_index=True)
            else:
                st.success("สินค้าเพียงพอ")
        else:
            st.success("สินค้าเพียงพอ")

# --- 4. จัดการสินค้า ---
elif menu == "📦 จัดการสินค้าในสต็อก":
    st.header("📦 หน้าจัดการคลังสินค้า")
    t1, t2 = st.tabs(["➕ เพิ่มสินค้าใหม่", "✏️ แก้ไข/ลบสินค้า"])
    
    with t1:
        with st.form("add_p"):
            p_id = st.text_input("รหัสสินค้า").strip()
            p_name = st.text_input("ชื่อสินค้า").strip()
            p_cost = st.number_input("ราคาทุน", min_value=0.0)
            p_price = st.number_input("ราคาขาย", min_value=0.0)
            p_qty = st.number_input("จำนวน", min_value=1)
            if st.form_submit_button("บันทึก") and p_id and p_name:
                run_sql("INSERT INTO products VALUES (?,?,?,?,?)", (p_id, p_name, p_cost, p_price, p_qty))
                st.success("บันทึกสำเร็จ!"); st.rerun()

    with t2:
        if not df_products.empty:
            p_sel = st.selectbox("เลือกสินค้า", [f"{r.id} - {r['name']}" for _, r in df_products.iterrows()])
            pid = p_sel.split(" - ")[0]
            row = df_products[df_products["id"] == pid].iloc[0]
            with st.form("edit_p"):
                ename = st.text_input("ชื่อ", value=row["name"])
                eqty = st.number_input("จำนวน", value=int(row["qty"]))
                ecost = st.number_input("ทุน", value=float(row["cost"]))
                eprice = st.number_input("ขาย", value=float(row["price"]))
                if st.form_submit_button("อัปเดต"):
                    run_sql("UPDATE products SET name=?, cost=?, price=?, qty=? WHERE id=?", (ename, ecost, eprice, eqty, pid))
                    st.success("อัปเดตแล้ว!"); st.rerun()
            if st.button("ลบสินค้า"):
                run_sql("DELETE FROM products WHERE id=?", (pid,)); st.rerun()

    st.subheader("📋 รายการสินค้าทั้งหมด")
    if not df_products.empty:
        st.dataframe(df_products, hide_index=True)

# --- 5. ขายสินค้า ---
elif menu == "🛒 ขายสินค้า":
    st.header("🛒 หน้าบันทึกการขายสินค้า")
    if not df_products.empty:
        t1, t2 = st.tabs(["📝 ทำรายการขาย", "✏️ แก้ไข/ยกเลิกรายการขาย"])
        with t1:
            p_sel = st.selectbox("เลือกสินค้าที่จะขาย", [f"{r.id} - {r['name']} (เหลือ {r.qty})" for _, r in df_products.iterrows()])
            pid = p_sel.split(" - ")[0]
            item = df_products[df_products["id"] == pid].iloc[0]
            sell_qty = st.number_input("จำนวนที่ขาย", min_value=1, max_value=int(item["qty"]))
            tot_price, tot_cost = sell_qty * item["price"], sell_qty * item["cost"]
            st.write(f"**ราคารวม:** ฿{tot_price:,.2f}")
            if st.button("ยืนยันการขาย"):
                run_sql("UPDATE products SET qty = qty - ? WHERE id = ?", (sell_qty, pid))
                run_sql("INSERT INTO sales (product_id, product_name, qty, price_per_unit, total_price, total_cost) VALUES (?,?,?,?,?,?)",
                        (pid, item["name"], sell_qty, item["price"], tot_price, tot_cost))
                st.success("ขายสำเร็จ!"); st.rerun()
        with t2:
            if not df_sales.empty:
                s_sel = st.selectbox("เลือกบิลที่จะยกเลิก", [f"บิล #{r.id} - {r.product_name}" for _, r in df_sales.iterrows()])
                sid = s_sel.split(" - ")[0].replace("บิล #", "")
                if st.button("ยกเลิกบิลนี้"):
                    s_row = df_sales[df_sales["id"] == int(sid)].iloc[0]
                    run_sql("UPDATE products SET qty = qty + ? WHERE id = ?", (s_row["qty"], s_row["product_id"]))
                    run_sql("DELETE FROM sales WHERE id = ?", (sid,))
                    st.success("ยกเลิกเรียบร้อย!"); st.rerun()

# --- 6. บันทึกค่าใช้จ่าย ---
elif menu == "💸 บันทึกค่าใช้จ่าย":
    st.header("💸 หน้าบันทึกค่าใช้จ่าย")
    with st.form("exp_form"):
        desc = st.text_input("รายละเอียด")
        amt = st.number_input("จำนวนเงิน", min_value=1.0)
        if st.form_submit_button("บันทึก") and desc:
            run_sql("INSERT INTO expenses (description, amount) VALUES (?,?)", (desc, amt))
            st.success("บันทึกเรียบร้อย!"); st.rerun()
    st.dataframe(df_expenses, hide_index=True)

# --- 7. สรุปบัญชีและปันผล ---
elif menu == "📊 สรุปยอดและแบ่งปันผล":
    st.header("📊 สรุปบัญชีและการจัดสรรเงินปันผล")
    rev = df_sales["total_price"].sum() if not df_sales.empty else 0.0
    cogs = df_sales["total_cost"].sum() if not df_sales.empty else 0.0
    exp = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
    profit = rev - (cogs + exp)
    
    st.write(f"- **รายรับรวม:** ฿{rev:,.2f}\n- **รวมค่าใช้จ่าย:** ฿{(cogs+exp):,.2f}\n- **กำไรสุทธิ:** ฿{profit:,.2f}")
    if profit > 0:
        pct = st.slider("% หักเข้าทุนสำรองโรงเรียน", 10, 100, 10)
        st.success(f"🏫 **เงินทุนสำรอง ({pct}%):** ฿{(profit * pct / 100):,.2f}")
        st.info(f"🎁 **เงินปันผลสมาชิก:** ฿{(profit * (100 - pct) / 100):,.2f}")
