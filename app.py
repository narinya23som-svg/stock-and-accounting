import streamlit as st
import pandas as pd
import sqlite3

# ตั้งค่าหน้าเว็บ
st.set_page_config(
    page_title="ระบบจัดการสต็อกและบัญชีสหกรณ์",
    page_icon="🏛️",
    layout="wide"
)

# ------------------ 1. DATABASE SETUP (SQLITE) ------------------
DB_NAME = "coop_database.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ตารางสินค้า
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cost REAL NOT NULL,
            price REAL NOT NULL,
            qty INTEGER NOT NULL
        )
    """)
    
    # ตารางประวัติการขาย
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            product_name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            total_price REAL NOT NULL,
            total_cost REAL NOT NULL,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ตารางประวัติรายจ่าย
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ------------------ 2. DATABASE HELPER FUNCTIONS ------------------
def load_products():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    if not df.empty:
        # แปลงค่าให้เป็นตัวเลขที่ถูกต้อง ป้องกันปัญหา binary bytes
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0).astype(int)
    return df

def add_product(p_id, p_name, p_cost, p_price, p_qty):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO products (id, name, cost, price, qty) VALUES (?, ?, ?, ?, ?)",
        (str(p_id), str(p_name), float(p_cost), float(p_price), int(p_qty))
    )
    conn.commit()
    conn.close()

def update_product_qty(p_id, new_qty):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET qty = ? WHERE id = ?", (int(new_qty), str(p_id)))
    conn.commit()
    conn.close()

def delete_product(p_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE id = ?", (str(p_id),))
    conn.commit()
    conn.close()

def record_sale(p_id, p_name, qty, price, total_price, total_cost, current_stock):
    conn = get_db_connection()
    cursor = conn.cursor()
    new_stock = int(current_stock) - int(qty)
    cursor.execute("UPDATE products SET qty = ? WHERE id = ?", (new_stock, str(p_id)))
    cursor.execute(
        """INSERT INTO sales (product_id, product_name, qty, price_per_unit, total_price, total_cost)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(p_id), str(p_name), int(qty), float(price), float(total_price), float(total_cost))
    )
    conn.commit()
    conn.close()

def load_sales():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM sales ORDER BY id DESC", conn)
    conn.close()
    return df

def add_expense(desc, amount):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO expenses (description, amount) VALUES (?, ?)", (str(desc), float(amount)))
    conn.commit()
    conn.close()

def load_expenses():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
    conn.close()
    return df

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# ------------------ 3. HEADER & NAVIGATION ------------------
st.title("🏛️ ระบบจัดการสต็อกและบัญชีสหกรณ์")
st.caption("ระบบสำหรับบริหารจัดการคลังสินค้า บันทึกการขาย รายจ่าย และจัดสรรกำไรสหกรณ์ (บันทึกข้อมูลถาวรด้วย SQLite)")

menu = st.sidebar.radio(
    "เลือกเมนูการทำงาน",
    [
        "📊 แดชบอร์ดภาพรวม",
        "📦 จัดการสต็อกสินค้า",
        "🛒 บันทึกการขาย",
        "💸 บันทึกรายจ่ายอื่นๆ",
        "📊 สรุปบัญชีประจำปี & จัดสรรกำไร"
    ]
)

df_products = load_products()
df_sales = load_sales()
df_expenses = load_expenses()

