import bcrypt
import streamlit as st
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Time, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import date, time

# Setting up the SQLAlchemy engine and session
engine = create_engine('sqlite:///turf_booking.db')  # Using SQLite for simplicity
Session = sessionmaker(bind=engine)
session = Session()

# Base class for declarative models
Base = declarative_base()

# Define the User model
class User(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # "user" or "owner"

# Define the Slot model
class Slot(Base):
    __tablename__ = 'slots'
    slot_id = Column(Integer, primary_key=True, autoincrement=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    date = Column(Date, nullable=False)
    availability = Column(Boolean, default=True)

# Define the Booking model
class Booking(Base):
    __tablename__ = 'bookings'
    booking_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    slot_id = Column(Integer, ForeignKey('slots.slot_id'), nullable=False)
    confirmation_status = Column(Boolean, default=True)

    user = relationship('User')
    slot = relationship('Slot')

# Create tables
Base.metadata.create_all(engine)

# Helper functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def register_user(name, email, phone, password, role):
    try:
        hashed_pw = hash_password(password)
        new_user = User(name=name, email=email, phone=phone, password=hashed_pw, role=role)
        session.add(new_user)
        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False

def authenticate_user(email, password):
    user = session.query(User).filter_by(email=email).first()
    if user and check_password(password, user.password):
        return user
    return None

def generate_slots_for_date(selected_date):
    if not session.query(Slot).filter(Slot.date == selected_date).first():
        for hour in range(24):
            session.add(Slot(
                start_time=time(hour, 0), 
                end_time=time((hour + 1) % 24, 0), 
                date=selected_date
            ))
        session.commit()

def get_available_slots(selected_date):
    generate_slots_for_date(selected_date)
    return session.query(Slot).filter(Slot.date == selected_date).all()

def book_slot(user_id, slot_ids):
    successful_bookings = []
    for slot_id in slot_ids:
        slot = session.query(Slot).filter(Slot.slot_id == slot_id, Slot.availability == True).first()
        if slot:
            slot.availability = False
            booking = Booking(user_id=user_id, slot_id=slot_id)
            session.add(booking)
            successful_bookings.append(slot)
    session.commit()
    for slot in successful_bookings:
        user = session.query(User).filter(User.user_id == user_id).first()
        send_notification(user, slot)
    return successful_bookings

def cancel_booking(booking_id):
    booking = session.query(Booking).filter_by(booking_id=booking_id).first()
    if booking:
        booking.slot.availability = True
        session.delete(booking)
        session.commit()
        return True
    return False

def send_notification(user, slot):
    user_message = f"Hello {user.name},\nYour booking is confirmed for {slot.date} from {slot.start_time} to {slot.end_time}.\nThank you!"
    owner_message = f"New booking by {user.name}.\nDate: {slot.date}\nTime: {slot.start_time} to {slot.end_time}\nUser Email: {user.email}\nUser Phone: {user.phone}"

    # Mock sending email and SMS
    st.write(f"Email sent to {user.email}: {user_message}")
    st.write(f"Email sent to owner@example.com: {owner_message}")

def render_bookings_as_cards(bookings, page, items_per_page=3):
    start = page * items_per_page
    end = start + items_per_page
    bookings_on_page = bookings[start:end]

    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]

    for i, booking in enumerate(bookings_on_page):
        with columns[i % 3]:
            st.markdown(
                f"""
                <div style="border: 1px solid #ddd; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                    <h4 style="color: #4CAF50;">Booking ID: {booking.booking_id}</h4>
                    <p><strong>Date:</strong> {booking.slot.date}</p>
                    <p><strong>Time:</strong> {booking.slot.start_time.strftime('%H:%M')} to {booking.slot.end_time.strftime('%H:%M')}</p>
                    <p><strong>User:</strong> {booking.user.name}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

# Streamlit App
st.set_page_config(page_title="TURF Booking System", page_icon=":soccer:")

# Background and Style
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f9f9f9;
    }
    .stButton>button {
        color: white;
        background-color: #4CAF50;
        border-radius: 8px;
    }
    .google-btn {
        background-color: black;
        color: white;
        border-radius: 8px;
        width: 100%;
    }
    .google-logo {
        vertical-align: middle;
        margin-right: 10px;
    }
    .stTextInput>div>div>input {
        border: 1px solid #ddd;
    }
    h1 {
        color: #4CAF50;
    }
    h2 {
        color: #4CAF50;
    }
    h3 {
        color: #4CAF50;
    }
    h4 {
        color: #4CAF50;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("TURF Booking System :soccer:")

# Sidebar for authentication
with st.sidebar:
    if 'user' not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        st.header("Welcome to TURF Booking")

        # Use buttons instead of radio buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Login"):
                st.session_state.auth_action = "Login"
        with col2:
            if st.button("Sign Up"):
                st.session_state.auth_action = "Register"
        with col3:
            if st.button("Sign in with Google",type="primary"):
                st.session_state.auth_action = "Google"

        if 'auth_action' in st.session_state:
            if st.session_state.auth_action == "Login":
                # Show login fields
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                
                if st.button("Login Now"):
                    # Validate inputs
                    if not email or not password:
                        st.error("Email and password are required!")
                    else:
                        user = authenticate_user(email, password)
                        if user:
                            st.session_state.user = user
                            st.success(f"Welcome, {user.name}!")
                        else:
                            st.error("Invalid email or password.")

            elif st.session_state.auth_action == "Register":
                # Show registration fields
                role = st.radio("Register as", ["User", "Owner"])
                name = st.text_input("Name", key="register_name")
                email = st.text_input("Email", key="register_email")
                phone = st.text_input("Phone", key="register_phone")
                password = st.text_input("Password", type="password", key="register_password")
                
                if st.button("Register Now"):
                    # Validate inputs
                    if not name or not email or not phone or not password:
                        st.error("All fields are required!")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        if register_user(name, email, phone, password, role.lower()):
                            st.success("Registration successful! Please log in.")
                        else:
                            st.error("Registration failed. Email might already be in use.")

            elif st.session_state.auth_action == "Google":
                # Simulate Google Sign-In
                st.button("Sign in with Google", help="Google Sign-In is not implemented in this example.", 
                          key="google_signin", on_click=lambda: st.info("Google Sign-In is not implemented in this example."),
                          style="google-btn")
                st.markdown("""
                    <button class="google-btn">
                        <img class="google-logo" src="https://www.gstatic.com/images/branding/product/1x/gsa_48dp.png" width="20"/>
                        Sign in with Google
                    </button>
                    """, unsafe_allow_html=True)

    else:
        if st.button("Logout"):
            st.session_state.user = None
            st.success("Logged out successfully.")

# Main Content Area (Right Side)
if st.session_state.user is None:
    # Display welcome content
    st.write("## Welcome to the TURF Booking System")
    st.write("Easily manage your turf bookings with our user-friendly system.")
    st.image("https://lh3.googleusercontent.com/p/AF1QipPGvhDAFOx-gW6IbfKuZx3mbRXmlQVhfJyPThQN=s1360-w1360-h1020", caption="Turf Location")
    st.write("### Features:")
    st.write("- Easy booking and cancellation")
    st.write("- Real-time slot availability")
    st.write("- Manage bookings efficiently")
    st.image("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTM6fYuTm2-aOOpqldtBbhcce-o1SZGVD2u1w&s", width=100, caption="Join our community")

# Main Dashboard Logic
if st.session_state.user:
    user = st.session_state.user
    st.header(f"Welcome, {user.name} :wave:")

    if user.role == "user":
        st.subheader("User Dashboard")
        choice = st.selectbox("What would you like to do?", ["Book a Slot", "Cancel Booking", "List Bookings", "Get Turf Details"])

        if choice == "Book a Slot":
            selected_date = st.date_input("Select a Date", value=date.today())
            slots = get_available_slots(selected_date)
            
            # Filter only available slots
            available_slots = [slot for slot in slots if slot.availability]
            slot_options = [f"{slot.start_time.strftime('%H:%M')} to {slot.end_time.strftime('%H:%M')}" for slot in available_slots]
            slot_ids = [slot.slot_id for slot in available_slots]

            if slot_options:
                # Using multiselect for available slots
                selected_slots = st.multiselect(
                    "Select Slots",
                    options=slot_options
                )

                if st.button("Book Now"):
                    selected_slot_indices = [slot_options.index(slot) for slot in selected_slots]
                    selected_slot_ids = [slot_ids[i] for i in selected_slot_indices]
                    booked_slots = book_slot(user.user_id, selected_slot_ids)
                    if booked_slots:
                        st.success(f"Booking confirmed for {len(booked_slots)} slot(s)!")
                    else:
                        st.error("One or more selected slots are already booked. Please choose other slots.")
            else:
                st.info("No available slots for the selected date. Please choose another date.")

        elif choice == "Cancel Booking":
            bookings = session.query(Booking).filter_by(user_id=user.user_id).all()
            if bookings:
                booking_options = [f"Booking ID: {booking.booking_id}, Date: {booking.slot.date}, Time: {booking.slot.start_time.strftime('%H:%M')} to {booking.slot.end_time.strftime('%H:%M')}" for booking in bookings]
                selected_booking_index = st.selectbox("Select a Booking to Cancel", range(len(booking_options)), format_func=lambda x: booking_options[x])
                selected_booking = bookings[selected_booking_index]

                if st.button("Cancel Booking"):
                    if cancel_booking(selected_booking.booking_id):
                        st.success("Booking cancelled successfully.")
                    else:
                        st.error("Failed to cancel booking.")
            else:
                st.info("You have no bookings to cancel.")

        elif choice == "List Bookings":
            bookings = session.query(Booking).filter_by(user_id=user.user_id).all()
            if bookings:
                st.write("Your Bookings:")
                items_per_page = 3
                total_pages = (len(bookings) - 1) // items_per_page + 1
                page = st.number_input("Page", min_value=1, max_value=total_pages, step=1) - 1
                render_bookings_as_cards(bookings, page, items_per_page)
            else:
                st.info("No bookings found.")

        elif choice == "Get Turf Details":
            st.write("Turf Details:")
            st.image("https://example.com/turf_image.jpg", caption="Turf Location")
            st.write("Location: XYZ Sports Complex")
            st.write("Size: 100x50 meters")
            st.write("Surface: Artificial Grass")

    elif user.role == "owner":
        st.subheader("Owner Dashboard")
        choice = st.selectbox("What would you like to do?", ["Create Slot", "Block Slot", "Check Bookings"])

        if choice == "Create Slot":
            selected_date = st.date_input("Select a Date", value=date.today())
            start_hour = st.number_input("Start Hour", min_value=0, max_value=23, value=0)
            end_hour = (start_hour + 1) % 24

            if st.button("Create Slot"):
                slot_exists = session.query(Slot).filter(Slot.date == selected_date, Slot.start_time == time(start_hour, 0)).first()
                if not slot_exists:
                    session.add(Slot(start_time=time(start_hour, 0), end_time=time(end_hour, 0), date=selected_date))
                    session.commit()
                    st.success("Slot created successfully.")
                else:
                    st.warning("Slot already exists.")

        elif choice == "Block Slot":
            selected_date = st.date_input("Select a Date", value=date.today())
            slots = session.query(Slot).filter(Slot.date == selected_date).all()
            if slots:
                slot_options = [f"Slot ID: {slot.slot_id}, Time: {slot.start_time.strftime('%H:%M')} to {slot.end_time.strftime('%H:%M')}" for slot in slots]
                selected_slot_index = st.selectbox("Select a Slot to Block", range(len(slot_options)), format_func=lambda x: slot_options[x])
                selected_slot = slots[selected_slot_index]

                if st.button("Block Slot"):
                    selected_slot.availability = False
                    session.commit()
                    st.success("Slot blocked successfully.")
            else:
                st.info("No slots found for the selected date.")

        elif choice == "Check Bookings":
            selected_date = st.date_input("Select a Date", value=date.today())
            bookings = session.query(Booking).join(Slot).filter(Slot.date == selected_date).all()
            if bookings:
                st.write("Bookings for the Day:")
                items_per_page = 3
                total_pages = (len(bookings) - 1) // items_per_page + 1
                page = st.number_input("Page", min_value=1, max_value=total_pages, step=1) - 1
                render_bookings_as_cards(bookings, page, items_per_page)
            else:
                st.info("No bookings found for the selected date.")
