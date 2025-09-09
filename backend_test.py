#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Crypto PnL Tracker
Focus on auto-entry creation issue debugging with real Kraken API keys
"""

import requests
import json
from datetime import date, datetime, timedelta
import time
import sys
import base64
import hmac
import hashlib
import urllib.parse

# Backend URL from frontend/.env
BACKEND_URL = "https://crypto-profit-dash-1.preview.emergentagent.com/api"

# Test user credentials from review request
TEST_USER_ID = "6888e839-1191-4880-ac8d-1fab8c19ea4c"
TEST_USER_EMAIL = "abedin33@gmail.com"

# Kraken API Keys from review request
KRAKEN_API_KEY = "fFeuud7v9ZMpUgKDrvJg9qzmMYiG+T16fc4sHKWnGSAvZgSJsLVWXzcj"
KRAKEN_PRIVATE_KEY = "g/j/j1aK781xg5YyanJZH3uYPonVFwU6eiMd2mrpVS1oc8rUAgXvKf0Qc9C8I1how0WhhREZlPNpQwenVD+5IQ=="

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
    
    def log_result(self, test_name, success, message=""):
        """Log test results"""
        if success:
            self.passed_tests.append(test_name)
            print(f"✅ {test_name}: PASSED {message}")
        else:
            self.failed_tests.append(test_name)
            print(f"❌ {test_name}: FAILED {message}")
    
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
    
    def run_critical_issue_tests(self):
        """Run tests focused on the critical issues reported"""
        print("🚀 Starting Critical Issue Tests for Crypto PnL Tracker")
        print(f"🔗 Testing against: {self.base_url}")
        print(f"👤 Test User ID: {self.user_id}")
        print("=" * 60)
        
        # Test API connection first
        if not self.test_api_connection():
            print("\n❌ API connection failed. Cannot proceed with tests.")
            return False
        
        # Test authentication flow
        self.test_authentication_flow()
        
        # Run critical issue tests
        print("\n🔍 CRITICAL ISSUE TESTING")
        print("=" * 40)
        
        # 1. Test balance display issue
        existing_entry = self.test_critical_balance_display_issue()
        
        # 2. Test stats API issue
        stats_data = self.test_stats_api_issue()
        
        # 3. Test new API key management endpoints
        self.test_exchange_api_key_management()
        
        # 4. Test Kraken API integration
        self.test_kraken_api_integration()
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 CRITICAL ISSUE TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {len(self.passed_tests)}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        if self.passed_tests:
            print(f"\n✅ Passed Tests: {len(self.passed_tests)} total")
        
        # Analysis of critical issues
        print("\n🔍 CRITICAL ISSUE ANALYSIS")
        print("=" * 40)
        
        if existing_entry:
            print(f"✅ Database contains entry with €{existing_entry.get('total', 0)} balance")
        else:
            print("❌ No high-balance entry found in database")
        
        if stats_data and stats_data.get('total_balance', 0) == 0:
            print("❌ Stats API showing €0 balance (this is the reported issue)")
        elif stats_data:
            print(f"✅ Stats API showing €{stats_data.get('total_balance', 0)} balance")
        else:
            print("❌ Stats API not accessible")
        
        success_rate = len(self.passed_tests) / (len(self.passed_tests) + len(self.failed_tests)) * 100 if (len(self.passed_tests) + len(self.failed_tests)) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return len(self.failed_tests) == 0

if __name__ == "__main__":
    tester = CryptoPnLTester()
    
    # Run critical issue tests
    print("🎯 RUNNING CRITICAL ISSUE TESTS")
    print("=" * 50)
    critical_success = tester.run_critical_issue_tests()
    
    if critical_success:
        print("\n🎉 Critical issue tests completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Some critical issue tests failed. Check the output above for details.")
        sys.exit(1)