import logging
from typing import List, Optional
from typing_extensions import deprecated
from celery import shared_task
from django.core.cache import cache

from notes.models import Note

from .utils import *
from .analyze import *
from .config import model, tokenizer

import logging

""" Content Generation Tasks"""

def generate_keywords_task(note_id):
    note = Note.objects.get(pk=note_id)
    
    if note.updated_at < cache.get(f"keywords_{note_id}_timestamp", note.updated_at):
        logging.info("Keywords already up-to-date.")
        return note.keywords
    
    cache.set(f"keywords_{note_id}_timestamp", note.updated_at, None)
    
    note_content = strip_html_tags(note.content)
    preprocessed_content = get_preprocessed_content(note)
    
    tokens = tokenizer.tokenize(note_content + str(preprocessed_content))
    
    if len(tokens) > 1024:
        logging.warning("Content exceeds token limit. Truncating content...")
        tokens = tokens[:1024]
        
    keywords = generate_keywords(note_content, preprocessed_content)
    
    note.keywords = keywords
    note.save()

    return keywords

def generate_summary_task(note_id):
    note = Note.objects.get(pk=note_id)
    
    if note.updated_at < cache.get(f"summary_{note_id}_timestamp", note.updated_at):
        logging.info("Summary already up-to-date.")
        return note.summary
    
    cache.set(f"summary_{note_id}_timestamp", note.updated_at, None)
    
    note_content = strip_html_tags(note.content)
    
    # No need to preprocess content for summary generation
    # preprocessed_content = get_preprocessed_content(note)
    
    summary = generate_summary(note_content)
    
    logging.info(f"Generated summary: {summary}\n\n")
    
    note.summary = summary
    note.save()

    return summary

def generate_content_task(prompt, content):
    
    # TO-DO: Add check for empty content here
    input_text = f"{content}\n{prompt}"
    input_text = strip_html_tags(input_text)
    
    # TO-DO: Allow users to specify parameter (max_length, num_return_sequences) size in their settings. Use Slider? 
    max_length=150
    num_return_sequences=1
    additional_tokens=500
    
    suggestions = generate_content(input_text, max_length, num_return_sequences, additional_tokens)
    
    return suggestions

def generate_flashcards_task(note_id) -> dict[str, str]:
    note = Note.objects.get(id=note_id)
    
    keywords: dict = generate_keywords_task(note_id)
    num_keywords = len(keywords)
    logging.info(f"Generating flashcards for note {note_id}...\nNumber of keywords: {num_keywords}\nKeywords: {keywords}\n\n")
    
    for keyword, definition in keywords.items():
        if not definition:
            definition = generate_definition(keyword)
            keywords[keyword] = definition  
    
    note.keywords = keywords
    note.save()
    
    logging.info(f"Generated flashcards for note {note_id}.\n\n")
    
    return [{'term': k, 'definition': v} for k, v in keywords.items()]

def get_autocomplete_suggestions(note_id, content):
    
    content = strip_html_tags(content.strip())
    logging.info(f"Getting autocomplete suggestions...\n\n")
    
    if not content.strip().endswith(('.', '?', '!')):
        content = content.strip() + ' '

    content = f"Continue the following text: {content}"
    
    inputs = tokenizer.encode(content, return_tensors='pt', add_special_tokens=True)
    attention_mask = inputs.ne(tokenizer.pad_token_id).int()
    
    outputs = model.generate(
        input_ids=inputs,
        attention_mask=attention_mask,
        max_length=inputs.shape[-1] + 50, 
        num_return_sequences=3,
        do_sample=True,
        temperature=0.7,  
        top_k=50,  
        top_p=0.9,  
        pad_token_id=tokenizer.eos_token_id,
    )
    
    suggestions = [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]
    
    completions = [s[len(content):].strip() for s in suggestions]

    return completions

""" Auto Grouping Tasks"""

def auto_group_note(note_id: int, threshold: float = 0.15) -> Optional[NoteGroup]:
    try:
        target_note: Note = Note.objects.get(pk=note_id)
        other_notes: List[Note] = list(Note.objects.exclude(pk=note_id))

        target_content = ' '.join(preprocess_group_content(target_note)).lower()        
        other_contents = [' '.join(preprocess_group_content(note)).lower() for note in other_notes]
        
        contents: List[str] = [target_content] + other_contents
        sim_matrix: Optional[np.ndarray] = compute_similarity_matrix(contents)

        if sim_matrix is None:  # Fallback if similarity matrix fails
            preprocessed_list: List[str] = [note.content.lower() for note in [target_note] + other_notes]
            sim_matrix = compute_similarity_matrix(preprocessed_list)
            if sim_matrix is None:
                logging.error("Both attempts to compute the similarity matrix failed.")
                raise ValueError("Failed to compute similarity matrix on both attempts.")

        similarities: np.ndarray = sim_matrix[0, 1:]


        group_title: str = generate_group_title(" ".join(contents))
        group: Optional[NoteGroup] = group_note(target_note, other_notes, similarities, threshold, group_title)

        return group
     
    except ValueError as ve:
        logging.error("ValueError in auto_group_note: %s", ve)
        return None
    
    except Exception as e:
        logging.error("Exception in auto_group_note: %s", e)
        return None

def auto_group_all(threshold=0.15, owner=None) -> list[NoteGroup]:
    """
    Group all notes based on overall similarity.
    """
    try:
        notes = Note.objects.all().order_by('id')
        preprocessed_list = [str(preprocess_group_content(note)).lower() for note in notes]

        sim_matrix = compute_similarity_matrix(preprocessed_list)
        
        if sim_matrix is None:  # Fallback if similarity matrix fails
            
            preprocessed_list = [note.content.lower() for note in notes]  
            sim_matrix = compute_similarity_matrix(preprocessed_list)
            if sim_matrix is None:
                raise ValueError("Failed to compute similarity matrix on second attempt")

        if isinstance(sim_matrix, np.ndarray):
            sim_matrix = sim_matrix.astype(int)  # Converts dtype to native Python int 
        
        all_groups = group_all_notes(notes, sim_matrix, threshold, owner=owner)
        
    except Exception as e:
        logging.error(f"An error occurred while grouping all notes: {str(e)}")
        all_groups = []

    return all_groups

def generate_group_title(contents):
    
    prompt = "Generate a meaningful title for this group of notes based on their contents: " + ' '.join(contents)
    title = generate_content(prompt, num_return_sequences=1)[0]
    title = strip_prompt(prompt, title)
    
    return title.strip()

@deprecated("This method is deprecated.")
@shared_task
def analyze_note_task(note_id):
    note = Note.objects.get(pk=note_id)
    
    # Check cache
    if note.updated_at < cache.get(f"analysis_{note_id}_timestamp", note.updated_at):
        logging.info("Analysis already up-to-date.")
        return note.analysis
    
    cache.set(f"analysis_{note_id}_timestamp", note.updated_at, None)
    
    # Pre-process and strip HTML tags
    note_content = strip_html_tags(note.content)
    preprocessed_content = get_preprocessed_content(note_content)
    
    # Analyze note
    results = analyze(note_content, preprocessed_content)
    
    # Save analysis to Note model
    note.analysis = results
    note.save()

    return results

