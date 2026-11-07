from django import forms
from django.core.files.uploadedfile import UploadedFile

from .models import (
    ADMIN_STUDENT_ID, COLLEGE_CHOICES, Account, ConcernReply, StudentConcern,
)

MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'GIF', 'WEBP'}


def clean_name(value):
    return ' '.join((value or '').split())


class LoginForm(forms.Form):
    role = forms.ChoiceField(
        choices=Account.ROLE_CHOICES, widget=forms.HiddenInput(attrs={'id': 'login-role'})
    )
    Fullname = forms.CharField(
        max_length=100, required=False, label='Full Name',
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Juan Dela Cruz', 'autocomplete': 'off'}),
    )
    StudentID = forms.IntegerField(
        min_value=0, max_value=9999999, required=False, label='Student ID',
        widget=forms.NumberInput(attrs={'placeholder': 'Up to 7 digits', 'autocomplete': 'off'}),
    )
    College = forms.ChoiceField(
        required=False,
        choices=[('', 'Select your college')] + COLLEGE_CHOICES,
    )

    def clean(self):
        data = super().clean()
        role = data.get('role')
        if not role:
            return data
        data['Fullname'] = clean_name(data.get('Fullname'))
        if not data['Fullname']:
            self.add_error('Fullname', 'Enter your full name.')
        if role in (Account.ROLE_STUDENT, Account.ROLE_ADMIN) and data.get('StudentID') is None:
            if 'StudentID' not in self.errors:
                self.add_error('StudentID', 'Enter your Student ID.')
        if role == Account.ROLE_STAFF and not data.get('College'):
            if 'College' not in self.errors:
                self.add_error('College', 'Select your college.')
        return data


class EvidenceMixin:
    def clean_evidence(self):
        image = self.cleaned_data.get('evidence')
        if isinstance(image, UploadedFile):
            if image.size > MAX_EVIDENCE_BYTES:
                raise forms.ValidationError('Image must be 5 MB or smaller.')
            fmt = getattr(getattr(image, 'image', None), 'format', None)
            if fmt not in ALLOWED_IMAGE_FORMATS:
                raise forms.ValidationError('Upload a JPG, PNG, GIF or WEBP image.')
        return image


class ConcernForm(EvidenceMixin, forms.ModelForm):
    full_fields = ('College', 'Concern', 'evidence')

    class Meta:
        model = StudentConcern
        fields = ['College', 'category', 'priority', 'Concern', 'evidence']
        labels = {
            'category': 'Category',
            'priority': 'Priority',
            'evidence': 'Evidence (optional image)',
        }
        widgets = {
            'Concern': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Describe your concern', 'data-counter': 'true'}),
            'evidence': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/gif,image/webp'}),
        }

    def __init__(self, *args, with_college=False, **kwargs):
        super().__init__(*args, **kwargs)
        if with_college:
            self.fields['College'].choices = [('', 'Select a college')] + list(COLLEGE_CHOICES)
        else:
            del self.fields['College']
        self.fields['category'].choices = [('', 'Select a category')] + list(StudentConcern.CATEGORY_CHOICES)
        self.fields['evidence'].required = False


class ConcernAdminForm(EvidenceMixin, forms.ModelForm):
    full_fields = ('College', 'status', 'Concern', 'evidence')

    class Meta:
        model = StudentConcern
        fields = ['Fullname', 'StudentID', 'College', 'category', 'priority', 'status', 'Concern', 'evidence']
        labels = {
            'Fullname': 'Full Name',
            'StudentID': 'Student ID',
            'category': 'Category',
            'priority': 'Priority',
            'status': 'Status',
            'evidence': 'Evidence (optional image)',
        }
        widgets = {
            'Fullname': forms.TextInput(attrs={'placeholder': 'e.g. Juan Dela Cruz'}),
            'StudentID': forms.NumberInput(attrs={'placeholder': 'Up to 7 digits', 'min': 0, 'max': 9999999}),
            'Concern': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Describe the concern', 'data-counter': 'true'}),
            'evidence': forms.FileInput(attrs={'accept': 'image/jpeg,image/png,image/gif,image/webp'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['College'].choices = [('', 'Select a college')] + list(COLLEGE_CHOICES)
        self.fields['evidence'].required = False


class StatusForm(forms.ModelForm):
    class Meta:
        model = StudentConcern
        fields = ['status']
        labels = {'status': 'Status'}


class ReplyForm(forms.ModelForm):
    class Meta:
        model = ConcernReply
        fields = ['kind', 'message']
        labels = {'kind': 'Type', 'message': 'Message'}
        widgets = {
            'message': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your feedback or report on the action taken', 'data-counter': 'true'}),
        }


class AccountForm(forms.ModelForm):
    full_fields = ('role', 'Fullname')

    class Meta:
        model = Account
        fields = ['role', 'Fullname', 'StudentID', 'College']
        labels = {
            'role': 'Account Type',
            'Fullname': 'Full Name',
            'StudentID': 'Student ID',
        }
        widgets = {
            'Fullname': forms.TextInput(attrs={'placeholder': 'e.g. Juan Dela Cruz'}),
            'StudentID': forms.NumberInput(attrs={'placeholder': 'Up to 7 digits', 'min': 0, 'max': 9999999}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].choices = [
            (Account.ROLE_STUDENT, 'Student'),
            (Account.ROLE_STAFF, 'Staff'),
        ]
        self.fields['College'].choices = [('', 'Select a college')] + list(COLLEGE_CHOICES)

    def clean(self):
        data = super().clean()
        role = data.get('role')
        name = clean_name(data.get('Fullname'))
        data['Fullname'] = name
        college = data.get('College')
        others = Account.objects.exclude(pk=self.instance.pk)
        if role == Account.ROLE_STUDENT:
            student_id = data.get('StudentID')
            if student_id is None:
                if 'StudentID' not in self.errors:
                    self.add_error('StudentID', 'Student ID is required for students.')
            elif student_id == ADMIN_STUDENT_ID or others.filter(role=Account.ROLE_STUDENT, StudentID=student_id).exists():
                self.add_error('StudentID', 'This Student ID is already registered.')
            if not college:
                self.add_error('College', 'Select a college.')
        elif role == Account.ROLE_STAFF:
            data['StudentID'] = None
            if not college:
                self.add_error('College', 'Select a college.')
            elif name and others.filter(role=Account.ROLE_STAFF, College=college, Fullname__iexact=name).exists():
                self.add_error('Fullname', 'This staff member is already registered under that college.')
        return data
