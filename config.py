import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-this-in-production'
    
    # Use relative paths for Render
    VECTOR_DB_PATH = "./chroma_db"
    DATA_FILE = "./careers_data.xlsx"  # Move Excel file to root
    
    # Session configurations
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    
    # Add these for RIASEC matcher
    MIN_RIASEC_LENGTH = 2
    MAX_RIASEC_LENGTH = 3
    VALID_RIASEC_CODES = ['R', 'I', 'A', 'S', 'E', 'C']
    
    # Weights for matching algorithm
    RIASEC_WEIGHT = 0.4
    SKILLS_WEIGHT = 0.3
    INTERESTS_WEIGHT = 0.2
    TEXT_WEIGHT = 0.1