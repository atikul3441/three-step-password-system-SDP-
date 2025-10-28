# secure_access_fixed_plain.py
import sqlite3
import uuid
import getpass
import random
import time

DB = "users.db"

# -------------------- Database Connection --------------------
def connect_db():
    conn = sqlite3.connect(DB, timeout=30)  # Wait up to 10 seconds if locked
    conn.row_factory = sqlite3.Row
    return conn

# -------------------- Initialize Database --------------------
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

# -------------------- Add Missing Columns --------------------
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

# -------------------- Register New User --------------------
def register_user():
    print("\n--- User Registration ---")
    first_name = input("First Name: ").strip()
    last_name  = input("Last Name: ").strip()
    dob        = input("Date of Birth (YYYY-MM-DD): ").strip()
    phone      = input("Phone Number: ").strip()
    code_word  = input("Code Word (for recovery): ").strip()
    username   = input("Choose a Username: ").strip()
    password   = getpass.getpass("Choose a Password: ").strip()

    if not username or not password:
        print("Username and password cannot be empty.")
        return

    user_id = str(uuid.uuid4())

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

# -------------------- User Login --------------------
def login_user():
    print("\n--- Login ---")
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ").strip()

    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cur.fetchone()

        if not user:
            print("❌ Incorrect username or password.")
            return None
        else:
            print("✅ Login successful!")
            return user

# -------------------- Security Question --------------------
def security_question(user):
    print("\nSecurity Question:")
    answer = input("What is your code word? ").strip().lower()
    stored = (user["code_word"] or "").strip().lower()
    if answer == stored:
        print("✅ Security question passed.")
        return True
    else:
        print("❌ Wrong code word.")
        return False

# -------------------- OTP Verification --------------------
def otp_verification():
    otp = random.randint(1000, 9999)
    print(f"Your OTP is: {otp}")  # For demo only
    entered = input("Enter OTP: ").strip()
    if entered == str(otp):
        print("✅ OTP verified.")
        return True
    else:
        print("❌ Incorrect OTP.")
        return False

# -------------------- Main Security Interface --------------------
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

                if not otp_verification():
                    print("Access Denied.")
                    continue

                print(f"\n🎉 Access Granted! Welcome {user['first_name']} {user['last_name']} (User ID: {user['id']})")

            elif choice == "3":
                print("Goodbye!")
                break

            else:
                print("Invalid choice, try again.")
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting...")

# -------------------- Run Program --------------------
if __name__ == "__main__":
    security_interface()

