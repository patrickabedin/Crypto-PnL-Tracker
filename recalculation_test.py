#!/usr/bin/env python3
"""
Test automatic PnL recalculation when entries are modified or deleted
"""

import requests
import json
from datetime import date

BACKEND_URL = "https://pnldashboard.preview.emergentagent.com/api"

def test_recalculation():
    print("🧮 Testing Automatic PnL Recalculation")
    print("=" * 50)
    
    # Create three entries in sequence
    entries = []
    
    # Entry 1: Jan 1 - €5000
    entry1_data = {
        "date": "2024-01-01",
        "balances": {"kraken": 3000.0, "bitget": 1500.0, "binance": 500.0},
        "notes": "Base entry"
    }
    
    response = requests.post(f"{BACKEND_URL}/entries", json=entry1_data)
    if response.status_code == 200:
        entry1 = response.json()
        entries.append(entry1)
        print(f"✅ Entry 1 created: €{entry1['total']} (PnL: {entry1['pnl_percentage']}%)")
    
    # Entry 2: Jan 2 - €5500 (+10% gain)
    entry2_data = {
        "date": "2024-01-02", 
        "balances": {"kraken": 3300.0, "bitget": 1650.0, "binance": 550.0},
        "notes": "Growth day"
    }
    
    response = requests.post(f"{BACKEND_URL}/entries", json=entry2_data)
    if response.status_code == 200:
        entry2 = response.json()
        entries.append(entry2)
        print(f"✅ Entry 2 created: €{entry2['total']} (PnL: {entry2['pnl_percentage']}%)")
    
    # Entry 3: Jan 3 - €6000 (+9.09% gain from entry 2)
    entry3_data = {
        "date": "2024-01-03",
        "balances": {"kraken": 3600.0, "bitget": 1800.0, "binance": 600.0},
        "notes": "Another growth day"
    }
    
    response = requests.post(f"{BACKEND_URL}/entries", json=entry3_data)
    if response.status_code == 200:
        entry3 = response.json()
        entries.append(entry3)
        print(f"✅ Entry 3 created: €{entry3['total']} (PnL: {entry3['pnl_percentage']}%)")
    
    print("\n🔄 Now updating Entry 1 to €4000 (should recalculate Entry 2 and 3)")
    
    # Update Entry 1 to €4000 - this should trigger recalculation
    update_data = {
        "balances": {"kraken": 2400.0, "bitget": 1200.0, "binance": 400.0}
    }
    
    response = requests.put(f"{BACKEND_URL}/entries/{entry1['id']}", json=update_data)
    if response.status_code == 200:
        updated_entry1 = response.json()
        print(f"✅ Entry 1 updated: €{updated_entry1['total']}")
        
        # Check if Entry 2 was recalculated (should now be 37.5% gain: 5500/4000 - 1)
        response = requests.get(f"{BACKEND_URL}/entries/{entry2['id']}")
        if response.status_code == 200:
            recalc_entry2 = response.json()
            expected_pnl_2 = ((5500 - 4000) / 4000) * 100  # 37.5%
            print(f"📊 Entry 2 recalculated: PnL {recalc_entry2['pnl_percentage']}% (expected ~{expected_pnl_2:.1f}%)")
            
            if abs(recalc_entry2['pnl_percentage'] - expected_pnl_2) < 0.1:
                print("✅ Entry 2 PnL recalculation correct")
            else:
                print("❌ Entry 2 PnL recalculation incorrect")
        
        # Check if Entry 3 was recalculated (should still be 9.09% gain from Entry 2)
        response = requests.get(f"{BACKEND_URL}/entries/{entry3['id']}")
        if response.status_code == 200:
            recalc_entry3 = response.json()
            expected_pnl_3 = ((6000 - 5500) / 5500) * 100  # 9.09%
            print(f"📊 Entry 3 recalculated: PnL {recalc_entry3['pnl_percentage']}% (expected ~{expected_pnl_3:.1f}%)")
            
            if abs(recalc_entry3['pnl_percentage'] - expected_pnl_3) < 0.1:
                print("✅ Entry 3 PnL recalculation correct")
            else:
                print("❌ Entry 3 PnL recalculation incorrect")
    
    # Cleanup
    print("\n🧹 Cleaning up test entries...")
    for entry in entries:
        requests.delete(f"{BACKEND_URL}/entries/{entry['id']}")
    print("✅ Cleanup complete")

if __name__ == "__main__":
    test_recalculation()