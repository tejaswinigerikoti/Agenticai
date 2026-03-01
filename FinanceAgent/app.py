import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime
import requests
import json

# Page config
st.set_page_config(page_title="💰 Finance Manager", layout="wide")

# ---------------- DATABASE ----------------
@st.cache_resource
def init_db():
    conn = sqlite3.connect('finance.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS expenses(
        date TEXT,
        amount REAL,
        category TEXT,
        description TEXT
    )
    ''')
    conn.commit()
    return conn

conn = init_db()

# ---------------- APP TITLE ----------------
st.title("💰 Personal Finance Management Agent (Ollama Powered)")
st.markdown("---")

# Sidebar
menu = ["Add Expense", "View Expenses", "Budget Prediction", "Agent Suggestion", "💬 AI Chat"]
choice = st.sidebar.selectbox("Menu", menu)

# Ollama Configuration
if "ollama_configured" not in st.session_state:
    st.session_state.ollama_configured = False
    st.session_state.ollama_url = "http://localhost:11434"

# ---------------- OLLAMA FUNCTIONS ----------------
@st.cache_data(ttl=3600)
def call_ollama(prompt, model="llama3.2"):
    """Call Ollama API"""
    try:
        url = f"{st.session_state.ollama_url}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 300
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["message"]["content"]
        else:
            return None
    except Exception as e:
        st.error(f"Ollama connection failed: {str(e)}")
        return None

# ---------------- FUNCTION DEFINITIONS ----------------

def add_expense():
    st.subheader("➕ Add Daily Expense")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        date = st.date_input("📅 Date", datetime.now())
    with col2:
        amount = st.number_input("💰 Amount (₹)", min_value=0.0, step=10.0)
    
    col3, col4 = st.columns(2)
    with col3:
        category = st.selectbox("🏷️ Category", ["Food", "Travel", "Education", "Entertainment", "Shopping", "Bills", "Other"])
    with col4:
        description = st.text_input("📝 Description")
    
    if st.button("✅ Add Expense", type="primary"):
        c.execute("INSERT INTO expenses VALUES(?,?,?,?)", (str(date), amount, category, description))
        conn.commit()
        st.success("✅ Expense Added Successfully!")
        st.balloons()

def view_expenses():
    st.subheader("📋 Expense Records")
    
    data = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)
    
    if not data.empty:
        st.dataframe(data, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            category_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
            st.subheader("🏆 Category Wise Spending")
            fig, ax = plt.subplots()
            ax.pie(category_sum, labels=category_sum.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)
        
        with col2:
            total_spent = data['amount'].sum()
            avg_daily = data['amount'].mean()
            st.metric("💎 Total Spent", f"₹{total_spent:,.2f}")
            st.metric("📊 Avg Daily Spend", f"₹{avg_daily:.2f}")
            
    else:
        st.warning("📭 No expenses found. Add some expenses first!")

def budget_prediction():
    st.subheader("📈 Monthly Expense Prediction")
    data = pd.read_sql("SELECT * FROM expenses", conn)
    
    if not data.empty:
        data['date'] = pd.to_datetime(data['date'])
        data['month'] = data['date'].dt.to_period('M')
        monthly_total = data.groupby('month')['amount'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 📊 Monthly Expense Trend")
            fig, ax = plt.subplots(figsize=(8, 4))
            monthly_total.plot(kind='line', marker='o', linewidth=2, markersize=8, ax=ax)
            ax.set_title('Monthly Spending Trend', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3)
            st.pyplot(fig)
        
        with col2:
            # Prediction
            try:
                current_month = monthly_total.iloc[-1]
                previous_month = monthly_total.iloc[-2]
                growth_rate = (current_month - previous_month) / previous_month
                predicted_next = current_month * (1 + growth_rate)
                
                st.success(f"**Current Month**: ₹{current_month:,.2f}")
                st.success(f"**Previous Month**: ₹{previous_month:,.2f}")
                st.info(f"**Predicted Next Month**: ₹{predicted_next:,.2f}")
                st.caption(f"📈 Growth Rate: {growth_rate*100:.1f}%")
                
            except IndexError:
                current_month = monthly_total.iloc[-1]
                predicted_next = current_month * 1.1
                st.info(f"**Current Month**: ₹{current_month:,.2f}")
                st.info(f"**Predicted Next Month** (10% growth): ₹{predicted_next:,.2f}")
                
    else:
        st.warning("📊 No data available for prediction. Add expenses first!")

def agent_suggestion():
    st.subheader("🤖 Ollama AI-Powered Saving Suggestions")
    
    # Ollama Setup
    if not st.session_state.ollama_configured:
        st.info("🔧 **Setup Ollama first:**")
        ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
        model = st.selectbox("Model", ["llama3.2", "llama3.1:8b", "mistral", "gemma2:2b"])
        
        if st.button("✅ Configure Ollama", type="primary"):
            st.session_state.ollama_url = ollama_url
            st.session_state.model = model
            st.session_state.ollama_configured = True
            st.success("✅ Ollama configured! Run `ollama serve` locally.")
            st.rerun()
        return
    
    data = pd.read_sql("SELECT * FROM expenses", conn)
    
    if not data.empty:
        category_sum = data.groupby('category')['amount'].sum().sort_values(ascending=False)
        highest_category = category_sum.index[0]
        highest_amount = category_sum.iloc[0]
        total_spent = data['amount'].sum()
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("🏆 Highest Spending Category", f"{highest_category}", f"₹{highest_amount:,.2f}")
            st.metric("💰 Total Monthly Spend", f"₹{total_spent:,.2f}")
        
        with col2:
            # Ollama-powered suggestion
            prompt = f"""
            You are a personal finance expert in India. User spending analysis:
            - Highest category: {highest_category} (₹{highest_amount:.2f})
            - Total monthly spend: ₹{total_spent:.2f}
            
            Give 3 practical, actionable saving tips specifically for reducing {highest_category} spending.
            Keep it concise (3 sentences max), positive, and realistic for Indian context.
            Format as bullet points.
            """
            
            with st.spinner("🤖 Getting Ollama suggestions..."):
                suggestion = call_ollama(prompt, st.session_state.model)
                if suggestion:
                    st.markdown("### 💡 **Ollama AI Suggestions**")
                    st.success(suggestion)
                else:
                    st.error("❌ Ollama not responding. Check if `ollama serve` is running.")
                    
                    # Fallback tips
                    st.info("**Quick Tips:**")
                    manual_tips = {
                        "Food": "✅ Cook at home 3x/week, use BigBasket coupons",
                        "Travel": "✅ Use metro/bus, UPI cashback on Ola/Uber",
                        "Entertainment": "✅ Free YouTube Premium trial, limit movies",
                        "Shopping": "✅ Flipkart/Amazon sales only, 24hr rule",
                        "Bills": "✅ Pay before due date, switch to JioAirFiber"
                    }
                    st.success(manual_tips.get(highest_category, "Keep tracking!"))
    else:
        st.warning("📈 Add expenses to get AI suggestions!")

def ai_chat():
    st.subheader("💬 Chat with Ollama Finance Assistant")
    
    if not st.session_state.ollama_configured:
        st.warning("⚙️ Configure Ollama in Agent Suggestion first!")
        return
    
    # Initialize chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Display chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("మీ ఫైనాన్స్ గురించి అడగండి... (Ask about finances)"):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            data = pd.read_sql("SELECT * FROM expenses", conn)
            finance_summary = f"Total spent: ₹{data['amount'].sum():.2f}, Highest category: {data.groupby('category')['amount'].sum().idxmax()}" if not data.empty else "No expense data"
            
            full_prompt = f"""
            You are a friendly Telugu/English finance assistant. Current finance: {finance_summary}
            User: {prompt}
            
            Answer helpfully about personal finance. Use Indian rupees (₹), local context.
            Be conversational and practical.
            """
            
            with st.spinner("Ollama thinking..."):
                response = call_ollama(full_prompt, st.session_state.model)
                if response:
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                else:
                    st.error("❌ Ollama connection failed")

# ---------------- FUNCTION MAP ----------------
menu_functions = {
    "Add Expense": add_expense,
    "View Expenses": view_expenses,
    "Budget Prediction": budget_prediction,
    "Agent Suggestion": agent_suggestion,
    "💬 AI Chat": ai_chat
}

# ---------------- RUN SELECTED FUNCTION ----------------
menu_functions[choice]()

# Footer
st.markdown("---")
st.markdown("*Powered by Streamlit + Ollama (Local AI) 🚀*")
