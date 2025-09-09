#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Crypto PnL Tracker
Focus on critical issues: Balance display, API key management, Kraken integration, Stats API
"""

import requests
import json
from datetime import date, datetime, timedelta
import time
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://crypto-profit-dash-1.preview.emergentagent.com/api"

# Test user credentials from review request
TEST_USER_ID = "6888e839-1191-4880-ac8d-1fab8c19ea4c"
TEST_USER_EMAIL = "abedin33@gmail.com"

class CryptoPnLTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_entries = []
        self.failed_tests = []
        self.passed_tests = []
        self.session_token = None
        self.user_id = TEST_USER_ID
        
    def get_auth_headers(self):
        """Get authentication headers for API requests"""
        if self.session_token:
            return {"Authorization": f"Bearer {self.session_token}"}
        return {}
    
    def test_critical_balance_display_issue(self):
        """Test the critical issue: Balance showing €0 despite database having €57,699.48"""
        print("\n=== Testing Critical Balance Display Issue ===")
        
        try:
            # Test GET /api/entries to see if existing entry is returned
            response = requests.get(f"{self.base_url}/entries", 
                                  headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                entries = response.json()
                self.log_result("GET /api/entries - Response", True, 
                              f"- Retrieved {len(entries)} entries")
                
                if entries:
                    # Check if we have the €57,699.48 entry
                    high_balance_entry = None
                    for entry in entries:
                        if entry.get("total", 0) > 50000:  # Looking for the high balance entry
                            high_balance_entry = entry
                            break
                    
                    if high_balance_entry:
                        self.log_result("Critical Balance Entry Found", True, 
                                      f"- Found entry with balance: €{high_balance_entry['total']}")
                        
                        # Verify entry structure
                        required_fields = ["id", "date", "total", "balances", "pnl_percentage", "pnl_amount"]
                        missing_fields = [field for field in required_fields if field not in high_balance_entry]
                        
                        if not missing_fields:
                            self.log_result("Entry Structure Validation", True, 
                                          "- Entry has all required fields")
                        else:
                            self.log_result("Entry Structure Validation", False, 
                                          f"- Missing fields: {missing_fields}")
                        
                        # Check balances array structure
                        if "balances" in high_balance_entry and isinstance(high_balance_entry["balances"], list):
                            self.log_result("Balances Array Structure", True, 
                                          f"- Balances array has {len(high_balance_entry['balances'])} entries")
                            
                            # Log balance details for debugging
                            for balance in high_balance_entry["balances"]:
                                if isinstance(balance, dict) and "exchange_id" in balance and "amount" in balance:
                                    print(f"   Balance: Exchange ID {balance['exchange_id']}, Amount: €{balance['amount']}")
                                else:
                                    self.log_result("Balance Entry Structure", False, 
                                                  f"- Invalid balance structure: {balance}")
                        else:
                            self.log_result("Balances Array Structure", False, 
                                          "- Balances field missing or not an array")
                        
                        return high_balance_entry
                    else:
                        self.log_result("Critical Balance Entry Found", False, 
                                      "- No entry with balance > €50,000 found")
                        
                        # Log all entries for debugging
                        print("   Available entries:")
                        for i, entry in enumerate(entries[:5]):  # Show first 5 entries
                            print(f"   Entry {i+1}: Date: {entry.get('date', 'N/A')}, Total: €{entry.get('total', 0)}")
                        
                        return None
                else:
                    self.log_result("GET /api/entries - Data", False, 
                                  "- No entries returned from database")
                    return None
            else:
                self.log_result("GET /api/entries - Response", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Critical Balance Display Test", False, f"- Error: {str(e)}")
            return None
    
    def test_stats_api_issue(self):
        """Test GET /api/stats - Should show total_balance from existing entries, not €0"""
        print("\n=== Testing Stats API Issue ===")
        
        try:
            response = requests.get(f"{self.base_url}/stats", 
                                  headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                stats = response.json()
                self.log_result("GET /api/stats - Response", True, 
                              f"- Stats API responded successfully")
                
                # Check if total_balance is showing €0 incorrectly
                total_balance = stats.get("total_balance", 0)
                
                if total_balance == 0:
                    self.log_result("Stats API Balance Issue", False, 
                                  f"- total_balance showing €0 (this is the reported issue)")
                    
                    # Check if we have entries but stats shows 0
                    entries_response = requests.get(f"{self.base_url}/entries", 
                                                  headers=self.get_auth_headers(), timeout=10)
                    if entries_response.status_code == 200:
                        entries = entries_response.json()
                        if entries:
                            latest_entry = entries[0]  # Should be sorted by date desc
                            expected_balance = latest_entry.get("total", 0)
                            self.log_result("Stats vs Entries Mismatch", False, 
                                          f"- Stats shows €0 but latest entry has €{expected_balance}")
                        else:
                            self.log_result("No Entries Available", True, 
                                          "- No entries in database, €0 balance is correct")
                else:
                    self.log_result("Stats API Balance", True, 
                                  f"- total_balance: €{total_balance}")
                
                # Verify other required fields
                required_fields = ["total_entries", "total_balance", "daily_pnl", 
                                 "daily_pnl_percentage", "avg_daily_pnl"]
                missing_fields = [field for field in required_fields if field not in stats]
                
                if not missing_fields:
                    self.log_result("Stats API Structure", True, 
                                  "- All required fields present")
                else:
                    self.log_result("Stats API Structure", False, 
                                  f"- Missing fields: {missing_fields}")
                
                return stats
            else:
                self.log_result("GET /api/stats - Response", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Stats API Test", False, f"- Error: {str(e)}")
            return None
    
    def test_exchange_api_key_management(self):
        """Test new API Key Management endpoints"""
        print("\n=== Testing Exchange API Key Management ===")
        
        # Test GET /api/exchange-api-keys
        try:
            response = requests.get(f"{self.base_url}/exchange-api-keys", 
                                  headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                api_keys = response.json()
                self.log_result("GET /api/exchange-api-keys", True, 
                              f"- Retrieved {len(api_keys)} API keys")
                
                # Verify structure of returned keys
                if api_keys:
                    first_key = api_keys[0]
                    required_fields = ["id", "exchange_name", "api_key_preview", "created_at", "is_active"]
                    missing_fields = [field for field in required_fields if field not in first_key]
                    
                    if not missing_fields:
                        self.log_result("API Key Structure", True, 
                                      "- API key structure is correct")
                    else:
                        self.log_result("API Key Structure", False, 
                                      f"- Missing fields: {missing_fields}")
                        
                    # Verify API key is masked for security
                    if "..." in first_key.get("api_key_preview", ""):
                        self.log_result("API Key Security", True, 
                                      "- API key is properly masked")
                    else:
                        self.log_result("API Key Security", False, 
                                      "- API key not properly masked")
                
            elif response.status_code == 401:
                self.log_result("GET /api/exchange-api-keys", False, 
                              "- Authentication required (expected without session)")
            else:
                self.log_result("GET /api/exchange-api-keys", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("GET API Keys Test", False, f"- Error: {str(e)}")
        
        # Test POST /api/exchange-api-keys (create new API key)
        test_api_key_data = {
            "exchange_name": "test_exchange",
            "api_key": "test_api_key_12345",
            "api_secret": "test_secret_67890"
        }
        
        try:
            response = requests.post(f"{self.base_url}/exchange-api-keys", 
                                   json=test_api_key_data,
                                   headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.log_result("POST /api/exchange-api-keys", True, 
                              f"- API key created: {result.get('message', 'Success')}")
            elif response.status_code == 401:
                self.log_result("POST /api/exchange-api-keys", False, 
                              "- Authentication required")
            else:
                self.log_result("POST /api/exchange-api-keys", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("POST API Keys Test", False, f"- Error: {str(e)}")
        
        # Test DELETE /api/exchange-api-keys/{exchange_name}
        try:
            response = requests.delete(f"{self.base_url}/exchange-api-keys/test_exchange", 
                                     headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                self.log_result("DELETE /api/exchange-api-keys", True, 
                              f"- API key deleted: {result.get('message', 'Success')}")
            elif response.status_code == 401:
                self.log_result("DELETE /api/exchange-api-keys", False, 
                              "- Authentication required")
            elif response.status_code == 404:
                self.log_result("DELETE /api/exchange-api-keys", True, 
                              "- API key not found (expected for test)")
            else:
                self.log_result("DELETE /api/exchange-api-keys", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("DELETE API Keys Test", False, f"- Error: {str(e)}")
    
    def test_kraken_api_integration(self):
        """Test Kraken API Integration endpoints"""
        print("\n=== Testing Kraken API Integration ===")
        
        # Test GET /api/exchanges/kraken/balance
        try:
            response = requests.get(f"{self.base_url}/exchanges/kraken/balance", 
                                  headers=self.get_auth_headers(), timeout=15)
            
            if response.status_code == 200:
                balance_data = response.json()
                self.log_result("GET /api/exchanges/kraken/balance", True, 
                              f"- Kraken balance API responded")
                
                # Check response structure
                if balance_data.get("success"):
                    balance_eur = balance_data.get("balance_eur", 0)
                    self.log_result("Kraken Balance Success", True, 
                                  f"- Balance: €{balance_eur}")
                    
                    # Check for additional data
                    if "raw_balances" in balance_data:
                        raw_balances = balance_data["raw_balances"]
                        self.log_result("Kraken Raw Data", True, 
                                      f"- Raw balances: {len(raw_balances)} assets")
                        
                        # Log some details for debugging
                        for asset, amount in list(raw_balances.items())[:3]:
                            print(f"   Asset: {asset}, Amount: {amount}")
                    
                    if "asset_details" in balance_data:
                        asset_details = balance_data["asset_details"]
                        self.log_result("Kraken Asset Details", True, 
                                      f"- Asset details: {len(asset_details)} significant balances")
                else:
                    error_msg = balance_data.get("error", "Unknown error")
                    self.log_result("Kraken Balance Success", False, 
                                  f"- Error: {error_msg}")
                    
            elif response.status_code == 401:
                self.log_result("GET /api/exchanges/kraken/balance", False, 
                              "- Authentication required")
            else:
                self.log_result("GET /api/exchanges/kraken/balance", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Kraken Balance Test", False, f"- Error: {str(e)}")
        
        # Test POST /api/exchanges/sync
        try:
            response = requests.post(f"{self.base_url}/exchanges/sync", 
                                   headers=self.get_auth_headers(), timeout=15)
            
            if response.status_code == 200:
                sync_data = response.json()
                self.log_result("POST /api/exchanges/sync", True, 
                              "- Exchange sync API responded")
                
                # Check sync results
                if "sync_results" in sync_data:
                    sync_results = sync_data["sync_results"]
                    self.log_result("Exchange Sync Results", True, 
                                  f"- Sync results for {len(sync_results)} exchanges")
                    
                    # Check Kraken sync specifically
                    if "kraken" in sync_results:
                        kraken_result = sync_results["kraken"]
                        if kraken_result.get("success"):
                            self.log_result("Kraken Sync Success", True, 
                                          f"- Kraken balance: €{kraken_result.get('balance', 0)}")
                        else:
                            self.log_result("Kraken Sync Success", False, 
                                          f"- Kraken error: {kraken_result.get('error', 'Unknown')}")
                
                # Check suggested entry
                if "suggested_entry" in sync_data:
                    suggested = sync_data["suggested_entry"]
                    self.log_result("Suggested Entry", True, 
                                  f"- Total suggested: €{suggested.get('total', 0)}")
                    
            elif response.status_code == 401:
                self.log_result("POST /api/exchanges/sync", False, 
                              "- Authentication required")
            else:
                self.log_result("POST /api/exchanges/sync", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Exchange Sync Test", False, f"- Error: {str(e)}")
        
        # Test POST /api/entries/auto-create
        try:
            response = requests.post(f"{self.base_url}/entries/auto-create", 
                                   headers=self.get_auth_headers(), timeout=15)
            
            if response.status_code == 200:
                auto_entry_data = response.json()
                self.log_result("POST /api/entries/auto-create", True, 
                              "- Auto-create entry API responded")
                
                # Check if entry was created or already exists
                message = auto_entry_data.get("message", "")
                if "created successfully" in message:
                    total_balance = auto_entry_data.get("total_balance", 0)
                    self.log_result("Auto-Create Entry Success", True, 
                                  f"- Entry created with balance: €{total_balance}")
                elif "already exists" in message:
                    self.log_result("Auto-Create Entry Exists", True, 
                                  "- Entry for today already exists")
                else:
                    self.log_result("Auto-Create Entry Response", True, 
                                  f"- Response: {message}")
                    
            elif response.status_code == 400:
                # This might be expected if no exchange balances are available
                response_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_detail = response_data.get("detail", response.text)
                self.log_result("POST /api/entries/auto-create", True, 
                              f"- Expected error: {error_detail}")
            elif response.status_code == 401:
                self.log_result("POST /api/entries/auto-create", False, 
                              "- Authentication required")
            else:
                self.log_result("POST /api/entries/auto-create", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_result("Auto-Create Entry Test", False, f"- Error: {str(e)}")
    
    def test_authentication_flow(self):
        """Test authentication to get session token for other tests"""
        print("\n=== Testing Authentication Flow ===")
        
        # For testing purposes, we'll try to authenticate with a mock session
        # In a real scenario, this would use Google OAuth or the legacy auth endpoint
        
        # Try to access a protected endpoint without auth first
        try:
            response = requests.get(f"{self.base_url}/entries", timeout=10)
            if response.status_code == 401:
                self.log_result("Protected Endpoint Security", True, 
                              "- Properly requires authentication")
            else:
                self.log_result("Protected Endpoint Security", False, 
                              f"- Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_result("Auth Test", False, f"- Error: {str(e)}")
        
        # Note: For comprehensive testing, we would need a valid session token
        # This would typically come from the Google OAuth flow or legacy auth
        print("   Note: Full API testing requires valid authentication token")
        print("   Current tests will show authentication errors for protected endpoints")
    
    def test_api_connection(self):
        """Test basic API connectivity"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "Crypto PnL Tracker API" in data.get("message", ""):
                    self.log_result("API Connection", True, "- API is accessible")
                    return True
                else:
                    self.log_result("API Connection", False, f"- Unexpected response: {data}")
                    return False
            else:
                self.log_result("API Connection", False, f"- Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("API Connection", False, f"- Error: {str(e)}")
            return False
    
    def test_create_entry(self):
        """Test POST /api/entries - Create new PnL entries"""
        print("\n=== Testing Entry Creation ===")
        
        # Test Case 1: First entry (no previous data)
        first_entry_data = {
            "date": "2024-01-01",
            "balances": {
                "kraken": 2400.50,
                "bitget": 1600.25,
                "binance": 100.75
            },
            "notes": "Initial portfolio entry"
        }
        
        try:
            response = requests.post(f"{self.base_url}/entries", 
                                   json=first_entry_data, timeout=10)
            if response.status_code == 200:
                entry = response.json()
                self.test_entries.append(entry)
                
                # Verify calculations
                expected_total = 2400.50 + 1600.25 + 100.75  # 4101.50
                if abs(entry["total"] - expected_total) < 0.01:
                    self.log_result("Create First Entry - Total Calculation", True, 
                                  f"- Total: €{entry['total']}")
                else:
                    self.log_result("Create First Entry - Total Calculation", False, 
                                  f"- Expected: €{expected_total}, Got: €{entry['total']}")
                
                # First entry should have 0 PnL
                if entry["pnl_percentage"] == 0.0 and entry["pnl_amount"] == 0.0:
                    self.log_result("Create First Entry - PnL Calculation", True, 
                                  "- PnL correctly set to 0 for first entry")
                else:
                    self.log_result("Create First Entry - PnL Calculation", False, 
                                  f"- PnL should be 0, got {entry['pnl_percentage']}%, €{entry['pnl_amount']}")
                
                # Test KPI calculations
                expected_kpi_5k = expected_total - 5000  # -898.50
                expected_kpi_10k = expected_total - 10000  # -5898.50
                expected_kpi_15k = expected_total - 15000  # -10898.50
                
                if (abs(entry["kpi_5k"] - expected_kpi_5k) < 0.01 and 
                    abs(entry["kpi_10k"] - expected_kpi_10k) < 0.01 and 
                    abs(entry["kpi_15k"] - expected_kpi_15k) < 0.01):
                    self.log_result("Create First Entry - KPI Calculation", True, 
                                  f"- KPIs: 5K: €{entry['kpi_5k']}, 10K: €{entry['kpi_10k']}, 15K: €{entry['kpi_15k']}")
                else:
                    self.log_result("Create First Entry - KPI Calculation", False, 
                                  f"- KPI calculation error")
                
            else:
                self.log_result("Create First Entry", False, 
                              f"- Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Create First Entry", False, f"- Error: {str(e)}")
            return False
        
        # Test Case 2: Second entry with gains
        second_entry_data = {
            "date": "2024-01-02",
            "balances": {
                "kraken": 2500.00,
                "bitget": 1700.00,
                "binance": 150.00
            },
            "notes": "Portfolio growth day"
        }
        
        try:
            response = requests.post(f"{self.base_url}/entries", 
                                   json=second_entry_data, timeout=10)
            if response.status_code == 200:
                entry = response.json()
                self.test_entries.append(entry)
                
                expected_total = 4350.00
                previous_total = 4101.50
                expected_pnl_amount = expected_total - previous_total  # 248.50
                expected_pnl_percentage = (expected_pnl_amount / previous_total) * 100  # ~6.06%
                
                if (abs(entry["total"] - expected_total) < 0.01 and
                    abs(entry["pnl_amount"] - expected_pnl_amount) < 0.01 and
                    abs(entry["pnl_percentage"] - expected_pnl_percentage) < 0.1):
                    self.log_result("Create Second Entry - PnL Calculation", True, 
                                  f"- PnL: {entry['pnl_percentage']}%, €{entry['pnl_amount']}")
                else:
                    self.log_result("Create Second Entry - PnL Calculation", False, 
                                  f"- Expected PnL: {expected_pnl_percentage:.2f}%, €{expected_pnl_amount}, Got: {entry['pnl_percentage']}%, €{entry['pnl_amount']}")
                
            else:
                self.log_result("Create Second Entry", False, 
                              f"- Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Create Second Entry", False, f"- Error: {str(e)}")
            return False
        
        # Test Case 3: Third entry with losses
        third_entry_data = {
            "date": "2024-01-03",
            "balances": {
                "kraken": 2200.00,
                "bitget": 1500.00,
                "binance": 80.00
            },
            "notes": "Market correction day"
        }
        
        try:
            response = requests.post(f"{self.base_url}/entries", 
                                   json=third_entry_data, timeout=10)
            if response.status_code == 200:
                entry = response.json()
                self.test_entries.append(entry)
                
                expected_total = 3780.00
                previous_total = 4350.00
                expected_pnl_amount = expected_total - previous_total  # -570.00
                expected_pnl_percentage = (expected_pnl_amount / previous_total) * 100  # ~-13.10%
                
                if (abs(entry["total"] - expected_total) < 0.01 and
                    abs(entry["pnl_amount"] - expected_pnl_amount) < 0.01 and
                    abs(entry["pnl_percentage"] - expected_pnl_percentage) < 0.1):
                    self.log_result("Create Third Entry - Negative PnL", True, 
                                  f"- PnL: {entry['pnl_percentage']}%, €{entry['pnl_amount']}")
                else:
                    self.log_result("Create Third Entry - Negative PnL", False, 
                                  f"- Expected PnL: {expected_pnl_percentage:.2f}%, €{expected_pnl_amount}, Got: {entry['pnl_percentage']}%, €{entry['pnl_amount']}")
                
            else:
                self.log_result("Create Third Entry", False, 
                              f"- Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Create Third Entry", False, f"- Error: {str(e)}")
            return False
        
        return True
    
    def test_get_entries(self):
        """Test GET /api/entries - Retrieve all entries"""
        print("\n=== Testing Entry Retrieval ===")
        
        try:
            response = requests.get(f"{self.base_url}/entries", timeout=10)
            if response.status_code == 200:
                entries = response.json()
                
                if len(entries) >= len(self.test_entries):
                    self.log_result("Get All Entries", True, 
                                  f"- Retrieved {len(entries)} entries")
                    
                    # Verify entries are sorted by date (newest first)
                    if len(entries) > 1:
                        dates = [entry["date"] for entry in entries]
                        if dates == sorted(dates, reverse=True):
                            self.log_result("Get All Entries - Sorting", True, 
                                          "- Entries properly sorted by date (newest first)")
                        else:
                            self.log_result("Get All Entries - Sorting", False, 
                                          "- Entries not properly sorted")
                    
                    return entries
                else:
                    self.log_result("Get All Entries", False, 
                                  f"- Expected at least {len(self.test_entries)} entries, got {len(entries)}")
                    return []
            else:
                self.log_result("Get All Entries", False, 
                              f"- Status: {response.status_code}")
                return []
                
        except Exception as e:
            self.log_result("Get All Entries", False, f"- Error: {str(e)}")
            return []
    
    def test_get_single_entry(self):
        """Test GET /api/entries/{id} - Get specific entry"""
        print("\n=== Testing Single Entry Retrieval ===")
        
        if not self.test_entries:
            self.log_result("Get Single Entry", False, "- No test entries available")
            return False
        
        entry_id = self.test_entries[0]["id"]
        
        try:
            response = requests.get(f"{self.base_url}/entries/{entry_id}", timeout=10)
            if response.status_code == 200:
                entry = response.json()
                if entry["id"] == entry_id:
                    self.log_result("Get Single Entry", True, 
                                  f"- Retrieved entry {entry_id}")
                    return True
                else:
                    self.log_result("Get Single Entry", False, 
                                  "- Retrieved entry ID mismatch")
                    return False
            else:
                self.log_result("Get Single Entry", False, 
                              f"- Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Get Single Entry", False, f"- Error: {str(e)}")
            return False
        
        # Test non-existent entry
        try:
            response = requests.get(f"{self.base_url}/entries/non-existent-id", timeout=10)
            if response.status_code == 404:
                self.log_result("Get Non-existent Entry", True, 
                              "- Properly returns 404 for non-existent entry")
            else:
                self.log_result("Get Non-existent Entry", False, 
                              f"- Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_result("Get Non-existent Entry", False, f"- Error: {str(e)}")
    
    def test_update_entry(self):
        """Test PUT /api/entries/{id} - Update existing entries"""
        print("\n=== Testing Entry Updates ===")
        
        if not self.test_entries:
            self.log_result("Update Entry", False, "- No test entries available")
            return False
        
        entry_id = self.test_entries[0]["id"]
        
        # Test updating balances
        update_data = {
            "balances": {
                "kraken": 2600.00,
                "bitget": 1800.00,
                "binance": 200.00
            },
            "notes": "Updated portfolio balances"
        }
        
        try:
            response = requests.put(f"{self.base_url}/entries/{entry_id}", 
                                  json=update_data, timeout=10)
            if response.status_code == 200:
                updated_entry = response.json()
                
                expected_total = 4600.00
                if abs(updated_entry["total"] - expected_total) < 0.01:
                    self.log_result("Update Entry - Balance Update", True, 
                                  f"- Updated total: €{updated_entry['total']}")
                    
                    # Update our test entry for subsequent tests
                    self.test_entries[0] = updated_entry
                else:
                    self.log_result("Update Entry - Balance Update", False, 
                                  f"- Expected total: €{expected_total}, Got: €{updated_entry['total']}")
                
                # Verify KPI recalculation
                expected_kpi_5k = expected_total - 5000  # -400.00
                if abs(updated_entry["kpi_5k"] - expected_kpi_5k) < 0.01:
                    self.log_result("Update Entry - KPI Recalculation", True, 
                                  f"- KPI 5K: €{updated_entry['kpi_5k']}")
                else:
                    self.log_result("Update Entry - KPI Recalculation", False, 
                                  f"- Expected KPI 5K: €{expected_kpi_5k}, Got: €{updated_entry['kpi_5k']}")
                
            else:
                self.log_result("Update Entry", False, 
                              f"- Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Update Entry", False, f"- Error: {str(e)}")
            return False
        
        return True
    
    def test_portfolio_stats(self):
        """Test GET /api/stats - Portfolio statistics"""
        print("\n=== Testing Portfolio Statistics ===")
        
        try:
            response = requests.get(f"{self.base_url}/stats", timeout=10)
            if response.status_code == 200:
                stats = response.json()
                
                required_fields = ["total_entries", "total_balance", "daily_pnl", 
                                 "daily_pnl_percentage", "avg_daily_pnl", "kpi_progress"]
                
                missing_fields = [field for field in required_fields if field not in stats]
                if not missing_fields:
                    self.log_result("Portfolio Stats - Structure", True, 
                                  "- All required fields present")
                else:
                    self.log_result("Portfolio Stats - Structure", False, 
                                  f"- Missing fields: {missing_fields}")
                    return False
                
                # Verify KPI progress structure
                kpi_fields = ["5k", "10k", "15k"]
                missing_kpi = [field for field in kpi_fields if field not in stats["kpi_progress"]]
                if not missing_kpi:
                    self.log_result("Portfolio Stats - KPI Structure", True, 
                                  "- KPI progress structure correct")
                else:
                    self.log_result("Portfolio Stats - KPI Structure", False, 
                                  f"- Missing KPI fields: {missing_kpi}")
                
                # Verify data types and reasonable values
                if (isinstance(stats["total_entries"], int) and stats["total_entries"] >= 0 and
                    isinstance(stats["total_balance"], (int, float)) and
                    isinstance(stats["daily_pnl"], (int, float)) and
                    isinstance(stats["daily_pnl_percentage"], (int, float)) and
                    isinstance(stats["avg_daily_pnl"], (int, float))):
                    self.log_result("Portfolio Stats - Data Types", True, 
                                  f"- Stats: Balance: €{stats['total_balance']}, Entries: {stats['total_entries']}")
                else:
                    self.log_result("Portfolio Stats - Data Types", False, 
                                  "- Invalid data types in stats response")
                
                return True
            else:
                self.log_result("Portfolio Stats", False, 
                              f"- Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Portfolio Stats", False, f"- Error: {str(e)}")
            return False
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n=== Testing Edge Cases ===")
        
        # Test zero balances
        zero_entry_data = {
            "date": "2024-01-04",
            "balances": {
                "kraken": 0.0,
                "bitget": 0.0,
                "binance": 0.0
            },
            "notes": "Zero balance test"
        }
        
        try:
            response = requests.post(f"{self.base_url}/entries", 
                                   json=zero_entry_data, timeout=10)
            if response.status_code == 200:
                entry = response.json()
                if entry["total"] == 0.0:
                    self.log_result("Edge Case - Zero Balances", True, 
                                  "- Zero balance entry created successfully")
                    self.test_entries.append(entry)
                else:
                    self.log_result("Edge Case - Zero Balances", False, 
                                  f"- Expected total 0, got {entry['total']}")
            else:
                self.log_result("Edge Case - Zero Balances", False, 
                              f"- Status: {response.status_code}")
        except Exception as e:
            self.log_result("Edge Case - Zero Balances", False, f"- Error: {str(e)}")
        
        # Test invalid date format
        invalid_date_data = {
            "date": "invalid-date",
            "balances": {
                "kraken": 100.0,
                "bitget": 100.0,
                "binance": 100.0
            }
        }
        
        try:
            response = requests.post(f"{self.base_url}/entries", 
                                   json=invalid_date_data, timeout=10)
            if response.status_code in [400, 422]:  # Bad request or validation error
                self.log_result("Edge Case - Invalid Date", True, 
                              "- Properly rejects invalid date format")
            else:
                self.log_result("Edge Case - Invalid Date", False, 
                              f"- Expected 400/422, got {response.status_code}")
        except Exception as e:
            self.log_result("Edge Case - Invalid Date", False, f"- Error: {str(e)}")
    
    def test_delete_entry(self):
        """Test DELETE /api/entries/{id} - Delete entries"""
        print("\n=== Testing Entry Deletion ===")
        
        if not self.test_entries:
            self.log_result("Delete Entry", False, "- No test entries available")
            return False
        
        # Delete the last entry we created
        entry_to_delete = self.test_entries[-1]
        entry_id = entry_to_delete["id"]
        
        try:
            response = requests.delete(f"{self.base_url}/entries/{entry_id}", timeout=10)
            if response.status_code == 200:
                result = response.json()
                if "deleted successfully" in result.get("message", "").lower():
                    self.log_result("Delete Entry", True, 
                                  f"- Entry {entry_id} deleted successfully")
                    
                    # Verify entry is actually deleted
                    verify_response = requests.get(f"{self.base_url}/entries/{entry_id}", timeout=10)
                    if verify_response.status_code == 404:
                        self.log_result("Delete Entry - Verification", True, 
                                      "- Entry properly removed from database")
                    else:
                        self.log_result("Delete Entry - Verification", False, 
                                      "- Entry still exists after deletion")
                    
                    # Remove from our test entries
                    self.test_entries.remove(entry_to_delete)
                    return True
                else:
                    self.log_result("Delete Entry", False, 
                                  f"- Unexpected response: {result}")
                    return False
            else:
                self.log_result("Delete Entry", False, 
                              f"- Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Delete Entry", False, f"- Error: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """Clean up test entries"""
        print("\n=== Cleaning Up Test Data ===")
        
        for entry in self.test_entries:
            try:
                response = requests.delete(f"{self.base_url}/entries/{entry['id']}", timeout=10)
                if response.status_code == 200:
                    print(f"✅ Cleaned up entry {entry['id']}")
                else:
                    print(f"⚠️ Failed to clean up entry {entry['id']}")
            except Exception as e:
                print(f"⚠️ Error cleaning up entry {entry['id']}: {str(e)}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Crypto PnL Tracker Backend API Tests")
        print(f"🔗 Testing against: {self.base_url}")
        print("=" * 60)
        
        # Test API connection first
        if not self.test_api_connection():
            print("\n❌ API connection failed. Cannot proceed with tests.")
            return False
        
        # Run all test suites
        self.test_create_entry()
        self.test_get_entries()
        self.test_get_single_entry()
        self.test_update_entry()
        self.test_portfolio_stats()
        self.test_edge_cases()
        self.test_delete_entry()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {len(self.passed_tests)}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        if self.passed_tests:
            print(f"\n✅ Passed Tests: {len(self.passed_tests)} total")
        
        # Cleanup
        self.cleanup_test_data()
        
        success_rate = len(self.passed_tests) / (len(self.passed_tests) + len(self.failed_tests)) * 100
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return len(self.failed_tests) == 0

if __name__ == "__main__":
    tester = CryptoPnLTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Backend API is working correctly.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Check the output above for details.")
        sys.exit(1)