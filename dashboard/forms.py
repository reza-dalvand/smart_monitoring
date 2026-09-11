from django import forms
from .models import Classroom, WeeklySchedule


class ClassroomForm(forms.ModelForm):
    """فرم ساخت کلاس جدید توسط معاون"""
    class Meta:
        model = Classroom
        fields = ['name', 'subject', 'grade', 'field', 'teacher_name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: کلاس ۱۰۱'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: ریاضی پایه دهم'
            }),
            'grade': forms.Select(attrs={'class': 'form-select'}),
            'field': forms.Select(attrs={'class': 'form-select'}),
            'teacher_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام کامل معلم'
            }),
        }


class WeeklyScheduleForm(forms.ModelForm):
    """فرم ساخت برنامه هفتگی"""
    class Meta:
        model = WeeklySchedule
        fields = ['classroom', 'day_of_week', 'start_time', 'end_time', 'room']
        widgets = {
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'day_of_week': forms.Select(attrs={'class': 'form-select'}),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'room': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'شماره اتاق (اختیاری)'
            }),
        }


class CopyScheduleForm(forms.Form):
    """فرم کپی برنامه از یک کلاس به کلاس دیگر"""
    source_classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        label='کلاس مبدأ',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    target_classroom = forms.ModelChoiceField(
        queryset=Classroom.objects.all(),
        label='کلاس مقصد',
        widget=forms.Select(attrs={'class': 'form-select'})
    )