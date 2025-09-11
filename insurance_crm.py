import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime, timedelta

# Set up the page
st.set_page_config(
    page_title="Insurance CRM System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Database setup
def init_db():
    conn = sqlite3.connect('crm.db')
    c = conn.cursor()

    # Create tables if they don't exist
    c.execute('''CREATE TABLE IF NOT EXISTS agents
                (id TEXT PRIMARY KEY, name TEXT, email TEXT, phone TEXT, created_at TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS customers
                (id TEXT PRIMARY KEY, agent_id TEXT, pan TEXT UNIQUE, aadhar TEXT,
                name TEXT, phone TEXT, email TEXT, income_range TEXT,
                parent_id TEXT, relationship TEXT,
                created_at TIMESTAMP, FOREIGN KEY(agent_id) REFERENCES agents(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS policies
                (id TEXT PRIMARY KEY, customer_id TEXT, policy_holder_id TEXT, policy_number TEXT UNIQUE,
                premium_amount REAL, frequency TEXT, type TEXT, provider TEXT,
                coverage_type TEXT, nominee_name TEXT, nominee_pan TEXT, nominee_aadhar TEXT,
                beneficiary_name TEXT, beneficiary_pan TEXT, beneficiary_aadhar TEXT,
                start_date TIMESTAMP, end_date TIMESTAMP, status TEXT,
                FOREIGN KEY(customer_id) REFERENCES customers(id),
                FOREIGN KEY(policy_holder_id) REFERENCES customers(id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS premiums
                (id TEXT PRIMARY KEY, policy_id TEXT, due_date TIMESTAMP,
                amount REAL, status TEXT, paid_date TIMESTAMP,
                FOREIGN KEY(policy_id) REFERENCES policies(id))''')

    conn.commit()
    conn.close()

# Initialize database
init_db()

# Session state setup
if 'current_agent' not in st.session_state:
    st.session_state.current_agent = None
if 'page' not in st.session_state:
    st.session_state.page = 'Dashboard'

# Agent authentication
def agent_login(agent_id):
    conn = sqlite3.connect('crm.db')
    c = conn.cursor()
    c.execute("SELECT * FROM agents WHERE id=?", (agent_id,))
    agent = c.fetchone()
    conn.close()
    if agent:
        st.session_state.current_agent = {
            'id': agent[0],
            'name': agent[1],
            'email': agent[2],
            'phone': agent[3]
        }
        return True
    return False

# Create a demo agent if none exists
def create_demo_agent():
    conn = sqlite3.connect('crm.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM agents")
    count = c.fetchone()[0]
    if count == 0:
        demo_agent_id = "A1001"
        c.execute("INSERT INTO agents (id, name, email, phone, created_at) VALUES (?, ?, ?, ?, ?)",
                  (demo_agent_id, "John Doe", "john@insureCRM.com", "9876543210", datetime.now()))
        conn.commit()
    conn.close()

create_demo_agent()

# Navigation function
def navigate_to(page):
    st.session_state.page = page
    st.rerun()

# Sidebar navigation
def render_sidebar():
    with st.sidebar:
        st.title("InsureCRM Navigation")
        
        if st.session_state.current_agent:
            st.write(f"**Logged in as:** {st.session_state.current_agent['name']}")
            st.write(f"**Agent ID:** {st.session_state.current_agent['id']}")
            st.divider()
        
        # Navigation options
        nav_options = {
            "Dashboard": "📊",
            "Customer Enrollment": "👥",
            "Policy Enrollment": "📝",
            "Records": "📂",
            "Family Management": "👨‍👩‍👧‍👦",
            "Upcoming Premiums": "💰"
        }
        
        for page, icon in nav_options.items():
            if st.button(f"{icon} {page}", use_container_width=True, 
                        type="primary" if st.session_state.page == page else "secondary"):
                navigate_to(page)
        
        st.divider()
        
        if st.session_state.current_agent:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.current_agent = None
                st.session_state.page = 'Login'
                st.rerun()

# Login page
def login_page():
    st.title("🏢 Insurance CRM Login")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("### Agent Login")
            agent_id = st.text_input("Agent ID", value="A1001", placeholder="Enter your Agent ID")
            login_button = st.form_submit_button("Login", type="primary")

            if login_button:
                if agent_login(agent_id):
                    st.success("Login successful!")
                    st.session_state.page = 'Dashboard'
                    st.rerun()
                else:
                    st.error("Invalid Agent ID")

# Dashboard page
def dashboard_page():
    st.title("📊 Insurance CRM Dashboard")
    
    # Dashboard metrics
    conn = sqlite3.connect('crm.db')
    
    # Get counts
    customers_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM customers WHERE agent_id=?", 
        conn, params=(st.session_state.current_agent['id'],)
    ).iloc[0]['count']
    
    policies_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM policies p JOIN customers c ON p.customer_id = c.id WHERE c.agent_id=?",
        conn, params=(st.session_state.current_agent['id'],)
    ).iloc[0]['count']
    
    active_policies_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM policies p JOIN customers c ON p.customer_id = c.id WHERE c.agent_id=? AND p.status='Active'",
        conn, params=(st.session_state.current_agent['id'],)
    ).iloc[0]['count']
    
    family_members_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM customers WHERE agent_id=? AND parent_id IS NOT NULL",
        conn, params=(st.session_state.current_agent['id'],)
    ).iloc[0]['count']
    
    # Get upcoming premiums (next 30 days)
    upcoming_premiums = pd.read_sql_query(
        "SELECT pr.due_date, pr.amount, c.name as customer_name, p.policy_number FROM premiums pr JOIN policies p ON pr.policy_id = p.id JOIN customers c ON p.customer_id = c.id WHERE c.agent_id=? AND pr.status='Pending' AND pr.due_date BETWEEN date('now') AND date('now', '+30 days') ORDER BY pr.due_date",
        conn, params=(st.session_state.current_agent['id'],)
    )
    
    conn.close()
    
    # Quick actions
    st.subheader("Quick Actions")
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("➕ Add New Customer", use_container_width=True):
            navigate_to("Customer Enrollment")
    with action_col2:
        if st.button("📝 Enroll New Policy", use_container_width=True):
            navigate_to("Policy Enrollment")
    with action_col3:
        if st.button("🔍 Search Records", use_container_width=True):
            navigate_to("Records")
    
    # Display metrics
    st.subheader("Business Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Customers", customers_count)
    with col2:
        st.metric("📋 Total Policies", policies_count)
    with col3:
        st.metric("✅ Active Policies", active_policies_count)
    with col4:
        st.metric("👨‍👩‍👧‍👦 Family Members", family_members_count)
    
    # Upcoming premiums
    st.subheader("📅 Upcoming Premiums (Next 30 Days)")
    if not upcoming_premiums.empty:
        upcoming_premiums['due_date'] = pd.to_datetime(upcoming_premiums['due_date']).dt.date
        st.dataframe(upcoming_premiums, use_container_width=True)
        
        # Calculate total upcoming premiums
        total_upcoming = upcoming_premiums['amount'].sum()
        st.write(f"**Total Amount Due:** ₹{total_upcoming:,.2f}")
        
        if st.button("View All Premiums", use_container_width=True):
            navigate_to("Upcoming Premiums")
    else:
        st.info("No upcoming premiums in the next 30 days")

