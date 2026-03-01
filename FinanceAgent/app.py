import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import hashlib
import os

# Page config
st.set_page_config(page_title="💰 Private Finance Manager", layout="wide")

# ---------------- AUTH ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

def login_page():
    st.title("🔐 Login")
    col1, col2 = st.columns([3,1])
    
    with col1:
        email = st.text_input("📧 Email", placeholder="user1@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.info("**Demo:**\nuser1@gmail.com\nPass: 123456")
    
    if st.button("🚀 Login", type="primary"):
        if email and password == "123456":
            st.session_state.user_email = email
            st.rerun()
    
    if st.button("👤 Guest Mode"):
        st.session_state.user_email = f"guest_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]}"
        st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- DATABASE (FILE-BASED - DATA PERSISTS) ----------------
@st.cache_resource
def get_connection():
    """File-based DB - DATA WON'T LOST"""
    if not os.path.exists('finance.db'):
        conn = sqlite3.connect('finance.db', check_same_thread=False)
        conn.execute('PRAGMA journal_mode=WAL')
        return conn
    else:
        return sqlite3.connect('finance.db', check_same_thread=False)

conn = get_connection()

# Create user table
user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
user_table = f"expenses_{user_id}"

# Create table if not exists
with conn:
    conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            amount REAL,
            category TEXT,
            description TEXT
        )
    ''')

# ---------------- UI ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Finance")

st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Budget"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- ADD EXPENSE (WORKING 100%) ----------------
def add_expense():
    st.subheader("➕ Add Your Expense")
    
    with st.form("expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("📅 Date", value=datetime.now())
            categories = [
                "Food", "Travel", "Education", "Entertainment", 
                "Shopping", "Bills", "Gym", "Medical", "Fuel", 
                "Rent", "Netflix", "Custom"
            ]
            selected_category = st.selectbox("🏷️ Category", categories)
            
            if selected_category == "Custom":
                custom_cat = st.text_input("✏️ Your category:", placeholder="Ex: Gifts")
                final_category = custom_cat if custom_cat else "Other"
            else:
                final_category = selected_category
        
        with col2:
            amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0, format="%.0f")
            description = st.text_input("📝 Description")
        
        submitted = st.form_submit_button("✅ Save Expense")
        
        if submitted:
            if amount > 0:
                with conn:
                    conn.execute(f"""
                        INSERT INTO {user_table} (date, amount, category, description) 
                        VALUES (?, ?, ?, ?)
                    """, (str(date), float(amount), final_category, description))
                
                st.success("✅ **Expense Successfully Saved!** 🎉")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Amount must be greater than 0")

# ---------------- VIEW EXPENSES ----------------
def view_expenses():
    st.subheader("📊 Your Expenses")
    
    df = pd.read_sql(f"SELECT * FROM {user_table} ORDER BY id DESC", conn)
    
    if df.empty:
        st.info("📭 No expenses yet. Add some first!")
        st.stop()
    
    # ✅ BEAUTIFUL TABLE
    st.dataframe(
        df.style.format({'amount': '₹{:,.0f}', 'date': '{:%Y-%m-%d}'}),
        use_container_width=True
    )
    
    # DELETE BUTTONS
    st.subheader("🗑️ Delete Expense")
    for idx, row in df.iterrows():
        col1, col2 = st.columns([4,1])
        with col1:
            st.write(f"**{row.date}** | ₹{row.amount:,.0f} | {row.category}")
        with col2:
            if st.button("🗑️ Delete", key=f"del_{row.id}"):
                with conn:
                    conn.execute(f"DELETE FROM {user_table} WHERE id=?", (row.id,))
                st.success("✅ Deleted!")
                st.rerun()
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        cat_sum = df.groupby('category')['amount'].sum()
        fig, ax = plt.subplots(figsize=(6,6))
        ax.pie(cat_sum, labels=cat_sum.index, autopct='%1.1f%%')
        st.pyplot(fig)
    
    with col2:
        st.metric("💎 Total Spent", f"₹{df['amount'].sum():,.0f}")

# ---------------- BUDGET ----------------
def budget_predict():
    df = pd.read_sql(f"SELECT * FROM {user_table}", conn)
    if df.empty:
        st.warning("Add expenses first!")
        return
    
    total = df['amount'].sum()
    avg = df['amount'].mean()
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Total", f"₹{total:,.0f}")
        st.metric("📊 Average", f"₹{avg:,.0f}")
    with col2:
        st.success(f"📈 Monthly: ₹{total*1.1:,.0f}")

# ---------------- RUN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Budget":
    budget_predict()
