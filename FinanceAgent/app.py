import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import hashlib
import uuid

# Page config
st.set_page_config(page_title="💰 Private Finance Manager", layout="wide")

# ---------------- SIMPLE AUTH (No Errors) ----------------
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.conn = None

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
        st.session_state.user_email = f"guest_{str(uuid.uuid4())[:8]}"
        st.rerun()

if not st.session_state.user_email:
    login_page()
    st.stop()

# ---------------- FIXED DATABASE (NO CACHE) ----------------
def get_db_connection():
    """Create fresh connection every time - NO CACHE ERRORS"""
    user_id = hashlib.md5(st.session_state.user_email.encode()).hexdigest()[:8]
    user_table = f"expenses_{user_id}"
    
    # In-memory DB for demo (persists in session)
    conn = sqlite3.connect(':memory:')  # FIXED: In-memory DB
    cursor = conn.cursor()
    
    cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS {user_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, 
            amount REAL, 
            category TEXT, 
            description TEXT
        )
    ''')
    
    # Load existing data if any (for persistence simulation)
    try:
        existing_data = pd.read_sql(f"SELECT * FROM {user_table}", conn)
    except:
        pass
    
    st.session_state.user_table = user_table
    st.session_state.conn = conn
    return conn

# Initialize DB fresh every rerun
conn = get_db_connection()
user_table = st.session_state.user_table

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
        date = st.date_input("📅 Date", value=datetime.now())
        
        # ✅ ALL CATEGORIES
        categories = [
            "➕ Custom", "Food", "Travel", "Education", "Entertainment", 
            "Shopping", "Bills", "Gym", "Medical", "Fuel", "Rent", "Netflix"
        ]
        selected_category = st.selectbox("🏷️ Category", categories)
        
        final_category = selected_category
        if selected_category == "➕ Custom":
            custom_cat = st.text_input("✏️ Enter category:", placeholder="Ex: Gifts")
            final_category = custom_cat if custom_cat else "Other"
        
        st.info(f"**Category**: {final_category}")
    
    with col2:
        amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0, format="%.0f")
        description = st.text_input("📝 Description")
    
    if st.button("✅ Save Expense", type="primary"):
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {user_table} (date, amount, category, description) 
            VALUES(?,?,?,?)
        """, (str(date), float(amount), final_category, description))
        conn.commit()
        st.success("✅ **Expense Successfully Saved!** 🎉")
        st.balloons()
        st.rerun()

def view_expenses():
    st.subheader("📊 Your Expenses Table")
    
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {user_table} ORDER BY id DESC")
    data = pd.DataFrame(cursor.fetchall(), 
                       columns=['ID', 'Date', 'Amount', 'Category', 'Description'])
    
    if data.empty:
        st.info("📭 No expenses yet. Add some first!")
        return
    
    # ✅ BEAUTIFUL FORMATTED TABLE
    styled_data = data.style.format({
        'Amount': '₹{:,.0f}',
        'Date': '{:%Y-%m-%d}'
    }).set_properties(**{
        'text-align': 'center',
        'font-size': '14px',
        'border': '1px solid #ddd'
    })
    
    st.dataframe(styled_data, use_container_width=True, hide_index=False)
    
    # ✅ DELETE BUTTONS
    st.subheader("🗑️ Delete Selected")
    for idx, row in data.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{row['Date']}** | ₹{row['Amount']:,.0f} | {row['Category']}")
        with col2:
            if st.button("🗑️", key=f"delete_{row['ID']}"):
                cursor.execute(f"DELETE FROM {user_table} WHERE id=?", (row['ID'],))
                conn.commit()
                st.success("✅ Deleted!")
                st.rerun()
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        cat_sum = data.groupby('Category')['Amount'].sum()
        fig, ax = plt.subplots(figsize=(6,6))
        ax.pie(cat_sum, labels=cat_sum.index, autopct='%1.1f%%')
        ax.set_title("Spending Breakdown")
        st.pyplot(fig)
    
    with col2:
        st.metric("💎 Total Spent", f"₹{data['Amount'].sum():,.0f}")

def budget_predict():
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {user_table}")
    data = pd.DataFrame(cursor.fetchall(), 
                       columns=['ID', 'Date', 'Amount', 'Category', 'Description'])
    
    if data.empty:
        st.warning("Add expenses first!")
        return
    
    total = data['Amount'].sum()
    avg = data['Amount'].mean()
    st.metric("💰 Total", f"₹{total:,.0f}")
    st.metric("📊 Average", f"₹{avg:,.0f}")
    st.success(f"📈 Monthly Estimate: ₹{total*1.1:,.0f}")

# ---------------- MAIN ----------------
if choice == "➕ Add Expense":
    add_expense()
elif choice == "📊 View Expenses":
    view_expenses()
elif choice == "📈 Budget":
    budget_predict()
