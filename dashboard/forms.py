from django import forms

from .models import (
    Classroom,
    WeeklySchedule,
    ClassSession,
    AIGenerationJob,
    Question,
)


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


class AIGenerationForm(forms.ModelForm):
    """
    فرم درخواست تولید سوال با هوش مصنوعی

    فعلاً سرویس هوش مصنوعی ماک است.
    """

    class Meta:
        model = AIGenerationJob
        fields = [
            'classroom',
            'pdf_file',
            'topic',
            'prompt',
            'requested_count',
            'default_timer_seconds',
        ]
        widgets = {
            'classroom': forms.Select(attrs={
                'class': 'form-select'
            }),
            'pdf_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'application/pdf'
            }),
            'topic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: فصل دوم - متغیرها و حلقه‌ها'
            }),
            'prompt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'مثال: از مبحث مشخص‌شده، سوالات چهارگزینه‌ای مفهومی و در سطح کتاب طراحی کن. از طرح سوال خارج از مبحث خودداری کن.'
            }),
            'requested_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
            'default_timer_seconds': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 30,
                'max': 3600
            }),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        if teacher is not None:
            self.fields['classroom'].queryset = Classroom.objects.filter(
                teacher=teacher
            ).order_by('name')
        else:
            self.fields['classroom'].queryset = Classroom.objects.none()

        self.fields['classroom'].empty_label = 'یک کلاس انتخاب کنید'
        self.fields['pdf_file'].help_text = 'فقط فایل PDF، حداکثر ۲۰ مگابایت'
        self.fields['requested_count'].help_text = 'بین ۱ تا ۲۰ سوال'
        self.fields['default_timer_seconds'].help_text = 'زمان پاسخ هر سوال به ثانیه؛ پیش‌فرض ۳۰۰ ثانیه معادل ۵ دقیقه'

    def clean_requested_count(self):
        count = self.cleaned_data.get('requested_count')

        if count is None:
            raise forms.ValidationError('تعداد سوال الزامی است.')

        if count < 1 or count > 20:
            raise forms.ValidationError('تعداد سوال باید بین ۱ تا ۲۰ باشد.')

        return count

    def clean_default_timer_seconds(self):
        timer = self.cleaned_data.get('default_timer_seconds')

        if timer is None:
            raise forms.ValidationError('زمان پاسخ سوال الزامی است.')

        if timer < 30 or timer > 3600:
            raise forms.ValidationError('زمان پاسخ هر سوال باید بین ۳۰ ثانیه تا ۳۶۰۰ ثانیه باشد.')

        return timer


class QuestionForm(forms.ModelForm):
    """
    فرم ساخت / ویرایش سوال دستی یا ویرایش سوال هوش مصنوعی
    """

    class Meta:
        model = Question
        fields = [
            'classroom',
            'session',
            'topic',
            'text',
            'choice_a',
            'choice_b',
            'choice_c',
            'choice_d',
            'correct_answer',
            'timer_seconds',
        ]
        widgets = {
            'classroom': forms.Select(attrs={
                'class': 'form-select'
            }),
            'session': forms.Select(attrs={
                'class': 'form-select'
            }),
            'topic': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثال: فصل اول'
            }),
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'متن سوال را وارد کنید'
            }),
            'choice_a': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'گزینه الف'
            }),
            'choice_b': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'گزینه ب'
            }),
            'choice_c': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'گزینه ج'
            }),
            'choice_d': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'گزینه د'
            }),
            'correct_answer': forms.Select(attrs={
                'class': 'form-select'
            }),
            'timer_seconds': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 10,
                'max': 7200
            }),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)

        if teacher is not None:
            self.fields['classroom'].queryset = Classroom.objects.filter(
                teacher=teacher
            ).order_by('name')

            self.fields['session'].queryset = ClassSession.objects.filter(
                classroom__teacher=teacher
            ).order_by('-session_date')
        else:
            self.fields['classroom'].queryset = Classroom.objects.none()
            self.fields['session'].queryset = ClassSession.objects.none()

        self.fields['classroom'].empty_label = 'یک کلاس انتخاب کنید'
        self.fields['session'].empty_label = 'بدون جلسه (ذخیره در بانک سوال)'
        self.fields['timer_seconds'].help_text = 'زمان پاسخ دانش‌آموز به ثانیه'

    def clean_session(self):
        session = self.cleaned_data.get('session')
        classroom = self.cleaned_data.get('classroom')

        if session and classroom and session.classroom != classroom:
            raise forms.ValidationError('جلسه انتخاب‌شده باید متعلق به کلاس انتخاب‌شده باشد.')

        return session

    def clean_timer_seconds(self):
        timer = self.cleaned_data.get('timer_seconds')

        if timer is None:
            raise forms.ValidationError('زمان پاسخ سوال الزامی است.')

        if timer < 10 or timer > 7200:
            raise forms.ValidationError('زمان پاسخ سوال باید بین ۱۰ ثانیه تا ۷۲۰۰ ثانیه باشد.')

        return timer