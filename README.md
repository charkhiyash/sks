# Sanyukt Karmyogi Sena - NGO Website

This is a complete website built with Flask and Vanilla JavaScript as per the provided instructions.

## Setup and Installation

1.  **Clone the repository or create the project files as described.**

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install the required packages:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create Placeholder Images:**
    - Add your NGO logo to `static/images/logo.png`.
    - Add your donation QR code to `static/images/qr_code.png`.

5.  **Run the application:**
    ```bash
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000`.

## First Time Setup: Creating the Leader Account

The application is designed to be secure, with no default admin credentials. To create the first **Leader** account:

1.  Run the application.
2.  Navigate to `http://127.0.0.1:5000/register` and create a normal user account.
3.  Stop the Flask server (Ctrl+C).
4.  Open a Python shell in your project directory (with the virtual environment activated):
    ```bash
    python
    ```
5.  Run the following commands, replacing `'your_username'` with the username you just registered:
    ```python
    from app import app
    from database import db, User
    with app.app_context():
        user = User.query.filter_by(username='your_username').first()
        if user:
            user.role = 'Leader'
            db.session.commit()
            print(f"User '{user.username}' has been promoted to Leader.")
        else:
            print("User not found.")
    exit()
    ```
6.  Now, restart the Flask server (`flask run`). You can log in with your account, and you will have Leader privileges.