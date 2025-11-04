
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
            created_at INTEGER
        )
        """)
        conn.commit()

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
                except Exception:
                    pass

# GUI App ---
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Helper functions used by GUI, re-using the same validation rules as backend:
def validate_dob_str(dob_str):
    
    try:
        parsed = datetime.strptime(dob_str, "%d/%m/%Y")
    except ValueError:
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
    """Generate a 7-character alphanumeric ID and ensure uniqueness in DB."""
    with connect_db() as conn:
        cur = conn.cursor()
        while True:
            user_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
            cur.execute("SELECT 1 FROM users WHERE id=?", (user_id,))
            if not cur.fetchone():
                return user_id

# OTP 
def gui_otp_flow(phone):
    otp = random.randint(1000, 9999)
    # simulate sending
    messagebox.showinfo("OTP Sent", f"📱 Sending OTP to {phone}...\n\n(For demo) OTP: {otp}")
    attempts = 0
    while attempts < 3:
        entered = simpledialog.askstring("Enter OTP", f"Enter the OTP sent to {phone} (attempt {attempts+1}/3):")
        if entered is None:
            # user cancelled
            return False
        if entered.strip() == str(otp):
            messagebox.showinfo("OTP", "✅ OTP verified.")
            return True
        else:
            attempts += 1
            if attempts < 3:
                messagebox.showwarning("OTP", f"Incorrect OTP. Attempts left: {3 - attempts}")
            else:
                messagebox.showerror("OTP", "Incorrect OTP. Maximum attempts reached.")
                return False
    return False

# Database insert 
def insert_user_to_db(user_id, first_name, last_name, dob, phone, code_word, username, password):
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
    return True, None

def check_login_credentials(username, password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        return cur.fetchone()

# GUI Layout Classes ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TriSecure")
        self.geometry("940x700")
        self.resizable(True, True)

        # init DB
        init_db()
        add_missing_columns()

        # container frames
        self.frames = {}
        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=120, pady=120)

        for F in (HomeFrame, RegisterFrame, LoginFrame, WelcomeFrame):
            frame = F(parent=container, controller=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("HomeFrame")

    def show_frame(self, name, **kwargs):
        frame = self.frames[name]
        if hasattr(frame, "on_show"):
            frame.on_show(**kwargs)
        frame.tkraise()

# Home Frame
class HomeFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ctk.CTkLabel(self, text="TriSecure Access Interface", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20,10))
        ctk.CTkLabel(self, text="Choose an option below:", font=ctk.CTkFont(size=14)).pack(pady=(0,20))

        btn_reg = ctk.CTkButton(self, text="Register", width=200, command=lambda: controller.show_frame("RegisterFrame"))
        btn_login = ctk.CTkButton(self, text="Login", width=200, command=lambda: controller.show_frame("LoginFrame"))
        btn_exit = ctk.CTkButton(self, text="Exit", width=200, fg_color="red", command=self.quit_app)

        btn_reg.pack(pady=10)
        btn_login.pack(pady=10)
        btn_exit.pack(pady=10)

    def quit_app(self):
        self.controller.destroy()

# Register Frame
class RegisterFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        header = ctk.CTkLabel(self, text="Register New User", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=(10,10))

        form = ctk.CTkFrame(self)
        form.pack(pady=6, padx=12, fill="both", expand=False)

        # first row
        self.first_name_entry = ctk.CTkEntry(form, placeholder_text="First Name")
        self.last_name_entry = ctk.CTkEntry(form, placeholder_text="Last Name")
        self.first_name_entry.grid(row=0, column=0, padx=8, pady=8)
        self.last_name_entry.grid(row=0, column=1, padx=8, pady=8)

        # dob and phone
        self.dob_entry = ctk.CTkEntry(form, placeholder_text="Date of Birth (dd/mm/yyyy)")
        self.phone_entry = ctk.CTkEntry(form, placeholder_text="Phone Number")
        self.dob_entry.grid(row=1, column=0, padx=8, pady=8)
        self.phone_entry.grid(row=1, column=1, padx=8, pady=8)

        # code word, username, password
        self.code_word_entry = ctk.CTkEntry(form, placeholder_text="Code Word (Remember this Code)")
        self.username_entry = ctk.CTkEntry(form, placeholder_text="Choose a Username")
        self.password_entry = ctk.CTkEntry(form, placeholder_text="Choose a Password", show="*")
        self.code_word_entry.grid(row=2, column=0, padx=8, pady=8)
        self.username_entry.grid(row=2, column=1, padx=8, pady=8)
        self.password_entry.grid(row=3, column=0, columnspan=2, padx=8, pady=8, sticky="ew")

        # buttons
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        submit_btn = ctk.CTkButton(btn_frame, text="Submit Registration", command=self.submit_registration)
        back_btn = ctk.CTkButton(btn_frame, text="Back", command=lambda: controller.show_frame("HomeFrame"))
        submit_btn.grid(row=0, column=0, padx=10)
        back_btn.grid(row=0, column=1, padx=10)

        self.status_label = ctk.CTkLabel(self, text="", fg_color=None)
        self.status_label.pack(pady=6)

    def submit_registration(self):
        first_name = self.first_name_entry.get().strip()
        last_name = self.last_name_entry.get().strip()
        dob = self.dob_entry.get().strip()
        phone = self.phone_entry.get().strip()
        code_word = self.code_word_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        # Basic presence checks 
        if not first_name or not last_name:
            messagebox.showwarning("Validation", "First and last name are required.")
            return

        # DOB validation with up to 3 attempts
        ok, msg = validate_dob_str(dob)
        if not ok:
            messagebox.showerror("DOB Error", f"Date of birth invalid: {msg}")
            return

        # Phone validation
        ok, msg = validate_phone_str(phone)
        if not ok:
            messagebox.showerror("Phone Error", msg)
            return

        # OTP flow 
        ok = gui_otp_flow(phone)
        if not ok:
            messagebox.showerror("OTP", "Registration cancelled due to failed OTP verification.")
            return

        if not username or not password:
            messagebox.showwarning("Validation", "Username and password cannot be empty.")
            return

        # generate unique id 
        user_id = generate_unique_user_id()

        success, err = insert_user_to_db(user_id, first_name, last_name, dob, phone, code_word, username, password)
        if not success:
            messagebox.showerror("DB Error", err or "Unknown error")
            return

        messagebox.showinfo("Registered", f"✅ Registration successful! Your User ID: {user_id}")
        # clear form
        self.first_name_entry.delete(0, "end")
        self.last_name_entry.delete(0, "end")
        self.dob_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")
        self.code_word_entry.delete(0, "end")
        self.username_entry.delete(0, "end")
        self.password_entry.delete(0, "end")
        # go to home
        self.controller.show_frame("HomeFrame")

# Login Frame
class LoginFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        header = ctk.CTkLabel(self, text="Login", font=ctk.CTkFont(size=20, weight="bold"))
        header.pack(pady=(10,10))

        form = ctk.CTkFrame(self)
        form.pack(padx=12, pady=6)

        self.username_entry = ctk.CTkEntry(form, placeholder_text="Username")
        self.password_entry = ctk.CTkEntry(form, placeholder_text="Password", show="*")
        self.username_entry.grid(row=0, column=0, padx=8, pady=8)
        self.password_entry.grid(row=1, column=0, padx=8, pady=8)

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=12)
        login_btn = ctk.CTkButton(btn_frame, text="Login", command=self.attempt_login)
        back_btn = ctk.CTkButton(btn_frame, text="Back", command=lambda: controller.show_frame("HomeFrame"))
        login_btn.grid(row=0, column=0, padx=8)
        back_btn.grid(row=0, column=1, padx=8)

        self.attempts_left = 3

    def attempt_login(self):
        # three attempts for username/password overall; restart after 3 fails
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Validation", "Username and password required.")
            return

        row = check_login_credentials(username, password)
        if not row:
            self.attempts_left -= 1
            if self.attempts_left > 0:
                messagebox.showerror("Login Failed", f"Invalid username or password. Attempts left: {self.attempts_left}")
                return
            else:
                messagebox.showerror("Login Failed", "Invalid username or password.")
                # reset attempts and inputs; user must start login again
                self.attempts_left = 3
                self.username_entry.delete(0, "end")
                self.password_entry.delete(0, "end")
                return
        # credentials ok -> ask security question (3 attempts)
        code_word_stored = (row["code_word"] or "").strip().lower()
        for i in range(3):
            ans = simpledialog.askstring("Security Question", "What is your code word? (Recovery)")
            if ans is None:
                # cancelled
                return
            if ans.strip().lower() == code_word_stored:
                # success
                self.attempts_left = 3
                # show welcome
                self.controller.show_frame("WelcomeFrame", user_row=row)
                return
            else:
                if i < 2:
                    messagebox.showwarning("Security", f"Wrong code word. Attempts left: {2 - i}")
                else:
                    messagebox.showerror("Security", "Wrong code word. Access denied.")
                    return

# Welcome Frame
class WelcomeFrame(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=18, weight="bold"))
        self.label.pack(pady=30)
        back_btn = ctk.CTkButton(self, text="Log out", command=lambda: controller.show_frame("HomeFrame"))
        back_btn.pack(pady=10)

    def on_show(self, user_row=None):
        if user_row is not None:
            fname = user_row["first_name"]
            lname = user_row["last_name"]
            uid = user_row["id"]
            self.label.configure(text=f"🎉 Access Granted!\nWelcome {fname} {lname}\nUser ID: {uid}")

# -------------------- Run App --------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
