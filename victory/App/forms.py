# forms.py
from django import forms
from django.contrib.auth.models import User
from django.forms.widgets import DateInput
from .models import Parent, Child, ChildProfile, Coach,PlayerAssessment
from django.db import models
# ------------------------ User Form ------------------------
class UserForm(forms.ModelForm):
    # Password input field with hiding capability
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'username': forms.TextInput(attrs={'id': 'username'}),
        }


# ------------------------ Parent Form ------------------------
class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ['full_name', 'phone']


# ------------------------ Child Basic Details Form ------------------------
class ChildForm(forms.ModelForm):
    class Meta:
        model = Child
        fields = ['name', 'gender', 'dob', 'school', 'place', 'profile_image']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),  # Date picker for DOB
        }


# ------------------------ Child Profile Form ------------------------
class ChildProfileForm(forms.ModelForm):
    class Meta:
        model = ChildProfile
        fields = [
            'preferred_position',
            'playing_background',
            'height_cm',
            'weight_kg',
            'medical_issues',
            'consent_signed',
        ]
        widgets = {
            'preferred_position': forms.Select(attrs={'class': 'form-control'}),  # changed here
            'playing_background': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control'}),
            'medical_issues': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'consent_signed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }



# ------------------------ Coach Registration Form ------------------------
class CoachRegistrationForm(forms.ModelForm):
    # Custom fields not in the Coach model
    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Create a username'})
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a password'}),
        required=True
    )

    date_of_birth = forms.DateField(
        widget=DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': 'Select your date of birth'
        }),
        input_formats=['%Y-%m-%d']
    )

    GENDER_CHOICES = [
        ('', 'Select Gender'),
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=True)

    declaration = forms.BooleanField(
        required=True,
        label="I hereby declare that the information provided is true and correct."
    )

    class Meta:
        model = Coach
        exclude = ['user', 'is_approved', 'date_registered']



class PlayerAssessmentForm(forms.ModelForm):
    POSITION_CHOICES = [
        ('', 'Select Position'),  # optional default
        ('Forward', 'Forward'),
        ('Midfielder', 'Midfielder'),
        ('Defender', 'Defender'),
        ('Goalkeeper', 'Goalkeeper'),
    ]

    position = forms.ChoiceField(choices=POSITION_CHOICES)

    class Meta:
        model = PlayerAssessment
        exclude = ['child', 'coach', 'date']
        widgets = {
            field.name: forms.Select(choices=[(i, i) for i in range(1, 6)])
            for field in PlayerAssessment._meta.fields
            if isinstance(field, models.IntegerField)
        }
