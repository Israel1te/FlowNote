from notes.models import Note, NoteGroup

from .utils import *
from .config import model, tokenizer

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import torch
import numpy as np

from datetime import datetime as dt
from datetime import datetime as dt
import logging

def generate_content(prompt, num_return_sequences=1, additional_tokens=500, temperature=0.8, top_k=50, top_p=0.92):
    
    # inputs = tokenizer.encode_plus(input_text, return_tensors='pt', add_special_tokens=True, max_length=512, truncation=True)
    encoding = tokenizer(prompt, return_tensors='pt', truncation=True)
    input_ids = encoding['input_ids']
    attention_mask = encoding['attention_mask']

    total_max_length = input_ids.shape[1] + additional_tokens

    with torch.no_grad():
        generated_ids = model.generate(
            
            input_ids=input_ids,
            attention_mask=attention_mask,
            
            # max_new_tokens=100, 
            max_length=total_max_length,
            min_length=input_ids.shape[1] + 20,  
            no_repeat_ngram_size=3,  
            num_return_sequences=num_return_sequences,
            
            temperature=temperature, 
            top_k=top_k,
            top_p=top_p,
            
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )

    # content = tokenizer.decode(outputs[0], skip_special_tokens=True)
    suggestions = [tokenizer.decode(generated_id, skip_special_tokens=True) for generated_id in generated_ids]
    return suggestions

""" Analysis Methods (Summary, Keywords)"""

def analyze(content, processed_content):
    
    keywords = generate_keywords(content, processed_content)
    summary = generate_summary(content)
    return {
        "keywords": keywords,
        "summary": summary
    }

def generate_definition(keyword):
    
    definition = generate_content(f"Define the term: {keyword}",num_return_sequences=1,additional_tokens=100,temperature=0.5, top_k=20,top_p=0.75)[0]
    
    return definition

def generate_keywords(note_content, processed_content) -> dict[str, str]:
    
    prompt = f"""
    Text:
    "{note_content}"
    Prompt:
    "From this list of words: {processed_content} return only a comma separated list of the most important keywords relevant to the text."
    """
    
    keywords: str = generate_content(prompt, num_return_sequences=1, additional_tokens=50, temperature=0.5, top_k=20, top_p=0.75)[0]
    keywords: str = strip_prompt(prompt, keywords)
    
    print(keywords + '\n\n')
    # keyword_list = keywords.split(', ')
    
    keywords_dict = clean_keywords(keywords)
    
    return keywords_dict

def generate_summary(note_content) -> str:
    prompt = f"""
    Text:
    {note_content}
    Prompt:
    "Generate a summary for the provided text."
    """
    summary = generate_content(prompt, num_return_sequences=1)[0]
    summary = strip_prompt(prompt, summary)
    
    return summary    

""" Auto Grouping Methods"""
def compute_similarity_matrix(contents):
    try:
        vectorizer = TfidfVectorizer(min_df=1, max_df=0.7, ngram_range=(1, 2))
        tfidf_matrix = vectorizer.fit_transform(contents)
        
        if tfidf_matrix.shape[1] == 0:  # No valid terms extracted
            raise ValueError("No terms left after vectorization; adjust preprocessing or vectorizer settings.")
        
        cosine_sim = cosine_similarity(tfidf_matrix)
        return cosine_sim
    
    except Exception as e:
        logging.error("Failed to compute similarity matrix: %s", e, exc_info=True)
        return None
    

def group_note(target_note, other_notes, similarities, threshold=0.5, group_title=''):
    try:
        similar_indices = [int(i) for i in np.where(similarities > threshold)[0]]
        similar_notes = [other_notes[i] for i in similar_indices]  

        if similar_notes:
            existing_group = find_existing_group(target_note, threshold)
            if existing_group:
                for note in similar_notes:
                    existing_group.notes.add(note)
                existing_group.notes.add(target_note)
                existing_group.save()
                return existing_group
            else:
                if group_title:
                    note_group = NoteGroup(title=group_title, owner=target_note.owner)
                else:
                    note_group = NoteGroup(title=f"Group for Note {target_note.pk} - {dt.now().strftime('%Y-%m-%d %H:%M:%S')}", owner=target_note.owner)
                note_group.save()
                note_group.notes.add(target_note, *similar_notes)
                return note_group
            
    except Exception as e:
        logging.error(f"Error occurred while grouping notes: {e}")

    return None

def group_all_notes(notes, similarity_matrix, threshold=0.5, owner=None, group_title=''):
    note_groups = []
    visited = set()

    for idx, similarities in enumerate(similarity_matrix):
        if idx in visited:
            continue

        similar_indices = [int(i) for i in np.where(similarities > threshold)[0]]
        group = [notes[i] for i in similar_indices if i not in visited]

        visited.update(similar_indices)

        if group:
            try:
                for note in group:
                    existing_group = find_existing_group(note, threshold)
                    if existing_group:
                        for n in group:
                            existing_group.notes.add(n)
                        existing_group.save()
                        note_groups.append(existing_group)
                        break
                    else:
                        # We're clear to create a new group. Use group_title.
                        if group_title:
                            note_group = NoteGroup(title=group_title, owner=owner)
                        else:    
                            note_group = NoteGroup(title=f"Auto Group {len(note_groups) + 1} - {dt.now().strftime('%Y-%m-%d %H:%M:%S')}", owner=owner)
                        note_group.save()
                        note_group.notes.set(group)
                        note_groups.append(note_group)
                        
            except Exception as e:
                logging.error(f"Error occurred while grouping (all) notes: {e}")

    return note_groups

def find_existing_group(note, threshold=0.2) -> NoteGroup:
    """
    Find an existing group with high similarity to the note's content.
    """
    try:
        existing_groups = NoteGroup.objects.filter(owner=note.owner)
        for group in existing_groups:
            group_contents = [get_preprocessed_content(n) for n in group.notes.all()]
            group_contents.append(get_preprocessed_content(note))
            sim_matrix = compute_similarity_matrix(group_contents)
            
            if sim_matrix is None:
                continue
            
            # Average similarity of 'note' across all notes in the group
            avg_similarity = np.mean(sim_matrix[-1][:-1])
            if avg_similarity > threshold:
                logging.info(f"Found existing group with similarity: {avg_similarity}")
                return group

    except Exception as e:
        logging.error(f"Error occurred while finding existing group: {e}")
        
    return None