# ------------------ 4. MENU 1: OVERVIEW DASHBOARD ------------------
if menu == "📊 แดชบอร์ดภาพรวม":
    st.header("📊 ภาพรวมการดำเนินงาน")
    
    total_rev = df_sales["total_price"].sum() if not df_sales.empty else 0.0
    total_cogs = df_sales["total_cost"].sum() if not df_sales.empty else 0.0
    other_exp = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
    total_exp = total_cogs + other_exp
    net_profit = total_rev - total_exp
    total_stock_qty = df_products["qty"].sum() if not df_products.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("รายรับรวม", f"฿{total_rev:,.2f}")
    col2.metric("รายจ่ายรวม", f"฿{total_exp:,.2f}")
    col3.metric("กำไรสุทธิ", f"฿{net_profit:,.2f}")
    col4.metric("สินค้าคงคลังรวม (ชิ้น)", f"{total_stock_qty:,}")

    st.divider()

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📦 ปริมาณสินค้าคงเหลือในคลัง")
        if not df_products.empty:
            st.bar_chart(df_products.set_index("name")["qty"])
        else:
            st.info("ℹ️ ยังไม่มีสินค้าในคลังสินค้า")

    with col_right:
        st.subheader("⚠️ สินค้าใกล้หมด (น้อยกว่า 10 ชิ้น)")
        if not df_products.empty:
            low_stock = df_products[df_products["qty"] < 10][["id", "name", "qty"]].rename(
                columns={"id": "รหัส", "name": "ชื่อ", "qty": "คงเหลือ"}
            )
            if not low_stock.empty:
                st.dataframe(low_stock, hide_index=True, use_container_width=True)
            else:
                st.success("สินค้าทุกรายการมีจำนวนเพียงพอ")
        else:
            st.caption("ยังไม่มีรายการสินค้า")

