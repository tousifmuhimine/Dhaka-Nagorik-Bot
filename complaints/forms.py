"""Django forms for the complaints system."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Complaint, ComplaintUpdate, UserProfile


AUTH_INPUT_CLASS = (
    'auth-input w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-4 '
    'text-sm text-white transition placeholder:text-white/35 focus:border-emerald-200/50 '
    'focus:bg-white/10 focus:outline-none'
)
AUTH_SELECT_CLASS = (
    'auth-input w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-4 '
    'text-sm text-white transition focus:border-emerald-200/50 focus:bg-white/10 focus:outline-none'
)
AUTH_TEXTAREA_CLASS = (
    'auth-input w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-4 '
    'text-sm text-white transition placeholder:text-white/35 focus:border-emerald-200/50 '
    'focus:bg-white/10 focus:outline-none min-h-28'
)


class SignUpForm(UserCreationForm):
    """User registration form."""

    role = forms.ChoiceField(
        choices=UserProfile.ROLE_CHOICES,
        initial='citizen',
        widget=forms.Select(attrs={'class': AUTH_SELECT_CLASS}),
    )
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Your full name',
            'autocomplete': 'name',
        })
    )
    thana = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Authorized thana or area',
        }),
    )
    department = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Department or office name',
        }),
    )
    employee_id = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Employee ID or government ID',
        }),
    )
    phone_number = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Contact phone number',
            'autocomplete': 'tel',
        }),
    )
    access_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': AUTH_TEXTAREA_CLASS,
            'placeholder': 'Tell the admin why you need this access and what area you serve.',
            'rows': 4,
        }),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'you@example.com',
            'autocomplete': 'email',
        })
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Create a password',
            'autocomplete': 'new-password',
        })
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })
    )
    
    class Meta:
        model = User
        fields = (
            'role',
            'first_name',
            'thana',
            'department',
            'employee_id',
            'phone_number',
            'access_reason',
            'email',
            'password1',
            'password2',
        )

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        thana = (cleaned_data.get('thana') or '').strip()
        department = (cleaned_data.get('department') or '').strip()
        employee_id = (cleaned_data.get('employee_id') or '').strip()
        phone_number = (cleaned_data.get('phone_number') or '').strip()
        access_reason = (cleaned_data.get('access_reason') or '').strip()

        if role in {'authority', 'admin'}:
            if not department:
                self.add_error('department', 'Department or office is required for authority/admin access.')
            if not employee_id:
                self.add_error('employee_id', 'Employee ID is required for authority/admin access.')
            if not phone_number:
                self.add_error('phone_number', 'Phone number is required for authority/admin access.')
            if not access_reason:
                self.add_error('access_reason', 'Please explain why you need elevated access.')

        if role == 'authority' and not thana:
            self.add_error('thana', 'Authority access requires an authorized thana or area.')

        if role == 'admin' and thana:
            cleaned_data['thana'] = ''

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name'].strip()
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        if self.cleaned_data['role'] in {'authority', 'admin'}:
            user.is_active = False
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """User login form."""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Enter your email',
            'autocomplete': 'email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': AUTH_INPUT_CLASS,
            'placeholder': 'Enter your password',
            'autocomplete': 'current-password',
        })
    )


class ComplaintForm(forms.ModelForm):
    """Form for creating/editing complaints."""
    
    class Meta:
        model = Complaint
        fields = ['category', 'thana', 'area', 'description']
        widgets = {
            'category': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
            'thana': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Enter your thana/area'
            }),
            'area': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'placeholder': 'Specific location/address'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'rows': 5,
                'placeholder': 'Describe your complaint in detail...'
            }),
        }


class ComplaintUpdateForm(forms.ModelForm):
    """Form for adding complaint notes."""

    class Meta:
        model = ComplaintUpdate
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'rows': 4,
                'placeholder': 'Add an update note...'
            }),
        }
