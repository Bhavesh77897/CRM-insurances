import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime, timedelta
import os

# Set up the page
st.set_page_config(
    page_title="Insurance CRM System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Database setup
def init_db():
    # Create data directory if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')

    # Connect to database in data directory
    conn = sqlite3.connect('data/crm.db')
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
    conn = sqlite3.connect('data/crm.db')
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
    conn = sqlite3.connect('data/crm.db')
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

        # Data management section
        st.divider()
        st.subheader("Data Management")

        if st.button("💾 Export Data (CSV + TXT)", use_container_width=True):
            export_data_to_csv_and_txt()

        st.divider()

        if st.session_state.current_agent:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.current_agent = None
                st.session_state.page = 'Login'
                st.rerun()


# Data export function - FIXED VERSION
from datetime import datetime


def export_data_to_csv_and_txt():
    try:
        export_path = r"D:\test"
        if not os.path.exists(export_path):
            os.makedirs(export_path)

        conn = sqlite3.connect('data/crm.db')

        # Add timestamp to avoid locked overwrite issues
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # --- Customers ---
        customers_df = pd.read_sql_query(
            "SELECT * FROM customers WHERE agent_id=?",
            conn, params=(st.session_state.current_agent['id'],)
        )
        customers_file = os.path.join(export_path, f"customers_export_{timestamp}.csv")
        customers_df.to_csv(customers_file, index=False, encoding="utf-8-sig")

        # --- Policies with all statuses ---
        policies_df = pd.read_sql_query('''
            SELECT p.*, c.name as customer_name 
            FROM policies p 
            JOIN customers c ON p.customer_id = c.id 
            WHERE c.agent_id=?
        ''', conn, params=(st.session_state.current_agent['id'],))
        policies_file = os.path.join(export_path, f"policies_export_{timestamp}.csv")
        policies_df.to_csv(policies_file, index=False, encoding="utf-8-sig")

        # --- Premiums ---
        premiums_df = pd.read_sql_query('''
            SELECT pr.*, p.policy_number, c.name as customer_name, p.status as policy_status
            FROM premiums pr 
            JOIN policies p ON pr.policy_id = p.id 
            JOIN customers c ON p.customer_id = c.id 
            WHERE c.agent_id=?
        ''', conn, params=(st.session_state.current_agent['id'],))
        premiums_file = os.path.join(export_path, f"premiums_export_{timestamp}.csv")
        premiums_df.to_csv(premiums_file, index=False, encoding="utf-8-sig")

        # --- TXT Export ---
        txt_file = os.path.join(export_path, f"data_export_{timestamp}.txt")
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write("=== Customers ===\n\n")
            f.write(customers_df.to_string(index=False))
            f.write("\n\n=== Policies ===\n\n")
            f.write(policies_df.to_string(index=False))
            f.write("\n\n=== Premiums ===\n\n")
            f.write(premiums_df.to_string(index=False))
            f.write("\n")

        conn.close()

        st.sidebar.success(f"✅ Data exported successfully to {export_path}")
        st.sidebar.info("📁 Files created with timestamp suffix (CSV + TXT)")

    except Exception as e:
        st.sidebar.error(f"❌ Error exporting data: {str(e)}")


# Add this function to update policy status automatically


def update_policy_status(policy_id, conn):
    c = conn.cursor()

    # First check if policy is already cancelled
    c.execute("SELECT status FROM policies WHERE id=?", (policy_id,))
    current_status = c.fetchone()[0]

    # If policy is already cancelled, don't change the status
    if current_status == 'Cancelled':
        return

    # Check if all premiums are paid
    c.execute("SELECT COUNT(*) FROM premiums WHERE policy_id=? AND status='Pending'", (policy_id,))
    pending_count = c.fetchone()[0]

    if pending_count == 0:
        # All premiums paid - mark as Completed
        c.execute("UPDATE policies SET status='Completed' WHERE id=?", (policy_id,))
    else:
        # Check if any premium is overdue
        c.execute("SELECT COUNT(*) FROM premiums WHERE policy_id=? AND status='Pending' AND due_date < date('now')",
                  (policy_id,))
        overdue_count = c.fetchone()[0]

        if overdue_count > 0:
            # Has overdue premiums - mark as Lapsed
            c.execute("UPDATE policies SET status='Lapsed' WHERE id=?", (policy_id,))
        else:
            # Has pending premiums but none overdue - mark as Active
            c.execute("UPDATE policies SET status='Active' WHERE id=?", (policy_id,))

    conn.commit()

# Modify the mark_premium_as_paid function to call update_policy_status
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

        # Update policy status after marking premium as paid
        update_policy_status(policy_id, conn)
        st.success("Premium marked as paid!")


# Add a function to cancel a policy
def cancel_policy(policy_id, conn):
    c = conn.cursor()

    # First, delete all pending premiums for this policy
    c.execute("DELETE FROM premiums WHERE policy_id=? AND status='Pending'", (policy_id,))

    # Then mark the policy as cancelled (direct update without calling update_policy_status)
    c.execute("UPDATE policies SET status='Cancelled' WHERE id=?", (policy_id,))

    conn.commit()
    st.success("Policy cancelled successfully! All pending premiums have been removed.")
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
    conn = sqlite3.connect('data/crm.db')

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

    # Add counts for other statuses
    lapsed_policies_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM policies p JOIN customers c ON p.customer_id = c.id WHERE c.agent_id=? AND p.status='Lapsed'",
        conn, params=(st.session_state.current_agent['id'],)
    ).iloc[0]['count']

    completed_policies_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM policies p JOIN customers c ON p.customer_id = c.id WHERE c.agent_id=? AND p.status='Completed'",
        conn, params=(st.session_state.current_agent['id'],)
    ).iloc[0]['count']

    cancelled_policies_count = pd.read_sql_query(
        "SELECT COUNT(*) as count FROM policies p JOIN customers c ON p.customer_id = c.id WHERE c.agent_id=? AND p.status='Cancelled'",
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

    # Additional policy status metrics
    st.subheader("Policy Status Overview")
    status_col1, status_col2, status_col3, status_col4 = st.columns(4)
    with status_col1:
        st.metric("⏰ Lapsed Policies", lapsed_policies_count)
    with status_col2:
        st.metric("🏁 Completed Policies", completed_policies_count)
    with status_col3:
        st.metric("❌ Cancelled Policies", cancelled_policies_count)
    with status_col4:
        total_pending = upcoming_premiums['amount'].sum() if not upcoming_premiums.empty else 0
        st.metric("💰 Pending Premiums", f"₹{total_pending:,.2f}")

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
    conn = sqlite3.connect('data/crm.db')
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
                parent_options = {row['id']: f"{row['name']} ({row['pan']})" for _, row in
                                  existing_customers.iterrows()}
                selected_parent = st.selectbox(
                    "Select Parent/Primary Customer",
                    options=[""] + list(parent_options.keys()),
                    format_func=lambda x: parent_options.get(x,
                                                             "Select Parent Customer") if x else "Select Parent Customer"
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
            conn = sqlite3.connect('data/crm.db')
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
                    (customer_id, st.session_state.current_agent['id'], pan_card, aadhar_number,
                     customer_name, phone_number, email_address, income_range,
                     parent_customer_id, relationship, datetime.now().date()))
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
    conn = sqlite3.connect('data/crm.db')
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
            conn = sqlite3.connect('data/crm.db')
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

    conn = sqlite3.connect('data/crm.db')

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

                # Add sorting options
                sort_option = st.selectbox(
                    "Sort policies by",
                    ["Status", "Policy Number", "Type", "Provider"],
                    key=f"sort_{primary['id']}"
                )

                # Apply sorting
                if sort_option == "Status":
                    family_policies = family_policies.sort_values("status")
                elif sort_option == "Policy Number":
                    family_policies = family_policies.sort_values("policy_number")
                elif sort_option == "Type":
                    family_policies = family_policies.sort_values("type")
                elif sort_option == "Provider":
                    family_policies = family_policies.sort_values("provider")

                st.dataframe(family_policies, use_container_width=True)

    conn.close()


# Records page
def records_page():
    st.title("🔍 Customer Records")
    st.markdown("Search and view customer information and policies")

    search_option = st.radio("Search by", ["PAN Card", "Customer Name", "Family"])

    conn = sqlite3.connect('data/crm.db')

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


# Update the display_customer_details function to handle cancelled policies better
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

    # Get policies for this customer (including cancelled ones)
    policies = pd.read_sql_query(
        "SELECT p.*, holder.name as holder_name FROM policies p LEFT JOIN customers holder ON p.policy_holder_id = holder.id WHERE p.customer_id=? ORDER BY p.start_date DESC",
        conn, params=(customer['id'],)
    )

    if not policies.empty:
        st.subheader("📋 Policies")

        # Add policy status filter
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Active", "Lapsed", "Completed", "Cancelled"],
            key=f"status_filter_{customer['id']}"
        )

        if status_filter != "All":
            policies = policies[policies['status'] == status_filter]

        for _, policy in policies.iterrows():
            status_emoji = "✅" if policy['status'] == 'Active' else "⏰" if policy['status'] == 'Lapsed' else "🏁" if policy['status'] == 'Completed' else "❌"

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

                # Policy actions - only show for active/lapsed policies
                if policy['status'] in ['Active', 'Lapsed']:
                    if st.button(f"❌ Cancel Policy", key=f"cancel_{policy['id']}"):
                        cancel_policy(policy['id'], conn)
                        st.rerun()

                # Show premium history only for non-cancelled policies
                if policy['status'] != 'Cancelled':
                    premiums = pd.read_sql_query(
                        "SELECT * FROM premiums WHERE policy_id=? ORDER BY due_date",
                        conn, params=(policy['id'],)
                    )

                    if not premiums.empty:
                        st.write("**Premium History:**")

                        # Separate paid and pending premiums
                        paid_premiums = premiums[premiums['status'] == 'Paid']
                        pending_premiums = premiums[premiums['status'] == 'Pending']

                        if not paid_premiums.empty:
                            st.write("**Paid Premiums:**")
                            for _, premium in paid_premiums.iterrows():
                                paid_date = premium['paid_date'][:10] if isinstance(premium['paid_date'], str) else premium['paid_date']
                                due_date = premium['due_date'][:10] if isinstance(premium['due_date'], str) else premium['due_date']
                                st.write(f"• ₹{premium['amount']:,.2f} paid on {paid_date} (due: {due_date})")

                        if not pending_premiums.empty:
                            st.write("**Upcoming Premiums:**")
                            for _, premium in pending_premiums.iterrows():
                                due_date = premium['due_date'][:10] if isinstance(premium['due_date'], str) else premium['due_date']
                                # Fixed line below:
                                status_icon = "⏰" if pd.to_datetime(due_date).date() < datetime.now().date() else "📅"
                                st.write(f"• {status_icon} ₹{premium['amount']:,.2f} due on {due_date}")

                        # Mark premium as paid (only for pending premiums)
                        if not pending_premiums.empty:
                            due_dates = [premium['due_date'] for _, premium in pending_premiums.iterrows()]
                            selected_due_date = st.selectbox(
                                "Select premium to mark as paid",
                                due_dates,
                                key=f"premium_select_{policy['id']}",
                                format_func=lambda x: x[:10] if isinstance(x, str) else x
                            )

                            if st.button(f"Mark Premium as Paid", key=f"pay_{policy['id']}"):
                                mark_specific_premium_as_paid(policy['id'], selected_due_date, conn)
                                st.rerun()
                else:
                    st.info("This policy has been cancelled. No premium payments are required.")
    else:
        st.info("No policies found for this customer")


