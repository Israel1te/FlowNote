from django.test import TestCase

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from django.core.cache import cache
import logging
from celery.result import AsyncResult

from notes.models import Note, NoteGroup
from AIEngine.tasks import *  

# python manage.py test notes.tests.NoteSummaryTestCase

class NoteSummaryTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='12345')
        # Reusing notes GPT-2 Medium scored poorly on during analysis testing 
        cls.note1 = Note.objects.create(owner=cls.user, title="Neuro AI", content=
                                        """The interface between neuroscience and artificial intelligence (AI) represents a frontier of interdisciplinary research with transformative potential. Neuroscience, through the study of the brains structure and function, provides insights into cognition, perception, and learning processes. AI, particularly in the realm of machine learning and neural networks, seeks to emulate these cognitive functions computationally. The synergy between these fields is evident in the development of algorithms inspired by neural processing, enhancing AIs capabilities in pattern recognition, decision-making, and natural language processing. Conversely, AI techniques are employed in analyzing neurological data, advancing our understanding of brain function and disorders. This reciprocal relationship not only propels AI towards more sophisticated and human-like intelligence but also opens new avenues in brain research, with implications for neurology, psychology, and cognitive science."""
                                        )
        cls.note2 = Note.objects.create(owner=cls.user, title="Economics - Market Structures", content=
                                        """Market structures in economics refer to the competitive environment within a market. These structures range from perfect competition, where many firms are price takers, to monopoly, where a single firm controls the market. Other types include oligopoly, characterized by a few firms, and monopolistic competition, where many firms compete but have differentiated products. Each structure affects pricing, efficiency, and consumer choice differently.""")

    def test_note_analysis(self):
        notes = Note.objects.filter(id__in=[self.note1.id, self.note2.id])
        for note in notes:
            print(f"\n--- {note.title} Summary ---")
            result = generate_summary_task(note.pk)
            # Wait for the task to complete and get the result
            # result = async_result.get(timeout=30)
            print("Analysis Results:")
            print(f"SUMMARY: {result}")
            
# python manage.py test notes.tests.AutoGroupTestCase
class AutoGroupTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='testuser', password='12345')
        cls.note1 = Note.objects.create(owner=cls.user, title="Django Testing", content="Testing in Django can be complex due to its rich and robust framework. A good grasp of Django's testing framework is crucial for effectively writing and running tests. This includes understanding Django's TestCase for database integrity, the SimpleTestCase for middleware testing, and the LiveServerTestCase for end-to-end tests involving HTTP and database interactions. Mastering these can significantly reduce bugs and ensure high-quality software development.")
        cls.note2 = Note.objects.create(owner=cls.user, title="Django Models", content="Django models form the foundational layer for database interaction within Django. They not only define the structure of the database tables but also provide a systematic approach to handling database queries. By defining fields and behaviors of the data you’re storing, Django models encapsulate database access and are a crucial element in facilitating an organized, efficient, and robust database architecture. Understanding relationships such as ForeignKey, ManyToMany, and OneToOne fields are essential for leveraging the full capability of Django's ORM.")
        cls.note3 = Note.objects.create(owner=cls.user, title="Testing Basics", content="Understanding the basics of software testing is fundamental to any software development process. Writing tests is crucial as it helps ensure the quality of code and reduces bugs in production. In software development, various testing methodologies are employed, including unit tests that help verify the functionality of a small part of the system, integration tests which ensure that different parts of the application work together as expected, and system tests which evaluate the complete and fully integrated software product. The goal is to catch bugs early in the development cycle and save costs in later stages while maintaining software quality.")

    def test_auto_grouping_individual_notes(self):
        print("\n--- Auto Grouping Individual Notes Test ---")
        for note in [self.note1, self.note2, self.note3]:
            group = auto_group_note(note.pk, threshold=0.10)
            if group:
                print(f"\nGroup Title: {group.title}")
                print("Grouped Notes (Threshold 0.10):")
                for grouped_note in group.notes.all():
                    print(f"- {grouped_note.title}")
            else:
                print(f"\nNo similar notes found for {note.title}")

    def test_auto_grouping_all_notes(self):
        print("\n--- Auto Grouping All Notes Test ---")
        groups: list[NoteGroup] = auto_group_all(threshold=0.15, owner=self.user)
        if groups:
            for group in groups:
                print(f"\nGroup Title: {group.title}")
                print("Grouped Notes:")
                for note in group.notes.all():
                    print(f"- {note.title}")
        else:
            print("\nNo groups formed.")

    def test_threshold_variability(self):
        print("\n--- Testing Threshold Variability ---")
        thresholds = [0.05, 0.10, 0.15, 0.20]
        for threshold in thresholds:
            group = auto_group_note(self.note1.pk, threshold)
            print(f"\nThreshold: {threshold}")
            if group:
                print("Group formed with title:", group.title)
            else:
                print("No group formed.")

class GenerateVocabAndKeywordsTaskTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.note = Note.objects.create(owner=self.user, content="Artificial Intelligence (AI) is transforming industries by automating tasks, analyzing vast amounts of data, and solving complex problems. It has applications in various fields such as healthcare, finance, and autonomous driving.")

    def test_generate_vocab_and_keywords(self):
        flashcards = generate_flashcards_task(self.note.id)
        
        print("Flashcards:", flashcards)
        
        self.note.refresh_from_db()
        #print("Updated Keywords:", self.note.keywords)

    def tearDown(self):
        self.note.delete()
        self.user.delete()


class GetAutocompleteSuggestionsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.note = Note.objects.create(owner=self.user, content='<p>Last sunday was a breeze! Generally speaking, </p>')

    def test_get_autocomplete_suggestions(self):
        
        suggestions = get_autocomplete_suggestions(self.note.id, self.note.content)
        print("Suggestions:", suggestions)


    def tearDown(self):
        self.note.delete()
        self.user.delete()
    
""" DJANGO SHELL TESTS """

# notes = Note.objects.all().order_by('-id')[:k]
# from notes.models import Note  
# from AIEngine.tasks import analyze_note  
# def test_analysis():
#     # Fetch FIRST k notes from db
#     # notes = Note.objects.all()[:k]
#     notes = Note.objects.filter(id__in=[6, 7])
    
#     if not notes:
#         print(f"No notes found. Please check your database.")
#         return
    
#     for idx, note in enumerate(notes, start=1):
#         print(f"\n\n--- Note {idx} Analysis ---")
#         print("Note Content:")
#         print(note.content)
#         print("\n--- Performing Analysis ---\n")
        
#         result = analyze_note(note.pk)  
        
#         print("Analysis Results:")
#         print(f"Summary: {result['summary']}")
#         print(f"Keywords: {result['keywords']}")

# test_analysis()