# ------------------ 5. MENU 2: INVENTORY MANAGEMENT ------------------
elif menu == "📦 จัดการสต็อกสินค้า":
    st.header("📦 รายการสินค้าและคลังสินค้า")

    tab1, tab2 = st.tabs(["➕ เพิ่มสินค้าใหม่", "⚙️ ลบ / แก้ไขสต็อกสินค้า"])

    with tab1:
        st.subheader("เพิ่มสินค้าใหม่เข้าสต็อก")
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            p_id = col1.text_input("รหัสสินค้า (เช่น P001)").strip()
            p_name = col2.text_input("ชื่อสินค้า").strip()
            
            col3, col4, col5 = st.columns(3)
            p_cost = col3.number_input("ต้นทุนต่อชิ้น (บาท)", min_value=0.0, step=1.0)
            p_price = col4.number_input("ราคาขายต่อชิ้น (บาท)", min_value=0.0, step=1.0)
            p_qty = col5.number_input("จำนวนเข้าสต็อก (ชิ้น)", min_value=1, step=1)

            submitted = st.form_submit_button("➕ บันทึกสินค้าเข้าสต็อก")
            if submitted:
                if not p_id or not p_name:
                    st.error("❌ กรุณากรอกรหัสสินค้าและชื่อสินค้าให้ครบถ้วน")
                elif not df_products.empty and p_id in df_products["id"].values:
                    st.error("❌ รหัสสินค้านี้มีอยู่ในระบบแล้ว")
                else:
                    add_product(p_id, p_name, p_cost, p_price, p_qty)
                    st.success(f"✅ เพิ่มสินค้า '{p_name}' เข้าฐานข้อมูลเรียบร้อยแล้ว!")
                    st.rerun()

    with tab2:
        st.subheader("⚙️ จัดการ / ลบสินค้าออกจากระบบ")
        if df_products.empty:
            st.info("ไม่มีรายการสินค้าให้จัดการ")
        else:
            product_list = [f"{row['id']} - {row['name']} (คงเหลือ: {int(row['qty'])} ชิ้น)" for _, row in df_products.iterrows()]
            selected_option = st.selectbox("เลือกสินค้าที่ต้องการจัดการ", product_list)
            selected_id = selected_option.split(" - ")[0]
            selected_row = df_products[df_products["id"] == selected_id].iloc[0]

            col_edit1, col_edit2 = st.columns(2)

            with col_edit1:
                st.write("**ปรับเปลี่ยนจำนวนสินค้าในคลัง**")
                current_q = int(selected_row["qty"])
                new_qty = st.number_input("กำหนดจำนวนคงเหลือใหม่ (ชิ้น)", min_value=0, value=current_q, step=1)
                if st.button("💾 อัปเดตจำนวนสินค้า"):
                    update_product_qty(selected_id, new_qty)
                    st.success(f"✅ ปรับปรุงจำนวน '{selected_row['name']}' เป็น {new_qty} ชิ้นเรียบร้อย!")
                    st.rerun()

            with col_edit2:
                st.write("**ลบสินค้าออกจากระบบอย่างถาวร**")
                st.caption("⚠️ เมื่อลบแล้ว รายการสินค้านี้จะหายไปจากฐานข้อมูลทันที")
                if st.button("🗑️ ลบสินค้านี้ออกจากระบบ", type="primary"):
                    delete_product(selected_id)
                    st.success("🗑️ ลบรายการสินค้าออกจากฐานข้อมูลเรียบร้อยแล้ว!")
                    st.rerun()

    st.divider()

    st.subheader("📋 รายการสินค้าทั้งหมดในสต็อก")
    
    if not df_products.empty:
        search_query = st.text_input("🔍 ค้นหาสินค้า (พิมพ์รหัสหรือชื่อสินค้า):", "").strip().lower()
        
        filtered_df = df_products.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["id"].str.lower().str.contains(search_query) | 
                filtered_df["name"].str.lower().str.contains(search_query)
            ]
        
        filtered_df["มูลค่าคลังรวม"] = filtered_df["price"] * filtered_df["qty"]
        display_df = filtered_df.rename(columns={
            "id": "รหัสสินค้า",
            "name": "ชื่อสินค้า",
            "cost": "ต้นทุนต่อชิ้น",
            "price": "ราคาขายต่อชิ้น",
            "qty": "จำนวนคงเหลือ"
        })
        
        st.dataframe(display_df, hide_index=True, use_container_width=True)
        
        csv_data = convert_df_to_csv(display_df)
        st.download_button(
            label="📥 ดาวน์โหลดรายการสินค้าทั้งหมด (ไฟล์ CSV)",
            data=csv_data,
            file_name="coop_inventory_report.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("ℹ️ ยังไม่มีรายการสินค้าในระบบ")

# ------------------ 6. MENU 3: RECORD SALES ------------------
elif menu == "🛒 บันทึกการขาย":
    st.header("🛒 บันทึกการขายสินค้า")

    if df_products.empty:
        st.warning("⚠️ ยังไม่มีสินค้าในสต็อก!")
    else:
        col_form, col_hist = st.columns([1, 1])

        with col_form:
            st.subheader("📝 ทำรายการขาย")
            
            search_sale = st.text_input("🔍 ค้นหาสินค้าที่จะขาย (รหัส/ชื่อ):", "").strip().lower()
            
            sale_products = df_products.copy()
            if search_sale:
                sale_products = sale_products[
                    sale_products["id"].str.lower().str.contains(search_sale) | 
                    sale_products["name"].str.lower().str.contains(search_sale)
                ]

            if sale_products.empty:
                st.error("❌ ไม่พบสินค้าที่ค้นหา")
            else:
                product_options = {
                    f"{row['id']} - {row['name']} (คงเหลือ: {int(row['qty'])} ชิ้น)": row['id']
                    for _, row in sale_products.iterrows()
                }
                selected_option = st.selectbox("เลือกสินค้าที่ต้องการขาย", list(product_options.keys()))
                selected_id = product_options[selected_option]
                selected_row = df_products[df_products["id"] == selected_id].iloc[0]

                stock_qty = int(selected_row["qty"])

                if stock_qty <= 0:
                    st.error("❌ สินค้าชิ้นนี้หมดสต็อกแล้ว ไม่สามารถขายได้")
                else:
                    qty_to_sell = st.number_input(
                        "จำนวนที่ขาย", 
                        min_value=1, 
                        max_value=stock_qty, 
                        step=1
                    )

                    total_sale_price = float(selected_row["price"]) * qty_to_sell
                    total_sale_cost = float(selected_row["cost"]) * qty_to_sell
                    st.write(f"**ราคารวมทั้งสิ้น:** ฿{total_sale_price:,.2f}")

                    if st.button("✅ ยืนยันการขายและตัดสต็อก", use_container_width=True):
                        record_sale(
                            selected_id, 
                            selected_row["name"], 
                            qty_to_sell, 
                            selected_row["price"], 
                            total_sale_price, 
                            total_sale_cost, 
                            stock_qty
                        )
                        st.success(f"✅ บันทึกการขายสำเร็จ! (ยอดขาย ฿{total_sale_price:,.2f})")
                        st.rerun()

        with col_hist:
            st.subheader("📜 ประวัติการขายล่าสุด")
            if not df_sales.empty:
                display_sales = df_sales[["product_id", "product_name", "qty", "total_price", "sale_date"]].rename(columns={
                    "product_id": "รหัสสินค้า",
                    "product_name": "ชื่อสินค้า",
                    "qty": "จำนวน",
                    "total_price": "ยอดขายรวม",
                    "sale_date": "วันที่-เวลา"
                })
                st.dataframe(display_sales, hide_index=True, use_container_width=True)
            else:
                st.info("ยังไม่มีประวัติการขายในระบบ")

# ------------------ 7. MENU 4: RECORD EXPENSES ------------------
elif menu == "💸 บันทึกรายจ่ายอื่นๆ":
    st.header("💸 บันทึกรายจ่ายประจำวัน/ดำเนินงาน")

    col_exp_form, col_exp_hist = st.columns([1, 1])

    with col_exp_form:
        st.subheader("📝 บันทึกรายการใหม่")
        with st.form("expense_form", clear_on_submit=True):
            exp_desc = st.text_input("รายละเอียดรายจ่าย").strip()
            exp_amount = st.number_input("จำนวนเงิน (บาท)", min_value=1.0, step=10.0)
            
            submitted_exp = st.form_submit_button("💸 บันทึกรายจ่าย")
            if submitted_exp:
                if not exp_desc:
                    st.error("❌ กรุณากรอกรายละเอียดรายจ่าย")
                else:
                    add_expense(exp_desc, exp_amount)
                    st.success(f"✅ บันทึกรายจ่ายเรียบร้อย!")
                    st.rerun()

    with col_exp_hist:
        st.subheader("📜 ประวัติรายจ่ายอื่นๆ")
        if not df_expenses.empty:
            display_expenses = df_expenses[["description", "amount", "expense_date"]].rename(columns={
                "description": "รายการ",
                "amount": "จำนวนเงิน (บาท)",
                "expense_date": "วันที่-เวลา"
            })
            st.dataframe(display_expenses, hide_index=True, use_container_width=True)
        else:
            st.info("ยังไม่มีบันทึกรายจ่ายอื่นๆ ในระบบ")

# ------------------ 8. MENU 5: ANNUAL SUMMARY ------------------
elif menu == "📊 สรุปบัญชีประจำปี & จัดสรรกำไร":
    st.header("🏛️ สรุปผลการดำเนินงานประจำปี")

    total_revenue = df_sales["total_price"].sum() if not df_sales.empty else 0.0
    total_cogs = df_sales["total_cost"].sum() if not df_sales.empty else 0.0
    other_expenses = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
    total_expenses = total_cogs + other_expenses
    net_profit = total_revenue - total_expenses

    summary_table = [
        {"รายการ": "1. รายรับรวมจากการขาย", "จำนวนเงิน (บาท)": f"฿{total_revenue:,.2f}"},
        {"รายการ": "2.1 ต้นทุนสินค้าที่ขาย (COGS)", "จำนวนเงิน (บาท)": f"฿{total_cogs:,.2f}"},
        {"รายการ": "2.2 รายจ่ายดำเนินงานอื่นๆ", "จำนวนเงิน (บาท)": f"฿{other_expenses:,.2f}"},
        {"รายการ": "2. รวมรายจ่ายทั้งสิ้น", "จำนวนเงิน (บาท)": f"฿{total_expenses:,.2f}"},
        {"รายการ": "3. กำไรสุทธิประจำปี", "จำนวนเงิน (บาท)": f"฿{net_profit:,.2f}"}
    ]
    st.table(pd.DataFrame(summary_table))

    if net_profit > 0:
        reserve_rate = st.slider("เปอร์เซ็นต์หักเข้าทุนสำรอง (%)", min_value=10, max_value=100, value=10)
        reserve_amount = net_profit * (reserve_rate / 100.0)
        dividend_pool = net_profit - reserve_amount

        col_res1, col_res2 = st.columns(2)
        col_res1.success(f"🏛️ **ทุนสำรอง ({reserve_rate}%):** ฿{reserve_amount:,.2f}")
        col_res2.info(f"🎁 **สำหรับจัดสรรปันผล:** ฿{dividend_pool:,.2f}")
