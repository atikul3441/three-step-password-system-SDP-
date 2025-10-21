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
    
def step2_pattern_image_security():
    print("=== Step 1: Pattern + Image Security ===")

    images = ["🐶 Dog", "🐱 Cat", "🚗 Car", "🌳 Tree", "📱 Phone"]
    correct_sequence = ["Dog", "Cat", "Car"]
    correct_pattern = "2580"

    names = [img.split(maxsplit=1)[1] for img in images]

    print("\nAvailable images:")
    for i, img in enumerate(images, start=1):
        print(f"{i}. {img}")

    attempts = 3
    while attempts > 0:
        print("\nSelect the correct image sequence (you can enter names or indices, e.g. 'Dog Cat Car' or '1 2 3'):")
        raw = input("Enter in correct order (separated by space): ").strip()
        if not raw:
            print("Empty input.")
            attempts -= 1
            continue

        tokens = raw.split()
        # If all tokens are digits, treat them as indices
        if all(t.isdigit() for t in tokens):
            try:
                user_sequence = [names[int(t) - 1] for t in tokens]
            except (IndexError, ValueError):
                print("Invalid index provided.")
                attempts -= 1
                continue
        else:
            # Normalize words (handle case-insensitive)
            user_sequence = [t.title() for t in tokens]

        if user_sequence != correct_sequence:
            attempts -= 1
            print(f"❌ Wrong image sequence. Attempts left: {attempts}")
            if attempts == 0:
                print("Access Denied at Step 1.\n")
                return False
            continue

        print("\n✅ Image sequence correct!")
        break

    # Pattern input (give 3 tries)
    attempts = 3
    while attempts > 0:
        print("\nNow enter your unlock pattern (Example: 2580):")
        user_pattern = input("Enter pattern: ").strip().replace(" ", "")
        if not user_pattern.isdigit():
            print("Pattern must be numeric.")
            attempts -= 1
            continue

        if user_pattern == correct_pattern:
            print("✅ Pattern verified successfully.\n")
            return True
        else:
            attempts -= 1
            print(f"❌ Incorrect pattern. Attempts left: {attempts}")

    print("Access Denied at Step 1.\n")
    return False

if __name__ == "__main__":
    step2_pattern_image_security()