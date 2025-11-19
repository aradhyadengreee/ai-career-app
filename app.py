from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import pandas as pd
import uuid
import time
from typing import List, Dict
from config import Config
from vector_db import CareerVectorDB
import os

app = Flask(__name__)
app.config.from_object(Config)

# RIASEC Code Generator
class RIASECGenerator:
    def __init__(self):
        self.riasec_codes = ['R', 'I', 'A', 'S', 'E', 'C']
    
    def generate_from_scores(self, scores: Dict) -> str:
        """Generate RIASEC code from provided scores - returns 3 characters in chronological order"""
        # Sort by score descending, then by code for consistency
        sorted_codes = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
        return ''.join([code for code, score in sorted_codes[:3]])

# Initialize components
riasec_generator = RIASECGenerator()

# Initialize Vector Database
try:
    vector_db = CareerVectorDB(app.config['DATA_FILE'])
    print("✅ Vector database initialized successfully")
except Exception as e:
    print(f"❌ Error initializing vector database: {e}")
    vector_db = None

# Enhanced multi-user session management
class UserSessionManager:
    def __init__(self):
        self.user_sessions = {}
        self.session_timeout = 3600  # 1 hour timeout
    
    def create_session(self, user_info: Dict) -> str:
        """Create a new user session"""
        user_id = str(uuid.uuid4())
        
        # Generate RIASEC code
        riasec_scores = {
            'R': user_info.get('realistic_score', 0),
            'I': user_info.get('investigative_score', 0),
            'A': user_info.get('artistic_score', 0),
            'S': user_info.get('social_score', 0),
            'E': user_info.get('enterprising_score', 0),
            'C': user_info.get('conventional_score', 0)
        }
        
        riasec_code = riasec_generator.generate_from_scores(riasec_scores)
        
        # Store session data
        self.user_sessions[user_id] = {
            'user_info': user_info,
            'riasec_code': riasec_code,
            'riasec_scores': riasec_scores,
            'created_at': time.time(),
            'last_accessed': time.time()
        }
        
        print(f"✅ New user session created: {user_id}, RIASEC: {riasec_code}")
        return user_id
    
    def get_session(self, user_id: str) -> Dict:
        """Get user session data and update access time"""
        if user_id in self.user_sessions:
            session_data = self.user_sessions[user_id]
            session_data['last_accessed'] = time.time()
            return session_data
        return None
    
    def delete_session(self, user_id: str):
        """Delete a user session"""
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            print(f"🗑️  User session deleted: {user_id}")
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = [
            user_id for user_id, session_data in self.user_sessions.items()
            if current_time - session_data['last_accessed'] > self.session_timeout
        ]
        
        for user_id in expired_sessions:
            self.delete_session(user_id)
        
        if expired_sessions:
            print(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.user_sessions)

# Initialize session manager
session_manager = UserSessionManager()

# Helper functions (keep your existing helper functions)
def parse_skills_list(skills_str: str) -> List[str]:
    """Parse skills string into list"""
    if not skills_str or pd.isna(skills_str):
        return []
    try:
        if skills_str.startswith('['):
            import ast
            skills_data = ast.literal_eval(skills_str)
            if isinstance(skills_data, list):
                return [skill.get('skill_name', '') for skill in skills_data if skill.get('skill_name')]
        skills = [skill.strip() for skill in str(skills_str).split(',')]
        return [skill for skill in skills if skill]
    except:
        return []

def extract_salary_range(salary_str: str) -> Dict:
    """Extract salary range from string"""
    if not salary_str or pd.isna(salary_str):
        return {"entry": "Not specified", "mid": "Not specified", "senior": "Not specified"}
    
    try:
        salary_parts = {}
        for part in salary_str.split(','):
            if ':' in part:
                level, range_val = part.split(':', 1)
                salary_parts[level.strip().lower()] = range_val.strip()
        return salary_parts
    except:
        return {"entry": salary_str, "mid": salary_str, "senior": salary_str}

# Routes
@app.route('/')
def index():
    # Clean up expired sessions on home page access
    session_manager.cleanup_expired_sessions()
    return render_template('index.html')

@app.route('/results')
def results():
    user_id = session.get('user_id')
    if not user_id or not session_manager.get_session(user_id):
        return redirect(url_for('index'))
    return render_template('results.html')

