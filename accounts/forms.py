from django.contrib.auth.forms import AuthenticationForm
from django import forms

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='نام کاربری',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'نام کاربری خود را وارد کنید',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        label='رمز عبور',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'رمز عبور خود را وارد کنید',
            'autocomplete': 'current-password'
        })
    )