# Customer enrollment page
def customer_enrollment_page():
    st.title("👤 Customer Enrollment")
    st.markdown("Register a new customer in the system")

    # Get existing customers for parent selection
    conn = sqlite3.connect('crm.db')
    existing_customers = pd.read_sql_query(
        "SELECT id, name, pan FROM customers WHERE agent_id=?",
        conn, params=(st.session_state.current_agent['id'],)
    )
    conn.close()

    with st.form("customer_form", clear_on_submit=True):
        st.subheader("Customer Details")

        # Main customer information
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input(
                "Full Name*", 
                placeholder="Enter customer's full name",
                help="Enter the complete name of the customer"
            )
            pan_card = st.text_input(
                "PAN Card Number*", 
                placeholder="ABCDE1234F",
                help="Enter 10-character PAN card number"
            ).upper()
            phone_number = st.text_input(
                "Phone Number*", 
                placeholder="+91 9876543210",
                help="Enter customer's phone number"
            )

        with col2:
            aadhar_number = st.text_input(
                "Aadhar Card Number*", 
                placeholder="1234 5678 9012",
                help="Enter 12-digit Aadhar number"
            )
            email_address = st.text_input(
                "Email Address", 
                placeholder="customer@email.com",
                help="Enter customer's email address"
            )
            income_range = st.selectbox(
                "Income Range*",
                ["", "Below ₹5L", "₹5L-₹10L", "₹10L-₹20L", "Above ₹20L"],
                help="Select customer's annual income range"
            )

        # Family relationship section
        st.subheader("Family Relationship (Optional)")
        col3, col4 = st.columns(2)

        with col3:
            is_family_member = st.checkbox("This is a family member of existing customer")

        parent_customer_id = None
        relationship = None

        if is_family_member and not existing_customers.empty:
            with col4:
                parent_options = {row['id']: f"{row['name']} ({row['pan']})" for _, row in existing_customers.iterrows()}
                selected_parent = st.selectbox(
                    "Select Parent/Primary Customer",
                    options=[""] + list(parent_options.keys()),
                    format_func=lambda x: parent_options.get(x, "Select Parent Customer") if x else "Select Parent Customer"
                )
                if selected_parent and selected_parent != "":
                    parent_customer_id = selected_parent

            relationship = st.selectbox(
                "Relationship to Primary Customer",
                ["", "Spouse", "Child", "Parent", "Sibling", "Other"],
                help="Select relationship with primary customer"
            )

        submitted = st.form_submit_button("Register Customer", type="primary")

        if submitted:
            # Validation
            if not all([customer_name, pan_card, aadhar_number, phone_number, income_range]):
                st.error("❌ Please fill all required fields marked with *")
                return

            if is_family_member and not parent_customer_id:
                st.error("❌ Please select a parent customer for family member")
                return

            # Save to database
            conn = sqlite3.connect('crm.db')
            c = conn.cursor()

            # Check if PAN already exists
            c.execute("SELECT id, name FROM customers WHERE pan=?", (pan_card,))
            existing = c.fetchone()
            if existing:
                st.error(f"❌ Customer with PAN {pan_card} already exists: {existing[1]}")
                conn.close()
                return

            try:
                customer_id = f"C{str(uuid.uuid4())[:8]}"
                c.execute(
                    "INSERT INTO customers (id, agent_id, pan, aadhar, name, phone, email, income_range, parent_id, relationship, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (customer_id, st.session_state.current_agent['id'], str(pan_card), str(aadhar_number),
                     customer_name, str(phone_number), email_address, income_range, 
                     parent_customer_id, relationship, datetime.now().date())
                conn.commit()
                conn.close()

                st.success(f"✅ Customer registered successfully!")
                st.success(f"**Customer ID:** {customer_id}")
                st.success(f"**Name:** {customer_name}")
                if parent_customer_id:
                    parent_name = existing_customers[existing_customers['id'] == parent_customer_id].iloc[0]['name']
                    st.success(f"**Family Member of:** {parent_name} ({relationship})")

            except Exception as e:
                st.error(f"❌ Error registering customer: {str(e)}")
                if conn:
                    conn.close()

