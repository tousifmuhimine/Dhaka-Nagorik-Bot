"""Create initial superuser and test data."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dhaka_web.settings')
django.setup()

from django.contrib.auth.models import User
from complaints.models import UserProfile

# Create admin user
if not User.objects.filter(email='admin@dhaka.gov').exists():
    admin_user = User.objects.create_superuser(
        username='admin@dhaka.gov',
        email='admin@dhaka.gov',
        password='Admin@1234',
        first_name='Admin'
    )
    UserProfile.objects.create(user=admin_user, role='admin')
    print("✓ Admin user created: admin@dhaka.gov / Admin@1234")
else:
    print("✓ Admin user already exists")

# Create test citizen
if not User.objects.filter(email='citizen@example.com').exists():
    citizen_user = User.objects.create_user(
        username='citizen@example.com',
        email='citizen@example.com',
        password='Citizen@1234',
        first_name='Arif'
    )
    UserProfile.objects.create(user=citizen_user, role='citizen')
    print("✓ Citizen user created: citizen@example.com / Citizen@1234")
else:
    print("✓ Citizen user already exists")

# Create test authority
if not User.objects.filter(email='authority@dhaka.gov').exists():
    auth_user = User.objects.create_user(
        username='authority@dhaka.gov',
        email='authority@dhaka.gov',
        password='Authority@1234',
        first_name='Ahmed'
    )
    UserProfile.objects.create(user=auth_user, role='authority', thana='Dhanmondi')
    print("✓ Authority user created: authority@dhaka.gov / Authority@1234")
else:
    print("✓ Authority user already exists")

print("\n🎉 Django app ready! Start with: python manage.py runserver")
print("\nTest Accounts:")
print("Admin     | admin@dhaka.gov        | Admin@1234")
print("Citizen   | citizen@example.com    | Citizen@1234")
print("Authority | authority@dhaka.gov    | Authority@1234")
