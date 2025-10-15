import getpass
import random


def stm_login():
    correct_username = "admin"
    correct_password = "123"

    print("Login")
    username = input("Username: ")
    password = getpass.getpass("Password: ")  # Hides input

    if username == correct_username and password == correct_password:
        print("Login successful.\n")
        return True
    else:
        print("Login failed.\n")
        return False

def stm_security_question():
    print("Security Question")
    answer = input("What is your favorite color? ").strip().lower()

    if answer == "blue":
        print("Security question passed.\n")
        return True
    else:
        print("Wrong answer.\n")
        return False
def stm_otp():
    print("One-Time Passcode (OTP)")
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
    
    if not stm_login():
        return print("Access Denied")
    
    if not stm_security_question():
        return print("Access Denied")
    
    if not stm_otp():
        return print("Access Denied")
    
    print("✅ Access Granted. Welcome!")

# Run the security interface
if __name__ == "__main__":
    security_interface()




