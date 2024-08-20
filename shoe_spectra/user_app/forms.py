from django import forms
from admin_app.models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'phone_number',
            'address_line1',
            'city',
            'state',
            'country',
            'postal_code',
            # 'date_of_birth',
            'gender',
        ]
        widgets = {
            # 'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.Select(choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]),
        }
