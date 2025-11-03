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
            first_name TE
            last_name TEXT,
            dob TEXT,
            phone TEXT,
            code_word TEXT,
            username TEXT UNIQUE,
            password TEXT,
            passkey TEXT,
            card_sequence TEXT,
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
        required_cols = {
            "first_name": "TEXT",
            "last_name": "TEXT",
            "passkey": "TEXT",
            "card_sequence": "TEXT"
        }
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    conn.commit()
                except Exception:
                    pass

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
                print("Invalid day! Try again.")
                continue
            if not (1 <= month <= 12):
                print("Invalid month! Try again.")
                continue
            if year > current_year:
                print("Invalid year! Try again.")
                continue
            break
        except ValueError:
            print("Invalid format! Please use dd/mm/yyyy.")
            if attempts >= 3:
                print("Registration cancelled.")
                return

    # Phone number validation ---
    attempts = 0
    phone = ""
    while attempts < 3:
        phone = input("Phone Number: ").strip()
        attempts += 1
        if len(phone) == 11 and phone.startswith("01") and phone[2] in "3456789":
            break
        print("Invalid phone number. Try again.")
        if attempts >= 3:
            print("Registration cancelled.")
            return

    if not otp_verification(phone):
        print("❌ Registration cancelled due to failed OTP verification.")
        return

    code_word  = input("Code Word (for recovery): ").strip()
    username   = input("Choose a Username: ").strip()
    password   = getpass.getpass("Choose a Password: ").strip()

    if not username or not password:
        print("Username and password cannot be empty.")
        return

    # Generate unique user_id
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
    except Exception as e:
        print("Error:", e)

# Step 1: Poker Card Security System ---
def step1_poker_security(user):
    cards = ["Spade", "Heart", "Diamond", "Club", "Ace", "King", "Queen", "Jack", "Joker"]

    # check if user already has 
    if not user["passkey"]:
        print("\n--- Step 1: Poker Card Security Setup ---")
        # assign random values 0–9 to cards
        values = random.sample(range(10), 9)
        card_values = dict(zip(cards, values))

        print("\nSelect 7 cards in sequence from this 3x3 matrix:\n")
        for i in range(3):
            print(" | ".join(cards[i*3:(i+1)*3]))
        print()

        selection = []
        while len(selection) < 7:
            choice = input(f"Select card #{len(selection)+1}: ").capitalize()
            if choice in cards and choice not in selection:
                selection.append(choice)
            else:
                print("Invalid or duplicate card. Try again.")

                # compute passkey
        numbers = [card_values[c] for c in selection]
        results = []
        for x in numbers:
            val = 3 * x + 1
            # if two-digit result, take only the last digit
            if val >= 10:
                val = int(str(val)[-1])
            results.append(val)

        joined = "".join(str(r) for r in results)
        passkey = joined[:7]

        # insert a random digit (0–9) into a random position to make it 8 digits
        random_digit = str(random.randint(0, 9))
        pos = random.randint(0, len(passkey))
        passkey = passkey[:pos] + random_digit + passkey[pos:]

        # store card values in database as hidden mapping (e.g., Ace:3, King:7, etc.)
        card_value_set = ", ".join([f"{k}:{v}" for k, v in card_values.items()])

        # handle duplicate passkey
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE passkey=?", (passkey,))
            if cur.fetchone():
                passkey = str(int(passkey) + random.randint(1, 9))[:8]

        abbrev = "".join([c[0:2].lower() if c.lower().startswith('j') else c[0].lower() for c in selection])
        shown = f"{passkey}({abbrev})"
        print(f"\nYour generated passkey: {shown}")
        print("⚠️ Remember this passkey and sequence for future logins!\n")

        # save to db
        with connect_db() as conn:
            conn.execute("UPDATE users SET passkey=?, card_sequence=? WHERE username=?",
                         (passkey, f"{','.join(selection)} | {card_value_set}", user["username"]))
            conn.commit()
        return True
    
    else:
        # existing user — verification mode (fixed and compatible)
        print("\n--- Step 1: Verify Your Poker Card Sequence ---")

        # get stored sequence and passkey directly (no .get() used)
        full_data = user["card_sequence"]
        stored_passkey = user["passkey"]

        # extract stored sequence and hidden card values if exist
        if " | " in full_data:
            seq_part, value_part = full_data.split(" | ", 1)
            stored_sequence = [s.strip() for s in seq_part.split(",") if s.strip()]
            try:
                value_pairs = dict(item.split(":") for item in value_part.split(", "))
            except Exception:
                value_pairs = {}
        else:
            stored_sequence = [s.strip() for s in full_data.split(",") if s.strip()]
            value_pairs = {}

        # use only the first 7 digits (ignore extra random one)
        numeric_values = [int(d) for d in stored_passkey if d.isdigit()][:7]

        # map the numbers back to the user's cards secretly
        card_values = dict(zip(stored_sequence, numeric_values))

        # keep original sequence for checking
        original_seq = [s for s in stored_sequence]

        lock_time = 60
        fail_count = 0
        lock_cycles = 0

        while True:
            # show full 3x3 matrix of cards randomly shuffled
            shuffled_cards = cards[:]  # use all 9 cards
            random.shuffle(shuffled_cards)

            print("\nSelect your 7 cards in correct sequence (choose from the 3x3 grid):")
            for i in range(3):
                print(" | ".join(shuffled_cards[i*3:(i+1)*3]))
            print()

            # user selects 7 cards
            attempt = []
            for i in range(7):
                choice = input(f"Select card #{i+1}: ").strip().title()
                attempt.append(choice)

            pass_input = input("Enter your 8-digit passkey: ").strip()

            # normalize inputs for safe comparison
            attempt_norm = [a.strip().lower() for a in attempt]
            original_norm = [s.strip().lower() for s in original_seq]

            if attempt_norm == original_norm and pass_input == stored_passkey:
                print("\n✅ Step 1 passed successfully!")
                return True
            else:
                fail_count += 1
                print("❌ Incorrect sequence or passkey.")

                # lock after 3 failed attempts
                if fail_count % 3 == 0:
                    lock_cycles += 1
                    print(f"⏳ Locked for {lock_time} seconds.")
                    time.sleep(lock_time)
                    lock_time += 60

                # lockout after 3 lock cycles
                if lock_cycles >= 3:
                    print("\n🚫 You have reached the trying limit. Log in after 24 hours.")
        return False 
                         
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
                print(f"Invalid username or password. Attempts left: {3 - attempts}")
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
            # Step 1 Poker Security
            if not step1_poker_security(user):
                continue
            print(f"\n🎉 Access Granted! Welcome {user['first_name']} {user['last_name']}")
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")

# Run Program ---
if __name__ == "__main__":
    security_interface()