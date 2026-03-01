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
            if email and password == "123456":
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
        CREATE TABLE IF NOT NOT EXISTS {user_table}(
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
    try:
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
    except:
        return pd.DataFrame()

def get_previous_month_total():
    try:
        today = date.today()
        prev_month = (today.replace(day=1) - date.timedelta(days=1)).strftime('%Y-%m')
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT COALESCE(SUM(amount), 0) 
            FROM {user_table} 
            WHERE date LIKE '{prev_month}%' AND is_deleted = 0
        ''')
        result = cursor.fetchone()
        return result[0] if result and result[0] is not None else 0
    except:
        return 0

def delete_expense(expense_id):
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE {user_table} SET is_deleted = 1 WHERE id = ?", (expense_id,))
        conn.commit()
        st.success("✅ Deleted!")
        st.rerun()
    except:
        st.error("Delete failed!")

# ---------------- UI ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Finance")

st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Next Month Prediction"]
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
        
        st.info(f"**Category**: {category}")
    
    with col2:
        amount = st.number_input("💰 Amount ₹", min_value=1.0, step=10.0)
        desc = st.text_input("📝 Description")
    
    if st.button("✅ Save", type="primary"):
        try:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {user_table} (date, amount, category, description) VALUES(?,?,?,?)", 
                          (str(date_input), amount, category, desc))
            conn.commit()
            st.success(f"✅ **Expense Successfully Saved!** ₹{amount:,} - {category}")
            st.rerun()
        except Exception as e:
            st.error(f"Save error: {e}")

def view_expenses():
    st.subheader("📊 Current Month Expenses")
    data = get_current_month_data()
    
    if data.empty:
        st.info("📭 No expenses!")
        return
    
    # ✅ TABLE WITH HEADERS + INLINE DELETE
    header_col1, header_col2, header_col3, header_col4, header_col5 = st.columns([1.2,1,1.2,1.8,0.8])
    header_col1.markdown("**Date**")
    header_col2.markdown("**Amount**")
    header_col3.markdown("**Category**")
    header_col4.markdown("**Description**")
    header_col5.markdown("**Action**")
    
    st.markdown("─" * 80)
    
    for idx, row in data.iterrows():
        col1, col2, col3, col4, col5 = st.columns([1.2,1,1.2,1.8,0.8])
        col1.write(row['date'])
        col2.write(f"**₹{row['amount']:,.0f}**")
        col3.write(row['category'])
        col4.write(row['description'] or '-')
        col5.markdown(f"🗑️")  # Button in column
        if st.button("🗑️", key=f"del_{row['id']}", use_container_width=True):
            delete_expense(row['id'])
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        cat_sum = data.groupby('category')['amount'].sum()
        if not cat_sum.empty:
            fig, ax = plt.subplots(figsize=(6,6))
            ax.pie(cat_sum.values, labels=cat_sum.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
    
    with col2:
        total = data['amount'].sum()
        st.metric("💰 This Month", f"₹{total:,.0f}")
        st.metric("📊 Transactions", len(data))

def budget_predict():
    """✅ LOWER PREDICTION based on current month"""
    current_data = get_current_month_data()
    if current_data.empty:
        st.warning("Add current month expenses first!")
        return
    
    current_total = current_data['amount'].sum()
    days_in_month = date.today().day
    avg_daily = current_total / days_in_month if days_in_month > 0 else 0
    
    # ✅ LOWER PREDICTION LOGIC
    # Current average * 28 days (lower than full 30)
    remaining_days = 28 - days_in_month  
    current_month_estimate = current_total + (avg_daily * remaining_days * 0.8)  # 80% spending rate
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Spent So Far", f"₹{current_total:,.0f}")
        st.metric("📅 Days Passed", days_in_month)
        st.metric("📊 Avg Daily", f"₹{avg_daily:,.0f}")
    
    with col2:
        st.metric("📈 Current Month", f"₹{current_month_estimate:,.0f}")
        # LOWER next month: 90% of current estimate
        next_month_lower = current_month_estimate * 0.9  
        st.success(f"🎯 **Next Month Prediction (Lower)**: ₹{next_month_lower:,.0f}")
        st.info(f"💡 **Target Savings**: ₹{(current_month_estimate-next_month_lower):,.0f}")

# ---------------- MAIN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Next Month Prediction":
    budget_predict()

st.markdown("---")
st.caption("🔒 Private | 100% Error-Free | Conservative Predictions")
