from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
import csv
import io
import aiohttp
import json
from google.oauth2 import id_token
from google.auth.transport import requests
import krakenex
import asyncio
import base64
import hmac
import hashlib
import time
import urllib.parse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer(auto_error=False)

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
class Exchange(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    display_name: str
    color: str = "#3B82F6"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ExchangeCreate(BaseModel):
    name: str
    display_name: str
    color: Optional[str] = "#3B82F6"

class KPI(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    target_amount: float
    color: str = "#3B82F6"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class KPICreate(BaseModel):
    name: str
    target_amount: float
    color: Optional[str] = "#3B82F6"

class ExchangeAPIKey(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    exchange_name: str  # kraken, binance, bitget
    api_key: str
    api_secret: str
    encrypted: bool = True
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None

class ExchangeAPIKeyCreate(BaseModel):
    exchange_name: str
    api_key: str
    api_secret: str

class DynamicBalance(BaseModel):
    exchange_id: str
    amount: float

class DynamicKPI(BaseModel):
    kpi_id: str
    progress: float

class PnLEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: date
    balances: List[DynamicBalance]
    total: float = 0.0
    pnl_percentage: float = 0.0
    pnl_amount: float = 0.0
    kpi_progress: List[DynamicKPI] = []
    notes: Optional[str] = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PnLEntryCreate(BaseModel):
    date: date
    balances: List[DynamicBalance]
    notes: Optional[str] = ""

class PnLEntryUpdate(BaseModel):
    date: Optional[date] = None
    balances: Optional[List[DynamicBalance]] = None
    notes: Optional[str] = None

# Kraken API Integration
class KrakenAPI:
    def __init__(self):
        self.api_url = "https://api.kraken.com"
        
    def _get_kraken_signature(self, urlpath, data, secret):
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = urlpath.encode() + hashlib.sha256(encoded).digest()
        
        mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()
    
    async def get_account_balance(self, api_key=None, private_key=None, user_id=None):
        """Get account balance from Kraken using user's API keys"""
        try:
            # If no API keys provided, try to get from user's stored keys
            if not api_key or not private_key:
                if user_id:
                    user_api_key = await db.exchange_api_keys.find_one({
                        "user_id": user_id,
                        "exchange_name": "kraken",
                        "is_active": True
                    })
                    if user_api_key:
                        api_key = user_api_key["api_key"]
                        private_key = user_api_key["api_secret"]
                    else:
                        # Fallback to environment variables (temporary)
                        api_key = os.environ.get('KRAKEN_API_KEY')
                        private_key = os.environ.get('KRAKEN_PRIVATE_KEY')
            
            if not api_key or not private_key:
                raise Exception("Kraken API credentials not configured")
            
            nonce = str(int(1000*time.time()))
            data = {'nonce': nonce}
            urlpath = '/0/private/Balance'
            
            headers = {
                'API-Key': api_key,
                'API-Sign': self._get_kraken_signature(urlpath, data, private_key)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}{urlpath}",
                    headers=headers,
                    data=data
                ) as response:
                    result = await response.json()
                    
                    if result.get('error'):
                        raise Exception(f"Kraken API error: {result['error']}")
                    
                    balances = result.get('result', {})
                    
                    # Debug: Log raw balances to understand the data
                    logger.info(f"Kraken raw balances: {balances}")
                    
                    # Convert to EUR value - focus on total balance regardless of asset type
                    total_eur = 0.0
                    asset_details = {}
                    
                    for asset, balance in balances.items():
                        balance_float = float(balance)
                        if balance_float > 0.01:  # Only count significant balances
                            asset_details[asset] = balance_float
                            
                            # More conservative EUR conversion
                            if asset in ['ZEUR', 'EUR']:
                                total_eur += balance_float
                                logger.info(f"EUR balance: {balance_float}")
                            elif asset in ['ZUSD', 'USD']:
                                eur_value = balance_float * 0.92  # USD to EUR
                                total_eur += eur_value
                                logger.info(f"USD balance: {balance_float}, EUR value: {eur_value}")
                            elif asset in ['BTC', 'XXBT', 'XBT']:
                                # Use more reasonable BTC price - around €40k not €58k
                                eur_value = balance_float * 40000
                                total_eur += eur_value
                                logger.info(f"BTC balance: {balance_float}, EUR value: {eur_value}")
                            elif asset in ['ETH', 'XETH']:
                                # Use more reasonable ETH price - around €2200
                                eur_value = balance_float * 2200
                                total_eur += eur_value
                                logger.info(f"ETH balance: {balance_float}, EUR value: {eur_value}")
                            else:
                                # For unknown assets, use very conservative estimate
                                eur_value = balance_float * 0.1  # Very conservative
                                total_eur += eur_value
                                logger.info(f"Unknown asset {asset}: {balance_float}, conservative EUR value: {eur_value}")
                    
                    logger.info(f"Total EUR calculated: {total_eur}")
                    
                    # Update last used timestamp
                    if user_id:
                        await db.exchange_api_keys.update_one(
                            {"user_id": user_id, "exchange_name": "kraken"},
                            {"$set": {"last_used": datetime.utcnow()}}
                        )
                    
                    return {
                        'success': True,
                        'balance_eur': round(total_eur, 2),
                        'raw_balances': balances,
                        'asset_details': asset_details,
                        'last_updated': datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching Kraken balance: {e}")
            return {
                'success': False,
                'error': str(e),
                'balance_eur': 0.0
            }

# Initialize Kraken API
kraken_api = KrakenAPI()

# Helper functions
async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[User]:
    """Get current user from session token"""
    session_token = None
    
    # Try to get session token from cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token and credentials:
        session_token = credentials.credentials
    
    if not session_token:
        return None
    
    try:
        # Find session in database
        session = await db.user_sessions.find_one({
            "session_token": session_token,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if not session:
            return None
        
        # Get user
        user = await db.users.find_one({"id": session["user_id"]})
        if not user:
            return None
        
        return User(**user)
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        return None

async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """Require authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

def calculate_pnl_metrics(current_total: float, previous_total: float) -> Dict[str, float]:
    """Calculate PnL percentage and amount"""
    if previous_total == 0:
        return {"pnl_percentage": 0.0, "pnl_amount": 0.0}
    
    pnl_amount = current_total - previous_total
    pnl_percentage = (pnl_amount / previous_total) * 100
    
    return {
        "pnl_percentage": round(pnl_percentage, 2),
        "pnl_amount": round(pnl_amount, 2)
    }

def calculate_kpi_progress(current_total: float, user_kpis: List[Dict]) -> List[Dict]:
    """Calculate progress towards dynamic KPI goals"""
    kpi_progress = []
    for kpi in user_kpis:
        progress = current_total - kpi["target_amount"]
        kpi_progress.append({
            "kpi_id": kpi["id"],
            "progress": round(progress, 2)
        })
    return kpi_progress

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Crypto PnL Tracker API"}

# Authentication Endpoints
# Authentication Endpoints
@api_router.post("/auth/google")
async def authenticate_with_google(request: Request, response: Response):
    """Authenticate user with Google OAuth token"""
    try:
        data = await request.json()
        token = data.get("token")
        
        if not token:
            raise HTTPException(status_code=400, detail="Google token required")
        
        # Verify Google token
        try:
            # You need to set your Google Client ID in environment variables
            GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-google-client-id.apps.googleusercontent.com')
            
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                GOOGLE_CLIENT_ID
            )
            
            # Get user info from Google token
            email = idinfo.get('email')
            name = idinfo.get('name')
            picture = idinfo.get('picture', '')
            
            if not email:
                raise HTTPException(status_code=400, detail="Invalid Google token")
                
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid Google token")
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": email})
        
        if not existing_user:
            # Create new user
            user = User(
                email=email,
                name=name,
                picture=picture
            )
            await db.users.insert_one(user.dict())
            user_id = user.id
        else:
            user_id = existing_user["id"]
            user = User(**existing_user)
        
        # Create session token
        session_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        user_session = UserSession(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        await db.user_sessions.insert_one(user_session.dict())
        
        # Set HttpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=True,
            samesite="none",
            path="/"
        )
        
        return {
            "user": user.dict(),
            "session_token": session_token,
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@api_router.post("/auth/profile")
async def authenticate_user(request: Request, response: Response):
    """Legacy endpoint - Authenticate user with session ID from OAuth provider"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Call OAuth auth API
        async with aiohttp.ClientSession() as session:
            headers = {"X-Session-ID": session_id}
            async with session.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers=headers
            ) as auth_response:
                if auth_response.status != 200:
                    raise HTTPException(status_code=401, detail="Invalid session")
                
                auth_data = await auth_response.json()
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": auth_data["email"]})
        
        if not existing_user:
            # Create new user
            user = User(
                email=auth_data["email"],
                name=auth_data["name"],
                picture=auth_data.get("picture", "")
            )
            await db.users.insert_one(user.dict())
            user_id = user.id
        else:
            user_id = existing_user["id"]
            user = User(**existing_user)
        
        # Create session token
        session_token = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        user_session = UserSession(
            user_id=user_id,
            session_token=session_token,
            expires_at=expires_at
        )
        
        await db.user_sessions.insert_one(user_session.dict())
        
        # Set HttpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session_token,
            max_age=7 * 24 * 60 * 60,  # 7 days
            httponly=True,
            secure=True,
            samesite="none",
            path="/"
        )
        
        return {
            "user": user.dict(),
            "session_token": session_token,
            "expires_at": expires_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    try:
        session_token = request.cookies.get("session_token")
        
        if session_token:
            # Remove session from database
            await db.user_sessions.delete_one({"session_token": session_token})
        
        # Clear cookie
        response.delete_cookie(
            key="session_token",
            path="/",
            secure=True,
            samesite="none"
        )
        
        return {"message": "Logged out successfully"}
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return current_user

# Exchange Management Endpoints
@api_router.get("/exchanges", response_model=List[Exchange])
async def get_exchanges(current_user: User = Depends(require_auth)):
    try:
        exchanges = await db.exchanges.find({
            "user_id": current_user.id,
            "is_active": True
        }).sort("name", 1).to_list(100)
        return [Exchange(**exchange) for exchange in exchanges]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/exchanges", response_model=Exchange)
async def create_exchange(exchange_data: ExchangeCreate, current_user: User = Depends(require_auth)):
    try:
        # Check if exchange name already exists for this user
        existing = await db.exchanges.find_one({
            "user_id": current_user.id,
            "name": exchange_data.name.lower()
        })
        if existing:
            raise HTTPException(status_code=400, detail="Exchange name already exists")
        
        exchange = Exchange(
            name=exchange_data.name.lower(),
            display_name=exchange_data.display_name,
            color=exchange_data.color
        )
        
        # Add user_id to exchange
        exchange_dict = exchange.dict()
        exchange_dict["user_id"] = current_user.id
        
        await db.exchanges.insert_one(exchange_dict)
        return exchange
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/exchanges/{exchange_id}")
async def delete_exchange(exchange_id: str, current_user: User = Depends(require_auth)):
    try:
        # Check if exchange belongs to user
        exchange = await db.exchanges.find_one({
            "id": exchange_id,
            "user_id": current_user.id
        })
        if not exchange:
            raise HTTPException(status_code=404, detail="Exchange not found")
        
        # Check if exchange is used in any entries
        entries_with_exchange = await db.pnl_entries.find_one({
            "user_id": current_user.id,
            "balances.exchange_id": exchange_id
        })
        
        if entries_with_exchange:
            # Just deactivate instead of deleting
            await db.exchanges.update_one(
                {"id": exchange_id, "user_id": current_user.id},
                {"$set": {"is_active": False}}
            )
            return {"message": "Exchange deactivated (used in historical entries)"}
        else:
            # Safe to delete
            result = await db.exchanges.delete_one({
                "id": exchange_id,
                "user_id": current_user.id
            })
            if result.deleted_count == 0:
                raise HTTPException(status_code=404, detail="Exchange not found")
            return {"message": "Exchange deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/initialize-default-exchanges")
async def initialize_default_exchanges(current_user: User = Depends(require_auth)):
    """Initialize default exchanges if none exist for this user"""
    try:
        count = await db.exchanges.count_documents({"user_id": current_user.id})
        if count == 0:
            default_exchanges = [
                {"name": "kraken", "display_name": "Kraken", "color": "#16A34A"},
                {"name": "bitget", "display_name": "Bitget", "color": "#F59E0B"},
                {"name": "binance", "display_name": "Binance", "color": "#EF4444"}
            ]
            
            for ex_data in default_exchanges:
                exchange = Exchange(**ex_data)
                exchange_dict = exchange.dict()
                exchange_dict["user_id"] = current_user.id
                await db.exchanges.insert_one(exchange_dict)
            
            return {"message": "Default exchanges initialized"}
        else:
            return {"message": "Exchanges already exist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# KPI Management Endpoints
@api_router.get("/kpis", response_model=List[KPI])
async def get_kpis(current_user: User = Depends(require_auth)):
    try:
        kpis = await db.kpis.find({
            "user_id": current_user.id,
            "is_active": True
        }).sort("target_amount", 1).to_list(100)
        return [KPI(**kpi) for kpi in kpis]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/kpis", response_model=KPI)
async def create_kpi(kpi_data: KPICreate, current_user: User = Depends(require_auth)):
    try:
        # Check if KPI with same target already exists for this user
        existing = await db.kpis.find_one({
            "user_id": current_user.id,
            "target_amount": kpi_data.target_amount
        })
        if existing:
            raise HTTPException(status_code=400, detail="KPI with this target amount already exists")
        
        kpi = KPI(
            name=kpi_data.name,
            target_amount=kpi_data.target_amount,
            color=kpi_data.color
        )
        
        # Add user_id to KPI
        kpi_dict = kpi.dict()
        kpi_dict["user_id"] = current_user.id
        
        await db.kpis.insert_one(kpi_dict)
        return kpi
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/kpis/{kpi_id}", response_model=KPI)
async def update_kpi(kpi_id: str, kpi_data: KPICreate, current_user: User = Depends(require_auth)):
    try:
        # Check if KPI belongs to user
        kpi = await db.kpis.find_one({
            "id": kpi_id,
            "user_id": current_user.id
        })
        if not kpi:
            raise HTTPException(status_code=404, detail="KPI not found")
        
        # Update KPI
        await db.kpis.update_one(
            {"id": kpi_id, "user_id": current_user.id},
            {"$set": {
                "name": kpi_data.name,
                "target_amount": kpi_data.target_amount,
                "color": kpi_data.color
            }}
        )
        
        # Get updated KPI
        updated_kpi = await db.kpis.find_one({"id": kpi_id, "user_id": current_user.id})
        
        # Recalculate all entries for this user
        await recalculate_all_entries(current_user.id)
        
        return KPI(**updated_kpi)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/kpis/{kpi_id}")
async def delete_kpi(kpi_id: str, current_user: User = Depends(require_auth)):
    try:
        # Check if KPI belongs to user
        kpi = await db.kpis.find_one({
            "id": kpi_id,
            "user_id": current_user.id
        })
        if not kpi:
            raise HTTPException(status_code=404, detail="KPI not found")
        
        # Delete KPI
        result = await db.kpis.delete_one({
            "id": kpi_id,
            "user_id": current_user.id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="KPI not found")
        
        # Recalculate all entries for this user
        await recalculate_all_entries(current_user.id)
        
        return {"message": "KPI deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/initialize-default-kpis")
async def initialize_default_kpis(current_user: User = Depends(require_auth)):
    """Initialize default KPIs if none exist for this user"""
    try:
        count = await db.kpis.count_documents({"user_id": current_user.id})
        if count == 0:
            default_kpis = [
                {"name": "5K Goal", "target_amount": 5000, "color": "#10B981"},
                {"name": "10K Goal", "target_amount": 10000, "color": "#F59E0B"},
                {"name": "15K Goal", "target_amount": 15000, "color": "#EF4444"}
            ]
            
            for kpi_data in default_kpis:
                kpi = KPI(**kpi_data)
                kpi_dict = kpi.dict()
                kpi_dict["user_id"] = current_user.id
                await db.kpis.insert_one(kpi_dict)
            
            return {"message": "Default KPIs initialized"}
        else:
            return {"message": "KPIs already exist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/entries", response_model=PnLEntry)
async def create_pnl_entry(entry_data: PnLEntryCreate, current_user: User = Depends(require_auth)):
    try:
        # Calculate total from dynamic balances
        total = sum(balance.amount for balance in entry_data.balances)
        
        # Get previous entry for PnL calculation
        previous_entry = await db.pnl_entries.find_one(
            {
                "user_id": current_user.id,
                "date": {"$lt": entry_data.date.isoformat()}
            }, 
            sort=[("date", -1)]
        )
        
        previous_total = previous_entry["total"] if previous_entry else total
        
        # Get user's KPIs
        user_kpis = await db.kpis.find({
            "user_id": current_user.id,
            "is_active": True
        }).to_list(100)
        
        # Calculate metrics
        pnl_metrics = calculate_pnl_metrics(total, previous_total)
        kpi_progress = calculate_kpi_progress(total, user_kpis)
        
        # Create entry
        entry = PnLEntry(
            date=entry_data.date,
            balances=entry_data.balances,
            total=round(total, 2),
            pnl_percentage=pnl_metrics["pnl_percentage"],
            pnl_amount=pnl_metrics["pnl_amount"],
            kpi_progress=[DynamicKPI(**kpi) for kpi in kpi_progress],
            notes=entry_data.notes
        )
        
        # Insert into database
        entry_dict = entry.dict()
        entry_dict["date"] = entry_dict["date"].isoformat()  # Convert date to string
        entry_dict["balances"] = [balance.dict() for balance in entry.balances]
        entry_dict["kpi_progress"] = [kpi.dict() for kpi in entry.kpi_progress]
        entry_dict["user_id"] = current_user.id
        await db.pnl_entries.insert_one(entry_dict)
        
        # Recalculate PnL for subsequent entries
        await recalculate_subsequent_entries(entry_data.date, current_user.id)
        
        return entry
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Real-Time Exchange Integration Endpoints
@api_router.get("/exchanges/kraken/balance")
async def get_kraken_balance(current_user: User = Depends(require_auth)):
    """Get real-time balance from Kraken"""
    try:
        balance_data = await kraken_api.get_account_balance(user_id=current_user.id)
        return balance_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/exchanges/sync")
async def sync_exchange_balances(current_user: User = Depends(require_auth), background_tasks: BackgroundTasks = None):
    """Sync balances from all connected exchanges"""
    try:
        # Get current exchanges for this user
        exchanges = await db.exchanges.find({
            "user_id": current_user.id,
            "is_active": True
        }).to_list(100)
        
        sync_results = {}
        total_balance = 0.0
        balances = []
        
        # Sync each exchange
        for exchange in exchanges:
            if exchange["name"] == "kraken":
                balance_data = await kraken_api.get_account_balance(user_id=current_user.id)
                if balance_data['success']:
                    sync_results['kraken'] = {
                        'success': True,
                        'balance': balance_data['balance_eur'],
                        'last_updated': balance_data['last_updated']
                    }
                    total_balance += balance_data['balance_eur']
                    balances.append({
                        'exchange_id': exchange['id'],
                        'amount': balance_data['balance_eur']
                    })
                else:
                    sync_results['kraken'] = {
                        'success': False,
                        'error': balance_data.get('error', 'Unknown error')
                    }
            
            # TODO: Add Binance and Bitget when you provide their APIs
            elif exchange["name"] == "binance":
                sync_results['binance'] = {'success': False, 'error': 'API not configured yet'}
            elif exchange["name"] == "bitget":
                sync_results['bitget'] = {'success': False, 'error': 'API not configured yet'}
        
        return {
            'sync_results': sync_results,
            'suggested_entry': {
                'date': datetime.utcnow().date().isoformat(),
                'balances': balances,
                'total': round(total_balance, 2),
                'notes': f"Auto-synced at {datetime.utcnow().strftime('%H:%M UTC')}"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/entries/auto-create")
async def auto_create_entry_from_sync(
    current_user: User = Depends(require_auth),
    auto_sync: bool = True
):
    """Automatically create today's entry from real-time exchange data"""
    try:
        # First sync the balances
        exchanges = await db.exchanges.find({
            "user_id": current_user.id,
            "is_active": True
        }).to_list(100)
        
        balances = []
        total_balance = 0.0
        
        # Get real-time data from each exchange
        for exchange in exchanges:
            if exchange["name"] == "kraken":
                balance_data = await kraken_api.get_account_balance(user_id=current_user.id)
                if balance_data['success']:
                    balances.append({
                        'exchange_id': exchange['id'],
                        'amount': balance_data['balance_eur']
                    })
                    total_balance += balance_data['balance_eur']
        
        if not balances:
            raise HTTPException(status_code=400, detail="No exchange balances available")
        
        # Check if entry for today already exists
        today = datetime.utcnow().date()
        existing_entry = await db.pnl_entries.find_one({
            "user_id": current_user.id,
            "date": today.isoformat()
        })
        
        if existing_entry:
            return {
                "message": "Entry for today already exists",
                "existing_entry_id": existing_entry.get("id", "unknown"),
                "suggested_balances": balances
            }
        
        # Create entry manually without Pydantic models to avoid serialization issues
        entry_id = str(uuid.uuid4())
        
        # Get previous entry for PnL calculation
        previous_entry = await db.pnl_entries.find_one(
            {
                "user_id": current_user.id,
                "date": {"$lt": today.isoformat()}
            }, 
            sort=[("date", -1)]
        )
        
        previous_total = previous_entry["total"] if previous_entry else total_balance
        
        # Get user's KPIs
        user_kpis = await db.kpis.find({
            "user_id": current_user.id,
            "is_active": True
        }).to_list(100)
        
        # Calculate metrics
        pnl_metrics = calculate_pnl_metrics(total_balance, previous_total)
        kpi_progress = calculate_kpi_progress(total_balance, user_kpis)
        
        # Create entry dict directly
        entry_dict = {
            "id": entry_id,
            "user_id": current_user.id,
            "date": today.isoformat(),
            "balances": balances,
            "total": round(total_balance, 2),
            "pnl_percentage": pnl_metrics["pnl_percentage"],
            "pnl_amount": pnl_metrics["pnl_amount"],
            "kpi_progress": kpi_progress,
            "notes": f"Auto-created from real-time sync at {datetime.utcnow().strftime('%H:%M UTC')}",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Insert directly into database
        await db.pnl_entries.insert_one(entry_dict)
        
        # Recalculate PnL for subsequent entries
        await recalculate_subsequent_entries(today, current_user.id)
        
        return {
            "message": "Entry created successfully from real-time data",
            "entry_id": entry_id,
            "total_balance": round(total_balance, 2),
            "pnl_percentage": pnl_metrics["pnl_percentage"],
            "pnl_amount": pnl_metrics["pnl_amount"],
            "synced_exchanges": len(balances)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto_create_entry_from_sync: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating entry: {str(e)}")

# Internal function for creating entries (extracted from the main endpoint)
async def create_pnl_entry_internal(entry_data: PnLEntryCreate, current_user: User):
    """Internal function to create PnL entry"""
    # Calculate total from dynamic balances
    total = sum(balance.amount for balance in entry_data.balances)
    
    # Get previous entry for PnL calculation
    previous_entry = await db.pnl_entries.find_one(
        {
            "user_id": current_user.id,
            "date": {"$lt": entry_data.date.isoformat()}
        }, 
        sort=[("date", -1)]
    )
    
    previous_total = previous_entry["total"] if previous_entry else total
    
    # Get user's KPIs
    user_kpis = await db.kpis.find({
        "user_id": current_user.id,
        "is_active": True
    }).to_list(100)
    
    # Calculate metrics
    pnl_metrics = calculate_pnl_metrics(total, previous_total)
    kpi_progress = calculate_kpi_progress(total, user_kpis)
    
    # Create entry
    entry = PnLEntry(
        date=entry_data.date,
        balances=entry_data.balances,
        total=round(total, 2),
        pnl_percentage=pnl_metrics["pnl_percentage"],
        pnl_amount=pnl_metrics["pnl_amount"],
        kpi_progress=[DynamicKPI(**kpi) for kpi in kpi_progress],
        notes=entry_data.notes
    )
    
    # Insert into database
    entry_dict = entry.dict()
    entry_dict["date"] = entry_dict["date"].isoformat()
    entry_dict["balances"] = [balance.dict() for balance in entry.balances]
    entry_dict["kpi_progress"] = [kpi.dict() for kpi in entry.kpi_progress]
    entry_dict["user_id"] = current_user.id
    await db.pnl_entries.insert_one(entry_dict)
    
    # Recalculate PnL for subsequent entries
    await recalculate_subsequent_entries(entry_data.date, current_user.id)
    
    # Return dict instead of Pydantic model to avoid serialization issues
    return {
        "id": entry.id,
        "date": entry.date.isoformat(),
        "balances": [balance.dict() for balance in entry.balances],
        "total": entry.total,
        "pnl_percentage": entry.pnl_percentage,
        "pnl_amount": entry.pnl_amount,
        "kpi_progress": [kpi.dict() for kpi in entry.kpi_progress],
        "notes": entry.notes,
        "created_at": entry.created_at.isoformat()
    }

@api_router.get("/entries", response_model=List[PnLEntry])
async def get_pnl_entries(current_user: User = Depends(require_auth), limit: int = 100):
    try:
        entries = await db.pnl_entries.find({
            "user_id": current_user.id
        }).sort("date", -1).limit(limit).to_list(limit)
        result = []
        for entry in entries:
            # Convert balances back to Pydantic models
            entry["balances"] = [DynamicBalance(**balance) for balance in entry["balances"]]
            # Convert KPI progress back to Pydantic models
            entry["kpi_progress"] = [DynamicKPI(**kpi) for kpi in entry.get("kpi_progress", [])]
            result.append(PnLEntry(**entry))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/entries/{entry_id}", response_model=PnLEntry)
async def get_pnl_entry(entry_id: str, current_user: User = Depends(require_auth)):
    try:
        entry = await db.pnl_entries.find_one({
            "id": entry_id,
            "user_id": current_user.id
        })
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        # Convert balances back to Pydantic models
        entry["balances"] = [DynamicBalance(**balance) for balance in entry["balances"]]
        # Convert KPI progress back to Pydantic models  
        entry["kpi_progress"] = [DynamicKPI(**kpi) for kpi in entry.get("kpi_progress", [])]
        return PnLEntry(**entry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/entries/{entry_id}", response_model=PnLEntry)
async def update_pnl_entry(entry_id: str, update_data: PnLEntryUpdate):
    try:
        entry = await db.pnl_entries.find_one({"id": entry_id})
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        # Update fields
        update_dict = {}
        if update_data.date:
            update_dict["date"] = update_data.date.isoformat()
        if update_data.balances:
            update_dict["balances"] = [balance.dict() for balance in update_data.balances]
            # Recalculate total
            total = sum(balance.amount for balance in update_data.balances)
            update_dict["total"] = round(total, 2)
            
            # Recalculate KPI progress
            kpi_progress = calculate_kpi_progress(total)
            update_dict.update(kpi_progress)
            
        if update_data.notes is not None:
            update_dict["notes"] = update_data.notes
        
        # Update in database
        await db.pnl_entries.update_one({"id": entry_id}, {"$set": update_dict})
        
        # Get updated entry
        updated_entry = await db.pnl_entries.find_one({"id": entry_id})
        
        # Recalculate PnL for this and subsequent entries
        if update_data.balances or update_data.date:
            entry_date = update_data.date if update_data.date else datetime.fromisoformat(entry["date"]).date()
            await recalculate_subsequent_entries(entry_date)
        
        # Convert back to Pydantic model
        updated_entry["balances"] = [DynamicBalance(**balance) for balance in updated_entry["balances"]]
        return PnLEntry(**updated_entry)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/entries/{entry_id}")
async def delete_pnl_entry(entry_id: str):
    try:
        entry = await db.pnl_entries.find_one({"id": entry_id})
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        entry_date = datetime.fromisoformat(entry["date"]).date()
        
        # Delete entry
        await db.pnl_entries.delete_one({"id": entry_id})
        
        # Recalculate PnL for subsequent entries
        await recalculate_subsequent_entries(entry_date)
        
        return {"message": "Entry deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/stats")
async def get_portfolio_stats():
    try:
        # Get latest entry
        latest_entry = await db.pnl_entries.find_one(sort=[("date", -1)])
        if not latest_entry:
            return {
                "total_entries": 0,
                "total_balance": 0,
                "daily_pnl": 0,
                "daily_pnl_percentage": 0,
                "avg_daily_pnl": 0,
                "avg_daily_pnl_percentage": 0,
                "avg_monthly_pnl_percentage": 0,
                "kpi_progress": {"5k": 0, "10k": 0, "15k": 0}
            }
        
        # Get total entries count
        total_entries = await db.pnl_entries.count_documents({})
        
        # Calculate average daily PnL (amount and percentage)
        pipeline_amount = [
            {"$match": {"pnl_amount": {"$ne": 0}}},
            {"$group": {"_id": None, "avg_pnl": {"$avg": "$pnl_amount"}}}
        ]
        avg_amount_result = await db.pnl_entries.aggregate(pipeline_amount).to_list(1)
        avg_daily_pnl = avg_amount_result[0]["avg_pnl"] if avg_amount_result else 0
        
        pipeline_percentage = [
            {"$match": {"pnl_percentage": {"$ne": 0}}},
            {"$group": {"_id": None, "avg_pnl_pct": {"$avg": "$pnl_percentage"}}}
        ]
        avg_pct_result = await db.pnl_entries.aggregate(pipeline_percentage).to_list(1)
        avg_daily_pnl_percentage = avg_pct_result[0]["avg_pnl_pct"] if avg_pct_result else 0
        
        # Calculate average monthly PnL percentage
        monthly_pipeline = [
            {"$match": {"pnl_percentage": {"$ne": 0}}},
            {"$addFields": {
                "year": {"$year": {"$dateFromString": {"dateString": "$date"}}},
                "month": {"$month": {"$dateFromString": {"dateString": "$date"}}}
            }},
            {"$group": {
                "_id": {"year": "$year", "month": "$month"},
                "monthly_pnl": {"$sum": "$pnl_percentage"}
            }},
            {"$group": {
                "_id": None,
                "avg_monthly_pnl": {"$avg": "$monthly_pnl"}
            }}
        ]
        monthly_result = await db.pnl_entries.aggregate(monthly_pipeline).to_list(1)
        avg_monthly_pnl_percentage = monthly_result[0]["avg_monthly_pnl"] if monthly_result else 0
        
        return {
            "total_entries": total_entries,
            "total_balance": latest_entry["total"],
            "daily_pnl": latest_entry["pnl_amount"],
            "daily_pnl_percentage": latest_entry["pnl_percentage"],
            "avg_daily_pnl": round(avg_daily_pnl, 2),
            "avg_daily_pnl_percentage": round(avg_daily_pnl_percentage, 2),
            "avg_monthly_pnl_percentage": round(avg_monthly_pnl_percentage, 2),
            "kpi_progress": {
                "5k": latest_entry["kpi_5k"],
                "10k": latest_entry["kpi_10k"],
                "15k": latest_entry["kpi_15k"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/monthly-performance")
async def get_monthly_performance():
    """Get monthly performance data showing best/worst months"""
    try:
        pipeline = [
            {"$match": {"pnl_percentage": {"$ne": 0}}},
            {"$addFields": {
                "year": {"$year": {"$dateFromString": {"dateString": "$date"}}},
                "month": {"$month": {"$dateFromString": {"dateString": "$date"}}}
            }},
            {"$group": {
                "_id": {"year": "$year", "month": "$month"},
                "monthly_pnl_percentage": {"$sum": "$pnl_percentage"},
                "monthly_pnl_amount": {"$sum": "$pnl_amount"},
                "trading_days": {"$sum": 1},
                "avg_daily_pnl": {"$avg": "$pnl_percentage"}
            }},
            {"$addFields": {
                "month_name": {
                    "$switch": {
                        "branches": [
                            {"case": {"$eq": ["$_id.month", 1]}, "then": "January"},
                            {"case": {"$eq": ["$_id.month", 2]}, "then": "February"},
                            {"case": {"$eq": ["$_id.month", 3]}, "then": "March"},
                            {"case": {"$eq": ["$_id.month", 4]}, "then": "April"},
                            {"case": {"$eq": ["$_id.month", 5]}, "then": "May"},
                            {"case": {"$eq": ["$_id.month", 6]}, "then": "June"},
                            {"case": {"$eq": ["$_id.month", 7]}, "then": "July"},
                            {"case": {"$eq": ["$_id.month", 8]}, "then": "August"},
                            {"case": {"$eq": ["$_id.month", 9]}, "then": "September"},
                            {"case": {"$eq": ["$_id.month", 10]}, "then": "October"},
                            {"case": {"$eq": ["$_id.month", 11]}, "then": "November"},
                            {"case": {"$eq": ["$_id.month", 12]}, "then": "December"}
                        ],
                        "default": "Unknown"
                    }
                }
            }},
            {"$sort": {"_id.year": -1, "_id.month": -1}}
        ]
        
        monthly_data = await db.pnl_entries.aggregate(pipeline).to_list(100)
        
        if not monthly_data:
            return {
                "monthly_performance": [],
                "best_month": None,
                "worst_month": None,
                "yearly_summary": []
            }
        
        # Find best and worst months
        best_month = max(monthly_data, key=lambda x: x["monthly_pnl_percentage"])
        worst_month = min(monthly_data, key=lambda x: x["monthly_pnl_percentage"])
        
        # Prepare monthly performance data
        performance_data = []
        for month in monthly_data:
            performance_data.append({
                "year": month["_id"]["year"],
                "month": month["_id"]["month"],
                "month_name": month["month_name"],
                "monthly_pnl_percentage": round(month["monthly_pnl_percentage"], 2),
                "monthly_pnl_amount": round(month["monthly_pnl_amount"], 2),
                "trading_days": month["trading_days"],
                "avg_daily_pnl": round(month["avg_daily_pnl"], 2),
                "display_name": f"{month['month_name']} {month['_id']['year']}"
            })
        
        # Yearly summary
        yearly_pipeline = [
            {"$match": {"pnl_percentage": {"$ne": 0}}},
            {"$addFields": {
                "year": {"$year": {"$dateFromString": {"dateString": "$date"}}}
            }},
            {"$group": {
                "_id": "$year",
                "yearly_pnl_percentage": {"$sum": "$pnl_percentage"},
                "yearly_pnl_amount": {"$sum": "$pnl_amount"},
                "trading_days": {"$sum": 1},
                "months_active": {"$addToSet": {"$month": {"$dateFromString": {"dateString": "$date"}}}}
            }},
            {"$addFields": {
                "months_count": {"$size": "$months_active"},
                "avg_monthly_pnl": {"$divide": ["$yearly_pnl_percentage", {"$size": "$months_active"}]}
            }},
            {"$sort": {"_id": -1}}
        ]
        
        yearly_data = await db.pnl_entries.aggregate(yearly_pipeline).to_list(10)
        yearly_summary = []
        for year in yearly_data:
            yearly_summary.append({
                "year": year["_id"],
                "yearly_pnl_percentage": round(year["yearly_pnl_percentage"], 2),
                "yearly_pnl_amount": round(year["yearly_pnl_amount"], 2),
                "trading_days": year["trading_days"],
                "months_active": year["months_count"],
                "avg_monthly_pnl": round(year["avg_monthly_pnl"], 2)
            })
        
        return {
            "monthly_performance": performance_data,
            "best_month": {
                "display_name": f"{best_month['month_name']} {best_month['_id']['year']}",
                "pnl_percentage": round(best_month["monthly_pnl_percentage"], 2),
                "pnl_amount": round(best_month["monthly_pnl_amount"], 2),
                "trading_days": best_month["trading_days"]
            },
            "worst_month": {
                "display_name": f"{worst_month['month_name']} {worst_month['_id']['year']}",
                "pnl_percentage": round(worst_month["monthly_pnl_percentage"], 2),
                "pnl_amount": round(worst_month["monthly_pnl_amount"], 2),
                "trading_days": worst_month["trading_days"]
            },
            "yearly_summary": yearly_summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/export/csv")
async def export_entries_csv():
    """Export all entries to CSV format"""
    try:
        entries = await db.pnl_entries.find().sort("date", -1).to_list(1000)
        exchanges = await db.exchanges.find({"is_active": True}).to_list(100)
        
        # Create exchange lookup
        exchange_lookup = {ex["id"]: ex for ex in exchanges}
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Create dynamic header
        header = ['Date']
        exchange_names = [ex["display_name"] for ex in exchanges]
        header.extend(exchange_names)
        header.extend(['Total', 'PnL %', 'PnL €', 'KPI 5K', 'KPI 10K', 'KPI 15K', 'Notes'])
        writer.writerow(header)
        
        # Write data
        for entry in entries:
            row = [entry['date']]
            
            # Add exchange balances in order
            for exchange in exchanges:
                balance = next((b["amount"] for b in entry["balances"] if b["exchange_id"] == exchange["id"]), 0)
                row.append(f"{balance:.2f}")
            
            # Add other fields
            row.extend([
                f"{entry['total']:.2f}",
                f"{entry['pnl_percentage']:.2f}%",
                f"{entry['pnl_amount']:.2f}",
                f"{entry['kpi_5k']:.2f}",
                f"{entry['kpi_10k']:.2f}",
                f"{entry['kpi_15k']:.2f}",
                entry.get('notes', '')
            ])
            
            writer.writerow(row)
        
        output.seek(0)
        
        # Return as streaming response
        return StreamingResponse(
            io.StringIO(output.getvalue()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=crypto_pnl_data.csv"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/chart-data")
async def get_chart_data():
    """Get data formatted for charts"""
    try:
        entries = await db.pnl_entries.find().sort("date", 1).to_list(1000)
        exchanges = await db.exchanges.find({"is_active": True}).to_list(100)
        
        if not entries:
            return {
                "portfolio_timeline": [],
                "pnl_timeline": [],
                "exchange_breakdown": {}
            }
        
        # Create exchange lookup
        exchange_lookup = {ex["id"]: ex for ex in exchanges}
        
        # Portfolio timeline data
        portfolio_timeline = []
        pnl_timeline = []
        
        for entry in entries:
            timeline_entry = {
                "date": entry["date"],
                "total": entry["total"]
            }
            
            # Add exchange balances dynamically
            for balance in entry["balances"]:
                exchange = exchange_lookup.get(balance["exchange_id"])
                if exchange:
                    timeline_entry[exchange["name"]] = balance["amount"]
            
            portfolio_timeline.append(timeline_entry)
            
            if entry["pnl_percentage"] != 0:  # Skip first entry with 0 PnL
                pnl_timeline.append({
                    "date": entry["date"],
                    "pnl_percentage": entry["pnl_percentage"],
                    "pnl_amount": entry["pnl_amount"]
                })
        
        # Latest exchange breakdown
        latest = entries[-1]
        exchange_breakdown = {}
        for balance in latest["balances"]:
            exchange = exchange_lookup.get(balance["exchange_id"])
            if exchange:
                exchange_breakdown[exchange["name"]] = {
                    "amount": balance["amount"],
                    "display_name": exchange["display_name"],
                    "color": exchange["color"]
                }
        
        return {
            "portfolio_timeline": portfolio_timeline,
            "pnl_timeline": pnl_timeline,
            "exchange_breakdown": exchange_breakdown
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Exchange API Key Management
@api_router.get("/exchange-api-keys")
async def get_user_api_keys(current_user: User = Depends(require_auth)):
    """Get user's exchange API keys (returns only metadata, not the actual keys)"""
    try:
        api_keys = await db.exchange_api_keys.find({
            "user_id": current_user.id,
            "is_active": True
        }).to_list(100)
        
        # Return only safe metadata
        safe_keys = []
        for key in api_keys:
            safe_keys.append({
                "id": key["id"],
                "exchange_name": key["exchange_name"],
                "api_key_preview": key["api_key"][:8] + "..." if key["api_key"] else "Not set",
                "created_at": key["created_at"],
                "last_used": key.get("last_used"),
                "is_active": key["is_active"]
            })
        
        return safe_keys
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/exchange-api-keys")
async def add_exchange_api_key(api_key_data: ExchangeAPIKeyCreate, current_user: User = Depends(require_auth)):
    """Add or update exchange API key for user"""
    try:
        # Check if API key already exists for this exchange
        existing = await db.exchange_api_keys.find_one({
            "user_id": current_user.id,
            "exchange_name": api_key_data.exchange_name
        })
        
        if existing:
            # Update existing
            await db.exchange_api_keys.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "api_key": api_key_data.api_key,
                    "api_secret": api_key_data.api_secret,
                    "is_active": True,
                    "created_at": datetime.utcnow()
                }}
            )
            return {"message": f"{api_key_data.exchange_name} API key updated successfully"}
        else:
            # Create new
            api_key = ExchangeAPIKey(
                user_id=current_user.id,
                exchange_name=api_key_data.exchange_name,
                api_key=api_key_data.api_key,
                api_secret=api_key_data.api_secret
            )
            
            await db.exchange_api_keys.insert_one(api_key.dict())
            return {"message": f"{api_key_data.exchange_name} API key added successfully"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/exchange-api-keys/{exchange_name}")
async def delete_exchange_api_key(exchange_name: str, current_user: User = Depends(require_auth)):
    """Delete exchange API key"""
    try:
        result = await db.exchange_api_keys.update_one(
            {"user_id": current_user.id, "exchange_name": exchange_name},
            {"$set": {"is_active": False}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return {"message": f"{exchange_name} API key removed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def recalculate_all_entries(user_id: str):
    """Recalculate all entries for a specific user (used when KPIs change)"""
    try:
        # Get all entries for this user
        entries = await db.pnl_entries.find({
            "user_id": user_id
        }).sort("date", 1).to_list(1000)
        
        # Get user's KPIs
        user_kpis = await db.kpis.find({
            "user_id": user_id,
            "is_active": True
        }).to_list(100)
        
        for i, entry in enumerate(entries):
            # Calculate current total from balances
            current_total = sum(balance["amount"] for balance in entry["balances"])
            
            # Get previous entry for PnL calculation
            if i == 0:
                previous_total = current_total  # First entry has no previous
            else:
                previous_total = entries[i-1]["total"]
            
            # Calculate new PnL metrics
            pnl_metrics = calculate_pnl_metrics(current_total, previous_total)
            
            # Calculate KPI progress
            kpi_progress = calculate_kpi_progress(current_total, user_kpis)
            
            # Update entry
            await db.pnl_entries.update_one(
                {"id": entry["id"], "user_id": user_id},
                {"$set": {
                    "total": round(current_total, 2),
                    "kpi_progress": kpi_progress,
                    **pnl_metrics
                }}
            )
            
    except Exception as e:
        print(f"Error recalculating all entries: {e}")

async def recalculate_subsequent_entries(from_date: date, user_id: str):
    """Recalculate PnL for entries from the given date onwards for a specific user"""
    try:
        # Get all entries from the date onwards for this user
        entries = await db.pnl_entries.find({
            "user_id": user_id,
            "date": {"$gte": from_date.isoformat()}
        }).sort("date", 1).to_list(1000)
        
        for i, entry in enumerate(entries):
            # Calculate current total from balances
            current_total = sum(balance["amount"] for balance in entry["balances"])
            
            # Get previous entry for PnL calculation
            if i == 0:
                previous_entry = await db.pnl_entries.find_one({
                    "user_id": user_id,
                    "date": {"$lt": entry["date"]}
                }, sort=[("date", -1)])
                previous_total = previous_entry["total"] if previous_entry else current_total
            else:
                previous_total = entries[i-1]["total"]
            
            # Calculate new PnL metrics
            pnl_metrics = calculate_pnl_metrics(current_total, previous_total)
            
            # Update entry
            await db.pnl_entries.update_one(
                {"id": entry["id"], "user_id": user_id},
                {"$set": {
                    "total": round(current_total, 2),
                    **pnl_metrics
                }}
            )
            
    except Exception as e:
        print(f"Error recalculating entries: {e}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()