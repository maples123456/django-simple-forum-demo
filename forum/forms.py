from django import forms

from .models import Post, Reply


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('title', 'content')
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': '写一个清晰的标题'}),
            'content': forms.Textarea(attrs={'rows': 8, 'placeholder': '分享你的想法…'}),
        }


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Reply
        fields = ('content',)
        widgets = {'content': forms.Textarea(attrs={'rows': 4, 'placeholder': '写下你的回复…'})}