# Policy enrollment page
def policy_enrollment_page():
    st.title("📋 Policy Enrollment")
    st.markdown("Register a new insurance policy")

    # Get customers for this agent
    conn = sqlite3.connect('crm.db')
    customers = pd.read_sql_query(
        "SELECT c.id, c.name, c.pan, c.parent_id, c.relationship, parent.name as parent_name, parent.pan as parent_pan FROM customers c LEFT JOIN customers parent ON c.parent_id = parent.id WHERE c.agent_id=? ORDER BY c.name",
        conn, params=(st.session_state.current_agent['id'],)
    )
    conn.close()

    if customers.empty:
        st.warning("⚠️ No customers found. Please enroll customers first.")
        if st.button("Go to Customer Enrollment"):
            navigate_to("Customer Enrollment")
        return

    # Policy enrollment form
    with st.form("policy_form"):
        st.subheader("Customer Selection")

        # Enhanced customer selection with family info
        customer_options = {}
        for _, row in customers.iterrows():
            if row['parent_id']:
                display_name = f"{row['name']} ({row['pan']}) - {row['relationship']} of {row['parent_name']}"
            else:
                display_name = f"{row['name']} ({row['pan']})"
            customer_options[row['id']] = display_name

        selected_customer_id = st.selectbox(
            "Select Customer for Policy",
            options=list(customer_options.keys()),
            format_func=lambda x: customer_options[x]
        )

        # Policy holder selection (for family policies)
        selected_customer = customers[customers['id'] == selected_customer_id].iloc[0]

        policy_holder_id = selected_customer_id  # Default to same customer

        if selected_customer['parent_id']:
            st.info(f"ℹ️ Selected customer is a family member. Policy can be purchased by parent/guardian.")
            col1, col2 = st.columns(2)
            with col1:
                policy_holder_option = st.radio(
                    "Who is purchasing this policy?",
                    ["Self", "Parent/Guardian"]
                )
            if policy_holder_option == "Parent/Guardian":
                policy_holder_id = selected_customer['parent_id']
                with col2:
                    st.info(f"Policy will be purchased by: {selected_customer['parent_name']}")

        st.subheader("Policy Details")
        col1, col2 = st.columns(2)

        with col1:
            policy_number = st.text_input(
                "Policy Number*", 
                placeholder="POL123456789",
                help="Enter unique policy number"
            )
            premium_amount = st.number_input(
                "Premium Amount (₹)*", 
                min_value=0.0, 
                step=1000.0,
                help="Enter premium amount in rupees"
            )
            frequency = st.selectbox(
                "Payment Frequency*",
                ["Monthly", "Quarterly", "Half-Yearly", "Yearly"],
                help="Select premium payment frequency"
            )
            insurance_type = st.selectbox(
                "Type of Insurance*",
                ["Life Insurance", "Health Insurance", "Motor Insurance", "Home Insurance", "Travel Insurance"],
                help="Select type of insurance"
            )

        with col2:
            insurance_provider = st.text_input(
                "Insurance Provider*", 
                placeholder="LIC of India, HDFC Life, etc.",
                help="Enter name of insurance company"
            )
            coverage_type = st.selectbox(
                "Coverage Type*", 
                ["Individual", "Family"],
                help="Select coverage type"
            )
            start_date = st.date_input(
                "Policy Start Date*",
                value=datetime.now().date(),
                help="Select policy start date"
            )
            end_date = st.date_input(
                "Policy End Date*",
                value=(datetime.now() + timedelta(days=365)).date(),
                help="Select policy end date"
            )

        st.subheader("Nominee Details")
        col3, col4 = st.columns(2)
        with col3:
            nominee_name = st.text_input(
                "Nominee Name*",
                placeholder="Full name of nominee",
                help="Enter nominee's full name"
            )
            nominee_pan = st.text_input(
                "Nominee PAN",
                placeholder="ABCDE1234F",
                help="Enter nominee's PAN card number"
            ).upper()
        with col4:
            nominee_aadhar = st.text_input(
                "Nominee Aadhar",
                placeholder="1234 5678 9012",
                help="Enter nominee's Aadhar number"
            )

        st.subheader("Beneficiary Details (Optional)")
        col5, col6 = st.columns(2)
        with col5:
            beneficiary_name = st.text_input(
                "Beneficiary Name",
                placeholder="Full name of beneficiary",
                help="Enter beneficiary's full name"
            )
            beneficiary_pan = st.text_input(
                "Beneficiary PAN",
                placeholder="ABCDE1234F",
                help="Enter beneficiary's PAN card number"
            ).upper()
        with col6:
            beneficiary_aadhar = st.text_input(
                "Beneficiary Aadhar",
                placeholder="1234 5678 9012",
                help="Enter beneficiary's Aadhar number"
            )

        submitted = st.form_submit_button("Register Policy", type="primary")

        if submitted:
            # Validation
            required_fields = [policy_number, premium_amount, frequency, insurance_type,
                             insurance_provider, coverage_type, start_date, end_date, nominee_name]

            if not all(required_fields) or premium_amount <= 0:
                st.error("❌ Please fill all required fields marked with *")
                return

            if end_date <= start_date:
                st.error("❌ Policy end date must be after start date")
                return

            # Save policy
            conn = sqlite3.connect('crm.db')
            c = conn.cursor()

            # Check if policy number already exists
            c.execute("SELECT id FROM policies WHERE policy_number=?", (policy_number,))
            if c.fetchone():
                st.error(f"❌ Policy with number {policy_number} already exists")
                conn.close()
                return

            try:
                policy_id = f"P{str(uuid.uuid4())[:8]}"
                c.execute(
                    "INSERT INTO policies (id, customer_id, policy_holder_id, policy_number, premium_amount, frequency, type, provider, coverage_type, nominee_name, nominee_pan, nominee_aadhar, beneficiary_name, beneficiary_pan, beneficiary_aadhar, start_date, end_date, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (policy_id, selected_customer_id, policy_holder_id, policy_number, premium_amount, frequency,
                     insurance_type, insurance_provider, coverage_type, nominee_name, nominee_pan, nominee_aadhar,
                     beneficiary_name, beneficiary_pan, beneficiary_aadhar,
                     start_date, end_date, "Active"))

                # Create premium records based on frequency
                premium_dates = generate_premium_dates(start_date, end_date, frequency)
                for due_date in premium_dates:
                    premium_id = f"PR{str(uuid.uuid4())[:8]}"
                    c.execute(
                        "INSERT INTO premiums (id, policy_id, due_date, amount, status) VALUES (?, ?, ?, ?, ?)",
                        (premium_id, policy_id, due_date, premium_amount, "Pending"))

                conn.commit()
                conn.close()

                st.success("✅ Policy registered successfully!")
                st.success(f"**Policy ID:** {policy_id}")
                st.success(f"**Policy Number:** {policy_number}")
                st.success(f"**Customer:** {selected_customer['name']}")
                if policy_holder_id != selected_customer_id:
                    holder_name = customers[customers['id'] == policy_holder_id].iloc[0]['name']
                    st.success(f"**Policy Holder:** {holder_name}")

            except Exception as e:
                st.error(f"❌ Error registering policy: {str(e)}")
                if conn:
                    conn.close()

