import streamlit as st
import pandas as pd
import sqlite3

# ==========================================
# ระบบจัดการสต็อกและบัญชีร้านค้าสหกรณ์โรงเรียน
# ==========================================

st.set_page_config(
    page_title="ระบบสหกรณ์โรงเรียน",
    page_icon="🏫",
    layout="wide"
)

# ---------------- 1. สร้างฐานข้อมูล SQLite ----------------
DB_NAME = "coop_database.db"

def connect_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = connect_db()
    c = conn.cursor()
    
    # ตารางเก็บข้อมูลสินค้า
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            cost REAL NOT NULL,
            price REAL NOT NULL,
            qty INTEGER NOT NULL
        )
    """)
    
    # ตารางเก็บประวัติการขาย
    c.execute("""
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
    
    # ตารางเก็บประวัติรายจ่าย
    c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

create_tables()

# ---------------- 2. ฟังก์ชันจัดการข้อมูล (Database Helper) ----------------
def get_all_products():
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    if not df.empty:
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce').fillna(0.0)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
        df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0).astype(int)
    return df

def save_new_product(p_id, p_name, p_cost, p_price, p_qty):
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO products (id, name, cost, price, qty) VALUES (?, ?, ?, ?, ?)",
        (str(p_id), str(p_name), float(p_cost), float(p_price), int(p_qty))
    )
    conn.commit()
    conn.close()

def update_product_data(p_id, p_name, p_cost, p_price, new_qty):
    conn = connect_db()
    c = conn.cursor()
    c.execute(
        "UPDATE products SET name = ?, cost = ?, price = ?, qty = ? WHERE id = ?",
        (str(p_name), float(p_cost), float(p_price), int(new_qty), str(p_id))
    )
    conn.commit()
    conn.close()

def remove_product(p_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (str(p_id),))
    conn.commit()
    conn.close()

def save_sale_transaction(p_id, p_name, qty, price, total_price, total_cost, current_stock):
    conn = connect_db()
    c = conn.cursor()
    new_stock = int(current_stock) - int(qty)
    c.execute("UPDATE products SET qty = ? WHERE id = ?", (new_stock, str(p_id)))
    c.execute(
        """INSERT INTO sales (product_id, product_name, qty, price_per_unit, total_price, total_cost)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (str(p_id), str(p_name), int(qty), float(price), float(total_price), float(total_cost))
    )
    conn.commit()
    conn.close()

def edit_sale_transaction(sale_id, p_id, old_qty, new_qty, new_price, unit_cost):
    conn = connect_db()
    c = conn.cursor()
    
    qty_diff = new_qty - old_qty
    
    c.execute("SELECT qty FROM products WHERE id = ?", (str(p_id),))
    prod = c.fetchone()
    
    if prod:
        current_qty = prod["qty"]
        adjusted_stock = current_qty - qty_diff
        c.execute("UPDATE products SET qty = ? WHERE id = ?", (adjusted_stock, str(p_id)))
    
    total_price = new_qty * new_price
    total_cost = new_qty * unit_cost
    
    c.execute(
        """UPDATE sales 
           SET qty = ?, price_per_unit = ?, total_price = ?, total_cost = ? 
           WHERE id = ?""",
        (int(new_qty), float(new_price), float(total_price), float(total_cost), int(sale_id))
    )
    conn.commit()
    conn.close()

def cancel_sale_transaction(sale_id, p_id, qty_to_return):
    conn = connect_db()
    c = conn.cursor()
    
    c.execute("SELECT qty FROM products WHERE id = ?", (str(p_id),))
    prod = c.fetchone()
    if prod:
        c.execute("UPDATE products SET qty = ? WHERE id = ?", (prod["qty"] + qty_to_return, str(p_id)))
        
    c.execute("DELETE FROM sales WHERE id = ?", (int(sale_id),))
    conn.commit()
    conn.close()

def get_all_sales():
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM sales ORDER BY id DESC", conn)
    conn.close()
    return df

def save_expense(desc, amount):
    conn = connect_db()
    c = conn.cursor()
    c.execute("INSERT INTO expenses (description, amount) VALUES (?, ?)", (str(desc), float(amount)))
    conn.commit()
    conn.close()

def edit_expense(exp_id, desc, amount):
    conn = connect_db()
    c = conn.cursor()
    c.execute("UPDATE expenses SET description = ?, amount = ? WHERE id = ?", (str(desc), float(amount), int(exp_id)))
    conn.commit()
    conn.close()

def remove_expense(exp_id):
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id = ?", (int(exp_id),))
    conn.commit()
    conn.close()

def get_all_expenses():
    conn = connect_db()
    df = pd.read_sql_query("SELECT * FROM expenses ORDER BY id DESC", conn)
    conn.close()
    return df

def make_csv_file(df):
    return df.to_csv(index=False).encode('utf-8-sig')

# ---------------- 3. หน้าต่างโปรแกรมหลัก & แถบเมนู ----------------
st.title("🏫 โปรแกรมสหกรณ์ร้านค้าโรงเรียน")

menu_choice = st.sidebar.radio(
    "เมนูหลัก",
    [
        "📊 หน้าแรก (Dashboard)",
        "📦 จัดการสินค้าในสต็อก",
        "🛒 ขายสินค้า",
        "💸 บันทึกค่าใช้จ่าย",
        "📊 สรุปยอดและแบ่งปันผล"
    ]
)

df_products = get_all_products()
df_sales = get_all_sales()
df_expenses = get_all_expenses()

# ---------------- 4. เมนูที่ 1: หน้าแรก Dashboard ----------------
if menu_choice == "📊 หน้าแรก (Dashboard)":
    st.header("📊 สรุปภาพรวมของร้านค้า")
    
    sum_revenue = df_sales["total_price"].sum() if not df_sales.empty else 0.0
    sum_cogs = df_sales["total_cost"].sum() if not df_sales.empty else 0.0
    sum_expenses = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
    total_all_expenses = sum_cogs + sum_expenses
    total_net_profit = sum_revenue - total_all_expenses
    count_stock = df_products["qty"].sum() if not df_products.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("ยอดขายรวม", f"฿{sum_revenue:,.2f}")
    col2.metric("ค่าใช้จ่ายรวม", f"฿{total_all_expenses:,.2f}")
    col3.metric("กำไรสุทธิ", f"฿{total_net_profit:,.2f}")
    col4.metric("สินค้าเหลือในคลัง (ชิ้น)", f"{count_stock:,}")

    st.divider()

    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📦 กราฟแสดงจำนวนสินค้าคงเหลือ")
        if not df_products.empty:
            st.bar_chart(df_products.set_index("name")["qty"])
        else:
            st.info("ยังไม่มีข้อมูลสินค้าในระบบ")

    with col_right:
        st.subheader("⚠️ เตือนสินค้าเหลือน้อย (< 10)")
        if not df_products.empty:
            alert_stock = df_products[df_products["qty"] < 10][["id", "name", "qty"]].rename(
                columns={"id": "รหัส", "name": "ชื่อสินค้า", "qty": "คงเหลือ"}
            )
            if not alert_stock.empty:
                st.dataframe(alert_stock, hide_index=True, use_container_width=True)
            else:
                st.success("สินค้ายังมีพอขายทุกรายการ")
        else:
            st.caption("ไม่มีรายการสินค้า")

# ---------------- 5. เมนูที่ 2: จัดการสินค้าในสต็อก ----------------
elif menu_choice == "📦 จัดการสินค้าในสต็อก":
    st.header("📦 หน้าจัดการคลังสินค้า")

    tab1, tab2 = st.tabs(["➕ เพิ่มสินค้าใหม่", "✏️ แก้ไข/ลบสินค้า"])

    with tab1:
        st.subheader("กรอกข้อมูลเพื่อเพิ่มสินค้าใหม่")
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            input_id = col1.text_input("รหัสสินค้า (เช่น P01)").strip()
            input_name = col2.text_input("ชื่อสินค้า").strip()
            
            col3, col4, col5 = st.columns(3)
            input_cost = col3.number_input("ราคาทุนต่อชิ้น (บาท)", min_value=0.0, step=1.0)
            input_price = col4.number_input("ราคาขายต่อชิ้น (บาท)", min_value=0.0, step=1.0)
            input_qty = col5.number_input("จำนวนที่นำมาเพิ่ม (ชิ้น)", min_value=1, step=1)

            btn_save = st.form_submit_button("บันทึกสินค้าใหม่")
            if btn_save:
                if not input_id or not input_name:
                    st.error("กรุณากรอกรหัสและชื่อสินค้าให้ครบด้วยครับ")
                elif not df_products.empty and input_id in df_products["id"].values:
                    st.error("รหัสสินค้านี้ซ้ำครับ กรุณาใช้รหัสอื่น")
                else:
                    save_new_product(input_id, input_name, input_cost, input_price, input_qty)
                    st.success(f"บันทึกสินค้า '{input_name}' สำเร็จแล้ว!")
                    st.rerun()

    with tab2:
        st.subheader("แก้ไขข้อมูลสินค้า หรือลบออกจากระบบ")
        if df_products.empty:
            st.info("ไม่มีรายการสินค้า")
        else:
            product_list = [f"{row['id']} - {row['name']} (เหลือ: {int(row['qty'])} ชิ้น)" for _, row in df_products.iterrows()]
            selected_option = st.selectbox("เลือกสินค้าที่ต้องการจัดการ", product_list)
            selected_id = selected_option.split(" - ")[0]
            selected_row = df_products[df_products["id"] == selected_id].iloc[0]

            with st.form("edit_product_form"):
                col_e1, col_e2 = st.columns(2)
                edit_name = col_e1.text_input("ชื่อสินค้า", value=selected_row["name"])
                edit_qty = col_e2.number_input("จำนวนคงเหลือ (ชิ้น)", min_value=0, value=int(selected_row["qty"]), step=1)

                col_e3, col_e4 = st.columns(2)
                edit_cost = col_e3.number_input("ราคาทุน (บาท)", min_value=0.0, value=float(selected_row["cost"]), step=1.0)
                edit_price = col_e4.number_input("ราคาขาย (บาท)", min_value=0.0, value=float(selected_row["price"]), step=1.0)

                btn_update = st.form_submit_button("บันทึกการแก้ไข")
                
                if btn_update:
                    update_product_data(selected_id, edit_name, edit_cost, edit_price, edit_qty)
                    st.success(f"อัปเดตข้อมูล '{edit_name}' เรียบร้อยแล้ว!")
                    st.rerun()

            st.caption("ถ้าต้องการลบสินค้านี้ออกจากคลัง:")
            if st.button("ลบสินค้าชิ้นนี้", type="primary"):
                remove_product(selected_id)
                st.success("ลบรายการสินค้าเรียบร้อยแล้ว!")
                st.rerun()

    st.divider()

    st.subheader("📋 ตารางรายการสินค้าทั้งหมด")
    
    if not df_products.empty:
        search_text = st.text_input("🔍 พิมพ์ค้นหาสินค้า (รหัส หรือ ชื่อ):", "").strip().lower()
        
        filtered_df = df_products.copy()
        if search_text:
            filtered_df = filtered_df[
                filtered_df["id"].str.lower().str.contains(search_text) | 
                filtered_df["name"].str.lower().str.contains(search_text)
            ]
        
        filtered_df["มูลค่าคลังรวม"] = filtered_df["price"] * filtered_df["qty"]
        show_table = filtered_df.rename(columns={
            "id": "รหัสสินค้า",
            "name": "ชื่อสินค้า",
            "cost": "ราคาทุน",
            "price": "ราคาขาย",
            "qty": "จำนวนคงเหลือ"
        })
        
        st.dataframe(show_table, hide_index=True, use_container_width=True)
        
        csv_file = make_csv_file(show_table)
        st.download_button(
            label="ดาวน์โหลดตารางสินค้า (ไฟล์ CSV)",
            data=csv_file,
            file_name="products_report.csv",
            mime="text/csv",
            use_container_width=True
        )
    else:
        st.info("ยังไม่มีสินค้าในระบบ")

# ---------------- 6. เมนูที่ 3: ขายสินค้า ----------------
elif menu_choice == "🛒 ขายสินค้า":
    st.header("🛒 หน้าบันทึกการขายสินค้า")

    if df_products.empty:
        st.warning("ยังไม่มีสินค้าในระบบ กรุณาเพิ่มสินค้าก่อนครับ")
    else:
        tab_sale1, tab_sale2 = st.tabs(["📝 ทำรายการขาย", "✏️ แก้ไข/ยกเลิกรายการขาย"])

        with tab_sale1:
            col_form, col_hist = st.columns([1, 1])

            with col_form:
                st.subheader("กรอกข้อมูลการขาย")
                
                search_sell = st.text_input("🔍 ค้นหาสินค้าที่จะขาย:", "").strip().lower()
                
                sell_df = df_products.copy()
                if search_sell:
                    sell_df = sell_df[
                        sell_df["id"].str.lower().str.contains(search_sell) | 
                        sell_df["name"].str.lower().str.contains(search_sell)
                    ]

                if sell_df.empty:
                    st.error("หาไม่พบสินค้าที่ค้นหาครับ")
                else:
                    item_dict = {
                        f"{row['id']} - {row['name']} (เหลือ: {int(row['qty'])} ชิ้น)": row['id']
                        for _, row in sell_df.iterrows()
                    }
                    choice_str = st.selectbox("เลือกสินค้าที่จะขาย", list(item_dict.keys()))
                    choice_id = item_dict[choice_str]
                    current_item = df_products[df_products["id"] == choice_id].iloc[0]

                    current_qty = int(current_item["qty"])

                    if current_qty <= 0:
                        st.error("สินค้านี้หมดแล้ว ไม่สามารถขายได้ครับ")
                    else:
                        sell_num = st.number_input(
                            "จำนวนที่ต้องการซื้อ", 
                            min_value=1, 
                            max_value=current_qty, 
                            step=1
                        )

                        calc_total = float(current_item["price"]) * sell_num
                        calc_cost = float(current_item["cost"]) * sell_num
                        st.write(f"**ราคารวมทั้งหมด:** ฿{calc_total:,.2f}")

                        if st.button("ยืนยันการขาย", use_container_width=True):
                            save_sale_transaction(
                                choice_id, 
                                current_item["name"], 
                                sell_num, 
                                current_item["price"], 
                                calc_total, 
                                calc_cost, 
                                current_qty
                            )
                            st.success(f"บันทึกการขายเรียบร้อย! ยอดเงิน ฿{calc_total:,.2f}")
                            st.rerun()

            with col_hist:
                st.subheader("📜 ประวัติการขายล่าสุด")
                if not df_sales.empty:
                    show_sales = df_sales[["product_id", "product_name", "qty", "total_price", "sale_date"]].rename(columns={
                        "product_id": "รหัส",
                        "product_name": "ชื่อสินค้า",
                        "qty": "จำนวน",
                        "total_price": "ราคารวม",
                        "sale_date": "วัน-เวลา"
                    })
                    st.dataframe(show_sales, hide_index=True, use_container_width=True)
                else:
                    st.info("ยังไม่มีประวัติการขาย")

        with tab_sale2:
            st.subheader("แก้ไขหรือยกเลิกรายการขาย")
            if df_sales.empty:
                st.info("ไม่มีรายการขายให้แก้ไข")
            else:
                sales_dict = {
                    f"รายการที่ #{row['id']} - {row['product_name']} ({row['qty']} ชิ้น - รวม ฿{row['total_price']:,.2f})": row['id']
                    for _, row in df_sales.iterrows()
                }
                sale_choice = st.selectbox("เลือกรายการขายที่จะแก้ไข", list(sales_dict.keys()))
                target_sale_id = sales_dict[sale_choice]
                target_sale = df_sales[df_sales["id"] == target_sale_id].iloc[0]

                with st.form("edit_sale_form"):
                    col_s1, col_s2 = st.columns(2)
                    fix_qty = col_s1.number_input("จำนวนที่ถูกต้อง", min_value=1, value=int(target_sale["qty"]), step=1)
                    fix_price = col_s2.number_input("ราคาต่อชิ้น", min_value=0.0, value=float(target_sale["price_per_unit"]), step=1.0)
                    
                    unit_c = float(target_sale["total_cost"]) / float(target_sale["qty"]) if target_sale["qty"] > 0 else 0.0
                    
                    st.write(f"**ยอดรวมใหม่:** ฿{(fix_qty * fix_price):,.2f}")
                    
                    btn_fix_sale = st.form_submit_button("บันทึกแก้ไขรายการขาย")
                    if btn_fix_sale:
                        edit_sale_transaction(
                            target_sale_id, 
                            target_sale["product_id"], 
                            int(target_sale["qty"]), 
                            fix_qty, 
                            fix_price, 
                            unit_c
                        )
                        st.success("แก้ไขการขายและปรับสต็อกเรียบร้อย!")
                        st.rerun()

                st.caption("ถ้าขายผิดหรือต้องการยกเลิกบิลนี้ (ระบบจะคืนสต็อกเข้าคลัง):")
                if st.button("ยกเลิกการขายบิลนี้", type="primary"):
                    cancel_sale_transaction(target_sale_id, target_sale["product_id"], int(target_sale["qty"]))
                    st.success("ยกเลิกรายการขายและคืนสินค้าเข้าสต็อกแล้ว!")
                    st.rerun()

# ---------------- 7. เมนูที่ 4: บันทึกค่าใช้จ่าย ----------------
elif menu_choice == "💸 บันทึกค่าใช้จ่าย":
    st.header("💸 หน้าบันทึกค่าใช้จ่ายอื่นๆ")

    tab_exp1, tab_exp2 = st.tabs(["📝 เพิ่มค่าใช้จ่าย", "✏️ แก้ไข/ลบค่าใช้จ่าย"])

    with tab_exp1:
        col_exp_form, col_exp_hist = st.columns([1, 1])

        with col_exp_form:
            st.subheader("กรอกรายการค่าใช้จ่าย")
            with st.form("expense_form", clear_on_submit=True):
                exp_detail = st.text_input("รายละเอียดค่าใช้จ่าย (เช่น ค่าถุงพลาสติก)").strip()
                exp_money = st.number_input("จำนวนเงิน (บาท)", min_value=1.0, step=10.0)
                
                btn_save_exp = st.form_submit_button("บันทึกค่าใช้จ่าย")
                if btn_save_exp:
                    if not exp_detail:
                        st.error("กรุณากรอกรายละเอียดด้วยครับ")
                    else:
                        save_expense(exp_detail, exp_money)
                        st.success("บันทึกค่าใช้จ่ายเรียบร้อย!")
                        st.rerun()

        with col_exp_hist:
            st.subheader("📜 ประวัติค่าใช้จ่าย")
            if not df_expenses.empty:
                show_expenses = df_expenses[["description", "amount", "expense_date"]].rename(columns={
                    "description": "รายการ",
                    "amount": "จำนวนเงิน (บาท)",
                    "expense_date": "วัน-เวลา"
                })
                st.dataframe(show_expenses, hide_index=True, use_container_width=True)
            else:
                st.info("ยังไม่มีประวัติค่าใช้จ่าย")

    with tab_exp2:
        st.subheader("แก้ไขหรือลบรายการค่าใช้จ่าย")
        if df_expenses.empty:
            st.info("ไม่มีรายการค่าใช้จ่าย")
        else:
            exp_dict = {
                f"รายการ #{row['id']} - {row['description']} ({row['amount']:,.2f} บาท)": row['id']
                for _, row in df_expenses.iterrows()
            }
            exp_choice = st.selectbox("เลือกรายการที่จะแก้ไข", list(exp_dict.keys()))
            target_exp_id = exp_dict[exp_choice]
            target_exp = df_expenses[df_expenses["id"] == target_exp_id].iloc[0]

            with st.form("edit_expense_form"):
                fix_exp_detail = st.text_input("รายละเอียด", value=target_exp["description"])
                fix_exp_money = st.number_input("จำนวนเงิน (บาท)", min_value=0.0, value=float(target_exp["amount"]), step=10.0)

                btn_fix_exp = st.form_submit_button("บันทึกการแก้ไข")
                if btn_fix_exp:
                    edit_expense(target_exp_id, fix_exp_detail, fix_exp_money)
                    st.success("แก้ไขข้อมูลเรียบร้อย!")
                    st.rerun()

            st.caption("ถ้าต้องการลบรายการนี้:")
            if st.button("ลบรายการค่าใช้จ่ายนี้", type="primary"):
                remove_expense(target_exp_id)
                st.success("ลบรายการเรียบร้อย!")
                st.rerun()

# ---------------- 8. เมนูที่ 5: สรุปบัญชีและปันผล ----------------
elif menu_choice == "📊 สรุปยอดและแบ่งปันผล":
    st.header("📊 สรุปบัญชีประจำปี และการจัดสรรเงินปันผล")

    rev_total = df_sales["total_price"].sum() if not df_sales.empty else 0.0
    cogs_total = df_sales["total_cost"].sum() if not df_sales.empty else 0.0
    exp_total = df_expenses["amount"].sum() if not df_expenses.empty else 0.0
    expenses_all = cogs_total + exp_total
    profit_net = rev_total - expenses_all

    summary_list = [
        {"รายการ": "1. รายรับรวมจากการขายทั้งหมด", "จำนวนเงิน (บาท)": f"฿{rev_total:,.2f}"},
        {"รายการ": "2.1 ต้นทุนของสินค้าที่ขายไป", "จำนวนเงิน (บาท)": f"฿{cogs_total:,.2f}"},
        {"รายการ": "2.2 ค่าใช้จ่ายอื่นๆ", "จำนวนเงิน (บาท)": f"฿{exp_total:,.2f}"},
        {"รายการ": "2. รวมค่าใช้จ่ายทั้งหมด", "จำนวนเงิน (บาท)": f"฿{expenses_all:,.2f}"},
        {"รายการ": "3. กำไรสุทธิที่ได้", "จำนวนเงิน (บาท)": f"฿{profit_net:,.2f}"}
    ]
    st.table(pd.DataFrame(summary_list))

    if profit_net > 0:
        percent_reserve = st.slider("เลือก % เพื่อหักเข้าทุนสำรองโรงเรียน", min_value=10, max_value=100, value=10)
        reserve_money = profit_net * (percent_reserve / 100.0)
        dividend_money = profit_net - reserve_money

        col_r1, col_r2 = st.columns(2)
        col_r1.success(f"🏫 **เงินเข้าทุนสำรอง ({percent_reserve}%):** ฿{reserve_money:,.2f}")
        col_r2.info(f"🎁 **เงินปันผลสำหรับสมาชิก:** ฿{dividend_money:,.2f}")
