import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime, date
import hashlib
import os

# Page config
st.set_page_config(page_title="💰 Private Finance Manager", layout="wide")

# Fix SQLite
if not os.path.exists('finance.db'):
    open('finance.db', 'a').close()

# ---------------- AUTH ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_table = None

def login_page():
    st.title("🔐 Login to Your Private Finance")
    col1, col2 = st.columns([3,1])
    
    with col1:
        email = st.text_input("📧 Email", placeholder="user1@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.info("**Demo:**\nuser1@gmail.com\n123456")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Login", type="primary"):
            if email and password:
                st.session_state.user_email = email
                st.rerun()
    with col2:
        if st.button("👤 Guest"):
            st.session_state.user_email = f"guest_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}@demo.com"
            st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- DATABASE ----------------
@st.cache_resource
def get_user_connection():
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"expenses_{user_id}"
    
    conn = sqlite3.connect('finance.db', check_same_thread=False, timeout=20)
    cursor = conn.cursor()
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table}(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, amount REAL, category TEXT, description TEXT, 
            is_deleted INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    st.session_state.user_table = user_table
    return conn

conn = get_user_connection()
user_table = st.session_state.user_table

def get_current_month_data():
    today = date.today()
    current_month = today.strftime('%Y-%m')
    
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT * FROM {user_table} 
        WHERE date LIKE '{current_month}%' AND is_deleted = 0
        ORDER BY date DESC
    ''')
    data = pd.DataFrame(cursor.fetchall(), columns=['id', 'date', 'amount', 'category', 'description', 'is_deleted'])
    return data

def get_previous_month_total():
    today = date.today()
    # Previous month (Feb 2026 if today is March 1)
    prev_month = (today.replace(day=1) - date.timedelta(days=1)).strftime('%Y-%m')
    
    cursor = conn.cursor()
    cursor.execute(f'''
        SELECT COALESCE(SUM(amount), 0) as total 
        FROM {user_table} 
        WHERE date LIKE '{prev_month}%' AND is_deleted = 0
    ''')
    return cursor.fetchone()[0]

def delete_expense(expense_id):
    cursor = conn.cursor()
    cursor.execute(f"UPDATE {user_table} SET is_deleted = 1 WHERE id = ?", (expense_id,))
    conn.commit()
    st.success("✅ Deleted!")
    st.rerun()

# ---------------- UI ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Finance")

st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Budget"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- FUNCTIONS ----------------
def add_expense():
    st.subheader("➕ Add Expense")
    col1, col2 = st.columns(2)
    
    with col1:
        date_input = st.date_input("📅 Date", value=date.today())
        category_options = ["Food", "Travel", "Education", "Shopping", "Bills", "Gym", "Medical"]
        selected = st.selectbox("🏷️ Category", ["➕ Custom"] + category_options)
        
        if selected == "➕ Custom":
            custom_cat = st.text_input("Your category:", placeholder="Rent, Fuel")
            category = custom_cat.strip() if custom_cat.strip() else "Other"
        else:
            category = selected
    
    with col2:
        amount = st.number_input("💰 Amount ₹", min_value=1.0, step=10.0)
        desc = st.text_input("📝 Description")
    
    if st.button("✅ Save", type="primary"):
        try:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description) VALUES(?,?,?,?)", 
                          (str(date_input), amount, category, desc))
            conn.commit()
            st.success(f"✅ Added ₹{amount:,}")
            st.rerun()
        except:
            st.error("Save failed!")

def view_expenses():
    st.subheader("📊 Current Month Expenses")
    data = get_current_month_data()
    
    if data.empty:
        st.info("📭 No expenses!")
        return
    
    # ✅ TABLE WITH HEADINGS
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns(5)
    with header_col1: st.markdown("**Date**")
    with header_col2: st.markdown("**Amount**")
    with header_col3: st.markdown("**Category**")
    with header_col4: st.markdown("**Description**")
    with header_col5: st.markdown("**Delete**")
    
    st.markdown("---")
    
    # Data rows
    for idx, row in data.iterrows():
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1: st.write(row['date'])
        with col2: st.write(f"₹{row['amount']:,.0f}")
        with col3: st.write(row['category'])
        with col4: st.write(row['description'] or '-')
        with col5: 
            if st.button("🗑️", key=f"del_{row['id']}"):
                delete_expense(row['id'])
    
    # Pie chart + metrics
    col1, col2 = st.columns(2)
    with col1:
        cat_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(6,6))
        ax.pie(cat_sum.values, labels=cat_sum.index, autopct='%1.1f%%')
        ax.axis('equal')
        st.pyplot(fig)
    
    with col2:
        total = data['amount'].sum()
        st.metric("This Month", f"₹{total:,.0f}")
        st.metric("Count", len(data))

def budget_predict():
    current_data = get_current_month_data()
    if current_data.empty:
        st.warning("No data!")
        return
    
    # ✅ PREVIOUS MONTH BASED PREDICTION
    prev_month_total = get_previous_month_total()
    current_total = current_data['amount'].sum()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Current Month", f"₹{current_total:,.0f}")
        st.metric("Prev Month", f"₹{prev_month_total:,.0f}")
    
    with col2:
        # Prediction = Previous month × 1.05 (5% growth)
        next_month_pred = prev_month_total * 1.05
        st.success(f"**April Prediction**: ₹{next_month_pred:,.0f}")

# ---------------- MAIN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Budget":
    budget_predict()

st.markdown("---")
st.caption("🔒 Private | 📅 Previous Month Prediction")
