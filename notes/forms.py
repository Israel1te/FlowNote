from os import name

from .models import *

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from ckeditor.widgets import CKEditorWidget
from django.core.exceptions import ValidationError

class NoteGroupForm(forms.ModelForm):
    notes = forms.ModelMultipleChoiceField(
        queryset=Note.objects.all(), 
        required=False, 
        widget=forms.CheckboxSelectMultiple, 
        label='Notes'
    )

    class Meta:
        model = NoteGroup
        fields = ['title', 'description', 'notes']

    def __init__(self, *args, **kwargs):
        super(NoteGroupForm, self).__init__(*args, **kwargs)

    def clean_title(self):
        title = self.cleaned_data['title']
        # Validation logic
        # if not title.isalnum():
        #     raise ValidationError('Title should only contain letters and numbers.')
        return title

    def save(self, commit=True):
        instance = super(NoteGroupForm, self).save(commit=False)
        
        if commit:
            instance.save()
            self.save_m2m()  
        
        return instance

class NoteGroupAssignmentForm(forms.Form):
    note = forms.ModelChoiceField(queryset=Note.objects.all(), required=True, label='Note')
    groups = forms.ModelMultipleChoiceField(queryset=NoteGroup.objects.all(), required=False, label='Groups', widget=forms.CheckboxSelectMultiple)


class NoteForm(forms.ModelForm):
    content = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Note
        fields = ['title', 'content','summary']  # TO-DO: Add more fields here, such as 'tags' and 'is_favorite'.
        labels = {
            'title': '',
            'content': '',
            'summary': '',
        }
        placeholders = {
            'title': 'Enter title',
            'content': 'Enter content',
            'summary': 'Enter summary',
        }

    def __init__(self, *args, **kwargs):
        super(NoteForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            if field in self.Meta.placeholders:
                self.fields[field].widget.attrs['placeholder'] = self.Meta.placeholders[field]

class RegisterForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)
    email = forms.EmailField(required=False)  

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_password2(self):
        
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

class UserSettingsForm(forms.ModelForm):
    theme = forms.ChoiceField(choices=(('light', 'Light'), ('dark', 'Dark')), required=True)

    class Meta:
        model = UserProfile
        fields = ['theme']

class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)

class UpdateUsernameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username']

class ChangePasswordForm(PasswordChangeForm):   
    def __init__(self, *args, **kwargs):
        super(ChangePasswordForm, self).__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs['placeholder'] = 'Old Password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New Password'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm New Password'

class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ['max_length', 'num_return_sequences', 'additional_tokens']