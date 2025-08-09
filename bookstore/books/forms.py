# books/forms.py
from django import forms
from django.utils.text import slugify
from .models import Book, Category, Author, Publisher

class BookForm(forms.ModelForm):
    authors = forms.CharField(
        max_length=500,
        help_text="Enter author names separated by commas",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Book
        fields = [
            'title', 'authors', 'publisher', 'isbn', 'isbn13', 'category',
            'subcategory', 'description', 'short_description', 'format',
            'pages', 'language', 'price', 'original_price', 'cover_image',
            'publication_date', 'edition', 'weight', 'dimensions',
            'is_featured', 'is_bestseller', 'is_on_sale'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'publisher': forms.Select(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn13': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'subcategory': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'short_description': forms.TextInput(attrs={'class': 'form-control'}),
            'format': forms.Select(attrs={'class': 'form-control'}),
            'pages': forms.NumberInput(attrs={'class': 'form-control'}),
            'language': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'original_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control'}),
            'publication_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'edition': forms.TextInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_bestseller': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_on_sale': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields optional for manual entry
        self.fields['publisher'].required = False
        self.fields['isbn'].required = False
        self.fields['isbn13'].required = False
        self.fields['subcategory'].required = False
        self.fields['short_description'].required = False
        self.fields['pages'].required = False
        self.fields['original_price'].required = False
        self.fields['publication_date'].required = False
        self.fields['edition'].required = False
        self.fields['weight'].required = False
        self.fields['dimensions'].required = False
    
    def save(self, commit=True):
        book = super().save(commit=False)
        
        # Generate slug if not provided
        if not book.slug:
            book.slug = slugify(book.title)
        
        if commit:
            book.save()
            
            # Handle authors
            authors_string = self.cleaned_data.get('authors', '')
            if authors_string:
                author_names = [name.strip() for name in authors_string.split(',') if name.strip()]
                authors = []
                for author_name in author_names:
                    author, created = Author.objects.get_or_create(name=author_name)
                    authors.append(author)
                book.authors.set(authors)
        
        return book

class BookFilterForm(forms.Form):
    search = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search books...'
        })
    )
    
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    authors = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Author name...'
        })
    )
    
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    
    AVAILABILITY_CHOICES = [
        ('', 'All'),
        ('in_stock', 'In Stock'),
        ('out_of_stock', 'Out of Stock'),
    ]
    
    availability = forms.ChoiceField(
        choices=AVAILABILITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    SORT_CHOICES = [
        ('', 'Default'),
        ('price_low', 'Price: Low to High'),
        ('price_high', 'Price: High to Low'),
        ('newest', 'Newest First'),
        ('title', 'Title A-Z'),
    ]
    
    sort_by = forms.ChoiceField(
        choices=SORT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )