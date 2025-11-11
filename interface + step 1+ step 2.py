import sqlite3
import uuid
import getpass
import random
import time
from datetime import datetime
import string
import sys

DB = "users.db"

# Platform-specific single-character input for timing
try:
    import msvcrt
    PLATFORM = "windows"
except Exception:
    import tty
    import termios
    PLATFORM = "unix"

# Database Connection ---
def connect_db():
    conn = sqlite3.connect(DB, timeout=30)
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
            passkey TEXT,
            card_sequence TEXT,
            card_values TEXT,
            typing_wpm INTEGER,
            typing_intervals TEXT,
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
            "card_sequence": "TEXT",
            "card_values": "TEXT",
            "typing_wpm": "INTEGER",
            "typing_intervals": "TEXT"
        }
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    conn.commit()
                except Exception:
                    pass

# Helper: read a single character with timestamp, cross-platform
def _read_char_timestamp():
    if PLATFORM == "windows":
        ch = msvcrt.getwch()
        return ch, time.time()
    else:
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            return ch, time.time()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# Capture typed input per-character (shows prompt; optionally mask)
def capture_typed(prompt, mask=False):
    """
    Returns: typed_string, intervals_list_ms, total_duration_seconds
    intervals_list_ms: list of intervals between consecutive keypress timestamps in milliseconds
    """
    print(prompt, end="", flush=True)
    chars = []
    timestamps = []

    while True:
        ch, ts = _read_char_timestamp()
        # Enter/Return
        if ch in ("\r", "\n"):
            print("")  # newline after enter
            break
        # Backspace (Windows '\x08', Unix '\x7f')
        if ch in ("\x08", "\x7f"):
            if chars:
                chars.pop()
                timestamps.pop()
                # Erase character from console display
                sys.stdout.write("\b \b")
                sys.stdout.flush()
            continue
        # Ctrl-C -> raise KeyboardInterrupt
        if ord(ch) == 3:
            raise KeyboardInterrupt
        # Printable characters
        chars.append(ch)
        timestamps.append(ts)
        if mask:
            sys.stdout.write("*")
        else:
            sys.stdout.write(ch)
        sys.stdout.flush()

    # compute intervals between consecutive keystrokes in milliseconds
    intervals_ms = []
    for i in range(1, len(timestamps)):
        intervals_ms.append(int((timestamps[i] - timestamps[i - 1]) * 1000))
    total_duration = (timestamps[-1] - timestamps[0]) if len(timestamps) >= 2 else 0.0
    typed = "".join(chars)
    return typed, intervals_ms, total_duration

# Compute WPM from character count and duration_seconds
def compute_wpm(total_chars, duration_seconds):
    if duration_seconds <= 0:
        return 0
    words = total_chars / 5.0
    minutes = duration_seconds / 60.0
    wpm = words / minutes
    return int(round(wpm))

# OTP Verification ---
def otp_verification(phone=None):
    otp = random.randint(1000, 9999)
    if phone:
        print(f"\n Sending OTP to {phone}...")
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

    # Date of Birth validation (dd/mm/yyyy)
    attempts = 0
    dob = ""
    current_year = 2025
    while attempts < 3:
        dob = input("Date of Birth (dd/mm/yyyy): ").strip()
        attempts += 1
        try:
            parsed_date = datetime.strptime(dob, "%d/%m/%Y")
            day, month, year = parsed_date.day, parsed_date.month, parsed_date.year
            if not (1 <= day <= 31) or not (1 <= month <= 12) or year > current_year:
                print("Invalid date. Try again.")
                continue
            break
        except ValueError:
            print("Invalid format! Please use dd/mm/yyyy.")
            if attempts >= 3:
                print("Registration cancelled.")
                return

    # Phone validation
    attempts = 0
    phone = ""
    while attempts < 3:
        phone = input("Phone Number: ").strip()
        attempts += 1
        if len(phone) == 11 and phone.startswith("01") and phone[2] in "3456789" and phone.isdigit():
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
    # For registration password we use standard getpass (not timing)
    password   = getpass.getpass("Choose a Password: ").strip()

    if not username or not password:
        print("Username and password cannot be empty.")
        return

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

