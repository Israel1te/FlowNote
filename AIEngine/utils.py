import re
import string
import spacy

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer

import nltk

from notes.models import Note
nltk.download('wordnet')

from django.core.cache import cache
import logging

nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])


def preprocess_text(text):
    
    doc = nlp(text)
    keywords = [token.lemma_ for token in doc if not token.is_stop and token.pos_ in ('NOUN', 'PROPN', 'VERB', 'ADJ') and not token.is_punct]
    
    return list(set(keywords))

def strip_html_tags(input_string):
    
    html_tag_pattern = re.compile('<.*?>')
    cleaned = html_tag_pattern.sub('', input_string)
    
    cleaned = cleaned.replace('&nbsp;', ' ')
    cleaned = cleaned.replace('&amp;', '&')
    cleaned = cleaned.replace('&lt;', '<')
    cleaned = cleaned.replace('&gt;', '>')
    cleaned = cleaned.replace('&quot;', '"')
    cleaned = cleaned.replace('&apos;', "'")
    cleaned = cleaned.replace('&#39;', "'")
    cleaned = cleaned.replace('&#34;', '"')
    cleaned = cleaned.replace('\n', ' ')
    cleaned = ' '.join(cleaned.split())
    return cleaned

def clean_keywords(text):
    # Remove newlines and the prompt
    text = re.sub(r'[\n\r]', ' ', text)  # Replace newlines and carriage returns with space
    text = re.sub(r'".*?Prompt:.*?"', '', text)  # Attempt to remove the prompt
    
    # Split the text into individual words
    words = re.split(r'[^a-zA-Z-]', text)  # Split on non-alphabetic characters, preserving hyphenated words
    
    # Filter out empty strings and overly long words (more than 2 words in a phrase)
    keywords = [word.strip() for word in words if word and len(word.strip().split()) <= 2]
    
    # Deduplicate while preserving order
    seen = set()
    keywords = [x for x in keywords if not (x in seen or seen.add(x))]
    
    # Create a dictionary with keywords as keys
    keyword_dict = {keyword: '' for keyword in keywords}
    
    return keyword_dict

def strip_prompt(prompt, content):
    try:
        start_index = content.index(prompt) + len(prompt)
    except ValueError:
        start_index = 0
    return content[start_index:].strip()

def get_preprocessed_content(note: Note):
    try:
        cache_key = f"preprocessed_{note.pk}"
        preprocessed_content = cache.get(cache_key)

        if not preprocessed_content or note.updated_at > cache.get(f"{cache_key}_timestamp", note.updated_at):
            note_content = strip_html_tags(note.content)
            preprocessed_content = preprocess_text(note_content)

            cache.set(cache_key, preprocessed_content, None)        # None timeout means it's cached forever
            cache.set(f"{cache_key}_timestamp", note.updated_at, None)

        return preprocessed_content
    except Exception as e:
        logging.error(f"Error occurred while preprocessing content: {e}")
        return None

def preprocess_group_content(note):
    
    # Basic cleanup, HTML strip, lowering cases
    text = re.sub(r'<[^>]+>', '', note.content) 
    text = text.lower()  
    text = text.translate(str.maketrans('', '', string.punctuation)) 

    # Tokenization and more advanced processing like stemming/lemmatization
    stop_words = set(stopwords.words('english')) - {'over', 'under', 'more', 'most', 'such'}
    word_tokens = word_tokenize(text)
    lemmatizer = WordNetLemmatizer()
    filtered_sentence = [lemmatizer.lemmatize(w) for w in word_tokens if not w in stop_words]

    return ' '.join(filtered_sentence)
