"""Test login functionality."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhaka_web.settings')
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User

email = "citizen@example.com"
password = "Citizen@1234"

print(f"\nTesting login with:")
print(f"Email: {email}")
print(f"Password: {password}")

try:
    # Method 1: Get user by email
    print("\n1. Trying to get user by email...")
    user = User.objects.get(email=email)
    print(f"   ✓ Found user: {user.username}")
    
    # Method 2: Authenticate with username
    print("\n2. Authenticating with username & password...")
    authenticated_user = authenticate(username=user.username, password=password)
    
    if authenticated_user:
        print(f"   ✓ Login SUCCESS!")
        print(f"   Username: {authenticated_user.username}")
        print(f"   Email: {authenticated_user.email}")
    else:
        print(f"   ✗ Login FAILED - wrong password")
        
except User.DoesNotExist:
    print(f"   ✗ User not found with email: {email}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 60)
