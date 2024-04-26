# from .serializers import NoteSerializer, BlogPostSerializer
# from rest_framework import viewsets
import json
import os
from typing import Dict
import openai
import logging

from AIEngine.analyze import analyze
from AIEngine.tasks import *

from .forms import *
from .models import *

from django.urls import reverse, reverse_lazy
from django.shortcuts import *   # render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q      # For complex queries (search feature)
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, UpdateView, DeleteView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from celery.result import AsyncResult
from .ai import generate_response

openai.api_key = os.getenv('OPENAI_API_KEY')

def generate_summary(request, note_id):
    if request.method == "POST":
        
        summary = generate_summary_task(note_id)  
        return JsonResponse({'summary': summary})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)

""" Async Task Status Views """
def task_status(request, task_id):
    task = AsyncResult(task_id)
    if task.state == 'SUCCESS' or task.ready():
        return JsonResponse({'status': task.status, 'result': task.get()})
    else:
        return JsonResponse({'status': task.status})

def process_feedback(request, note_id):
    
    feedback = {
        # get model output the rating was based on (keywords, summary, etc.)
        'content': get_object_or_404(Note, pk=note_id).content,
        'rating': request.POST.get('rating', False),
        'module': request.POST.get('module', '')
    }
    
    # run_feedback_pipeline(feedback)
    
    return JsonResponse({'success': True})

""" AI, ML Views """
def generate_flashcards(request, note_id):
    if request.method == 'POST':
        note = get_object_or_404(Note, pk=note_id)  
        logging.info(f'Generating Flashcards for Note: {note.title}')
        #result: dict[str, str] = generate_flashcards_task(note_id)
        
        if note.content: #make sure it is not empty
            response = generate_response("Provide terms and their definitions in JSON Format (dict[str, str]) for the provided text: " + note.content)
            logging.info(f'Generated Flashcards Response: {response}')
            try:
                flashcards = json.loads(response) 
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid response format'}, status=500)

            logging.info(f'Generated Flashcards: {flashcards}\n')
            return JsonResponse(flashcards)
        
        return JsonResponse({'error': 'Invalid request'}, status=405)
    else:
        return JsonResponse({'error': 'Invalid request'}, status=405)

def autocomplete_view(request):
    if request.method == 'GET':
        logging.info('Autocomplete Request Received.')
        text = request.GET.get('text', '')
        note_id = request.GET.get('noteId', None)
        suggestions = get_autocomplete_suggestions(note_id, text) 
        
        resLog = ' \n'.join(suggestions)
        logging.info(f'AUTOCOMPLETE RESPONSE: {resLog}\n')
        return JsonResponse({'suggestions': suggestions})
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def generate_content_view(request, note_id):
    if request.method == 'POST':
        note = get_object_or_404(Note, pk=note_id)
        prompt = request.POST.get('prompt', '')
        
        generated_content = generate_content_task(note.content, prompt)
        return JsonResponse({'generated_content': generated_content})
        
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

def auto_group_note_view(request, note_id):
    if request.method == "POST":
        messages.info(request, 'Auto-grouping for this note has been initiated.')

        new_group = auto_group_note(note_id)
        
        if new_group:
            logging.debug(f"Auto Grouping for note {note_id} successful. Group: {new_group}")
            # Display a success message / notification to the user.

        return redirect('notes:note_detail', pk=note_id)  
    else:
        note = get_object_or_404(Note, pk=note_id)
        return render(request, 'notes/auto_group_note.html', {'note': note})

def auto_group_all_view(request):
    if request.method == "POST"and request.user.is_authenticated:
        messages.info(request, 'Auto-grouping for all notes has been initiated.')

        new_groups = auto_group_all(owner=request.user)
        
        if new_groups:
            logging.debug(f"Auto Grouping for all notes successful. Created {new_groups.count} new groups: {new_groups}")
            
        return redirect('notes:group_list') 
    return render(request, 'notes/auto_group_all.html')

def generate_response_from_prompt(request):
    if request.method == 'GET':
        prompt = request.GET.get('prompt')
        if prompt: #make sure it is not empty
            response = generate_response(prompt)
            return JsonResponse({'response': response})
    return JsonResponse({'error': 'Invalid request'}, status=400) #more error handling

""" Toggle Pin """

@require_POST
def toggle_pin(request, pk):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        note = get_object_or_404(Note, pk=pk)
        note.pinned = not note.pinned
        note.save()
        return JsonResponse({'pinned': note.pinned})
    else:
        return redirect('notes:note_list')  # Update 'notes:note_list' to your actual note listing page's URL name if different


""" Group Views """

class GroupSearchView(ListView):
    model = NoteGroup
    template_name = 'group_search.html'
    context_object_name = 'groups'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            # SEARCH BY TITLE
            return NoteGroup.objects.filter(Q(title__icontains=query), owner=self.request.user)
        else:
            return NoteGroup.objects.filter(owner=self.request.user)

