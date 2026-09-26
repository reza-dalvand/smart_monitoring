from django import forms
from .models import StudentRequest, StudentFaceChangeRequest
from .constants import StudentRequestType, StudentRequestPriority


class StudentRequestForm(forms.ModelForm):
    class Meta:
        model = StudentRequest
        fields = ['request_type', 'title', 'description', 'priority']
        widgets = {
            'request_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان درخواست',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'شرح کامل درخواست...',
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
        }


class FaceChangeRequestForm(forms.ModelForm):
    class Meta:
        model = StudentFaceChangeRequest
        fields = ['reason']
        widgets = {
            'reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'دلیل درخواست تغییر چهره...',
            }),
        }


class HomeworkSubmitForm(forms.Form):
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'متن پاسخ...',
        }),
        label='متن پاسخ',
    )
    attachment = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        label='فایل ارسالی',
    )