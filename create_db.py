from app import app, db

<<<<<<< HEAD
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("✅ Database created successfully.")
=======
with app.app_context():
    db.create_all()
    print("✅ Database created successfully!")
>>>>>>> 65b9ef74ff36e65d62039d53d2ac1714437d849f
