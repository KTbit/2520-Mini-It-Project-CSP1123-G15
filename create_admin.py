# To register new admins, done via terminal / CLI
# Updated and reworked 20 - 24 Jan 2026

from app import app, db
from databasemodels import User
import getpass


def create_admin():
    print("Admin Registration for Recipe Finder Website")
    print()
    
    with app.app_context():
        # Get username
        while True:
            username = input("Enter admin username: ").strip()
            if not username:
                print("Username cannot be empty.")
                continue
            
            # Check if username exists
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                print(f"Username '{username}' already exists")
                continue
            
            break
        
        # Get email
        while True:
            email = input("Enter admin email: ").strip().lower()
            if not email:
                print("Email cannot be empty.")
                continue
            
            if "@" not in email or "." not in email:
                print(" Invalid email format!")
                continue
            
            # Check if email exists
            existing_email = User.query.filter_by(email=email).first()
            if existing_email:
                print(f"Email '{email}' is already registered.")
                continue
            
            break
        
        # Get password
        while True:
            password = getpass.getpass("Enter admin password: ")
            if len(password) < 6:
                print("Password must be at least 6 characters")
                continue
            
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("Passwords do not match")
                continue
            
            break
        
        # Create admin user
        admin_user = User(
            username=username,
            email=email,
            is_admin=True
        )
        admin_user.set_password(password)
        
        try:
            db.session.add(admin_user)
            db.session.commit()
            
            print()
            print("Admin user created successfully")
            print(f"Username: {username}")
            print(f"Email: {email}")
            print(f"Admin Status: Yes")
            print()
            print("You can now log in at: /admin/login")
            
        except Exception as e:
            db.session.rollback()
            print()
            print(f"Error creating admin user: {e}")


def list_admins():
    #lists all existing admins
    print("Existing Admin Users")
    print()
    
    with app.app_context():
        admins = User.query.filter_by(is_admin=True).all()
        
        if not admins:
            print("No admins found.")
        else:
            for idx, admin in enumerate(admins, 1):
                print(f"{idx}. {admin.username} ({admin.email})")
                print(f"   Created: {admin.created_at.strftime('%Y-%m-%d %H:%M')}")
                print()


def promote_user():
    # promote a user to admin...
    print("Promote Existing User to Admin")
    print()
    
    with app.app_context():
        username = input("Enter username to promote: ").strip()
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            print(f"User '{username}' not found!")
            return
        
        if user.is_admin:
            print(f"User '{username}' is already an admin.")
            return
        
        confirm = input(f"Promote '{username}' to admin? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            user.is_admin = True
            db.session.commit()
            print(f"User '{username}' has been promoted to admin.")
        else:
            print("Operation cancelled.")


def main():
    """Main menu"""
    while True:
        print()
        print("Recipe Finder - Admin Management")
        print()
        print("1. Create new admin user")
        print("2. List existing admins")
        print("3. Promote existing user to admin")
        print("4. Exit")
        print()
        
        choice = input("Select an option (1-4): ").strip()
        
        if choice == '1':
            create_admin()
        elif choice == '2':
            list_admins()
        elif choice == '3':
            promote_user()
        elif choice == '4':
            print("Operation ended")
            break
        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()