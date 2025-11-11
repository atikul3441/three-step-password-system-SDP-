# Full GUI-wrapped version of your program using CustomTkinter + tkcalendar.
# All backend logic (DB functions, passkey generation, typing profiling, step1 logic)
# are preserved and used by the GUI. Only UI wrappers and bindings are added.

import sqlite3
import uuid
import getpass
import random
import time
from datetime import datetime
import string
import sys
import math

# GUI imports
import customtkinter as ctk
from tkcalendar import Calendar
from tkinter import messagebox, simpledialog

DB = "users.db"

# ----------------------
# Backend DB & Helpers
# ----------------------
def connect_db():
    conn = sqlite3.connect(DB, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

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

def compute_wpm(total_chars, duration_seconds):
    if duration_seconds <= 0 or total_chars == 0:
        return 0
    words = total_chars / 5.0
    minutes = duration_seconds / 60.0
    wpm = words / minutes
    return int(round(wpm))

# ----------------------
# Core logic functions (kept as original as possible)
# ----------------------
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

def otp_simulate_and_verify(phone, parent):
    otp = random.randint(1000, 9999)
    # show popup with OTP for demo
    messagebox.showinfo("OTP Sent", f"📱 Sending OTP to {phone}...\n\n(For demo) OTP: {otp}", parent=parent)
    attempts = 0
    while attempts < 3:
        entered = simpledialog.askstring("Enter OTP", f"Enter OTP sent to {phone} (attempt {attempts+1}/3):", parent=parent)
        if entered is None:
            return False
        if entered.strip() == str(otp):
            messagebox.showinfo("OTP", "✅ OTP verified.", parent=parent)
            return True
        attempts += 1
        if attempts < 3:
            messagebox.showwarning("OTP", f"Incorrect OTP. Attempts left: {3 - attempts}", parent=parent)
        else:
            messagebox.showerror("OTP", "Incorrect OTP. Maximum attempts reached.", parent=parent)
            return False
    return False

def register_user_console_flow(first_name, last_name, dob, phone, code_word, username, password):
    # This keeps original DB insertion behavior but is called by GUI with validated fields.
    if not username or not password:
        return False, "Username and password cannot be empty."

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
                return False, "Username already exists."
            cur.execute("""
                INSERT INTO users (
                    id, first_name, last_name, dob, phone, code_word, username, password, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, first_name, last_name, dob, phone, code_word, username, password, int(time.time())))
            conn.commit()
            return True, f"Registration successful! Your User ID: {user_id}"
    except Exception as e:
        return False, f"Error: {e}"

# Step1 helper: generate passkey from card selection
def generate_passkey_from_selection(selection, card_values):
    # selection: list of 7 card names in order
    # card_values: dict mapping 9 cards to digits 0-9
    numbers = [card_values[c] for c in selection]
    results = []
    for x in numbers:
        val = 3 * x + 1
        # if two-digit result, take last digit
        if val >= 10:
            val = int(str(val)[-1])
        results.append(val)
    joined = "".join(str(r) for r in results)
    passkey7 = joined[:7]
    # insert random digit anywhere to make 8 digits
    random_digit = str(random.randint(0, 9))
    pos = random.randint(0, len(passkey7))
    passkey8 = passkey7[:pos] + random_digit + passkey7[pos:]
    # ensure uniqueness in DB (simple tweak)
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE passkey=?", (passkey8,))
        if cur.fetchone():
            # replace the inserted digit with (digit+1)%10
            new_digit = str((int(random_digit) + 1) % 10)
            passkey8 = passkey7[:pos] + new_digit + passkey7[pos:]
    return passkey8

# Step1 verification helper: parse stored card_sequence and card_values, return cleaned sequence
def parse_card_sequence_field(field_text):
    """
    field_text expected as: "CardA,CardB,CardC,... | CardX:val, CardY:val, ..."
    Return (sequence_list, card_value_pairs_dict_or_empty)
    """
    if not field_text:
        return [], {}
    if " | " in field_text:
        seq_part, value_part = field_text.split(" | ", 1)
        seq_list = [s.strip() for s in seq_part.split(",") if s.strip()]
        value_pairs = {}
        try:
            for item in value_part.split(","):
                item = item.strip()
                if not item:
                    continue
                if ":" in item:
                    k, v = item.split(":", 1)
                    value_pairs[k.strip()] = int(v.strip())
        except Exception:
            value_pairs = {}
        return seq_list, value_pairs
    else:
        seq_list = [s.strip() for s in field_text.split(",") if s.strip()]
        return seq_list, {}

# ----------------------
# GUI: CustomTkinter wrappers
# ----------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class TriSecureApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TriSecure")
        # start full-screen-ish: user requested full-window screen layout
        self.state("zoomed") if sys.platform.startswith("win") else self.attributes("-zoomed", True)
        # container frame to swap pages
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)
        self.frames = {}
        for F in (HomePage, RegisterPage, LoginPage, Step1Page, WelcomePage):
            page = F(parent=self.container, controller=self)
            self.frames[F.__name__] = page
            page.grid(row=0, column=0, sticky="nsew")
        self.show_frame("HomePage")

    def show_frame(self, name, **kwargs):
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.tkraise()

# ---------- Home ----------
class HomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ctk.CTkLabel(self, text="TriSecure Access Interface", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=40)
        ctk.CTkButton(self, text="Register", width=200, command=lambda: controller.show_frame("RegisterPage")).pack(pady=10)
        ctk.CTkButton(self, text="Login", width=200, command=lambda: controller.show_frame("LoginPage")).pack(pady=10)
        ctk.CTkButton(self, text="Exit", width=200, fg_color="red", command=self.quit_app).pack(pady=10)

    def quit_app(self):
        self.controller.destroy()

# ---------- Register ----------
class RegisterPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        header = ctk.CTkLabel(self, text="Register New User", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=18)

        form = ctk.CTkFrame(self)
        form.pack(pady=10, padx=20, fill="x")

        # entries
        self.first_name = ctk.CTkEntry(form, placeholder_text="First Name")
        self.last_name = ctk.CTkEntry(form, placeholder_text="Last Name")
        self.dob_entry = ctk.CTkEntry(form, placeholder_text="Date of Birth (click to pick)")
        self.dob_entry.bind("<1>", self.open_calendar)  # open calendar on click
        self.phone = ctk.CTkEntry(form, placeholder_text="Phone Number")
        self.code_word = ctk.CTkEntry(form, placeholder_text="Code Word (for recovery)")
        self.username = ctk.CTkEntry(form, placeholder_text="Choose a Username")
        self.password = ctk.CTkEntry(form, placeholder_text="Choose a Password", show="*")

        self.first_name.grid(row=0, column=0, padx=10, pady=8)
        self.last_name.grid(row=0, column=1, padx=10, pady=8)
        self.dob_entry.grid(row=1, column=0, padx=10, pady=8)
        self.phone.grid(row=1, column=1, padx=10, pady=8)
        self.code_word.grid(row=2, column=0, padx=10, pady=8)
        self.username.grid(row=2, column=1, padx=10, pady=8)
        self.password.grid(row=3, column=0, columnspan=2, padx=10, pady=8, sticky="ew")

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Submit Registration", command=self.submit).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn_frame, text="Back", command=lambda: controller.show_frame("HomePage")).grid(row=0, column=1, padx=8)

    def open_calendar(self, event=None):
        # small toplevel window for calendar
        top = ctk.CTkToplevel(self)
        top.title("Select Date of Birth")
        top.geometry("350x320")
        # Use tkcalendar.Calendar widget
        cal = Calendar(top, selectmode="day", date_pattern="dd/mm/yyyy")
        cal.pack(padx=10, pady=10, expand=True, fill="both")
        def pick():
            val = cal.get_date()
            self.dob_entry.delete(0, "end")
            self.dob_entry.insert(0, val)
            top.destroy()
        ctk.CTkButton(top, text="Select", command=pick).pack(pady=8)

    def submit(self):
        fn = self.first_name.get().strip()
        ln = self.last_name.get().strip()
        dob = self.dob_entry.get().strip()
        phone = self.phone.get().strip()
        code_word = self.code_word.get().strip()
        username = self.username.get().strip()
        password = self.password.get().strip()

        # validations (reuse same rules)
        if not fn or not ln:
            messagebox.showwarning("Validation", "First and last name are required.")
            return
        # DOB format check
        try:
            parsed = datetime.strptime(dob, "%d/%m/%Y")
            if parsed.year > 2025:
                messagebox.showerror("DOB Error", "Year cannot be greater than 2025")
                return
        except Exception:
            messagebox.showerror("DOB Error", "Invalid date. Use the date picker.")
            return
        # phone check
        if not (phone.isdigit() and len(phone) == 11 and phone.startswith("01") and phone[2] in "3456789"):
            messagebox.showerror("Phone Error", "Invalid phone number.")
            return
        ok = otp_simulate_and_verify(phone, self)
        if not ok:
            messagebox.showerror("OTP", "Registration cancelled due to failed OTP.", parent=self)
            return
        
        #messagebox.showinfo("OTP", "An OTP will be shown in console for demo. Please follow console prompts.")
        #if not otp_verification(phone):
            messagebox.showerror("OTP", "Registration cancelled due to failed OTP verification.")
            return

        ok, msg = register_user_console_flow(fn, ln, dob, phone, code_word, username, password)
        if not ok:
            messagebox.showerror("Registration Error", msg)
            return
        messagebox.showinfo("Registered", msg)
        # clear
        self.first_name.delete(0, "end")
        self.last_name.delete(0, "end")
        self.dob_entry.delete(0, "end")
        self.phone.delete(0, "end")
        self.code_word.delete(0, "end")
        self.username.delete(0, "end")
        self.password.delete(0, "end")
        self.controller.show_frame("HomePage")

# ---------- Login Page (captures typing profile) ----------
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        header = ctk.CTkLabel(self, text="Login", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=18)

        form = ctk.CTkFrame(self)
        form.pack(padx=20, pady=10, fill="x")

        ctk.CTkLabel(form, text="(Input Your Usrnamr and Password)").grid(row=0, column=0, columnspan=2, pady=6)

        ctk.CTkLabel(form, text="Username").grid(row=1, column=0, sticky="w", padx=8)
        ctk.CTkLabel(form, text="Password").grid(row=2, column=0, sticky="w", padx=8)
        self.username_entry = ctk.CTkEntry(form)
        self.password_entry = ctk.CTkEntry(form, show="*")
        self.username_entry.grid(row=1, column=1, padx=8, pady=8, sticky="ew")
        self.password_entry.grid(row=2, column=1, padx=8, pady=8, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        # storage for key timestamps
        self.u_timestamps = []
        self.p_timestamps = []

        # bind key events to capture per-key timestamps
        self.username_entry.bind("<KeyPress>", self._on_username_key)
        self.password_entry.bind("<KeyPress>", self._on_password_key)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Login", command=self.attempt_login).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn_frame, text="Back", command=lambda: controller.show_frame("HomePage")).grid(row=0, column=1, padx=8)

    def on_show(self, **kwargs):
        # reset timestamps and fields each time shown
        self.u_timestamps = []
        self.p_timestamps = []
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")

    def _now_ms(self):
        return int(time.time() * 1000)

    def _on_username_key(self, event):
        # record timestamp in ms for each key press (excluding modifier-only keys)
        if len(event.keysym) == 1 or event.keysym in ("BackSpace", "Return"):
            self.u_timestamps.append(time.time())

    def _on_password_key(self, event):
        if len(event.keysym) == 1 or event.keysym in ("BackSpace", "Return"):
            self.p_timestamps.append(time.time())

    def attempt_login(self):
        typed_username = self.username_entry.get().strip()
        typed_password = self.password_entry.get().strip()

        # compute intervals lists and durations from timestamps
        def compute_intervals_and_duration(ts_list):
            if len(ts_list) < 2:
                return [], 0.0
            intervals = []
            for i in range(1, len(ts_list)):
                intervals.append(int((ts_list[i] - ts_list[i-1]) * 1000))  # ms
            total_dur = ts_list[-1] - ts_list[0]
            return intervals, total_dur

        u_intervals, u_duration = compute_intervals_and_duration(self.u_timestamps)
        p_intervals, p_duration = compute_intervals_and_duration(self.p_timestamps)

        total_chars = len(typed_username) + len(typed_password)
        total_duration = (u_duration or 0.0) + (p_duration or 0.0)
        if total_duration <= 0:
            # fallback: small epsilon to avoid division by zero
            total_duration = 0.001

        combined_intervals = u_intervals + p_intervals
        wpm = compute_wpm(total_chars, total_duration)

        # Query DB for credentials
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (typed_username, typed_password))
            user = cur.fetchone()

        if not user:
            messagebox.showerror("Login Failed", "Invalid username or password.")
            return

        # If first-time typing profile not set, save it
        stored_wpm = user["typing_wpm"]
        stored_intervals_field = user["typing_intervals"]
        if not stored_wpm:
            intervals_str = ",".join(str(i) for i in combined_intervals)
            with connect_db() as conn:
                conn.execute("UPDATE users SET typing_wpm=?, typing_intervals=? WHERE username=?",
                             (wpm, intervals_str, typed_username))
                conn.commit()
            messagebox.showinfo("Login Successful", f"Login successful. Typing profile recorded ({wpm} wpm).")
            # forward to security step1
            self.controller.show_frame("Step1Page", user_row=user)
            return

        # Else compare wpm tolerance and check keystroke uniformity
        try:
            stored_wpm_val = int(stored_wpm)
        except Exception:
            stored_wpm_val = int(stored_wpm) if stored_wpm else 0
        tol = 10  # chosen tolerance (+-10 wpm)
        if not (stored_wpm_val - tol <= wpm <= stored_wpm_val + tol):
            messagebox.showerror("Access Denied", f"Typing speed mismatch. Recorded: {stored_wpm_val} wpm, Now: {wpm} wpm.")
            return

        # bot detection via stddev of intervals (human intervals vary)
        import statistics
        stddev = None
        if len(combined_intervals) >= 3:
            try:
                stddev = statistics.pstdev(combined_intervals)
            except Exception:
                stddev = None
        if stddev is not None and stddev < 8:
            messagebox.showerror("Access Denied", "looks artificial (bot-like).")
            return

        messagebox.showinfo("Login Successful", "Welcome user.")
        # show Step1
        self.controller.show_frame("Step1Page", user_row=user)

# ---------- Step1 Page (Poker card) ----------
class Step1Page(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.user_row = None

        header = ctk.CTkLabel(self, text="--- Poker Card Security ---", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=12)

        info = ctk.CTkLabel(self, text="Select your 7 cards in sequence")
        info.pack(pady=8)

        # container for 3x3 grid
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(pady=10)

        # dynamic area for passkey display (only in setup)
        self.passkey_label = ctk.CTkLabel(self, text="")
        self.passkey_label.pack(pady=6)

        # action buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)
        self.submit_btn = ctk.CTkButton(btn_frame, text="Submit Selection", command=self.submit_selection)
        self.reset_btn =  ctk.CTkButton(btn_frame, text="Reset Selection",  command=lambda: self.on_show(self.user_row))
        self.back_btn = ctk.CTkButton(btn_frame, text="Back to Home", command=lambda: controller.show_frame("HomePage"))
        self.submit_btn.grid(row=0, column=0, padx=10)
        self.reset_btn.grid(row=0, column=1, padx=10)
        self.back_btn.grid(row=0, column=2, padx=10)

        # variables
        self.cards = ["Spade", "Heart", "Diamond", "Club", "Ace", "King", "Queen", "Jack", "Joker"]
        self.card_buttons = []
        self.current_selection = []
        self.card_values_map = {}
        self.is_setup_mode = False

    def on_show(self, user_row=None):
        # reset
        self.user_row = user_row
        self.current_selection = []
        self.card_values_map = {}
        self.passkey_label.configure(text="")
        for w in self.grid_frame.winfo_children():
            w.destroy()
        # Decide mode based on whether user has a passkey
        if not user_row:
            messagebox.showerror("Error", "No user context provided.")
            self.controller.show_frame("HomePage")
            return
        self.user_row = dict(user_row)
        self.is_setup_mode = not bool(self.user_row.get("passkey"))
        # Setup card values for first-time or verification
        if self.is_setup_mode:
            # first-time assign random values 0-9 mapped to 9 cards
            values = random.sample(range(10), 9)
            self.card_values_map = dict(zip(self.cards, values))
            self._render_grid(show_values=False)  # show only names
        else:
            # verification: show full 9 cards in shuffled grid
            # stored sequence parse to get saved selection (but not reveal values)
            full_seq_field = self.user_row.get("card_sequence") or ""
            seq_list, hidden_map = parse_card_sequence_field(full_seq_field)
            # For verification we should not show values. Use default cards ordering shuffled.
            self.card_values_map = {}  # will be derived from passkey later (secret)
            # Render grid shuffled
            self._render_grid(show_values=False)

    def _render_grid(self, show_values=False):
        # create 3x3 buttons
        shuffled = self.cards[:]
        random.shuffle(shuffled)
        self.card_buttons = []
        for r in range(3):
            for c in range(3):
                idx = r * 3 + c
                name = shuffled[idx]
                text = name if not show_values else f"{name}\n({self.card_values_map.get(name,'?')})"
                b = ctk.CTkButton(self.grid_frame, text=text, width=160, height=80,
                                  command=lambda n=name: self._on_card_click(n))
                b.grid(row=r, column=c, padx=8, pady=8)
                self.card_buttons.append(b)

    def _on_card_click(self, name):
        # toggle selection (disallow duplicates)
        if name in self.current_selection:
            messagebox.showwarning("Selection", "Card already selected. Pick another.")
            return
        if len(self.current_selection) >= 7:
            messagebox.showwarning("Selection", "You already selected 7 cards.")
            return
        self.current_selection.append(name)
        # update label
        self.passkey_label.configure(text=f"Selected ({len(self.current_selection)}/7): " + ", ".join(self.current_selection))

    def submit_selection(self):
        if len(self.current_selection) != 7:
            messagebox.showwarning("Selection", "Please select exactly 7 distinct cards in sequence.")
            return
        # Setup mode: generate passkey, save mapping & sequence
        if self.is_setup_mode:
            # ensure card_values_map exists (it was created in on_show)
            if not self.card_values_map:
                values = random.sample(range(10), 9)
                self.card_values_map = dict(zip(self.cards, values))
            passkey = generate_passkey_from_selection(self.current_selection, self.card_values_map)
            # create card_value_set (hidden mapping of original random assignment)
            card_value_set = ", ".join([f"{k}:{v}" for k, v in self.card_values_map.items()])
            shown_abbrev = "".join([c[0:2].lower() if c.lower().startswith('j') else c[0].lower() for c in self.current_selection])
            shown = f"{passkey}({shown_abbrev})"
            # save passkey and card_sequence in DB (card_values stored in separate column later)
            with connect_db() as conn:
                conn.execute("UPDATE users SET passkey=?, card_sequence=? WHERE username=?",
                             (passkey, f"{','.join(self.current_selection)} | {card_value_set}", self.user_row["username"]))
                conn.commit()
            messagebox.showinfo("Passkey Created", f"Your generated passkey: {shown}\n(Please memorize it now)")
            # after setup, mark user_row updated and continue to welcome
            # fetch updated user row and proceed
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username=?", (self.user_row["username"],))
                new_user = cur.fetchone()
            self.controller.show_frame("WelcomePage", user_row=new_user)
            return

        # Verification mode:
        # Fetch stored sequence (original) and stored passkey
        full_seq_field = self.user_row.get("card_sequence") or ""
        stored_passkey = (self.user_row.get("passkey") or "")
        seq_list, hidden_map = parse_card_sequence_field(full_seq_field)
        # Recompute mapping of first 7 digits of passkey to the seq_list
        digits_from_passkey = [int(d) for d in stored_passkey if d.isdigit()][:7]
        mapping_by_passkey = dict(zip(seq_list[:7], digits_from_passkey))
        # Save mapping into DB column card_values (clean format)
        if mapping_by_passkey:
            updated_value_text = ", ".join([f"{k}:{v}" for k, v in mapping_by_passkey.items()])
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET card_values=? WHERE username=?", (updated_value_text, self.user_row["username"]))
                conn.commit()

        # Now verify the user's selection equals stored sequence (order) and passkey entered matches
        # Ask user for passkey via a small prompt
        entered_passkey = ctk.CTkInputDialog(text="Enter your 8-digit passkey", title="Passkey").get_input()
        if entered_passkey is None:
            messagebox.showinfo("Cancelled", "Passkey entry cancelled.")
            return

        # Compare normalized sequences
        attempt_norm = [s.strip().lower() for s in self.current_selection]
        original_norm = [s.strip().lower() for s in seq_list[:7]]
        if attempt_norm == original_norm and entered_passkey == stored_passkey:
            messagebox.showinfo("Success","user confirmed!")
            # fetch updated user row and proceed
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username=?", (self.user_row["username"],))
                new_user = cur.fetchone()
            self.controller.show_frame("WelcomePage", user_row=new_user)
            return
        else:
            # handle fail & lock logic (simple counting as per your original design)
            # We'll implement local counters stored on this page object
            if not hasattr(self, "_fail_count"):
                self._fail_count = 0
                self._lock_cycles = 0
                self._lock_time = 60
            self._fail_count += 1
            messagebox.showerror("Failed", "Incorrect sequence or passkey.")
            if self._fail_count % 3 == 0:
                self._lock_cycles += 1
                messagebox.showwarning("Locked", f"Locked for {self._lock_time} seconds.")
                time.sleep(self._lock_time)
                self._lock_time += 60
            if self._lock_cycles >= 3:
                messagebox.showerror("Kicked", "You have reached the trying limit. Log in after 24 hours.")
                self.controller.show_frame("HomePage")
                return
            # reset selection for next try
            self.current_selection = []
            self.passkey_label.configure(text="")

# ---------- Welcome Page ----------
class WelcomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=24, weight="bold"))
        self.label.pack(pady=30)
        ctk.CTkButton(self, text="Log out", command=self.logout).pack(pady=10)

    def on_show(self, user_row=None):
        if user_row is None:
            self.controller.show_frame("HomePage")
            return
        self.user_row = user_row
        fname = user_row["first_name"]
        lname = user_row["last_name"]
        self.label.configure(text=f"🎉 Access Granted!\nWelcome {fname} {lname}")

    def logout(self):
        self.controller.show_frame("HomePage")

# ----------------------
# App start (backend init + GUI run)
# ----------------------
if __name__ == "__main__":
    init_db()
    add_missing_columns()
    app = TriSecureApp()
    app.mainloop()
