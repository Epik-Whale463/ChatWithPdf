import secrets
import streamlit as st
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import subprocess

uri = "mongodb+srv://pvrcharan2022:root@main.7hpxp9m.mongodb.net/?retryWrites=true&w=majority&appName=Main"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client["MainDb"]
collection = db["Credentials"]
collection1 = db["UserHistory"]

def converter(object_id):
    object_id = str(object_id)
    integer_id = int(object_id, 16)
    truncated_id = integer_id % 100000000
    return truncated_id

def generate_session_token(username):
    # Generate a random session token using secrets.token_hex()
    session_token = secrets.token_hex(16)  # Generates a 32-character random hexadecimal string
    # You can also combine the username with a random string to create a unique token
    # session_token = username + secrets.token_hex(8)  # Example of combining username and random string
    return session_token


def register_user(username, password):
    existing_user = collection.find_one({"username": username})
    if existing_user:
        st.error("User already exists. Please choose a different username.")
        return
    result = collection.insert_one({"username": username, "password": password})
    inserted_id = result.inserted_id
    user_document = collection.find_one({"_id": inserted_id})
    username = user_document["username"]
    user_id = converter(inserted_id)
    collection1.insert_one({"username": username, "user_id": user_id})
    st.success("User registered successfully!")

def login_user(username, password):
    user = collection.find_one({"username": username})
    if user and password == user["password"]:
        session_token = generate_session_token(username)
        return session_token
    return None

def main():
    st.title("User Authentication and History Viewer")

    # Set up layout using columns
    col1, col2 = st.columns(2)

    # User Registration
    with col1:
        st.header("User Registration")
        new_username = st.text_input("Enter username:")
        new_password = st.text_input("Enter password:", type="password")
        if st.button("Register"):
            register_user(new_username, new_password)

    # User Login
    with col2:
        st.header("User Login")
        username = st.text_input("Enter your username:")
        password = st.text_input("Enter your password:", type="password")
        if st.button("Login"):
            session_token = login_user(username, password)
            if session_token:
                st.success("Login successful!")
                # Redirect to the second Streamlit app with username and session_token
                subprocess.run(["streamlit", "run", "app.py", f"--username={username}", f"--session_token={session_token}"])
            else:
                st.error("Invalid username or password")

if __name__ == "__main__":
    main()
