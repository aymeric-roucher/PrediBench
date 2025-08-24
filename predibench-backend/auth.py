import json
import os
from functools import wraps
from typing import Optional

import firebase_admin
from firebase_admin import auth, credentials, firestore
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account"""
    if not firebase_admin._apps:
        service_account_path = '/Users/charlesazam/charloupioupiou/market-bench/predibench-backend/serviceAccountKey.json'
        
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
        else:
            # Initialize without service account credentials (will use default credentials or environment)
            firebase_admin.initialize_app()
    
    return firestore.client(database_id='predibench-db')

# HTTP Bearer token security
security = HTTPBearer()

class FirebaseAuth:
    def __init__(self):
        self.db = initialize_firebase()
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """Verify Firebase ID token and return user info"""
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(credentials.credentials)
            user_id = decoded_token['uid']
            email = decoded_token.get('email')
            
            return {
                "uid": user_id,
                "email": email,
                "token": credentials.credentials
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    async def verify_agent_token(self, agent_token: str) -> Optional[dict]:
        """Verify agent token and return agent info"""
        try:
            # Query Firestore to find the agent with this token
            agents_ref = self.db.collection_group('agents')
            query = agents_ref.where('token', '==', agent_token).limit(1)
            docs = query.stream()
            
            for doc in docs:
                agent_data = doc.to_dict()
                # Extract user ID from document path
                user_id = doc.reference.parent.parent.id
                
                return {
                    "agent_id": doc.id,
                    "user_id": user_id,
                    "agent_name": agent_data.get("name"),
                    "token": agent_token,
                    "created_at": agent_data.get("createdAt")
                }
                
            return None
        except Exception as e:
            print(f"Error verifying agent token: {e}")
            return None

# Create global instance
firebase_auth = FirebaseAuth()

# Dependency functions
async def get_current_user(user: dict = Depends(firebase_auth.verify_token)) -> dict:
    """Dependency to get current authenticated user"""
    return user

async def verify_agent_token_dependency(agent_token: str) -> dict:
    """Dependency to verify agent token from request"""
    agent_info = await firebase_auth.verify_agent_token(agent_token)
    if not agent_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent token"
        )
    return agent_info

# Decorator for endpoints that require authentication
def require_auth(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # This decorator can be used for additional auth logic if needed
        return await func(*args, **kwargs)
    return wrapper