# ---- Poker Card Security System ----
def step1_poker_security(user):
    cards = ["Spade", "Heart", "Diamond", "Club", "Ace", "King", "Queen", "Jack", "Joker"]

    # --- New User Setup ---
    if not user["passkey"]:
        print("\n--- Poker Card Security Setup ---")
        values = random.sample(range(10), 9)
        card_values = dict(zip(cards, values))

        print("\nSelect 7 cards in sequence:\n")
        for i in range(3):
            print(" | ".join(cards[i*3:(i+1)*3]))
        print()

        selection = []
        while len(selection) < 7:
            choice = input(f"Select card #{len(selection)+1}: ").strip().title()
            if choice in cards and choice not in selection:
                selection.append(choice)
            else:
                print("Invalid or duplicate card. Try again.")

        numbers = [card_values[c] for c in selection]
        results = []
        for x in numbers:
            val = 3 * x + 1
            # If result is >=10, take last digit (as requested)
            if val >= 10:
                val = int(str(val)[-1])
            results.append(val)

        joined = "".join(str(r) for r in results)
        passkey = joined[:7]

        # insert a random digit (0–9) into a random position to make it 8 digits
        random_digit = str(random.randint(0, 9))
        pos = random.randint(0, len(passkey))
        passkey = passkey[:pos] + random_digit + passkey[pos:]

        card_value_set = ", ".join([f"{k}:{v}" for k, v in card_values.items()])

        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE passkey=?", (passkey,))
            if cur.fetchone():
                # ensure still 8 characters: replace inserted random digit with a different digit
                new_digit = str((int(random_digit) + 1) % 10)
                passkey = passkey[:pos] + new_digit + passkey[pos:]

        abbrev = "".join([c[0:2].lower() if c.lower().startswith('j') else c[0].lower() for c in selection])
        shown = f"{passkey}({abbrev})"

        print(f"\nYour generated passkey: {shown}")
        print("⚠️ Remember this passkey and sequence for future logins!\n")

        with connect_db() as conn:
            conn.execute("UPDATE users SET passkey=?, card_sequence=? WHERE username=?",
                         (passkey, f"{','.join(selection)} | {card_value_set}", user["username"]))
            conn.commit()
        return True

    # --- Existing User Verification ---
    else:
        print("\n ---- Verify Your Poker Card Sequence ----")

        full_sequence_field = user["card_sequence"] or ""
        stored_passkey = user["passkey"] or ""

        # Split the card_sequence field cleanly — only take the part before '|'
        if " | " in full_sequence_field:
            sequence_part, _ = full_sequence_field.split(" | ", 1)
        else:
            sequence_part = full_sequence_field

        stored_sequence = [s.strip() for s in sequence_part.split(",") if s.strip()]
        numeric_values = [int(d) for d in stored_passkey if d.isdigit()][:7]
        mapped_cards = stored_sequence[:7]
        card_values_by_passkey = dict(zip(mapped_cards, numeric_values))

        # Format properly for DB
        updated_value_text = ", ".join([f"{k}:{v}" for k, v in card_values_by_passkey.items()])

        # Save updated card values in dedicated column so it's clean
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET card_values=? WHERE username=?", (updated_value_text, user["username"]))
            conn.commit()

        original_seq = [s for s in stored_sequence]
        lock_time = 60
        fail_count = 0
        lock_cycles = 0

        while True:
            shuffled_cards = cards[:]
            random.shuffle(shuffled_cards)
            print("\nSelect your 7 cards in correct sequence:")
            for i in range(3):
                print(" | ".join(shuffled_cards[i*3:(i+1)*3]))
            print()

            attempt = []
            for i in range(7):
                choice = input(f"Select card #{i+1}: ").strip().title()
                attempt.append(choice)

            pass_input = input("Enter your 8-digit passkey: ").strip()

            if [a.lower() for a in attempt] == [s.lower() for s in original_seq] and pass_input == stored_passkey:
                print("\n✅ Step 1 passed successfully!")
                return True
            else:
                fail_count += 1
                print("❌ Incorrect sequence or passkey.")
                if fail_count % 3 == 0:
                    lock_cycles += 1
                    print(f"⏳ Locked for {lock_time} seconds.")
                    time.sleep(lock_time)
                    lock_time += 60
                if lock_cycles >= 3:
                    print("\n🚫 You have reached the trying limit. Log in after 24 hours.")
                    return False
        return False

