# reviews/forms.py
from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={'placeholder': 'Brief summary of your review'}),
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Share your thoughts about this book...'})
        }