# API Routes
@app.route('/api/user/register', methods=['POST'])
def register_user():
    try:
        user_info = request.get_json()
        print(f"📝 Received user info: {user_info}")
        
        if not user_info:
            return jsonify({"error": "No data received"}), 400
        
        # Create new user session
        user_id = session_manager.create_session(user_info)
        
        # Store user ID in Flask session
        session['user_id'] = user_id
        
        # Get session data for response
        session_data = session_manager.get_session(user_id)
        
        return jsonify({
            "user_id": user_id,
            "riasec_code": session_data['riasec_code'],
            "message": "User registered successfully",
            "active_sessions": session_manager.get_active_sessions_count()
        })
        
    except Exception as e:
        print(f"❌ Error in register_user: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/careers/recommendations')
def get_career_recommendations():
    try:
        user_id = session.get('user_id')
        
        if not user_id:
            print("❌ No user ID in session")
            return jsonify({"error": "User not registered"}), 400
        
        user_data = session_manager.get_session(user_id)
        
        if not user_data:
            print(f"❌ No user data found for ID: {user_id}")
            return jsonify({"error": "User session expired or not found"}), 400
        
        user_info = user_data['user_info']
        riasec_code = user_data['riasec_code']
        
        if not vector_db:
            return jsonify({"error": "Vector database not available"}), 500
        
        print(f"🔍 Performing advanced semantic search for user {user_id}...")
        print(f"   User: {user_info['name']}, RIASEC: {riasec_code}")
        
        # Use advanced semantic search
        recommendations = vector_db.advanced_search(
            user_profile=user_info,
            riasec_code=riasec_code,
            n_results=5
        )
        
        print(f"🎯 Found {len(recommendations)} career recommendations for user {user_id}")
        
        # Format recommendations for frontend
        processed_recommendations = []
        for career in recommendations:
            salary_range = extract_salary_range(career.get('salary_range_analysis', ''))
            
            processed_recommendations.append({
                "family_title": career.get('family_title', ''),
                "nco_title": career.get('nco_title', ''),
                "nco_code": career.get('nco_code', ''),
                "riasec_code": career.get('riasec_code', ''),
                "job_description": career.get('job_description', ''),
                "primary_skills": parse_skills_list(career.get('primary_skills', '')),
                "secondary_skills": parse_skills_list(career.get('secondary_skills', '')),
                "emerging_skills": parse_skills_list(career.get('emerging_skills', '')),
                "market_demand_score": career.get('market_demand_score', 0),
                "salary_range": salary_range,
                "industry_growth": career.get('industry_growth_projection', ''),
                "learning_pathway": career.get('learning_pathway_recommendations', ''),
                "match_percentage": career.get('match_percentage', 0),
                "matching_parameters": career.get('matching_parameters', []),
                "automation_risk": career.get('automation_risk', ''),
                "geographic_demand": career.get('geographic_demand_hotspots', '')
            })
        
        return jsonify({
            "user_info": user_info,
            "riasec_code": riasec_code,
            "recommendations": processed_recommendations,
            "session_id": user_id
        })
        
    except Exception as e:
        print(f"❌ Error in get_career_recommendations: {str(e)}")
        return jsonify({"error": str(e)}), 400

@app.route('/api/user/logout', methods=['POST'])
def logout_user():
    """Logout user and clear session"""
    try:
        user_id = session.get('user_id')
        if user_id:
            session_manager.delete_session(user_id)
            session.clear()
            return jsonify({"message": "User logged out successfully"})
        return jsonify({"message": "No active session"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Debug routes
@app.route('/api/debug/sessions')
def debug_sessions():
    """Debug endpoint to check active sessions"""
    session_manager.cleanup_expired_sessions()
    return jsonify({
        "active_sessions_count": session_manager.get_active_sessions_count(),
        "current_session_id": session.get('user_id'),
        "all_session_ids": list(session_manager.user_sessions.keys())
    })

@app.route('/api/debug/session/<user_id>')
def debug_session(user_id):
    """Debug specific session (without sensitive info)"""
    session_data = session_manager.get_session(user_id)
    if session_data:
        return jsonify({
            "user_id": user_id,
            "riasec_code": session_data['riasec_code'],
            "created_at": session_data['created_at'],
            "last_accessed": session_data['last_accessed'],
            "user_name": session_data['user_info']['name']
        })
    return jsonify({"error": "Session not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
