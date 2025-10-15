import getpass
import random


def step1_login():
    correct_username = "admin"
    correct_password = "password123"

    print("Step 1: Login")
    username = input("Username: ")
    password = getpass.getpass("Password: ")  # Hides input

    if username == correct_username and password == correct_password:
        print("Login successful.\n")
        return True
    else:
        print("Login failed.\n")
        return False


def step2_security_question():
    print("Step 2: Security Question")
    answer = input("What is your favorite color? ").strip().lower()

    if answer == "blue":
        print("Security question passed.\n")
        return True
    else:
        print("Wrong answer.\n")
        return False
def step3_otp():
    print("Step 3: One-Time Passcode (OTP)")
    otp = random.randint(1000, 9999)
    print(f"Your OTP is: {otp}")  # In real systems, this would be sent via email/SMS
    entered_otp = input("Enter the OTP: ")

    if entered_otp == str(otp):
        print("OTP verified.\n")
        return True
    else:
        print("Incorrect OTP.\n")
        return False
    
# Main function
def security_interface():
    print("=== Secure Access Interface ===\n")
    
    if not step1_login():
        return print("Access Denied at Step 1.")
    
    if not step2_security_question():
        return print("Access Denied at Step 2.")
    
    if not step3_otp():
        return print("Access Denied at Step 3.")
    
    print("✅ Access Granted. Welcome!")

# Run the security interface
if __name__ == "__main__":
    security_interface()




