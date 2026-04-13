"""Check users in database."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhaka_web.settings')
django.setup()

from django.contrib.auth.models import User

print("=" * 60)
print("ALL USERS IN DATABASE")
print("=" * 60)

users = User.objects.all()
if users.exists():
    for u in users:
        print(f"\nUsername: {u.username}")
        print(f"Email:    {u.email}")
        print(f"Name:     {u.first_name}")
        try:
            profile = u.userprofile
            print(f"Role:     {profile.role}")
        except:
            print(f"Role:     (no profile)")
else:
    print("\nNo users found in database!")

print("\n" + "=" * 60)
