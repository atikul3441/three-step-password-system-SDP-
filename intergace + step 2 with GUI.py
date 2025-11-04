# fixed_secure_gui.py
import sqlite3
import uuid
import getpass
import random
import time
from datetime import datetime
import string
import customtkinter as ctk
from tkinter import messagebox, simpledialog

DB = "users.db"


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
            "card_values": "TEXT"
        }
        for col, col_type in required_cols.items():
            if col not in existing_cols:
                try:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    conn.commit()
                except Exception:
                    pass

# OTP helper (UI popup simulation)
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

# ---------------------------
# Small validation utilities re-used by GUI handlers
# ---------------------------
def validate_dob_str(dob_str):
    try:
        parsed = datetime.strptime(dob_str, "%d/%m/%Y")
    except Exception:
        return False, "Invalid format — use dd/mm/yyyy"
    day, month, year = parsed.day, parsed.month, parsed.year
    if not (1 <= day <= 31):
        return False, "Day must be between 1 and 31"
    if not (1 <= month <= 12):
        return False, "Month must be between 1 and 12"
    if year > 2025:
        return False, "Year cannot be greater than 2025"
    return True, ""

def validate_phone_str(phone):
    if not phone:
        return False, "Phone number required"
    if not phone.isdigit():
        return False, "Phone must contain digits only"
    if len(phone) != 11:
        return False, "Phone must be exactly 11 digits"
    if not phone.startswith("01"):
        return False, "Phone must start with '01'"
    if phone[2] not in "3456789":
        return False, "3rd digit must be between 3 and 9"
    return True, ""

def generate_unique_user_id():
    with connect_db() as conn:
        cur = conn.cursor()
        while True:
            user_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
            if not cur.fetchone():
                return user_id

# ---------------------------
# GUI App (CustomTkinter)
# ---------------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class SecureApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TriSecure Access")
        
        try:
            self.state("zoomed")
        except Exception:
            
            self.geometry("1200x800")

        # init DB
        init_db()
        add_missing_columns()

        # pages container
        self.container = ctk.CTkFrame(self)
        self.container.pack(fill="both", expand=True)

        # frames dict
        self.frames = {}
        for F in (HomePage, RegisterPage, LoginPage, PokerStepPage, WelcomePage):
            page = F(parent=self.container, controller=self)
            self.frames[F.__name__] = page
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame("HomePage")

    def show_frame(self, name, **kwargs):
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.lift()

# --- Home Page ---
class HomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ctk.CTkLabel(self, text="TriSecure Access Interface", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=30)
        ctk.CTkLabel(self, text="Choose an option below:", font=ctk.CTkFont(size=14)).pack(pady=(0,20))
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="Register", width=200, command=lambda: controller.show_frame("RegisterPage")).grid(row=0, column=0, padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="Login", width=200, command=lambda: controller.show_frame("LoginPage")).grid(row=0, column=1, padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="Exit", width=200, fg_color="red", command=self.quit_app).grid(row=0, column=2, padx=10, pady=10)

    def quit_app(self):
        self.controller.destroy()

