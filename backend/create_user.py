import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhaka_web.settings')
django.setup()

from django.contrib.auth.models import User
from complaints.models import UserProfile

email = 'abdullahtsn13@gmail.com'
password = 'youaremyqueen'

print(f"Creating user: {email}\n")

# Create user if doesn't exist
user, created = User.objects.get_or_create(
    username=email,
    defaults={
        'email': email,
        'first_name': 'Abdullah',
        'last_name': 'Tsn',
    }
)

if created:
    print(f"✓ User created: {user.username}")
else:
    print(f"⚠ User already existed: {user.username}")

# Set password
user.set_password(password)
user.is_active = True
user.save()
print(f"✓ Password set")

# Create or update UserProfile
profile, created = UserProfile.objects.get_or_create(
    user=user,
    defaults={'role': 'citizen'}
)

if created:
    print(f"✓ UserProfile created with role: citizen")
else:
    print(f"⚠ UserProfile already existed with role: {profile.role}")

print(f"\n✓ User is ready to login!")
print(f"  Email: {email}")
print(f"  Password: {password}")

# Verify
from django.contrib.auth import authenticate
auth_user = authenticate(username=email, password=password)
if auth_user:
    print(f"\n✓ VERIFIED: Login works!")
else:
    print(f"\n✗ ERROR: Login still not working")
