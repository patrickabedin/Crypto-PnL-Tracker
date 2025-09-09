from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, date
from decimal import Decimal
import csv
import io

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

# Pydantic Models
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

class DynamicBalance(BaseModel):
    exchange_id: str
    amount: float

class PnLEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: date
    balances: List[DynamicBalance]
    total: float = 0.0
    pnl_percentage: float = 0.0
    pnl_amount: float = 0.0
    kpi_5k: float = 0.0
    kpi_10k: float = 0.0
    kpi_15k: float = 0.0
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

# Helper functions
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

def calculate_kpi_progress(current_total: float) -> Dict[str, float]:
    """Calculate progress towards KPI goals"""
    return {
        "kpi_5k": round(current_total - 5000, 2),
        "kpi_10k": round(current_total - 10000, 2),
        "kpi_15k": round(current_total - 15000, 2)
    }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Crypto PnL Tracker API"}

# Exchange Management Endpoints
@api_router.get("/exchanges", response_model=List[Exchange])
async def get_exchanges():
    try:
        exchanges = await db.exchanges.find({"is_active": True}).sort("name", 1).to_list(100)
        return [Exchange(**exchange) for exchange in exchanges]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/exchanges", response_model=Exchange)
async def create_exchange(exchange_data: ExchangeCreate):
    try:
        # Check if exchange name already exists
        existing = await db.exchanges.find_one({"name": exchange_data.name.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Exchange name already exists")
        
        exchange = Exchange(
            name=exchange_data.name.lower(),
            display_name=exchange_data.display_name,
            color=exchange_data.color
        )
        
        await db.exchanges.insert_one(exchange.dict())
        return exchange
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/exchanges/{exchange_id}")
async def delete_exchange(exchange_id: str):
    try:
        # Check if exchange is used in any entries
        entries_with_exchange = await db.pnl_entries.find_one({
            "balances.exchange_id": exchange_id
        })
        
        if entries_with_exchange:
            # Just deactivate instead of deleting
            await db.exchanges.update_one(
                {"id": exchange_id},
                {"$set": {"is_active": False}}
            )
            return {"message": "Exchange deactivated (used in historical entries)"}
        else:
            # Safe to delete
            result = await db.exchanges.delete_one({"id": exchange_id})
            if result.deleted_count == 0:
                raise HTTPException(status_code=404, detail="Exchange not found")
            return {"message": "Exchange deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/initialize-default-exchanges")
async def initialize_default_exchanges():
    """Initialize default exchanges if none exist"""
    try:
        count = await db.exchanges.count_documents({})
        if count == 0:
            default_exchanges = [
                {"name": "kraken", "display_name": "Kraken", "color": "#16A34A"},
                {"name": "bitget", "display_name": "Bitget", "color": "#F59E0B"},
                {"name": "binance", "display_name": "Binance", "color": "#EF4444"}
            ]
            
            for ex_data in default_exchanges:
                exchange = Exchange(**ex_data)
                await db.exchanges.insert_one(exchange.dict())
            
            return {"message": "Default exchanges initialized"}
        else:
            return {"message": "Exchanges already exist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/entries", response_model=PnLEntry)
async def create_pnl_entry(entry_data: PnLEntryCreate):
    try:
        # Calculate total from dynamic balances
        total = sum(balance.amount for balance in entry_data.balances)
        
        # Get previous entry for PnL calculation
        previous_entry = await db.pnl_entries.find_one(
            {"date": {"$lt": entry_data.date.isoformat()}}, 
            sort=[("date", -1)]
        )
        
        previous_total = previous_entry["total"] if previous_entry else total
        
        # Calculate metrics
        pnl_metrics = calculate_pnl_metrics(total, previous_total)
        kpi_progress = calculate_kpi_progress(total)
        
        # Create entry
        entry = PnLEntry(
            date=entry_data.date,
            balances=entry_data.balances,
            total=round(total, 2),
            pnl_percentage=pnl_metrics["pnl_percentage"],
            pnl_amount=pnl_metrics["pnl_amount"],
            kpi_5k=kpi_progress["kpi_5k"],
            kpi_10k=kpi_progress["kpi_10k"],
            kpi_15k=kpi_progress["kpi_15k"],
            notes=entry_data.notes
        )
        
        # Insert into database
        entry_dict = entry.dict()
        entry_dict["date"] = entry_dict["date"].isoformat()  # Convert date to string
        entry_dict["balances"] = [balance.dict() for balance in entry.balances]
        await db.pnl_entries.insert_one(entry_dict)
        
        # Recalculate PnL for subsequent entries
        await recalculate_subsequent_entries(entry_data.date)
        
        return entry
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/entries", response_model=List[PnLEntry])
async def get_pnl_entries(limit: int = 100):
    try:
        entries = await db.pnl_entries.find().sort("date", -1).limit(limit).to_list(limit)
        result = []
        for entry in entries:
            # Convert balances back to Pydantic models
            entry["balances"] = [DynamicBalance(**balance) for balance in entry["balances"]]
            result.append(PnLEntry(**entry))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/entries/{entry_id}", response_model=PnLEntry)
async def get_pnl_entry(entry_id: str):
    try:
        entry = await db.pnl_entries.find_one({"id": entry_id})
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        # Convert balances back to Pydantic models
        entry["balances"] = [DynamicBalance(**balance) for balance in entry["balances"]]
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

async def recalculate_subsequent_entries(from_date: date):
    """Recalculate PnL for entries from the given date onwards"""
    try:
        # Get all entries from the date onwards
        entries = await db.pnl_entries.find(
            {"date": {"$gte": from_date.isoformat()}}
        ).sort("date", 1).to_list(1000)
        
        for i, entry in enumerate(entries):
            # Get previous entry for PnL calculation
            if i == 0:
                previous_entry = await db.pnl_entries.find_one(
                    {"date": {"$lt": entry["date"]}}, 
                    sort=[("date", -1)]
                )
                previous_total = previous_entry["total"] if previous_entry else entry["total"]
            else:
                previous_total = entries[i-1]["total"]
            
            # Calculate new PnL metrics
            pnl_metrics = calculate_pnl_metrics(entry["total"], previous_total)
            
            # Update entry
            await db.pnl_entries.update_one(
                {"id": entry["id"]},
                {"$set": pnl_metrics}
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