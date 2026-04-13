import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhaka_web.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

email = 'abdullahtsn13@gmail.com'
password = 'youaremyqueen'

print(f"Testing login for: {email}\n")

# Check 1: Does user exist?
try:
    user = User.objects.get(email=email)
    print(f"✓ User found in database")
    print(f"  Username: {user.username}")
    print(f"  Email: {user.email}")
    print(f"  First Name: {user.first_name}")
    print(f"  Is Active: {user.is_active}")
    print(f"  Has UserProfile: {hasattr(user, 'userprofile')}")
    if hasattr(user, 'userprofile'):
        print(f"  Role: {user.userprofile.role}")
    else:
        print(f"  ⚠ WARNING: No UserProfile! This could cause login issue")
except User.DoesNotExist:
    print(f"✗ User NOT found in database")
    exit(1)

# Check 2: Can we authenticate with username?
print(f"\n2. Testing authentication with USERNAME...")
authenticated_user = authenticate(username=user.username, password=password)
if authenticated_user:
    print(f"✓ Authentication with username works!")
else:
    print(f"✗ Authentication with username FAILED - password might be wrong")

# Check 3: Can we authenticate with email?
print(f"\n3. Testing authentication with EMAIL...")
authenticated_user = authenticate(username=email, password=password)
if authenticated_user:
    print(f"✓ Authentication with email works!")
else:
    print(f"✗ Authentication with email FAILED")

# Check 4: Test Django login like the form does
print(f"\n4. Testing login_view flow...")
try:
    user_obj = User.objects.get(email=email)
    auth_user = authenticate(username=user_obj.username, password=password)
    if auth_user:
        print(f"✓ Login flow works!")
    else:
        print(f"✗ Login flow FAILED - password incorrect")
except User.DoesNotExist:
    print(f"✗ Login flow FAILED - email not found")
