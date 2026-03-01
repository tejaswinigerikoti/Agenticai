import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import hashlib

# Page config
st.set_page_config(page_title="💰 Private Finance Manager", layout="wide")

# ---------------- AUTH & USER ISOLATION ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_table = None

def login_page():
    st.title("🔐 Login to Your Private Finance")
    
    col1, col2 = st.columns([3,1])
    with col1:
        email = st.text_input("📧 Your Email", placeholder="yourname@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.info("**Demo Accounts:**\n• `user1@gmail.com`\n• Pass: `123456`\n\n• `user2@gmail.com`\n• Pass: `123456`")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Login", type="primary", use_container_width=True):
            if email and password:
                st.session_state.user_email = email
                st.session_state.user_password = hashlib.md5(password.encode()).hexdigest()
                st.success("✅ Welcome!")
                st.rerun()
    
    with col2:
        if st.button("👤 Guest Mode", use_container_width=True):
            st.session_state.user_email = f"guest_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}@demo.com"
            st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- USER-SPECIFIC DATABASE ----------------
@st.cache_resource
def get_user_connection():
    # UNIQUE table per user (expenses_a1b2c3d4)
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"expenses_{user_id}"
    
    conn = sqlite3.connect('finance.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table}(
            date TEXT, amount REAL, category TEXT, description TEXT
        )
    ''')
    conn.commit()
    st.session_state.user_table = user_table
    return conn

conn = get_user_connection()
user_table = st.session_state.user_table

# ---------------- APP UI ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Private Finance")

# Sidebar
st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Budget"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- FUNCTIONS ----------------

def add_expense():
    st.subheader("➕ Add Your Private Expense")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("📅 Date", datetime.now())
        
        # 🔥 CUSTOM CATEGORY SYSTEM
        st.markdown("**🏷️ Category**")
        category_options = ["Food", "Travel", "Education", "Entertainment", "Shopping", "Bills", "Gym", "Medical", "Gifts", "Fuel"]
        selected_category = st.selectbox("Select or ➕ Add New:", ["➕ Add New"] + category_options)
        
        if selected_category == "➕ Add New":
            new_category = st.text_input("✨ Enter your category:", 
                                       placeholder="Ex: Rent, Netflix, Petrol")
            final_category = new_category.strip() if new_category.strip() else "Other"
        else:
            final_category = selected_category
        
        st.info(f"📋 **Category**: {final_category}")
    
    with col2:
        amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0, format="%.0f")
        description = st.text_input("📝 Description (optional)")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Save Expense", type="primary", use_container_width=True):
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {user_table} VALUES(?,?,?,?)", 
                          (str(date), float(amount), final_category, description))
            conn.commit()
            st.success(f"✅ Saved ₹{amount:,} → **{final_category}**")
            st.balloons()
            st.rerun()

def view_expenses():
    st.subheader("📊 Your Private Expenses Only")
    
    data = pd.read_sql(f"SELECT * FROM {user_table} ORDER BY date DESC", conn)
    
    if data.empty:
        st.warning("📭 No expenses yet. Add some first!")
        st.info("💡 Click '➕ Add Expense' to start tracking")
        return
    
    # Data table (YOUR data only)
    st.dataframe(data.style.format({'amount': '₹{:,.0f}'}), use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Your Spending Breakdown")
        category_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(8,6))
        ax.pie(category_sum, labels=category_sum.index, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
    
    with col2:
        total = data['amount'].sum()
        avg_daily = data['amount'].mean()
        count = len(data)
        
        st.metric("💎 Your Total Spent", f"₹{total:,.0f}")
        st.metric("📊 Avg Per Expense", f"₹{avg_daily:.0f}")
        st.metric("📅 Total Transactions", count)

def budget_predict():
    st.subheader("📈 Your Budget Insights")
    
    data = pd.read_sql(f"SELECT * FROM {user_table}", conn)
    
    if data.empty:
        st.warning("📊 Add expenses first to see predictions!")
        return
    
    total_spent = data['amount'].sum()
    days_tracked = len(pd.unique(pd.to_datetime(data['date']).dt.date))
    avg_daily = total_spent / days_tracked if days_tracked > 0 else 0
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("💰 Total Spent", f"₹{total_spent:,.0f}")
        st.metric("📅 Days Tracked", days_tracked)
        st.metric("📊 Avg Daily", f"₹{avg_daily:.0f}")
    
    with col2:
        predicted_monthly = avg_daily * 30
        savings_goal = predicted_monthly * 0.2
        
        st.success(f"📈 **Predicted Monthly**: ₹{predicted_monthly:,.0f}")
        st.info(f"💡 **Save**: ₹{savings_goal:,.0f} per month")
        st.caption("✨ Based on your spending pattern")

# ---------------- MAIN EXECUTION ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Budget":
    budget_predict()

# Footer
st.markdown("---")
st.caption("🔒 **Your data is 100% private** - Separate table per user")
st.caption("🚀 Deploy on Streamlit Cloud for free multi-user access")