# Also update the mark_specific_premium_as_paid function to not update status for cancelled policies
def mark_specific_premium_as_paid(policy_id, due_date, conn):
    # First check if policy is cancelled
    c = conn.cursor()
    c.execute("SELECT status FROM policies WHERE id=?", (policy_id,))
    policy_status = c.fetchone()[0]

    if policy_status == 'Cancelled':
        st.error("Cannot mark premium as paid for a cancelled policy!")
        return

    c.execute("UPDATE premiums SET status='Paid', paid_date=? WHERE policy_id=? AND due_date=?",
              (datetime.now().date(), policy_id, due_date))
    conn.commit()

    # Update policy status after marking premium as paid (only if not cancelled)
    if policy_status != 'Cancelled':
        update_policy_status(policy_id, conn)
    st.success("Premium marked as paid!")


# Upcoming premiums page with enhanced features
# Update the upcoming_premiums_page function to exclude cancelled policies
def upcoming_premiums_page():
    st.title("📅 Upcoming Premiums")

    timeframe = st.selectbox("Show premiums due within",
                             ["30 days", "60 days", "90 days", "All upcoming", "Overdue"])

    # Status filter - exclude cancelled policies
    status_filter = st.selectbox("Filter by Policy Status",
                                 ["All", "Active", "Lapsed", "Completed"])

    days_map = {"30 days": 30, "60 days": 60, "90 days": 90, "All upcoming": 3650, "Overdue": -3650}
    days = days_map[timeframe]

    conn = sqlite3.connect('data/crm.db')

    # Build query based on filters - exclude cancelled policies
    query = '''
        SELECT pr.due_date, pr.amount, pr.status as premium_status, 
               c.name as customer_name, p.policy_number, p.type as policy_type, 
               p.provider, p.status as policy_status, holder.name as policy_holder 
        FROM premiums pr 
        JOIN policies p ON pr.policy_id = p.id 
        JOIN customers c ON p.customer_id = c.id 
        LEFT JOIN customers holder ON p.policy_holder_id = holder.id 
        WHERE c.agent_id=? AND pr.status='Pending' AND p.status != 'Cancelled'
    '''

    params = [st.session_state.current_agent['id']]

    if timeframe == "Overdue":
        query += " AND pr.due_date < date('now')"
    elif timeframe != "All upcoming":
        query += " AND pr.due_date BETWEEN date('now') AND date('now', ?)"
        params.append(f"+{days} days")

    if status_filter != "All":
        query += " AND p.status=?"
        params.append(status_filter)

    query += " ORDER BY pr.due_date"

    premiums = pd.read_sql_query(query, conn, params=params)

    if not premiums.empty:
        if isinstance(premiums['due_date'].iloc[0], str):
            premiums['due_date'] = pd.to_datetime(premiums['due_date']).dt.date

        total_amount = premiums['amount'].sum()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Total Amount Due", f"₹{total_amount:,.2f}")
        with col2:
            st.metric("📊 Number of Premiums", len(premiums))
        with col3:
            overdue_count = len(premiums[premiums['due_date'] < datetime.now().date()])
            st.metric("⏰ Overdue Premiums", overdue_count)

        # Add sorting options
        sort_option = st.selectbox("Sort by", ["Due Date", "Amount", "Customer Name", "Policy Number"])

        if sort_option == "Due Date":
            premiums = premiums.sort_values("due_date")
        elif sort_option == "Amount":
            premiums = premiums.sort_values("amount", ascending=False)
        elif sort_option == "Customer Name":
            premiums = premiums.sort_values("customer_name")
        elif sort_option == "Policy Number":
            premiums = premiums.sort_values("policy_number")

        # Format display
        display_df = premiums.copy()
        display_df['due_date'] = display_df['due_date'].apply(
            lambda x: x.strftime('%Y-%m-%d') if hasattr(x, 'strftime') else x)
        display_df['amount'] = display_df['amount'].apply(lambda x: f"₹{x:,.2f}")

        st.dataframe(display_df, use_container_width=True)

        # Bulk actions section
        st.subheader("Bulk Actions")

        # Select policies with premiums
        policy_options = premiums['policy_number'].unique()
        selected_policies = st.multiselect("Select Policies", policy_options)

        if selected_policies:
            # Get due dates for selected policies
            selected_premiums = premiums[premiums['policy_number'].isin(selected_policies)]
            due_dates = selected_premiums['due_date'].unique()

            if st.button("Mark Selected Premiums as Paid", type="primary"):
                c = conn.cursor()
                for policy_number in selected_policies:
                    policy_premiums = selected_premiums[selected_premiums['policy_number'] == policy_number]
                    for due_date in policy_premiums['due_date']:
                        c.execute(
                            "UPDATE premiums SET status='Paid', paid_date=? WHERE policy_id=(SELECT id FROM policies WHERE policy_number=?) AND due_date=?",
                            (datetime.now().date(), policy_number, due_date)
                        )
                        # Update policy status
                        c.execute("SELECT id FROM policies WHERE policy_number=?", (policy_number,))
                        policy_id = c.fetchone()[0]
                        update_policy_status(policy_id, conn)

                conn.commit()
                st.success("Selected premiums marked as paid!")
                st.rerun()
    else:
        st.info("No upcoming premiums found")

    conn.close()

# Add a function to update all policy statuses (for maintenance)
def update_all_policy_statuses():
    conn = sqlite3.connect('data/crm.db')
    c = conn.cursor()

    # Get all policies for this agent
    c.execute('''
        SELECT p.id FROM policies p 
        JOIN customers c ON p.customer_id = c.id 
        WHERE c.agent_id=?
    ''', (st.session_state.current_agent['id'],))

    policy_ids = [row[0] for row in c.fetchall()]

    for policy_id in policy_ids:
        update_policy_status(policy_id, conn)

    conn.close()
    st.sidebar.success("All policy statuses updated!")


# Add this to the sidebar for maintenance
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

        # Data management section
        st.divider()
        st.subheader("Data Management")

        if st.button("💾 Export Data (CSV + TXT)", use_container_width=True):
            export_data_to_csv_and_txt()

        if st.button("🔄 Update All Policy Statuses", use_container_width=True):
            update_all_policy_statuses()

        st.divider()

        if st.session_state.current_agent:
            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.current_agent = None
                st.session_state.page = 'Login'
                st.rerun()


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
