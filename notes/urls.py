from django.urls import path
from .views import *
from django.contrib.auth import views as auth_views

app_name = 'notes' 

urlpatterns = [
    
    path('', home, name='home'),
    # .as_view() is used to convert the class-based view into a function-based view. See views.py for the difference between the two.
    
    # CRUD URLs
    path('list/', NoteListView.as_view(), name='note_list'), 
    path('<int:pk>/', NoteDetailView.as_view(), name='note_detail'),  
    path('create/', create_note, name='create_note'),
    path('<int:pk>/delete/', NoteDeleteView.as_view(), name='note_delete'),
    path('<int:pk>/update/', NoteUpdateView.as_view(), name='note_update'),

    # Task Status URL
    path('task-status/<str:task_id>/', task_status, name='task-status'),
    
    # Trained GPT-2 Model URLs
    path('autocomplete', autocomplete_view, name='autocomplete'),
    path('generate-flashcards/<int:note_id>/', generate_flashcards, name='generate-flashcards'),
    path('generate-content/<int:note_id>/', generate_content_view, name='generate-content'),    
    path('generate_summary/<int:note_id>/', generate_summary, name='generate_summary'),
    
    # AI Assistant URL
    path('generate-response/', generate_response_from_prompt, name='generate-response'),

    # Group URLs
    # Auto Grouping
    path('notes/<int:note_id>/auto-group/', auto_group_note_view, name='auto_group_note'),
    path('notes/auto-group-all/', auto_group_all_view, name='auto_group_all'),
    
    # User Grouping
    path('note-groups/', group_list, name='group_list'),
    path('note-groups/<int:pk>/', group_detail, name='group_detail'),
    path('note-groups/create/', group_create, name='group_create'),
    path('note-groups/<int:pk>/edit/', group_edit, name='group_edit'),
    path('note-groups/<int:pk>/delete/', group_delete, name='group_delete'),
    path('note-groups/search', GroupSearchView.as_view(), name='group_search'),
    path('note-groups/<int:group_id>/remove-note/<int:note_id>/', note_remove_from_group, name='note_remove_from_group'),
    
    # Registration/User Profile URLs
    path('register/', register, name='register'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/profile/', profile, name='profile'),
    path('accounts/profile/update-theme/', update_theme, name='update_theme'),
    path('contact/', contact, name='contact'),
    path('about/', about, name='about'),
    path('update-username/', update_username, name='update_username'),
    path('change-password/', change_password, name='change_password'),
    path('update_preferences/', update_preferences, name='update_preferences'),

    # Search URLs
    path('search/', NoteSearchView.as_view(), name='note_search'),

    
]