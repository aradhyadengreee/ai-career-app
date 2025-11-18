import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from config import Config

class RIASECMatcher:
    def __init__(self):
        self.data = None
        self.vectorizer = None
        self.job_vectors = None
        
    def set_data(self, data):
        """Set the job data"""
        self.data = data
        self._prepare_similarity_matrix()
    
    def _prepare_similarity_matrix(self):
        """Prepare TF-IDF vectorizer for text similarity"""
        if self.data is None:
            return
            
        texts = (
            self.data['Family_Title'] + ' ' + 
            self.data['NCO_2015_Title'] + ' ' + 
            self.data['primary_skills_list'] + ' ' + 
            self.data['primary_interest_cluster']
        ).tolist()
        
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.job_vectors = self.vectorizer.fit_transform(texts)
    
    def validate_riasec_code(self, riasec_code):
        """Validate RIASEC code format"""
        if not riasec_code or len(riasec_code) < Config.MIN_RIASEC_LENGTH:
            return False
            
        riasec_code = riasec_code.upper()
        if len(riasec_code) > Config.MAX_RIASEC_LENGTH:
            return False
            
        # Check if all characters are valid RIASEC codes
        return all(char in Config.VALID_RIASEC_CODES for char in riasec_code)
    
    def calculate_riasec_similarity(self, user_riasec, job_riasec):
        """Calculate similarity between user RIASEC and job RIASEC codes"""
        if not job_riasec or len(job_riasec) < 2:
            return 0
            
        user_riasec = user_riasec.upper()
        job_riasec = job_riasec.upper()
        
        # Focus on first two characters for 100% match requirement
        job_primary = job_riasec[:2]
        
        # Exact match for first two characters - 100% match
        if job_primary == user_riasec[:2]:
            return 1.0
        
        # Calculate character-based similarity
        user_chars = set(user_riasec)
        job_chars = set(job_primary)
        
        intersection = user_chars.intersection(job_chars)
        union = user_chars.union(job_chars)
        
        if not union:
            return 0
            
        jaccard_similarity = len(intersection) / len(union)
        
        # Boost similarity if first character matches
        if user_riasec[0] == job_primary[0]:
            jaccard_similarity = max(jaccard_similarity, 0.7)
            
        return jaccard_similarity
    
    def calculate_skills_similarity(self, user_skills, job_skills_text):
        """Calculate similarity based on skills"""
        if not user_skills:
            return 0.5  # Neutral score if no skills provided
            
        user_skills_text = ' '.join([skill.lower() for skill in user_skills])
        job_skills_text = job_skills_text.lower()
        
        user_words = set(user_skills_text.split())
        job_words = set(job_skills_text.split())
        
        if not user_words:
            return 0
            
        intersection = user_words.intersection(job_words)
        return len(intersection) / len(user_words)
    
    def calculate_interest_similarity(self, user_interests, job_interests_text):
        """Calculate similarity based on interests"""
        if not user_interests:
            return 0.5  # Neutral score if no interests provided
            
        user_interests_text = ' '.join([interest.lower() for interest in user_interests])
        job_interests_text = job_interests_text.lower()
        
        user_words = set(user_interests_text.split())
        job_words = set(job_interests_text.split())
        
        if not user_words:
            return 0
            
        intersection = user_words.intersection(job_words)
        return len(intersection) / len(user_words)
    
    def calculate_text_similarity(self, user_profile):
        """Calculate text-based similarity using TF-IDF"""
        if self.vectorizer is None or self.job_vectors is None:
            return np.zeros(len(self.data))
            
        user_text = (
            ' '.join(user_profile.get('skills', [])) + ' ' +
            ' '.join(user_profile.get('interests', [])) + ' ' +
            user_profile.get('riasec_code', '')
        )
        
        if not user_text.strip():
            return np.zeros(len(self.data))
            
        user_vector = self.vectorizer.transform([user_text])
        similarities = cosine_similarity(user_vector, self.job_vectors)
        return similarities[0]
    
    def get_recommendations(self, riasec_code, skills=None, interests=None, top_n=5):
        """Get top job recommendations"""
        if self.data is None:
            return []
            
        if not self.validate_riasec_code(riasec_code):
            raise ValueError("Invalid RIASEC code format")
        
        skills = skills or []
        interests = interests or []
        
        user_profile = {
            'riasec_code': riasec_code,
            'skills': skills,
            'interests': interests
        }
        
        matches = []
        
        for idx, job in self.data.iterrows():
            # Calculate individual similarity scores
            riasec_similarity = self.calculate_riasec_similarity(riasec_code, job['NCO_RIASEC_Codes'])
            skills_similarity = self.calculate_skills_similarity(skills, job['primary_skills_list'])
            interests_similarity = self.calculate_interest_similarity(interests, job['primary_interest_cluster'])
            text_similarities = self.calculate_text_similarity(user_profile)
            text_similarity = text_similarities[idx] if idx < len(text_similarities) else 0
            
            # Combined score with weights from config
            combined_score = (
                riasec_similarity * Config.RIASEC_WEIGHT +
                skills_similarity * Config.SKILLS_WEIGHT +
                interests_similarity * Config.INTERESTS_WEIGHT +
                text_similarity * Config.TEXT_WEIGHT
            )
            
            # Convert to percentage
            match_percentage = round(combined_score * 100)
            
            # Apply RIASEC-based boosting for high matches
            match_percentage = self._apply_riasec_boosting(match_percentage, riasec_similarity)
            
            matches.append({
                'job_id': job['Job_ID'],
                'job_title': job['NCO_2015_Title'],
                'family_title': job['Family_Title'],
                'riasec_code': job['NCO_RIASEC_Codes'],
                'match_percentage': match_percentage,
                'similarity_breakdown': {
                    'riasec': round(riasec_similarity * 100),
                    'skills': round(skills_similarity * 100),
                    'interests': round(interests_similarity * 100),
                    'text': round(text_similarity * 100)
                },
                'primary_skills': job['primary_skills_list'],
                'interest_cluster': job['primary_interest_cluster'],
                'mapping_confidence': job['Mapping_Confidence'],
                'salary_range': job.get('salary_range_analysis', 'Not specified')
            })
        
        # Sort by match percentage and get top N
        matches.sort(key=lambda x: x['match_percentage'], reverse=True)
        top_matches = matches[:top_n]
        
        return top_matches
    
    def _apply_riasec_boosting(self, match_percentage, riasec_similarity):
        """Apply boosting based on RIASEC similarity"""
        boosted_percentage = match_percentage
        
        # Significant boost for high RIASEC matches
        if riasec_similarity == 1.0:
            boosted_percentage = max(boosted_percentage, 100)
        elif riasec_similarity >= 0.9:
            boosted_percentage = max(boosted_percentage, 95)
        elif riasec_similarity >= 0.8:
            boosted_percentage = max(boosted_percentage, 90)
        elif riasec_similarity >= 0.7:
            boosted_percentage = max(boosted_percentage, 80)
        elif riasec_similarity >= 0.6:
            boosted_percentage = max(boosted_percentage, 70)
            
        return min(100, boosted_percentage)  # Ensure we don't exceed 100%