# NEW: capture typing during login, save first-time profile, detect bots and compare WPM
def login_user():
    print("\n--- Login (typing profiling enabled) ---")
    # Capture username with timing (per-character)
    try:
        typed_username, u_intervals, u_duration = capture_typed("Username: ", mask=False)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return None

    # Capture password with timing (mask)
    print("Password: ", end="", flush=True)
    try:
        typed_password, p_intervals, p_duration = capture_typed("", mask=True)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return None

    # Combine metrics
    total_chars = len(typed_username) + len(typed_password)
    # total duration: if both have durations use sum, else recompute from intervals if needed
    total_duration = (u_duration or 0.0) + (p_duration or 0.0)
    # Combined intervals: use username intervals then password intervals (phone-like)
    combined_intervals = u_intervals + p_intervals

    # Compute WPM
    wpm = compute_wpm(total_chars, total_duration)

    # Lookup credentials (use typed_username & typed_password)
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (typed_username, typed_password))
        user = cur.fetchone()

    if not user:
        print("❌ Invalid username or password.")
        return None

    # Check if this is first successful login regarding typing profile
    stored_wpm = user["typing_wpm"]
    stored_intervals_field = user["typing_intervals"]
    if not stored_wpm:
        # first-time: store wpm and intervals string
        intervals_str = ",".join(str(i) for i in combined_intervals)
        with connect_db() as conn:
            conn.execute("UPDATE users SET typing_wpm=?, typing_intervals=? WHERE username=?",
                         (wpm, intervals_str, typed_username))
            conn.commit()
        print(f"✅ Login successful! (Typing profile recorded: {wpm} wpm)")
        return user
    else:
        # Subsequent login: compare WPM within tolerance and detect bots by interval variance
        try:
            stored_wpm_val = int(stored_wpm)
        except Exception:
            stored_wpm_val = stored_wpm or 0

        # choose tolerance; user wanted +- flexibility — use +-25 wpm (reasonable)
        tol = 25
        if not (stored_wpm_val - tol <= wpm <= stored_wpm_val + tol):
            print(f"❌ Typing speed mismatch. Recorded: {stored_wpm_val} wpm, Now: {wpm} wpm. Access denied.")
            return None

        # bot detection: check if combined_intervals are too uniform (low stddev)
        import statistics
        if len(combined_intervals) >= 3:
            try:
                stddev = statistics.pstdev(combined_intervals)
            except Exception:
                stddev = None
        else:
            stddev = None

        # If stddev is extremely low (e.g., < 8 ms), suspect bot
        if stddev is not None and stddev < 8:
            print("❌ Keystroke timing looks artificial (bot-like). Access denied.")
            return None

        # otherwise accept; do not overwrite stored profile
        print("✅ Login successful! Typing profile matched.")
        return user

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
            if not step1_poker_security(user):
                continue
            print(f"\n Access Granted! Welcome {user['first_name']} {user['last_name']}")
        elif choice == "3":
            print("Goodbye!")
            break
        else:
            print("Invalid choice, try again.")

# Run Program ---
if __name__ == "__main__":
    security_interface()