def generate_premium_dates(start_date, end_date, frequency):
    dates = []
    current_date = start_date
    freq_days = {
        "Monthly": 30,
        "Quarterly": 90,
        "Half-Yearly": 180,
        "Yearly": 365
    }
    days = freq_days.get(frequency, 30)
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=days)
    return dates

# Family Management page
def family_management_page():
    st.title("👨‍👩‍👧‍👦 Family Management")
    st.markdown("Manage customer families and relationships")

    conn = sqlite3.connect('crm.db')

    # Get all customers with family info
    families = pd.read_sql_query(
        "SELECT c.id, c.name, c.pan, c.phone, c.email, c.parent_id, c.relationship, parent.name as parent_name, parent.pan as parent_pan FROM customers c LEFT JOIN customers parent ON c.parent_id = parent.id WHERE c.agent_id=? ORDER BY parent.name, c.name",
        conn, params=(st.session_state.current_agent['id'],)
    )

    if families.empty:
        st.info("No customers found. Please add customers first.")
        conn.close()
        return

    # Separate primary customers and family members
    primary_customers = families[families['parent_id'].isna()]
    family_members = families[families['parent_id'].notna()]

    # Display family structures
    for _, primary in primary_customers.iterrows():
        with st.expander(f"👨‍👩‍👧‍👦 {primary['name']} Family ({primary['pan']})"):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Primary Customer:**")
                st.write(f"• **Name:** {primary['name']}")
                st.write(f"• **PAN:** {primary['pan']}")
                st.write(f"• **Phone:** {primary['phone']}")
                st.write(f"• **Email:** {primary['email'] or 'Not provided'}")

            with col2:
                # Get family members for this primary customer
                family_of_primary = family_members[family_members['parent_id'] == primary['id']]

                if not family_of_primary.empty:
                    st.write("**Family Members:**")
                    for _, member in family_of_primary.iterrows():
                        st.write(f"• {member['name']} ({member['relationship']}) - {member['pan']}")
                else:
                    st.write("**Family Members:** None")

            # Get policies for this family
            family_policies = pd.read_sql_query(
                "SELECT p.policy_number, p.type, p.provider, p.status, customer.name as insured_name, holder.name as holder_name FROM policies p JOIN customers customer ON p.customer_id = customer.id JOIN customers holder ON p.policy_holder_id = holder.id WHERE (customer.id = ? OR customer.parent_id = ?) ORDER BY p.policy_number",
                conn, params=(primary['id'], primary['id'])
            )

            if not family_policies.empty:
                st.write("**Family Policies:**")
                st.dataframe(family_policies, use_container_width=True)

    conn.close()

