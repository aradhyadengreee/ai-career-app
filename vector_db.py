import chromadb
from sentence_transformers import SentenceTransformer
import pandas as pd
import numpy as np
import os
from typing import List, Dict, Optional
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CareerVectorDB:
    def __init__(self, excel_file_path: str, persist_directory: str = "./chroma_db"):
        self.persist_directory = persist_directory
        self.embedding_model = None
        self.collection = None
        
        # Initialize embedding model
        self._initialize_embedding_model()
        
        # Initialize ChromaDB
        self._initialize_chroma_db()
        
        # Load data from Excel
        self._load_and_index_data(excel_file_path)
    
    def _initialize_embedding_model(self):
        """Initialize the sentence transformer model for embeddings"""
        try:
            logger.info("Loading sentence transformer model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            raise
    
    def _initialize_chroma_db(self):
        """Initialize ChromaDB client and collection"""
        try:
            logger.info("Initializing ChromaDB...")
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Create or get collection
            self.collection = self.client.get_or_create_collection(
                name="career_recommendations_v2",
                metadata={"description": "Advanced career recommendations with multiple parameters"}
            )
            logger.info("✅ ChromaDB initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize ChromaDB: {e}")
            raise
    
    def _load_and_index_data(self, excel_file_path: str):
        """Load data from Excel and index it in ChromaDB"""
        if not os.path.exists(excel_file_path):
            raise FileNotFoundError(f"Excel file not found: {excel_file_path}")
        
        logger.info("Loading career data from Excel...")
        df = pd.read_excel(excel_file_path)
        df.columns = df.columns.str.strip()
        
        # Check if collection already has data
        if self.collection.count() > 0:
            logger.info("✅ Data already indexed in ChromaDB")
            return
        
        logger.info("Indexing career data in ChromaDB...")
        
        documents = []
        metadatas = []
        ids = []
        
        for idx, row in df.iterrows():
            # Create a comprehensive document for semantic search
            document_text = self._create_advanced_document(row)
            
            documents.append(document_text)
            metadatas.append({
                'family_title': str(row.get('Family_Title', '')),
                'nco_code': str(row.get('NCO_2015_Code', '')),
                'nco_title': str(row.get('NCO_2015_Title', '')),
                'riasec_code': str(row.get('NCO_RIASEC_Codes', '')),
                'mapping_confidence': str(row.get('Mapping_Confidence', '')),
                'similarity_score': float(row.get('Similarity_Score', 0)),
                'job_description': str(row.get('job_description', '')),
                'primary_skills': str(row.get('primary_skills_list', '')),  # Fixed column name
                'secondary_skills': str(row.get('secondary_skills_list', '')),  # Fixed column name
                'emerging_skills': str(row.get('emerging_skills_list', '')),  # Fixed column name
                'market_demand_score': float(row.get('market_demand_score', 0)),
                'salary_range_analysis': str(row.get('salary_range_analysis', '')),
                'industry_growth_projection': str(row.get('industry_growth_projection', '')),
                'learning_pathway_recommendations': str(row.get('learning_pathway_recommendations', '')),
                'automation_risk_assessment': str(row.get('automation_risk_assessment', '')),
                'geographic_demand_hotspots': str(row.get('geographic_demand_hotspots', ''))
            })    
            ids.append(f"career_{idx}")
        
        # Add to ChromaDB in batches
        batch_size = 50
        for i in range(0, len(documents), batch_size):
            end_idx = min(i + batch_size, len(documents))
            
            batch_documents = documents[i:end_idx]
            batch_metadatas = metadatas[i:end_idx]
            batch_ids = ids[i:end_idx]
            
            self.collection.add(
                documents=batch_documents,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
            
            logger.info(f"✅ Indexed batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}")
        
        logger.info(f"✅ Successfully indexed {len(documents)} career documents")
    
    def _create_advanced_document(self, row) -> str:
        """Create a comprehensive text document for semantic search with new columns"""
        document_parts = [
            f"Family Title: {row.get('Family_Title', '')}",
            f"NCO Title: {row.get('NCO_2015_Title', '')}",
            f"RIASEC Code: {row.get('NCO_RIASEC_Codes', '')}",
            f"Job Description: {row.get('job_description', '')}",
            f"Primary Skills: {row.get('primary_skills_list', '')}",
            f"Secondary Skills: {row.get('secondary_skills_list', '')}",
            f"Emerging Skills: {row.get('emerging_skills_list', '')}",
            f"Market Demand: {row.get('market_demand_score', '')}",
            f"Industry Growth: {row.get('industry_growth_projection', '')}",
            f"Learning Pathway: {row.get('learning_pathway_recommendations', '')}",
            f"Salary Range: {row.get('salary_range_analysis', '')}",
            f"Geographic Demand: {row.get('geographic_demand_hotspots', '')}",
            f"Automation Risk: {row.get('automation_risk_assessment', '')}"
        ]
        return " | ".join([part for part in document_parts if part.split(': ')[1].strip()])
    
    def advanced_search(self, user_profile: Dict, riasec_code: str, n_results: int = 5) -> List[Dict]:
        """Perform advanced search with improved matching"""
        
        # Build comprehensive query
        query_parts = [
            f"Career for {user_profile['occupation']}",
            f"Education: {user_profile['education_level']}",
            f"RIASEC personality: {riasec_code}",
            f"Skills and job preferences matching personality and background"
        ]
        
        if user_profile.get('current_field'):
            query_parts.append(f"Field: {user_profile['current_field']}")
        
        query = ". ".join(query_parts)
        
        # Perform semantic search with more results
        all_results = self.semantic_search(query=query, n_results=50)  # Increased from 20 to 50
        
        if not all_results:
            logger.warning("❌ No semantic results found")
            return []
        
        # Calculate match percentages with multiple parameters
        scored_results = []
        for result in all_results:
            match_percentage, matching_params = self._calculate_advanced_match(
                result, user_profile, riasec_code
            )
            
            # Lower the threshold to get more results
            if match_percentage >= 60:  # Reduced from 70 to 60
                result['match_percentage'] = match_percentage
                result['matching_parameters'] = matching_params
                result['automation_risk'] = self._extract_automation_risk(result.get('automation_risk_assessment', ''))
                result['geographic_demand'] = result.get('geographic_demand_hotspots', '')
                scored_results.append(result)
        
        # Sort by match percentage and get top results
        scored_results.sort(key=lambda x: x['match_percentage'], reverse=True)
        final_results = scored_results[:n_results]
        
        logger.info(f"🎯 Final recommendations with match percentages: {[r['match_percentage'] for r in final_results]}")
        
        return final_results

    def _calculate_advanced_match(self, career: Dict, user_profile: Dict, user_riasec: str) -> tuple:
        """Calculate advanced match percentage with improved RIASEC matching for 3 codes"""
        total_score = 0
        max_possible_score = 0
        matching_parameters = []
        
        # 1. RIASEC Code Match (50% weight) - IMPROVED for 3-character codes
        riasec_weight = 50
        career_riasec = career.get('riasec_code', '').replace(' ', '')[:3]  # Get up to 3 chars
        user_riasec_clean = user_riasec.replace(' ', '')[:3]  # Get up to 3 chars
        
        # Calculate RIASEC similarity with multiple matching strategies
        riasec_score = self._calculate_riasec_similarity_advanced(user_riasec_clean, career_riasec)
        
        if riasec_score >= 90:
            matching_parameters.append(f"RIASEC Code: Excellent match ({career_riasec})")
        elif riasec_score >= 70:
            matching_parameters.append(f"RIASEC Code: Good match ({career_riasec})")
        elif riasec_score >= 50:
            matching_parameters.append(f"RIASEC Code: Partial match ({career_riasec})")
        
        total_score += riasec_score * (riasec_weight / 100)
        max_possible_score += riasec_weight
        
        # 2. Education Level Match (20% weight)
        education_weight = 20
        user_education = user_profile.get('education_level', '').lower()
        career_education_context = career.get('learning_pathway_recommendations', '').lower()
        
        education_score = self._calculate_education_match(user_education, career_education_context)
        if education_score >= 80:
            matching_parameters.append(f"Education Level: Good match")
        elif education_score >= 50:
            matching_parameters.append(f"Education Level: Partial match")
        
        total_score += education_score * (education_weight / 100)
        max_possible_score += education_weight
        
        # 3. Experience Match (15% weight)
        experience_weight = 15
        user_experience = user_profile.get('experience_years', 0)
        experience_score = self._calculate_experience_match(user_experience, career)
        if experience_score >= 80:
            matching_parameters.append(f"Experience Level: Good match")
        
        total_score += experience_score * (experience_weight / 100)
        max_possible_score += experience_weight
        
        # 4. Field/Industry Match (10% weight)
        field_weight = 10
        user_field = user_profile.get('current_field', '').lower()
        career_domain = career.get('family_title', '').lower() + ' ' + career.get('nco_title', '').lower()
        
        field_score = self._calculate_field_match(user_field, career_domain)
        if field_score >= 80:
            matching_parameters.append(f"Field/Industry: Good match")
        elif field_score >= 50 and user_field:
            matching_parameters.append(f"Field/Industry: Related field")
        
        total_score += field_score * (field_weight / 100)
        max_possible_score += field_weight
        
        # 5. Market Demand Bonus (5% weight)
        demand_weight = 5
        market_demand = career.get('market_demand_score', 0)
        if isinstance(market_demand, (int, float)):
            demand_score = min(market_demand * 20, 100)  # More generous scoring
            if demand_score > 70:
                matching_parameters.append(f"Market Demand: High")
        else:
            demand_score = 70  # Default to good score if unknown
        
        total_score += demand_score * (demand_weight / 100)
        max_possible_score += demand_weight
        
        # Calculate final percentage
        if max_possible_score > 0:
            final_percentage = (total_score / max_possible_score) * 100
        else:
            final_percentage = 0
        
        # Apply RIASEC boost for high matches
        if riasec_score >= 80:
            final_percentage = min(final_percentage * 1.2, 100)  # 20% boost for high RIASEC matches
        
        # Round to nearest integer
        final_percentage = round(final_percentage)
        
        return min(final_percentage, 100), matching_parameters

    def _calculate_riasec_similarity_advanced(self, user_riasec: str, career_riasec: str) -> float:
        """Calculate RIASEC similarity with chronological order priority"""
        if not career_riasec:
            return 0
        
        # Clean and normalize codes
        user_riasec = user_riasec.replace(' ', '')[:3].upper()
        career_riasec = career_riasec.replace(' ', '')[:3].upper()
        
        # Exact 3-character match in same order - 100%
        if user_riasec == career_riasec:
            return 100
        
        # Exact first 2 characters in same order - 95%
        if user_riasec[:2] == career_riasec[:2]:
            return 95
        
        # First character matches + second character appears anywhere - 90%
        if user_riasec[0] == career_riasec[0] and user_riasec[1] in career_riasec:
            return 90
        
        # First character matches + any other user character appears - 85%
        if user_riasec[0] == career_riasec[0] and any(char in career_riasec for char in user_riasec[1:]):
            return 85
        
        # First two characters appear in career code (not necessarily in order) - 80%
        if all(char in career_riasec for char in user_riasec[:2]):
            # Bonus if they appear in relatively same positions
            user_first_pos = career_riasec.find(user_riasec[0])
            user_second_pos = career_riasec.find(user_riasec[1])
            if user_first_pos >= 0 and user_second_pos >= 0 and user_second_pos > user_first_pos:
                return 85  # Slight bonus for maintaining relative order
            return 80
        
        # First character matches - 75%
        if user_riasec[0] in career_riasec:
            return 75
        
        # At least 2 characters from user's top 3 appear in career - 70%
        common_chars = len(set(user_riasec) & set(career_riasec))
        if common_chars >= 2:
            # Check if common characters maintain some order
            user_chars_in_career = [char for char in user_riasec if char in career_riasec]
            career_positions = [career_riasec.find(char) for char in user_chars_in_career]
            if career_positions == sorted(career_positions):  # Maintains order
                return 75
            return 70
        
        # At least 1 character matches - 60%
        if common_chars >= 1:
            return 60
        
        return 30  # Minimal match for completely different codes

    def _calculate_education_match(self, user_education: str, career_education_context: str) -> float:
        """Calculate education level match"""
        education_keywords = {
            'high school': ['school', 'high school', 'secondary', 'basic'],
            'diploma': ['diploma', 'certificate', 'vocational'],
            'bachelor': ['bachelor', 'undergraduate', 'degree', 'college'],
            'master': ['master', 'postgraduate', 'graduate'],
            'phd': ['phd', 'doctorate', 'doctoral']
        }
        
        for level, keywords in education_keywords.items():
            if level in user_education:
                if any(keyword in career_education_context for keyword in keywords):
                    return 100
                else:
                    return 60  # Partial match for same level but different terms
        
        return 70  # Default good score if no specific match

    def _calculate_experience_match(self, user_experience: int, career: Dict) -> float:
        """Calculate experience level match"""
        if user_experience <= 2:
            exp_level = 'entry'
        elif user_experience <= 5:
            exp_level = 'mid'
        else:
            exp_level = 'senior'
        
        # Analyze job description for experience level
        job_desc = career.get('job_description', '').lower()
        career_title = career.get('nco_title', '').lower() + ' ' + career.get('family_title', '').lower()
        
        experience_keywords = {
            'entry': ['entry', 'junior', 'trainee', 'associate', 'beginner'],
            'mid': ['mid', 'middle', 'experienced', 'professional'],
            'senior': ['senior', 'lead', 'principal', 'manager', 'director', 'head']
        }
        
        # Check for experience level keywords
        for keyword in experience_keywords.get(exp_level, []):
            if keyword in job_desc or keyword in career_title:
                return 100
        
        # If no specific level mentioned, assume it's flexible
        return 80

    def _calculate_field_match(self, user_field: str, career_domain: str) -> float:
        """Calculate field/industry match"""
        if not user_field:
            return 80  # Good score if no specific field preference
        
        if user_field in career_domain:
            return 100
        
        # Check for related fields
        related_fields = self._get_related_fields(user_field)
        if any(field in career_domain for field in related_fields):
            return 85
        
        return 50  # Partial match for unrelated fields
    def _get_related_fields(self, field: str) -> List[str]:
        """Get related fields for flexible matching"""
        field_relations = {
            'technology': ['it', 'software', 'computer', 'tech', 'digital'],
            'healthcare': ['medical', 'health', 'hospital', 'clinical'],
            'finance': ['banking', 'accounting', 'financial', 'investment'],
            'education': ['teaching', 'academic', 'learning', 'training'],
            'engineering': ['technical', 'manufacturing', 'construction']
        }
        
        for main_field, related in field_relations.items():
            if field in main_field or any(rel in field for rel in related):
                return related + [main_field]
        
        return [field]
    
    def _extract_automation_risk(self, risk_str: str) -> str:
        """Extract automation risk from assessment string"""
        if not risk_str or pd.isna(risk_str):
            return "Not specified"
        
        risk_str_lower = risk_str.lower()
        if 'low' in risk_str_lower:
            return "Low"
        elif 'high' in risk_str_lower:
            return "High"
        elif 'medium' in risk_str_lower:
            return "Medium"
        else:
            return "Not specified"
    
    def semantic_search(self, query: str, n_results: int = 20) -> List[Dict]:
        """Perform semantic search"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            processed_results = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    similarity_score = 1 - distance
                    
                    processed_results.append({
                        **metadata,
                        "similarity_score": round(similarity_score, 3),
                        "full_document": doc
                    })
            
            return processed_results
            
        except Exception as e:
            logger.error(f"❌ Error in semantic search: {e}")
            return []
    
    def debug_collection(self):
        """Debug method to check collection status"""
        try:
            count = self.collection.count()
            sample = self.collection.peek(limit=1)
            return {
                "total_careers": count,
                "sample_document": sample['documents'][0][0] if sample['documents'][0] else None,
                "sample_metadata": sample['metadatas'][0][0] if sample['metadatas'][0] else None
            }
        except Exception as e:
            return {"error": str(e)}
        
# --- Add BELOW at the end of vector_db.py ---

import traceback
from typing import Optional

def create_vector_db(data_path: Optional[str] = "/app/careers_data.xlsx",
                     chroma_dir: Optional[str] = "/app/chroma-db"):
    """
    Build and persist the Chroma vector DB using the existing CareerVectorDB class.
    This is used by preload.py during Docker build so Cloud Run does NOT
    download the model at runtime.
    """
    try:
        logger.info(f"[create_vector_db] Starting preload with:")
        logger.info(f"  data_path={data_path}")
        logger.info(f"  chroma_dir={chroma_dir}")

        db = CareerVectorDB(excel_file_path=data_path, persist_directory=chroma_dir)

        logger.info("[create_vector_db] Vector DB created successfully")
        return db

    except Exception:
        logger.error("[create_vector_db] FAILED during preload")
        logger.error(traceback.format_exc())
        raise


if __name__ == "__main__":
    # Allow manual testing: python vector_db.py <excel> <persist_dir>
    import sys

    data_arg = "/app/careers_data.xlsx"
    chroma_arg = "/app/chroma-db"

    if len(sys.argv) >= 2:
        data_arg = sys.argv[1]
    if len(sys.argv) >= 3:
        chroma_arg = sys.argv[2]

    print(f"Running create_vector_db with:")
    print(f"  data_path={data_arg}")
    print(f"  chroma_dir={chroma_arg}")

    create_vector_db(data_arg, chroma_arg)