# --- Registration Page ---
class RegisterPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="Register New User", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=12)
        form = ctk.CTkFrame(self)
        form.pack(pady=8)

        # first + last
        self.first_entry = ctk.CTkEntry(form, placeholder_text="First Name")
        self.last_entry = ctk.CTkEntry(form, placeholder_text="Last Name")
        self.first_entry.grid(row=0, column=0, padx=8, pady=8)
        self.last_entry.grid(row=0, column=1, padx=8, pady=8)

        # dob and phone
        self.dob_entry = ctk.CTkEntry(form, placeholder_text="Date of Birth (dd/mm/yyyy)")
        self.phone_entry = ctk.CTkEntry(form, placeholder_text="Phone Number")
        self.dob_entry.grid(row=1, column=0, padx=8, pady=8)
        self.phone_entry.grid(row=1, column=1, padx=8, pady=8)

        # code, username, password
        self.code_entry = ctk.CTkEntry(form, placeholder_text="Code Word (Recovery)")
        self.user_entry = ctk.CTkEntry(form, placeholder_text="Username")
        self.pass_entry = ctk.CTkEntry(form, placeholder_text="Password", show="*")
        self.code_entry.grid(row=2, column=0, padx=8, pady=8)
        self.user_entry.grid(row=2, column=1, padx=8, pady=8)
        self.pass_entry.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="ew")

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        ctk.CTkButton(btn_frame, text="Submit Registration", command=self.submit).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn_frame, text="Back", command=lambda: controller.show_frame("HomePage")).grid(row=0, column=1, padx=8)

    def submit(self):
        first = self.first_entry.get().strip()
        last  = self.last_entry.get().strip()
        dob   = self.dob_entry.get().strip()
        phone = self.phone_entry.get().strip()
        code  = self.code_entry.get().strip()
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not first or not last:
            messagebox.showwarning("Validation", "First and last name required.", parent=self)
            return

        ok, msg = validate_dob_str(dob)
        if not ok:
            messagebox.showerror("DOB Error", msg, parent=self)
            return

        ok, msg = validate_phone_str(phone)
        if not ok:
            messagebox.showerror("Phone Error", msg, parent=self)
            return

        # OTP simulate
        ok = otp_simulate_and_verify(phone, self)
        if not ok:
            messagebox.showerror("OTP", "Registration cancelled due to failed OTP.", parent=self)
            return

        if not username or not password:
            messagebox.showwarning("Validation", "Username and password cannot be empty.", parent=self)
            return

        # create user id
        user_id = generate_unique_user_id()
        try:
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM users WHERE username=?", (username,))
                if cur.fetchone():
                    messagebox.showerror("DB", "Username already exists. Try another.", parent=self)
                    return
                cur.execute("""
                    INSERT INTO users (id, first_name, last_name, dob, phone, code_word, username, password, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, first, last, dob, phone, code, username, password, int(time.time())))
                conn.commit()
            messagebox.showinfo("Registered", f"✅ Registered! Your User ID: {user_id}", parent=self)
            # clear
            self.first_entry.delete(0, "end")
            self.last_entry.delete(0, "end")
            self.dob_entry.delete(0, "end")
            self.phone_entry.delete(0, "end")
            self.code_entry.delete(0, "end")
            self.user_entry.delete(0, "end")
            self.pass_entry.delete(0, "end")
            self.controller.show_frame("HomePage")
        except Exception as e:
            messagebox.showerror("Error", f"Error: {e}", parent=self)

# --- Login Page ---
class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        ctk.CTkLabel(self, text="Login", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=12)
        form = ctk.CTkFrame(self)
        form.pack(pady=8)
        self.user_entry = ctk.CTkEntry(form, placeholder_text="Username")
        self.pass_entry = ctk.CTkEntry(form, placeholder_text="Password", show="*")
        self.user_entry.grid(row=0, column=0, padx=8, pady=8)
        self.pass_entry.grid(row=1, column=0, padx=8, pady=8)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Login", command=self.login).grid(row=0, column=0, padx=8)
        ctk.CTkButton(btn_frame, text="Back", command=lambda: controller.show_frame("HomePage")).grid(row=0, column=1, padx=8)

        self.attempts_left = 3

    def login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Validation", "Username and password required.", parent=self)
            return

        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            row = cur.fetchone()

        if not row:
            self.attempts_left -= 1
            if self.attempts_left > 0:
                messagebox.showerror("Login Failed", f"Invalid username or password. Attempts left: {self.attempts_left}", parent=self)
                return
            else:
                messagebox.showerror("Login Failed", "Invalid username or password. Restarting attempts.", parent=self)
                self.attempts_left = 3
                self.user_entry.delete(0, "end"); self.pass_entry.delete(0, "end")
                return

        # ask security question (3 attempts)
        stored_code = (row["code_word"] or "").strip().lower()
        for i in range(3):
            ans = simpledialog.askstring("Security Question", "What is your code word? (Recovery)", parent=self)
            if ans is None:
                return
            if ans.strip().lower() == stored_code:
                # success — move to Poker Step page with user row
                self.attempts_left = 3
                # refresh the row from DB to ensure latest fields
                with connect_db() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM users WHERE username=?", (row["username"],))
                    fresh = cur.fetchone()
                self.controller.show_frame("PokerStepPage", user_row=fresh)
                return
            else:
                if i < 2:
                    messagebox.showwarning("Security", f"Wrong code word. Attempts left: {2 - i}", parent=self)
                else:
                    messagebox.showerror("Security", "Wrong code word. Access denied.", parent=self)
                    return

# --- Poker Step Page (Step 1) ---
class PokerStepPage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.cards = ["Spade", "Heart", "Diamond", "Club", "Ace", "King", "Queen", "Jack", "Joker"]
        self.selected = []   # selected sequence during setup or verification
        self.card_values_assigned = {}  # per-setup random assignment (hidden)
        self.user_row = None
        self.mode = "setup"  # or "verify"

        header = ctk.CTkLabel(self, text="Step 1 — Poker Card Security", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=8)
        self.grid_frame = ctk.CTkFrame(self)
        self.grid_frame.pack(pady=8)

        # info label & controls
        self.info_label = ctk.CTkLabel(self, text="")
        self.info_label.pack(pady=6)
        ctl_frame = ctk.CTkFrame(self)
        ctl_frame.pack(pady=6)
        ctk.CTkButton(ctl_frame, text="Back to Home", command=self.back_home).grid(row=0, column=0, padx=6)
        ctk.CTkButton(ctl_frame, text="Reset Selection", command=self.reset_selection).grid(row=0, column=1, padx=6)
        ctk.CTkButton(ctl_frame, text="Submit Selection", command=self.submit_selection).grid(row=0, column=2, padx=6)

        # passkey entry for verification (used in verify mode)
        self.passkey_entry = ctk.CTkEntry(self, placeholder_text="Enter 8-digit passkey (verification)")
        self.passkey_entry.pack(pady=8)

    def on_show(self, user_row=None):
        self.user_row = user_row
        # if user_row was passed as sqlite Row, it's fine. Refresh to ensure latest data
        if self.user_row:
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username=?", (self.user_row["username"],))
                self.user_row = cur.fetchone()

        self.reset_selection()
        # decide mode: setup if no passkey, verify otherwise
        if not self.user_row or not (self.user_row["passkey"]):
            self.mode = "setup"
            self.info_label.configure(text="Setup: Choose 7 cards (no duplicates) from grid.")
            # assign fresh random card values (0–9) for this setup
            values = random.sample(range(10), 9)
            self.card_values_assigned = dict(zip(self.cards, values))
        else:
            self.mode = "verify"
            self.info_label.configure(text="Verification: Select your 7 cards in the original order (grid is shuffled).")
            # in verify mode we will derive mapping from stored passkey when the user submits

        # build the grid
        self.build_grid()

    def build_grid(self):
        # clear existing
        for w in self.grid_frame.winfo_children():
            w.destroy()
        # show 3x3 grid of buttons (card names only)
        for i in range(3):
            for j in range(3):
                idx = i*3 + j
                name = self.cards[idx]
                btn = ctk.CTkButton(self.grid_frame, text=name, width=180, height=80,
                                    command=lambda n=name: self.card_clicked(n))
                btn.grid(row=i, column=j, padx=8, pady=8)
        self.update_info_label()

    def card_clicked(self, name):
        if self.mode == "setup":
            if name in self.selected:
                messagebox.showwarning("Duplicate", "Card already selected.", parent=self)
                return
            if len(self.selected) >= 7:
                messagebox.showwarning("Limit", "You already selected 7 cards.", parent=self)
                return
            self.selected.append(name)
            self.update_info_label()
        else:
            # verify mode - selecting sequence
            if len(self.selected) >= 7:
                messagebox.showwarning("Limit", "You already selected 7 cards.", parent=self)
                return
            self.selected.append(name)
            self.update_info_label()

    def update_info_label(self):
        if self.selected:
            seq = " → ".join(self.selected)
            self.info_label.configure(text=f"Selected ({len(self.selected)}/7): {seq}")
        else:
            self.info_label.configure(text="No cards selected yet.")

    def reset_selection(self):
        self.selected = []
        self.passkey_entry.delete(0, "end")
        self.update_info_label()

    def back_home(self):
        self.controller.show_frame("HomePage")

    def submit_selection(self):
        if len(self.selected) != 7:
            messagebox.showwarning("Selection", "You must select exactly 7 cards.", parent=self)
            return

        if self.mode == "setup":
            # compute numbers from assigned card_values using 3*x+1, take last digit if >=10
            numbers = [self.card_values_assigned[c] for c in self.selected]
            results = []
            for x in numbers:
                val = 3 * x + 1
                if val >= 10:
                    val = int(str(val)[-1])  # last digit
                results.append(val)
            joined = "".join(str(r) for r in results)
            base7 = joined[:7]  # first 7 digits
            # insert random digit into random position to make 8-digit passkey
            random_digit = str(random.randint(0,9))
            pos = random.randint(0, len(base7))
            final_passkey = base7[:pos] + random_digit + base7[pos:]

            # store: passkey, card_sequence (selection order), store hidden original card_value assignment too
            card_value_set = ", ".join([f"{k}:{v}" for k, v in self.card_values_assigned.items()])
            seq_field = f"{','.join(self.selected)} | {card_value_set}"
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET passkey=?, card_sequence=? WHERE username=?",
                            (final_passkey, seq_field, self.user_row["username"]))
                conn.commit()

            shown_abbrev = "".join([c[0:2].lower() if c.lower().startswith('j') else c[0].lower() for c in self.selected])
            messagebox.showinfo("Passkey Created", f"Your passkey: {final_passkey}({shown_abbrev})\n\nWrite it down — you'll only see the bracketed mnemonic once.", parent=self)

            # refresh DB row and go to Welcome
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM users WHERE username=?", (self.user_row["username"],))
                new_row = cur.fetchone()
            self.controller.show_frame("WelcomePage", user_row=new_row)

        else:
            # VERIFY mode
            stored_passkey = (self.user_row["passkey"] or "")
            # extract numeric digits in order and take first 7
            numeric_values = [int(d) for d in stored_passkey if d.isdigit()][:7]

            # get stored sequence (original chosen sequence)
            full_seq_field = (self.user_row["card_sequence"] or "")
            if " | " in full_seq_field:
                seq_part, _ = full_seq_field.split(" | ", 1)
            else:
                seq_part = full_seq_field
            stored_sequence = [s.strip() for s in seq_part.split(",") if s.strip()]

            # map first 7 numbers to stored_sequence (silently)
            mapping_seq = stored_sequence[:7]
            card_value_by_passkey = dict(zip(mapping_seq, numeric_values))

            # save updated values into dedicated card_values column (clean formatting)
            updated_value_text = ", ".join([f"{k}:{v}" for k,v in card_value_by_passkey.items()])
            with connect_db() as conn:
                cur = conn.cursor()
                cur.execute("UPDATE users SET card_values=? WHERE username=?", (updated_value_text, self.user_row["username"]))
                conn.commit()

            # now compare user selected sequence and passkey entry
            attempt_norm = [a.strip().lower() for a in self.selected]
            original_norm = [s.strip().lower() for s in stored_sequence]
            entered_passkey = self.passkey_entry.get().strip()

            if attempt_norm == original_norm and entered_passkey == stored_passkey:
                messagebox.showinfo("Success", "Step 1 passed successfully!", parent=self)
                # refresh and go to welcome
                with connect_db() as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT * FROM users WHERE username=?", (self.user_row["username"],))
                    new_row = cur.fetchone()
                self.controller.show_frame("WelcomePage", user_row=new_row)
                return
            else:
                messagebox.showerror("Failed", "Incorrect sequence or passkey.", parent=self)
                return

# --- Welcome Page ---
class WelcomePage(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=22, weight="bold"))
        self.label.pack(pady=30)
        ctk.CTkButton(self, text="Log out", command=lambda: controller.show_frame("HomePage")).pack(pady=10)
        self.user_row = None

    def on_show(self, user_row=None):
        if user_row:
            self.user_row = user_row
            fname = user_row["first_name"]
            lname = user_row["last_name"]
            self.label.configure(text=f"🎉 Access Granted!\nWelcome {fname} {lname}")

# ---------------------------
# Run App
# ---------------------------
if __name__ == "__main__":
    app = SecureApp()
    app.mainloop()