# Records page
def records_page():
    st.title("🔍 Customer Records")
    st.markdown("Search and view customer information and policies")

    search_option = st.radio("Search by", ["PAN Card", "Customer Name", "Family"])

    conn = sqlite3.connect('crm.db')

    if search_option == "PAN Card":
        pan_search = st.text_input("Enter PAN Card Number", placeholder="ABCDE1234F").upper()
        if pan_search:
            customer = pd.read_sql_query(
                "SELECT c.*, parent.name as parent_name, parent.pan as parent_pan FROM customers c LEFT JOIN customers parent ON c.parent_id = parent.id WHERE c.pan=? AND c.agent_id=?",
                conn, params=(pan_search, st.session_state.current_agent['id'])
            )

            if not customer.empty:
                display_customer_details(customer.iloc[0], conn)
            else:
                st.warning("No customer found with this PAN number")

    elif search_option == "Customer Name":
        name_search = st.text_input("Enter Customer Name", placeholder="Enter full or partial name")
        if name_search:
            customers = pd.read_sql_query(
                "SELECT c.*, parent.name as parent_name, parent.pan as parent_pan FROM customers c LEFT JOIN customers parent ON c.parent_id = parent.id WHERE c.name LIKE ? AND c.agent_id=? ORDER BY c.name",
                conn, params=(f"%{name_search}%", st.session_state.current_agent['id'])
            )

            if not customers.empty:
                for _, customer in customers.iterrows():
                    display_customer_details(customer, conn)
            else:
                st.warning("No customers found with this name")

    elif search_option == "Family":
        # Get primary customers
        primary_customers = pd.read_sql_query(
            "SELECT id, name, pan FROM customers WHERE agent_id=? AND parent_id IS NULL ORDER BY name",
            conn, params=(st.session_state.current_agent['id'],)
        )

        if not primary_customers.empty:
            family_options = {row['id']: f"{row['name']} ({row['pan']})" for _, row in primary_customers.iterrows()}
            selected_family = st.selectbox(
                "Select Family",
                options=list(family_options.keys()),
                format_func=lambda x: family_options[x]
            )

            if selected_family:
                # Get all family members
                family_members = pd.read_sql_query(
                    "SELECT c.*, parent.name as parent_name, parent.pan as parent_pan FROM customers c LEFT JOIN customers parent ON c.parent_id = parent.id WHERE (c.id = ? OR c.parent_id = ?) AND c.agent_id=? ORDER BY c.parent_id, c.name",
                    conn, params=(selected_family, selected_family, st.session_state.current_agent['id'])
                )

                for _, member in family_members.iterrows():
                    display_customer_details(member, conn)

    conn.close()

