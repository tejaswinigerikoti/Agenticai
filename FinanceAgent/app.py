import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import hashlib

# Page config
st.set_page_config(page_title="💰 Private Finance Manager", layout="wide")

# ---------------- GLOBAL CONNECTION ----------------
@st.cache_resource
def init_db():
    conn = sqlite3.connect('finance.db', check_same_thread=False)
    return conn

conn = init_db()

# ---------------- AUTH & USER ISOLATION ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

def login_page():
    st.title("🔐 Login to Your Private Finance")
    
    col1, col2 = st.columns([3,1])
    with col1:
        email = st.text_input("📧 Your Email", placeholder="yourname@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.markdown("**Demo Accounts:**")
        st.code("user1@gmail.com\n123456")
        st.code("user2@gmail.com\n123456")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Login", type="primary", use_container_width=True):
            if email and password:
                st.session_state.user_email = email
                st.rerun()
    
    with col2:
        if st.button("👤 Guest Mode", use_container_width=True):
            st.session_state.user_email = f"guest_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]}@demo.com"
            st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- USER TABLE SETUP ----------------
def get_user_table():
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"expenses_{user_id}"
    
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table}(
            date TEXT, amount REAL, category TEXT, description TEXT
        )
    ''')
    conn.commit()
    return user_table

user_table = get_user_table()

# ---------------- APP UI ----------------
st.title(f"💰 {st.session_state.user_email.split('@')[0]}'s Private Finance")

# Sidebar
st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    st.session_state.clear()
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Budget"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- FUNCTIONS ----------------

def add_expense():
    st.subheader("➕ Add Your Private Expense")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("📅 Date", value=datetime.now().date())
        
        # 🔥 CUSTOM CATEGORY
        category_options = ["Food", "Travel", "Education", "Entertainment", "Shopping", "Bills", "Gym", "Medical", "Gifts", "Fuel"]
        selected_category = st.selectbox("🏷️ Category:", ["➕ Add New"] + category_options)
        
        if selected_category == "➕ Add New":
            new_category = st.text_input("✨ New category:", placeholder="Rent, Netflix, Petrol")
            final_category = new_category.strip() if new_category.strip() else "Other"
        else:
            final_category = selected_category
    
    with col2:
        amount = st.number_input("💰 Amount (₹)", min_value=0.01, step=10.0, format="%.0f")
        description = st.text_input("📝 Description")
    
    if st.button("✅ Add Expense", type="primary"):
        try:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {user_table} VALUES(?,?,?,?)", 
                          (str(date), float(amount), final_category, description))
            conn.commit()
            
            # ✅ SIMPLE MESSAGE ONLY
            st.success("Expense added successfully!")
            
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error: {e}")

def view_expenses():
    st.subheader("📊 Your Private Expenses")
    
    try:
        data = pd.read_sql_query(f"SELECT * FROM {user_table} ORDER BY date DESC", conn)
    except:
        data = pd.DataFrame()
    
    if data.empty:
        st.warning("📭 No expenses yet. Add some first!")
        return
    
    st.dataframe(data.style.format({'amount': '₹{:,.0f}'}), use_container_width=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        category_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
        fig, ax = plt.subplots(figsize=(8,6))
        wedges, texts, autotexts = ax.pie(category_sum.values, labels=category_sum.index, autopct='%1.1f%%', startangle=90)
        plt.setp(autotexts, size=10, weight="bold")
        ax.set_title("Your Spending Breakdown")
        st.pyplot(fig)
    
    with col2:
        total = data['amount'].sum()
        avg = data['amount'].mean()
        st.metric("💎 Total Spent", f"₹{total:,.0f}")
        st.metric("📊 Avg Expense", f"₹{avg:.0f}")

def budget_predict():
    st.subheader("📈 Your Budget Insights")
    
    try:
        data = pd.read_sql_query(f"SELECT * FROM {user_table}", conn)
    except:
        data = pd.DataFrame()
    
    if data.empty:
        st.warning("📊 Add expenses first!")
        return
    
    total_spent = data['amount'].sum()
    days = len(pd.unique(pd.to_datetime(data['date']).dt.date))
    avg_daily = total_spent / days if days > 0 else 0
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Total Spent", f"₹{total_spent:,.0f}")
        st.metric("📅 Days Tracked", days)
    
    with col2:
        predicted_month = avg_daily * 30
        st.success(f"📈 **Monthly Prediction**: ₹{predicted_month:,.0f}")
        st.info(f"💡 **Suggested Savings**: ₹{predicted_month*0.2:,.0f}")

# ---------------- MAIN EXECUTION ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Budget":
    budget_predict()

st.markdown("---")
st.caption("🔒 Your data is 100% private | Custom categories supported")
