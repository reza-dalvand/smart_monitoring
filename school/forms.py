from django import forms
from .models import FollowUpCase, SchoolTask, SchoolStaffAssignment
from .constants import CaseCategory, CasePriority, AssistantType


class FollowUpCaseForm(forms.ModelForm):
    class Meta:
        model = FollowUpCase
        fields = ['title', 'description', 'student', 'classroom',
                  'category', 'priority', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'عنوان پرونده',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
            }),
            'student': forms.Select(attrs={'class': 'form-select'}),
            'classroom': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
        }


class SchoolTaskForm(forms.ModelForm):
    class Meta:
        model = SchoolTask
        fields = ['title', 'description', 'assigned_to', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
            }),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
        }


class AssistantAssignmentForm(forms.ModelForm):
    class Meta:
        model = SchoolStaffAssignment
        fields = ['user', 'assistant_type', 'start_date', 'end_date']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'assistant_type': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
            }),
        }