"""

prompt = f"Identify the key concepts in this text: {content}"

max_length=150, num_return_sequences=1, additional_tokens=500
total_max_length = input_ids.shape[1] + additional_tokens

with torch.no_grad():
        generated_ids = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            max_length=total_max_length,
            min_length=input_ids.shape[1] + 20,
            no_repeat_ngram_size=3,
            num_return_sequences=num_return_sequences,
            temperature=0.8,
            top_k=50,
            top_p=0.92,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id
        )
        

RESULTS (1 of 3, 33%):
--- Content 1 Vocabulary Extraction ---
Original Content:
Artificial intelligence in healthcare has transformed the way patient data is analyzed and interpreted. By leveraging machine learning algorithms, clinicians can now predict patient outcomes with greater accuracy and personalize treatment plans effectively. This paradigm shift towards data-driven medicine necessitates a comprehensive understanding of ethical considerations, such as patient privacy concerns and the potential for bias in algorithmic decisions.

Extracted Keywords:
The current state of artificial intelligence in medicine is largely in the hands of academia, providing opportunities for AI to improve patient care and patient privacy. However, AI's potential impact lies in its potential to provide personalized care, augment medical research, and improve patient outcomes.

--- Content 2 Vocabulary Extraction ---
Original Content:
The impact of climate change on marine biodiversity has become increasingly apparent, with rising sea temperatures causing widespread coral bleaching events. These ecological disturbances threaten the intricate food webs supported by coral reefs and may lead to substantial losses in marine species diversity. Researchers are urgently investigating adaptive strategies that marine organisms might employ to survive in these rapidly changing environments.

Extracted Keywords:
Keywords: coral reef, sea ice, ecosystem, climate change

1. Introduction Coral reefs provide a unique, diverse habitat that provides food, shelter, and economic value to many species of marine organisms. Coral reefs have been found to be vulnerable to climate change, with increased sea temperatures and rising ocean acidity causing severe declines in fish, shellfish, and shell-building organisms. The impacts of climate variability, ocean acidification, and bleaching have significant impacts on coral reefs worldwide, with bleaching occurring in the Gulf of Mexico, South America, and the Pacific Ocean. Many of these impacts are expected to become more pronounced as the climate continues to warm, as ocean temperatures rise, and as sea ice melts. In order to mitigate these environmental impacts, researchers are working to understand the role of marine systems in responding to changing climate.

--- Content 3 Vocabulary Extraction ---
Original Content:
Neurolinguistics explores the brain mechanisms underlying language comprehension and production, offering insights into the cognitive processes involved in linguistic tasks. Recent studies using functional magnetic resonance imaging (fMRI) have identified specific brain regions associated with syntactic processing and semantic analysis, contributing to a better understanding of language disorders such as dyslexia and aphasia.

Extracted Keywords:
Neurolinguitists have also developed cognitive-behavioral approaches that enhance cognitive functions such as visuo-spatial skills and inhibitory control, and are increasingly applied in cognitive neuroscience research.
"""

"""
RUN #2

prompt = f"Extract the most important keywords that represent the central themes of this text: {content}"

no_repeat_ngram_size=2,
temperature=0.7,
top_k=30,
top_p=0.85,
            
Testing Vocabulary Extraction

--- Content 1 Vocabulary Extraction ---
Original Content:
Artificial intelligence in healthcare has transformed the way patient data is analyzed and interpreted. By leveraging machine learning algorithms, clinicians can now predict patient outcomes with greater accuracy and personalize treatment plans effectively. This paradigm shift towards data-driven medicine necessitates a comprehensive understanding of ethical considerations, such as patient privacy concerns and the potential for bias in algorithmic decisions.

Extracted Keywords:
This paper examines AI and AI-assisted medicine through the lens of AI research in health care, AI ethics, and medical AI.

--- Content 2 Vocabulary Extraction ---
Original Content:
The impact of climate change on marine biodiversity has become increasingly apparent, with rising sea temperatures causing widespread coral bleaching events. These ecological disturbances threaten the intricate food webs supported by coral reefs and may lead to substantial losses in marine species diversity. Researchers are urgently investigating adaptive strategies that marine organisms might employ to survive in these rapidly changing environments.

Extracted Keywords:
...
 and
 "



.

 "

 ( )

 The Nature of the Marine Ecosystem

--- Content 3 Vocabulary Extraction ---
Original Content:
Neurolinguistics explores the brain mechanisms underlying language comprehension and production, offering insights into the cognitive processes involved in linguistic tasks. Recent studies using functional magnetic resonance imaging (fMRI) have identified specific brain regions associated with syntactic processing and semantic analysis, contributing to a better understanding of language disorders such as dyslexia and aphasia.

Extracted Keywords:
Neuropsychological research has also uncovered connections between cognitive function and neural processing, suggesting that these processes influence language processing.
"""

