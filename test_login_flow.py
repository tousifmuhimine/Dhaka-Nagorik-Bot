"""
Test the exact login flow that happens in Django.
This simulates what happens when a user submits the login form.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhaka_web.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from complaints.forms import LoginForm
from complaints.views import login_view

print("=" * 60)
print("TEST: Login Form Validation")
print("=" * 60)

# Test 1: Form with valid email/password
print("\n[TEST 1] Submitting form with valid credentials...")
test_data = {
    'email': 'citizen@example.com',
    'password': 'Citizen@1234'
}

form = LoginForm(test_data)
print(f"Form is valid: {form.is_valid()}")
if not form.is_valid():
    print(f"Form errors: {form.errors}")
else:
    print(f"Cleaned data - Email: {form.cleaned_data['email']}")
    print(f"Cleaned data - Password length: {len(form.cleaned_data['password'])} chars")

# Test 2: Check if user exists
print("\n[TEST 2] Checking if user exists in database...")
email = 'citizen@example.com'
try:
    user = User.objects.get(email=email)
    print(f"✓ User found: {user.username}")
    print(f"  - Email: {user.email}")
    print(f"  - First name: {user.first_name}")
    print(f"  - Username: {user.username}")
except User.DoesNotExist:
    print(f"✗ User NOT found: {email}")

# Test 3: Test authentication
print("\n[TEST 3] Testing authentication...")
from django.contrib.auth import authenticate
user = authenticate(username='citizen@example.com', password='Citizen@1234')
if user:
    print(f"✓ Authentication successful!")
    print(f"  - User: {user.username}")
else:
    print(f"✗ Authentication failed!")

# Test 4: Test with wrong password
print("\n[TEST 4] Testing with wrong password...")
user = authenticate(username='citizen@example.com', password='WrongPassword123')
if user:
    print(f"✓ Authentication successful (shouldn't happen!)")
else:
    print(f"✓ Authentication correctly failed for wrong password")

# Test 5: Empty form
print("\n[TEST 5] Testing invalid form submission (empty)...")
empty_form = LoginForm({})
print(f"Form is valid: {empty_form.is_valid()}")
if not empty_form.is_valid():
    print(f"Form errors: {empty_form.errors}")

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)