def note_remove_from_group(request, group_id, note_id):
    group = get_object_or_404(NoteGroup, id=group_id)
    note = get_object_or_404(Note, id=note_id)
    note.groups.remove(group)  
    return redirect('notes:group_detail', pk=group_id)
       
def group_edit(request, pk=None):
    group = get_object_or_404(NoteGroup, pk=pk) if pk else None
    if request.method == 'POST':
        form = NoteGroupForm(request.POST, instance=group)
        if form.is_valid():
            group = form.save()  
            return redirect('notes:group_detail', pk=group.pk)
    else:
        form = NoteGroupForm(instance=group)
        note_ids = list(group.notes.values_list('id', flat=True)) if group else []

    return render(request, 'group/group_form.html', {'form': form, 'note_ids': note_ids})
                  
def group_delete(request, pk):
    group = get_object_or_404(NoteGroup, pk=pk)
    if request.method == 'POST':
        group.delete()
        return redirect('notes:group_list')
    return render(request, 'group/group_delete.html', {'group': group})

def group_detail(request, pk):
    group = get_object_or_404(NoteGroup, pk=pk)
    notes = group.notes.all()  
    
    # FILTER BY TITLE
    title_query = request.GET.get('title')
    if title_query:
        notes = notes.filter(title__icontains=title_query)  

    # FILTER BY DATE
    date_query = request.GET.get('date')
    if date_query:
        notes = notes.filter(created_at__date=date_query)
        
    return render(request, 'group/group_detail.html', {'group': group, 'notes': notes})

def group_create(request):
    if request.method == 'POST':
        form = NoteGroupForm(request.POST)
        if form.is_valid():
            new_group = form.save(commit=False)
            new_group.owner = request.user
            new_group.save()
            return redirect('notes:group_list')
    else:
        form = NoteGroupForm()
    return render(request, 'group/group_form.html', {'form': form})

def group_list(request):
    groups = NoteGroup.objects.all()  
    return render(request, 'group/group_list.html', {'groups': groups})

def about(request):
    return render(request, 'about.html')

""" User Auth Views """
@login_required
def profile(request):
    return render(request, 'profile.html', {'user': request.user})

def update_theme(request):
    if request.method == 'POST':
        theme = request.POST.get('theme')
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        user_profile.theme = theme
        user_profile.save()
    return redirect('notes:profile')

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('notes:login')
    else:
        form = RegisterForm()  
    return render(request, 'registration/register.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(reverse('home'))  # TO-DO: Redirect to success page, or add a success message
        else:
            print('Invalid login') # TO-DO: Add error message, session handling logic
    
    # else: method is GET        
    return render(request, 'registration/login.html')  

def user_logout(request):
    logout(request)
    return redirect('home')  # TO-DO: Redirect to success page, or add a success message

@login_required
def update_username(request):
    if request.method == 'POST':
        form = UpdateUsernameForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('notes:profile')
    else:
        form = UpdateUsernameForm(instance=request.user)
    return render(request, 'update_username.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            return redirect('notes:profile')
    else:
        form = ChangePasswordForm(request.user)
    return render(request, 'change_password.html', {'form': form})

def home(request):
    return render(request, 'home.html')  

""" Note Views """
@login_required
def create_note(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            new_note = form.save(commit=False)
            new_note.owner = request.user  
            new_note.save()
            return redirect('notes:note_list')
    else:
        form = NoteForm()
    return render(request, 'note_form.html', {'form': form})

class NoteSearchView(ListView):
    model = Note
    template_name = 'note_search.html'
    context_object_name = 'notes'

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Note.objects.filter(Q(title__icontains=query) | Q(content__icontains=query), owner=self.request.user)
        else:
            return Note.objects.filter(owner=self.request.user)

class NoteListView(ListView):
    model = Note
    template_name = 'note_list.html'  
    context_object_name = 'notes'

class NoteDetailView(DetailView):
    model = Note
    template_name = 'note_detail.html'  

class NoteDeleteView(DeleteView):
    model = Note
    template_name = 'note_delete.html'
    success_url = reverse_lazy('notes:note_list') 

class NoteUpdateView(UpdateView):
    model = Note
    form_class = NoteForm
    template_name = 'note_update.html'
    
    def get_success_url(self):
        pk = self.object.pk
        return reverse('notes:note_detail', kwargs={'pk': pk})

""" Contact """
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            # Send email to your support team
            send_mail(
                subject,
                f'Name: {name}\nEmail: {email}\n\n{message}',
                email,
                [django_settings.SUPPORT_EMAIL],
                fail_silently=False,
            )
            
            # Redirect to a success page
            return redirect('home')
    else:
        form = ContactForm()
    
    return render(request, 'contact.html', {'form': form})

@login_required
def update_preferences(request):
    if request.method == 'POST':
        form = UserPreferenceForm(request.POST, instance=request.user.userpreference)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your preferences have been updated.')
            return redirect('notes:profile')
        else:
            messages.error(request, 'Please correct the error below.')
    else:
        form = UserPreferenceForm(instance=request.user.userpreference)

    return render(request, 'profile.html', {'form': form})