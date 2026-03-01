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
    st.session_state.user_table = None

def login_page():
    st.title("🔐 Login to Your Private Finance")
    
    col1, col2 = st.columns([3,1])
    with col1:
        email = st.text_input("📧 Email", placeholder="user1@gmail.com")
        password = st.text_input("🔑 Password", type="password")
    
    with col2:
        st.info("**Demo:**\n`user1@gmail.com`\nPass: `123456`")
    
    if st.button("🚀 Login", type="primary"):
        if email and password == "123456":
            st.session_state.user_email = email
            st.rerun()
    
    if st.button("👤 Guest"):
        st.session_state.user_email = f"guest_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:6]}"
        st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- FIXED DATABASE ----------------
@st.cache_resource(ttl=600)
def init_db():
    db_path = 'finance.db'
    conn = sqlite3.connect(db_path, check_same_thread=False)
    
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"expenses_{user_id}"
    st.session_state.user_table = user_table
    
    cursor = conn.cursor()
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table} (
            date TEXT, 
            amount REAL, 
            category TEXT, 
            description TEXT
        )
    ''')
    conn.commit()
    return conn

try:
    conn = init_db()
except:
    st.error("DB connection failed. Restarting...")
    st.rerun()

user_table = st.session_state.user_table

# ---------------- UI ----------------
st.title(f"💰 {st.session_state.user_email}'s Finance")

st.sidebar.title(f"👤 {st.session_state.user_email}")
if st.sidebar.button("🚪 Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

menu = ["➕ Add Expense", "📊 View Expenses", "📈 Budget"]
choice = st.sidebar.selectbox("Choose:", menu)

# ---------------- FUNCTIONS ----------------
def add_expense():
    st.subheader("➕ Add Your Expense")
    
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("📅 Date", datetime.now())
        
        # ✅ MORE CATEGORIES ADDED
        selected_category = st.selectbox("🏷️ Category", 
            ["➕ Custom", "Food", "Travel", "Education", "Entertainment", 
             "Shopping", "Bills", "Gym", "Medical", "Fuel", "Rent", "Netflix"])
        
        if selected_category == "➕ Custom":
            custom_cat = st.text_input("Enter category:", placeholder="Ex: Gifts, Petrol")
            final_category = custom_cat or "Other"
        else:
            final_category = selected_category
        
        st.info(f"**Selected**: {final_category}")
    
    with col2:
        amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0)
        description = st.text_input("📝 Description")
    
    # ✅ SUCCESS MESSAGE
    if st.button("✅ Save Expense", type="primary"):
        try:
            cursor = conn.cursor()
            cursor.execute(f"INSERT INTO {user_table} VALUES(?,?,?,?)", 
                          (str(date), amount, final_category, description))
            conn.commit()
            st.success("✅ **Expense Successfully Saved!** 🎉")
            st.balloons()
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

def view_expenses():
    st.subheader("📊 Your Expenses")
    
    try:
        data = pd.read_sql(f"SELECT * FROM {user_table} ORDER BY date DESC", conn)
    except:
        st.warning("No data yet!")
        return
    
    if data.empty:
        st.info("👆 Add expenses first!")
        return
    
    # ✅ BEAUTIFUL TABLE FORMAT
    st.dataframe(
        data.style
        .format({
            'date': '{:%Y-%m-%d}',
            'amount': '₹{:,.0f}'
        })
        .set_properties(**{
            'background-color': '#f0f2f6',
            'color': 'black',
            'font-weight': 'bold'
        }),
        use_container_width=True,
        hide_index=False
    )
    
    # ✅ DELETE BUTTONS BELOW TABLE
    st.subheader("🗑️ Delete Expenses")
    for index, row in data.iterrows():
        col1, col2, col3 = st.columns([4,1,1])
        with col1:
            st.write(f"**{row['date']}** | ₹{row['amount']:,.0f} | **{row['category']}**")
        with col2:
            if st.button("🗑️ Delete", key=f"del_{index}"):
                cursor = conn.cursor()
                cursor.execute(f"DELETE FROM {user_table} WHERE rowid={index+1}")
                conn.commit()
                st.success("✅ Deleted successfully!")
                st.rerun()
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏆 Spending Breakdown")
        category_sum = data.groupby('category')['amount'].sum()
        fig, ax = plt.subplots(figsize=(6,6))
        ax.pie(category_sum, labels=category_sum.index, autopct='%1.1f%%')
        st.pyplot(fig)
    
    with col2:
        total = data['amount'].sum()
        st.metric("💎 Total Spent", f"₹{total:,.0f}")

def budget_predict():
    try:
        data = pd.read_sql(f"SELECT * FROM {user_table}", conn)
        if data.empty:
            st.warning("Add expenses first!")
            return
        
        total = data['amount'].sum()
        st.success(f"📈 **Monthly Prediction**: ₹{total*1.1:,.0f}")
    except:
        st.warning("No data!")

# ---------------- RUN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Budget":
    budget_predict()