def display_customer_details(customer, conn):
    # Customer header with family info
    if customer.get('parent_id'):
        st.subheader(f"👤 {customer['name']} ({customer['relationship']} of {customer.get('parent_name', 'Unknown')})")
    else:
        st.subheader(f"👤 {customer['name']} (Primary Customer)")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**PAN:** {customer['pan']}")
        st.write(f"**Aadhar:** {customer['aadhar']}")
        st.write(f"**Phone:** {customer['phone']}")
    with col2:
        st.write(f"**Email:** {customer['email'] or 'Not provided'}")
        st.write(f"**Income Range:** {customer['income_range']}")
        st.write(f"**Customer Since:** {customer['created_at'][:10]}")

    # Get policies for this customer
    policies = pd.read_sql_query(
        "SELECT p.*, holder.name as holder_name FROM policies p LEFT JOIN customers holder ON p.policy_holder_id = holder.id WHERE p.customer_id=? ORDER BY p.start_date DESC",
        conn, params=(customer['id'],)
    )

    if not policies.empty:
        st.subheader("📋 Policies")
        for _, policy in policies.iterrows():
            status_emoji = "✅" if policy['status'] == 'Active' else "❌"

            with st.expander(f"{status_emoji} {policy['policy_number']} - {policy['type']} ({policy['status']})"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Provider:** {policy['provider']}")
                    st.write(f"**Premium:** ₹{policy['premium_amount']:,.2f}")
                    st.write(f"**Frequency:** {policy['frequency']}")

                with col2:
                    st.write(f"**Coverage:** {policy['coverage_type']}")
                    st.write(f"**Start Date:** {policy['start_date']}")
                    st.write(f"**End Date:** {policy['end_date']}")

                with col3:
                    st.write(f"**Nominee:** {policy['nominee_name']}")
                    if policy['nominee_pan']:
                        st.write(f"**Nominee PAN:** {policy['nominee_pan']}")
                    if policy.get('holder_name') and policy['holder_name'] != customer['name']:
                        st.write(f"**Policy Holder:** {policy['holder_name']}")

                # Show upcoming premiums for this policy
                premiums = pd.read_sql_query(
                    "SELECT * FROM premiums WHERE policy_id=? AND status='Pending' ORDER BY due_date LIMIT 3",
                    conn, params=(policy['id'],)
                )

                if not premiums.empty:
                    st.write("**Upcoming Premiums:**")
                    for _, premium in premiums.iterrows():
                        due_date = premium['due_date'][:10] if isinstance(premium['due_date'], str) else premium['due_date']
                        st.write(f"• ₹{premium['amount']:,.2f} due on {due_date}")

                    # Mark premium as paid
                    if st.button(f"Mark Next Premium as Paid", key=f"paid_{policy['id']}"):
                        mark_premium_as_paid(policy['id'], conn)
                        st.rerun()
    else:
        st.info("No policies found for this customer")

def mark_premium_as_paid(policy_id, conn):
    premium = pd.read_sql_query(
        "SELECT * FROM premiums WHERE policy_id=? AND status='Pending' ORDER BY due_date LIMIT 1",
        conn, params=(policy_id,)
    )
    if not premium.empty:
        c = conn.cursor()
        c.execute("UPDATE premiums SET status='Paid', paid_date=? WHERE id=?",
                  (datetime.now().date(), premium.iloc[0]['id']))
        conn.commit()
        st.success("Premium marked as paid!")

# Upcoming premiums page
def upcoming_premiums_page():
    st.title("📅 Upcoming Premiums")

    timeframe = st.selectbox("Show premiums due within",
                           ["30 days", "60 days", "90 days", "All upcoming"])

    days_map = {"30 days": 30, "60 days": 60, "90 days": 90, "All upcoming": 3650}
    days = days_map[timeframe]

    conn = sqlite3.connect('crm.db')
    premiums = pd.read_sql_query(
        "SELECT pr.due_date, pr.amount, pr.status, c.name as customer_name, p.policy_number, p.type as policy_type, p.provider, holder.name as policy_holder FROM premiums pr JOIN policies p ON pr.policy_id = p.id JOIN customers c ON p.customer_id = c.id LEFT JOIN customers holder ON p.policy_holder_id = holder.id WHERE c.agent_id=? AND pr.status='Pending' AND pr.due_date BETWEEN date('now') AND date('now', ?) ORDER BY pr.due_date",
        conn, params=(st.session_state.current_agent['id'], f"+{days} days")
    )

    if not premiums.empty:
        if isinstance(premiums['due_date'].iloc[0], str):
            premiums['due_date'] = pd.to_datetime(premiums['due_date']).dt.date

        total_amount = premiums['amount'].sum()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Total Amount Due", f"₹{total_amount:,.2f}")
        with col2:
            st.metric("📊 Number of Premiums", len(premiums))

        st.dataframe(premiums, use_container_width=True)

        # Option to mark as paid  
        st.subheader("Mark Premium as Paid")
        policy_options = premiums['policy_number'].unique()
        selected_policy = st.selectbox("Select Policy", policy_options)

        if selected_policy:
            policy_premiums = premiums[premiums['policy_number'] == selected_policy]
            due_dates = policy_premiums['due_date'].tolist()
            selected_date = st.selectbox("Select Due Date", due_dates)

            if st.button("Mark as Paid", type="primary"):
                c = conn.cursor()
                c.execute(
                    "UPDATE premiums SET status='Paid', paid_date=? WHERE policy_id=(SELECT id FROM policies WHERE policy_number=?) AND due_date=?",
                    (datetime.now().date(), selected_policy, selected_date)
                )
                conn.commit()
                st.success("Premium marked as paid!")
                st.rerun()
    else:
        st.info("No upcoming premiums found")

    conn.close()
# Database Viewer page
def database_viewer_page():
    st.title("📑 Database Viewer")
    st.markdown("Browse raw data stored in the SQLite database")

    conn = sqlite3.connect("crm.db")
    tables = ["agents", "customers", "policies", "premiums"]

    selected_table = st.selectbox("Select Table", tables)

    try:
        df = pd.read_sql_query(f"SELECT * FROM {selected_table}", conn)

        # 🔹 Fix formatting for specific columns
        if "phone" in df.columns:
            df["phone"] = df["phone"].astype(str)
        if "aadhar" in df.columns:
            df["aadhar"] = df["aadhar"].astype(str)
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(
                df["created_at"], errors="coerce", infer_datetime_format=True
            ).dt.date

        if df.empty:
            st.info(f"No records found in table `{selected_table}`.")
        else:
            st.dataframe(df, use_container_width=True)

            # Show row count
            st.write(f"**Total Rows:** {len(df)}")

            # ✅ Download as CSV with utf-8-sig (Excel friendly)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=f"⬇️ Download {selected_table} as CSV",
                data=csv,
                file_name=f"{selected_table}.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Error loading table: {e}")

    conn.close()

# Main app logic
def main():
    if st.session_state.current_agent is None:
        login_page()
    else:
        render_sidebar()
        if st.session_state.page == 'Dashboard':
            dashboard_page()
        elif st.session_state.page == 'Customer Enrollment':
            customer_enrollment_page()
        elif st.session_state.page == 'Policy Enrollment':
            policy_enrollment_page()
        elif st.session_state.page == 'Records':
            records_page()
        elif st.session_state.page == 'Family Management':
            family_management_page()
        elif st.session_state.page == 'Upcoming Premiums':
            upcoming_premiums_page()

if __name__ == "__main__":
    main()
