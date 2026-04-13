"""Django forms for the complaints system."""

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Complaint, ComplaintUpdate


class SignUpForm(UserCreationForm):
    """User registration form."""
    
    first_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg'})
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'email', 'password1', 'password2')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """User login form."""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'w-full px-4 py-2 border rounded-lg', 'placeholder': 'Password'})
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
    """Form for updating complaint status."""
    
    class Meta:
        model = ComplaintUpdate
        fields = ['message', 'status_change']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border rounded-lg',
                'rows': 4,
                'placeholder': 'Add an update message...'
            }),
            'status_change': forms.Select(attrs={'class': 'w-full px-4 py-2 border rounded-lg'}),
        }
