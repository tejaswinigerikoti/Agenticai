def view_expenses():
    st.subheader("📊 Current Month Expenses")
    data = get_current_month_data()
    
    if data.empty:
        st.info("📭 No expenses!")
        return
    
    # ✅ SIMPLE TABLE WITH DELETE COLUMN
    st.markdown("### 📋 Expenses")
    
    # Header row
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
    
    # Pie chart + metrics (same)
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
