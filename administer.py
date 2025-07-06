from app import app
from database import db, User
userName = input("Type the user to be promoted:")
with app.app_context():
    user = User.query.filter_by(username=userName).first()
    if user:
        user.role = 'Leader'
        db.session.commit()
        print(f"User '{user.username}' has been promoted to Leader.")
    else:
        print("User not found.")
exit()