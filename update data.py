import sqlite3
import uuid
import getpass
import random
import time
from datetime import datetime
import string

DB = "users.db"

# Database Connection ---
def connect_db():
    conn = sqlite3.connect(DB, timeout=30)  # Wait up to 10 seconds if locked
    conn.row_factory = sqlite3.Row
    return conn

# Initialize Database ---
def init_db():
    with connect_db() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            dob TEXT,
            phone TEXT,
            code_word TEXT,
            username TEXT UNIQUE,
            password TEXT,
            created_at INTEGER
        )
        """)
        conn.commit()

# Add Missing Columns ---
def add_missing_columns():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(users)")
        existing_cols = [row["name"] for row in cur.fetchall()]
        required_cols = {"first_name": "TEXT", "last_name": "TEXT"}
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    conn.commit()
                    print(f"✅ Column '{col}' added successfully.")
                except Exception as e:
                    print(f"❌ Failed to add '{col}':", e)

# OTP Verification ---
def otp_verification(phone=None):
    otp = random.randint(1000, 9999)
    if phone:
        print(f"\n📱 Sending OTP to {phone}...")
    time.sleep(1)
    print(f"Your OTP is: {otp}")

    attempts = 0
    while attempts < 3:
        entered = input("Enter OTP: ").strip()
        if entered == str(otp):
            print("✅ OTP verified.")
            return True
        else:
            attempts += 1
            if attempts < 3:
                print(f"❌ Incorrect OTP. Attempts left: {3 - attempts}")
            else:
                print("❌ Incorrect OTP. Maximum attempts reached.")
                return False
    return False

# Register New User ---
def register_user():
    print("\n--- User Registration ---")
    first_name = input("First Name: ").strip()
    last_name  = input("Last Name: ").strip()

    # Date of Birth validation (dd/mm/yyyy) ---
    attempts = 0
    dob = ""
    current_year = 2025
    while attempts < 3:
        dob = input("Date of Birth (dd/mm/yyyy): ").strip()
        attempts += 1

        try:
            parsed_date = datetime.strptime(dob, "%d/%m/%Y")
            day, month, year = parsed_date.day, parsed_date.month, parsed_date.year

            if not (1 <= day <= 31):
                print(f"Invalid day! Must be between 1 and 31. Attempts left: {3 - attempts}")
                if attempts >= 3:
                    print("Maximum attempts reached. Registration cancelled.")
                    return
                continue
            if not (1 <= month <= 12):
                print(f"Invalid month! Must be between 1 and 12. Attempts left: {3 - attempts}")
                if attempts >= 3:
                    print("Maximum attempts reached. Registration cancelled.")
                    return
                continue
            if year > current_year:
                print(f"Invalid year! Year cannot be greater than {current_year}. Attempts left: {3 - attempts}")
                if attempts >= 3:
                    print("Maximum attempts reached. Registration cancelled.")
                    return
                continue

            break
        except ValueError:
            print(f"Invalid format! Please use dd/mm/yyyy. Attempts left: {3 - attempts}")
            if attempts >= 3:
                print("Maximum attempts reached. Registration cancelled.")
                return
            continue

    # Phone number validation with retry ---
    attempts = 0
    phone = ""
    while attempts < 3:
        phone = input("Phone Number: ").strip()
        attempts += 1

        if not phone:
            print(f"Phone number is required. Attempts left: {3 - attempts}")
            if attempts >= 3:
                print("Maximum attempts reached. Registration cancelled.")
                return
            continue
        if not phone.isdigit():
            print(f"Invalid phone number: only digits are allowed. Attempts left: {3 - attempts}")
            if attempts >= 3:
                print("Maximum attempts reached. Registration cancelled.")
                return
            continue
        if len(phone) != 11:
            print(f"Invalid phone number: must contain exactly 11 digits. Attempts left: {3 - attempts}")
            if attempts >= 3:
                print("Maximum attempts reached. Registration cancelled.")
                return
            continue
        if not phone.startswith("01"):
            print(f"Invalid phone number: must start with '01'. Attempts left: {3 - attempts}")
            if attempts >= 3:
                print("Maximum attempts reached. Registration cancelled.")
                return
            continue
        if phone[2] not in "3456789":
            print(f"Invalid phone number: the 3rd digit must be between 3 and 9. Attempts left: {3 - attempts}")
            if attempts >= 3:
                print("Maximum attempts reached. Registration cancelled.")
                return
            continue
        break

    if not otp_verification(phone):
        print("❌ Registration cancelled due to failed OTP verification.")
        return

    code_word  = input("Code Word (for recovery): ").strip()
    username   = input("Choose a Username: ").strip()
    password   = getpass.getpass("Choose a Password: ").strip()

    if not username or not password:
        print("Username and password cannot be empty.")
        return

    # Generate a unique user_id
    with connect_db() as conn:
        cur = conn.cursor()
        while True:
            user_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
            if not cur.fetchone():
                break

    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
            if cur.fetchone():
                print("Username already exists. Try another one.")
                return

            cur.execute("""
                INSERT INTO users (
                    id, first_name, last_name, dob, phone, code_word, username, password, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, first_name, last_name, dob, phone, code_word, username, password, int(time.time())))
            conn.commit()
            print(f"✅ Registration successful! Your User ID: {user_id}")
    except sqlite3.IntegrityError as e:
        print("Database integrity error:", e)
    except Exception as e:
        print("An unexpected error occurred while registering:", e)

# User Login ---
def login_user():
    print("\n--- Login ---")
    attempts = 0
    while attempts < 3:
        username = input("Username: ").strip()
        password = getpass.getpass("Password: ").strip()

        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()

            if not user:
                attempts += 1
                if attempts < 3:
                    print(f"Invalid username or password. Attempts left: {3 - attempts}")
                    continue
                else:
                    print("Invalid username or password.")
                    return None
            else:
                print("✅ Login successful!")
                return user
    return None

# Security Question ---
def security_question(user):
    print("\nSecurity Question:")
    attempts = 0
    while attempts < 3:
        answer = input("What is your code word? ").strip().lower()
        stored = (user["code_word"] or "").strip().lower()
        if answer == stored:
            print("✅ Security question passed.")
            return True
        else:
            attempts += 1
            if attempts < 3:
                print(f"Wrong code word. Attempts left: {3 - attempts}")
            else:
                print("❌ Wrong code word.")
                return False

# Main Security Interface ---
def security_interface():
    init_db()
    add_missing_columns()

    print("\n=== Secure Access Interface ===")
    try:
        while True:
            print("\n1) Register")
            print("2) Login")
            print("3) Exit")
            choice = input("Choose an option: ").strip()

            if choice == "1":
                register_user()

            elif choice == "2":
                user = login_user()
                if not user:
                    continue

                if not security_question(user):
                    print("Access Denied.")
                    continue

                print(f"\n🎉 Access Granted! Welcome {user['first_name']} {user['last_name']}")

            elif choice == "3":
                print("Goodbye!")
                break

            else:
                print("Invalid choice, try again.")
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")

# Run Program ---
if __name__ == "__main__":
    security_interface()