"""
RUN 3 (1.8 of 3, 60%)

# Limited Max Length and reduced variability in temperature by 0.2, top_p by 0.1, and top_k by 10.
additional_tokens=50

temperature=0.5,
top_k=20,
top_p=0.75,

Testing Vocabulary Extraction

--- Content 1 Vocabulary Extraction ---
Original Content:
Artificial intelligence in healthcare has transformed the way patient data is analyzed and interpreted. By leveraging machine learning algorithms, clinicians can now predict patient outcomes with greater accuracy and personalize treatment plans effectively. This paradigm shift towards data-driven medicine necessitates a comprehensive understanding of ethical considerations, such as patient privacy concerns and the potential for bias in algorithmic decisions.

Extracted Keywords:
Keywords: AI, Artificial Intelligence, Health Care, Ethics, Data Science, Machine Learning

--- Content 2 Vocabulary Extraction ---
Original Content:
The impact of climate change on marine biodiversity has become increasingly apparent, with rising sea temperatures causing widespread coral bleaching events. These ecological disturbances threaten the intricate food webs supported by coral reefs and may lead to substantial losses in marine species diversity. Researchers are urgently investigating adaptive strategies that marine organisms might employ to survive in these rapidly changing environments.

Extracted Keywords:
Keywords
 The effects of global climate changes on biodiversity are well understood, but how these impacts will affect marine ecosystems remains uncertain. The impacts of these changes include increased ocean acidification, increased salinity, and altered nutrient cycling, leading to

--- Content 3 Vocabulary Extraction ---
Original Content:
Neurolinguistics explores the brain mechanisms underlying language comprehension and production, offering insights into the cognitive processes involved in linguistic tasks. Recent studies using functional magnetic resonance imaging (fMRI) have identified specific brain regions associated with syntactic processing and semantic analysis, contributing to a better understanding of language disorders such as dyslexia and aphasia.

Extracted Keywords:
Neuropsychology offers insights about the neural basis of cognition, emotion, and social behavior, providing insights that can be applied to the development of effective interventions for these disorders.
"""

"""
RUN 4 (2.5 of 3, 83%)

# Only changed the prompt
prompt = f"Return a list of the most important keywords relevant to this text: {content}"


Testing Vocabulary Extraction

--- Content 1 Vocabulary Extraction ---
Original Content:
Artificial intelligence in healthcare has transformed the way patient data is analyzed and interpreted. By leveraging machine learning algorithms, clinicians can now predict patient outcomes with greater accuracy and personalize treatment plans effectively. This paradigm shift towards data-driven medicine necessitates a comprehensive understanding of ethical considerations, such as patient privacy concerns and the potential for bias in algorithmic decisions.

Extracted Keywords:
Keywords: AI, Artificial Intelligence, Health Care, Data Science, Ethics, Machine Learning

--- Content 2 Vocabulary Extraction ---
Original Content:
The impact of climate change on marine biodiversity has become increasingly apparent, with rising sea temperatures causing widespread coral bleaching events. These ecological disturbances threaten the intricate food webs supported by coral reefs and may lead to substantial losses in marine species diversity. Researchers are urgently investigating adaptive strategies that marine organisms might employ to survive in these rapidly changing environments.

Extracted Keywords:
Keywords: Climate change, marine life, biodiversity, conservation, ocean sciences, fisheries,

--- Content 3 Vocabulary Extraction ---
Original Content:
Neurolinguistics explores the brain mechanisms underlying language comprehension and production, offering insights into the cognitive processes involved in linguistic tasks. Recent studies using functional magnetic resonance imaging (fMRI) have identified specific brain regions associated with syntactic processing and semantic analysis, contributing to a better understanding of language disorders such as dyslexia and aphasia.

Extracted Keywords:
Neuro-linguaistic approaches can also be applied to cognitive neuroscience research, particularly in the areas of attention, emotion, and cognition.
"""