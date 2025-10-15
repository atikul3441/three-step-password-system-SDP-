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


