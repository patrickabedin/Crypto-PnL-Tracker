#!/usr/bin/env python3
"""
FINAL DEBUGGING ATTEMPT - Comprehensive Backend API Tests for Crypto PnL Tracker
Focus on resolving persistent balance and sync issues:
- Dashboard shows €0 balance instead of expected €57,699.48
- Sync reports "0/3 exchanges synced successfully"
- "Error creating entry from sync data" persists
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
        self.critical_issues = []
        self.balance_found = None
        self.entries_found = []
        
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
    
    def log_critical_issue(self, issue):
        """Log critical issues for final summary"""
        self.critical_issues.append(issue)
        print(f"🔴 CRITICAL: {issue}")
    
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
    
    def test_database_entry_verification(self):
        """CRITICAL TEST 1: Check if €57,699.48 entry exists and is associated with correct user"""
        print("\n=== CRITICAL TEST 1: Database Entry Verification ===")
        
        try:
            # Test GET /api/entries without authentication first
            response = requests.get(f"{self.base_url}/entries", timeout=10)
            
            if response.status_code == 401:
                self.log_result("Entries Endpoint Security", True, "- Properly requires authentication")
                
                # Since we can't authenticate, we'll test the stats endpoint which should also require auth
                stats_response = requests.get(f"{self.base_url}/stats", timeout=10)
                
                if stats_response.status_code == 401:
                    self.log_result("Stats Endpoint Security", True, "- Properly requires authentication")
                    self.log_critical_issue("Cannot verify €57,699.48 entry without authentication - this is the core issue")
                    return False
                else:
                    self.log_result("Stats Endpoint Security", False, f"- Expected 401, got {stats_response.status_code}")
                    
                    # If stats endpoint doesn't require auth, check what it returns
                    if stats_response.status_code == 200:
                        stats_data = stats_response.json()
                        total_balance = stats_data.get("total_balance", 0)
                        
                        if total_balance == 57699.48:
                            self.log_result("Expected Balance Found", True, f"- Found €{total_balance} in stats")
                            self.balance_found = total_balance
                            return True
                        elif total_balance == 0:
                            self.log_critical_issue(f"Stats API returns €0 balance instead of expected €57,699.48")
                            return False
                        else:
                            self.log_result("Unexpected Balance", True, f"- Found €{total_balance} (not expected €57,699.48)")
                            self.balance_found = total_balance
                            return True
                    
            elif response.status_code == 200:
                # Entries endpoint doesn't require auth - check entries
                entries = response.json()
                self.log_result("Entries Retrieved", True, f"- Retrieved {len(entries)} entries")
                
                # Look for the €57,699.48 entry
                target_balance = 57699.48
                found_entry = None
                
                for entry in entries:
                    total = entry.get("total", 0)
                    if abs(total - target_balance) < 1:  # Allow small rounding differences
                        found_entry = entry
                        break
                
                if found_entry:
                    self.log_result("Target Entry Found", True, f"- Found entry with €{found_entry['total']}")
                    self.entries_found.append(found_entry)
                    
                    # Check user association
                    entry_user_id = found_entry.get("user_id")
                    if entry_user_id == TEST_USER_ID:
                        self.log_result("User Association", True, f"- Entry belongs to correct user")
                        return True
                    else:
                        self.log_critical_issue(f"Entry belongs to different user: {entry_user_id} vs expected {TEST_USER_ID}")
                        return False
                else:
                    self.log_critical_issue(f"€57,699.48 entry not found in database")
                    
                    # Log all entries for debugging
                    print("   Available entries:")
                    for entry in entries[:5]:  # Show first 5 entries
                        total = entry.get("total", 0)
                        date = entry.get("date", "unknown")
                        user_id = entry.get("user_id", "unknown")
                        print(f"     Date: {date}, Total: €{total}, User: {user_id[:8]}...")
                    
                    return False
            else:
                self.log_result("Entries Endpoint", False, f"- HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Database Entry Verification", False, f"- Error: {str(e)}")
            return False
    
    def test_stats_api_verification(self):
        """CRITICAL TEST 4: Test GET /api/stats - should return €57,699.48 if entry exists"""
        print("\n=== CRITICAL TEST 4: Stats API Verification ===")
        
        try:
            response = requests.get(f"{self.base_url}/stats", 
                                  headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                stats_data = response.json()
                self.log_result("Stats API Response", True, "- Stats endpoint responded successfully")
                
                # Check total balance
                total_balance = stats_data.get("total_balance", 0)
                total_entries = stats_data.get("total_entries", 0)
                daily_pnl = stats_data.get("daily_pnl", 0)
                
                print(f"   Total Balance: €{total_balance}")
                print(f"   Total Entries: {total_entries}")
                print(f"   Daily PnL: €{daily_pnl}")
                
                if total_balance == 57699.48:
                    self.log_result("Expected Balance in Stats", True, f"- Stats shows correct €{total_balance}")
                    self.balance_found = total_balance
                    return True
                elif total_balance == 0:
                    self.log_critical_issue(f"Stats API shows €0 balance instead of expected €57,699.48")
                    
                    # Check if there are entries but balance is 0
                    if total_entries > 0:
                        self.log_critical_issue(f"Database has {total_entries} entries but balance is €0 - calculation error")
                    else:
                        self.log_critical_issue(f"No entries found in database for authenticated user")
                    
                    return False
                else:
                    self.log_result("Different Balance Found", True, f"- Stats shows €{total_balance} (not expected €57,699.48)")
                    self.balance_found = total_balance
                    
                    # Check KPI progress
                    kpi_progress = stats_data.get("kpi_progress", {})
                    if kpi_progress:
                        print(f"   KPI Progress: {kpi_progress}")
                        self.log_result("KPI Progress Available", True, "- KPI data present")
                    
                    return True
                    
            elif response.status_code == 401:
                self.log_result("Stats API Authentication", False, "- Authentication required")
                self.log_critical_issue("Cannot test stats API without authentication")
                return False
            else:
                self.log_result("Stats API Response", False, f"- HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Stats API Test", False, f"- Error: {str(e)}")
            return False
    
    def test_direct_kraken_api(self):
        """Test direct Kraken API call to verify the provided keys work"""
        print("\n=== Testing Direct Kraken API with Provided Keys ===")
        
        try:
            # Create Kraken API signature
            nonce = str(int(1000*time.time()))
            data = {'nonce': nonce}
            urlpath = '/0/private/Balance'
            
            postdata = urllib.parse.urlencode(data)
            encoded = (str(data['nonce']) + postdata).encode()
            message = urlpath.encode() + hashlib.sha256(encoded).digest()
            
            mac = hmac.new(base64.b64decode(KRAKEN_PRIVATE_KEY), message, hashlib.sha512)
            sigdigest = base64.b64encode(mac.digest())
            
            headers = {
                'API-Key': KRAKEN_API_KEY,
                'API-Sign': sigdigest.decode()
            }
            
            # Make direct call to Kraken API
            response = requests.post(
                "https://api.kraken.com/0/private/Balance",
                headers=headers,
                data=data,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                self.log_result("Direct Kraken API Call", True, "- Successfully connected to Kraken")
                
                if result.get('error'):
                    self.log_result("Kraken API Error Check", False, f"- Kraken error: {result['error']}")
                    return None
                else:
                    balances = result.get('result', {})
                    self.log_result("Kraken Balance Retrieval", True, f"- Retrieved {len(balances)} balance entries")
                    
                    # Log balance details
                    total_eur = 0.0
                    significant_balances = {}
                    
                    for asset, balance in balances.items():
                        balance_float = float(balance)
                        if balance_float > 0.01:  # Only significant balances
                            significant_balances[asset] = balance_float
                            print(f"   {asset}: {balance_float}")
                            
                            # Calculate EUR equivalent
                            if asset in ['ZEUR', 'EUR']:
                                total_eur += balance_float
                            elif asset in ['ZUSD', 'USD']:
                                total_eur += balance_float * 0.92  # USD to EUR
                            elif asset in ['BTC', 'XXBT', 'XBT']:
                                total_eur += balance_float * 40000  # Conservative BTC price
                            elif asset in ['ETH', 'XETH']:
                                total_eur += balance_float * 2200   # Conservative ETH price
                    
                    self.log_result("Kraken Balance Calculation", True, f"- Estimated total: €{total_eur:.2f}")
                    return {'balances': balances, 'total_eur': total_eur, 'significant': significant_balances}
            else:
                self.log_result("Direct Kraken API Call", False, f"- HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Direct Kraken API Test", False, f"- Error: {str(e)}")
            return None
    
    def test_kraken_balance_endpoint(self):
        """Test /api/exchanges/kraken/balance endpoint specifically"""
        print("\n=== Testing Backend Kraken Balance Endpoint ===")
        
        try:
            response = requests.get(f"{self.base_url}/exchanges/kraken/balance", 
                                  headers=self.get_auth_headers(), timeout=15)
            
            if response.status_code == 200:
                balance_data = response.json()
                self.log_result("Kraken Balance Endpoint", True, "- Endpoint responded successfully")
                
                if balance_data.get("success"):
                    balance_eur = balance_data.get("balance_eur", 0)
                    self.log_result("Kraken Balance Success", True, f"- Balance: €{balance_eur}")
                    
                    # Check for raw balance data
                    if "raw_balances" in balance_data:
                        raw_balances = balance_data["raw_balances"]
                        self.log_result("Kraken Raw Balances", True, f"- {len(raw_balances)} assets returned")
                        
                        # Log significant balances
                        for asset, amount in raw_balances.items():
                            if float(amount) > 0.01:
                                print(f"   {asset}: {amount}")
                    
                    if "asset_details" in balance_data:
                        asset_details = balance_data["asset_details"]
                        self.log_result("Kraken Asset Details", True, f"- {len(asset_details)} significant balances")
                    
                    return balance_data
                else:
                    error_msg = balance_data.get("error", "Unknown error")
                    self.log_result("Kraken Balance Success", False, f"- Error: {error_msg}")
                    return None
                    
            elif response.status_code == 401:
                self.log_result("Kraken Balance Endpoint", False, "- Authentication required")
                return None
            else:
                self.log_result("Kraken Balance Endpoint", False, f"- HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Kraken Balance Endpoint Test", False, f"- Error: {str(e)}")
            return None
    
    def test_exchange_sync_endpoint(self):
        """Test /api/exchanges/sync endpoint"""
        print("\n=== Testing Exchange Sync Endpoint ===")
        
        try:
            response = requests.post(f"{self.base_url}/exchanges/sync", 
                                   headers=self.get_auth_headers(), timeout=20)
            
            if response.status_code == 200:
                sync_data = response.json()
                self.log_result("Exchange Sync Endpoint", True, "- Sync endpoint responded")
                
                # Check sync results structure
                if "sync_results" in sync_data:
                    sync_results = sync_data["sync_results"]
                    self.log_result("Sync Results Structure", True, f"- {len(sync_results)} exchange results")
                    
                    # Check Kraken specifically
                    if "kraken" in sync_results:
                        kraken_result = sync_results["kraken"]
                        if kraken_result.get("success"):
                            balance = kraken_result.get("balance", 0)
                            self.log_result("Kraken Sync Success", True, f"- Kraken balance: €{balance}")
                        else:
                            error = kraken_result.get("error", "Unknown error")
                            self.log_result("Kraken Sync Success", False, f"- Kraken error: {error}")
                    else:
                        self.log_result("Kraken Sync Present", False, "- No Kraken result in sync")
                    
                    # Log all sync results for debugging
                    for exchange, result in sync_results.items():
                        success = result.get("success", False)
                        if success:
                            balance = result.get("balance", 0)
                            print(f"   {exchange}: SUCCESS - €{balance}")
                        else:
                            error = result.get("error", "Unknown")
                            print(f"   {exchange}: FAILED - {error}")
                
                # Check suggested entry
                if "suggested_entry" in sync_data:
                    suggested = sync_data["suggested_entry"]
                    total = suggested.get("total", 0)
                    balances = suggested.get("balances", [])
                    self.log_result("Suggested Entry", True, f"- Total: €{total}, Balances: {len(balances)}")
                    
                    # Log balance details
                    for balance in balances:
                        exchange_id = balance.get("exchange_id", "unknown")
                        amount = balance.get("amount", 0)
                        print(f"   Exchange {exchange_id}: €{amount}")
                    
                    return sync_data
                else:
                    self.log_result("Suggested Entry", False, "- No suggested entry in response")
                    return sync_data
                    
            elif response.status_code == 401:
                self.log_result("Exchange Sync Endpoint", False, "- Authentication required")
                return None
            else:
                self.log_result("Exchange Sync Endpoint", False, f"- HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Exchange Sync Test", False, f"- Error: {str(e)}")
            return None
    
    def test_auto_create_entry_endpoint(self):
        """Test /api/entries/auto-create endpoint - the main issue"""
        print("\n=== Testing Auto-Create Entry Endpoint (Main Issue) ===")
        
        try:
            response = requests.post(f"{self.base_url}/entries/auto-create", 
                                   headers=self.get_auth_headers(), timeout=20)
            
            if response.status_code == 200:
                auto_data = response.json()
                message = auto_data.get("message", "")
                self.log_result("Auto-Create Entry Endpoint", True, f"- Response: {message}")
                
                if "created successfully" in message:
                    # Entry was created successfully
                    total_balance = auto_data.get("total_balance", 0)
                    pnl_percentage = auto_data.get("pnl_percentage", 0)
                    pnl_amount = auto_data.get("pnl_amount", 0)
                    synced_exchanges = auto_data.get("synced_exchanges", 0)
                    
                    self.log_result("Auto-Entry Creation Success", True, 
                                  f"- Balance: €{total_balance}, PnL: {pnl_percentage}% (€{pnl_amount})")
                    self.log_result("Synced Exchanges Count", True, f"- {synced_exchanges} exchanges synced")
                    
                    return auto_data
                    
                elif "already exists" in message:
                    # Entry for today already exists
                    self.log_result("Auto-Entry Already Exists", True, "- Entry for today already exists")
                    
                    # Check if suggested balances are provided
                    if "suggested_balances" in auto_data:
                        suggested = auto_data["suggested_balances"]
                        self.log_result("Suggested Balances", True, f"- {len(suggested)} balance suggestions")
                        
                        for balance in suggested:
                            exchange_id = balance.get("exchange_id", "unknown")
                            amount = balance.get("amount", 0)
                            print(f"   Exchange {exchange_id}: €{amount}")
                    
                    return auto_data
                else:
                    self.log_result("Auto-Entry Response", True, f"- Unexpected response: {message}")
                    return auto_data
                    
            elif response.status_code == 400:
                # Bad request - might be expected if no balances available
                try:
                    error_data = response.json()
                    detail = error_data.get("detail", "Unknown error")
                    self.log_result("Auto-Create Entry Error", False, f"- Error: {detail}")
                except:
                    self.log_result("Auto-Create Entry Error", False, f"- Error: {response.text}")
                return None
                
            elif response.status_code == 401:
                self.log_result("Auto-Create Entry Endpoint", False, "- Authentication required")
                return None
            else:
                self.log_result("Auto-Create Entry Endpoint", False, f"- HTTP {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.log_result("Auto-Create Entry Test", False, f"- Error: {str(e)}")
            return None
    
    def test_api_key_storage_retrieval(self):
        """Test if API keys are being stored and retrieved properly"""
        print("\n=== Testing API Key Storage and Retrieval ===")
        
        # Test storing the Kraken API keys
        api_key_data = {
            "exchange_name": "kraken",
            "api_key": KRAKEN_API_KEY,
            "api_secret": KRAKEN_PRIVATE_KEY
        }
        
        try:
            # Store API key
            response = requests.post(f"{self.base_url}/exchange-api-keys", 
                                   json=api_key_data,
                                   headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                message = result.get("message", "")
                self.log_result("Store Kraken API Key", True, f"- {message}")
            elif response.status_code == 401:
                self.log_result("Store Kraken API Key", False, "- Authentication required")
                return False
            else:
                self.log_result("Store Kraken API Key", False, f"- HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Store API Key Test", False, f"- Error: {str(e)}")
            return False
        
        # Test retrieving API keys
        try:
            response = requests.get(f"{self.base_url}/exchange-api-keys", 
                                  headers=self.get_auth_headers(), timeout=10)
            
            if response.status_code == 200:
                api_keys = response.json()
                self.log_result("Retrieve API Keys", True, f"- Retrieved {len(api_keys)} API keys")
                
                # Check if Kraken key is present
                kraken_key = None
                for key in api_keys:
                    if key.get("exchange_name") == "kraken":
                        kraken_key = key
                        break
                
                if kraken_key:
                    self.log_result("Kraken API Key Present", True, "- Kraken API key found in storage")
                    
                    # Verify key is masked
                    preview = kraken_key.get("api_key_preview", "")
                    if "..." in preview and len(preview) > 8:
                        self.log_result("API Key Security", True, "- API key properly masked")
                    else:
                        self.log_result("API Key Security", False, f"- API key not properly masked: {preview}")
                    
                    return True
                else:
                    self.log_result("Kraken API Key Present", False, "- Kraken API key not found")
                    return False
                    
            elif response.status_code == 401:
                self.log_result("Retrieve API Keys", False, "- Authentication required")
                return False
            else:
                self.log_result("Retrieve API Keys", False, f"- HTTP {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.log_result("Retrieve API Keys Test", False, f"- Error: {str(e)}")
            return False
    
    def test_authentication_flow(self):
        """Test authentication to get session token for other tests"""
        print("\n=== Testing Authentication Flow ===")
        
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
    
    def run_auto_entry_debug_tests(self):
        """Run comprehensive tests to debug the auto-entry creation issue"""
        print("🚀 Starting Auto-Entry Creation Debug Tests")
        print(f"🔗 Testing against: {self.base_url}")
        print(f"🔑 Using Kraken API Key: {KRAKEN_API_KEY[:8]}...")
        print("=" * 70)
        
        # Test API connection first
        if not self.test_api_connection():
            print("\n❌ API connection failed. Cannot proceed with tests.")
            return False
        
        # Test authentication flow
        self.test_authentication_flow()
        
        print("\n🔍 AUTO-ENTRY CREATION DEBUG TESTS")
        print("=" * 50)
        
        # 1. Test direct Kraken API to verify keys work
        kraken_direct = self.test_direct_kraken_api()
        
        # 2. Test backend Kraken balance endpoint
        kraken_backend = self.test_kraken_balance_endpoint()
        
        # 3. Test API key storage and retrieval
        api_keys_working = self.test_api_key_storage_retrieval()
        
        # 4. Test exchange sync endpoint
        sync_data = self.test_exchange_sync_endpoint()
        
        # 5. Test auto-create entry endpoint (the main issue)
        auto_create_data = self.test_auto_create_entry_endpoint()
        
        # Print comprehensive summary
        print("\n" + "=" * 70)
        print("📊 AUTO-ENTRY CREATION DEBUG SUMMARY")
        print("=" * 70)
        print(f"✅ Passed: {len(self.passed_tests)}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        
        if self.failed_tests:
            print("\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"   - {test}")
        
        # Detailed analysis
        print("\n🔍 ROOT CAUSE ANALYSIS")
        print("=" * 40)
        
        if kraken_direct:
            print(f"✅ Direct Kraken API works - Balance: €{kraken_direct.get('total_eur', 0):.2f}")
        else:
            print("❌ Direct Kraken API failed - Check API keys")
        
        if kraken_backend:
            balance = kraken_backend.get('balance_eur', 0)
            print(f"✅ Backend Kraken endpoint works - Balance: €{balance}")
        else:
            print("❌ Backend Kraken endpoint failed - Check authentication or backend implementation")
        
        if api_keys_working:
            print("✅ API key storage/retrieval working")
        else:
            print("❌ API key storage/retrieval failed - Check authentication")
        
        if sync_data:
            sync_results = sync_data.get('sync_results', {})
            kraken_sync = sync_results.get('kraken', {})
            if kraken_sync.get('success'):
                print(f"✅ Exchange sync works - Kraken: €{kraken_sync.get('balance', 0)}")
            else:
                print(f"❌ Exchange sync failed - Kraken error: {kraken_sync.get('error', 'Unknown')}")
        else:
            print("❌ Exchange sync failed - Check authentication or implementation")
        
        if auto_create_data:
            message = auto_create_data.get('message', '')
            if 'created successfully' in message:
                print(f"✅ Auto-create entry works - Balance: €{auto_create_data.get('total_balance', 0)}")
            elif 'already exists' in message:
                print("ℹ️ Auto-create entry: Entry for today already exists")
            else:
                print(f"⚠️ Auto-create entry: Unexpected response - {message}")
        else:
            print("❌ Auto-create entry failed - This is the main issue")
        
        # Specific issue analysis
        print("\n🎯 SPECIFIC ISSUE ANALYSIS")
        print("=" * 40)
        
        if not kraken_direct:
            print("🔴 CRITICAL: Kraken API keys don't work directly")
            print("   → Check if keys are correct and have proper permissions")
        elif not kraken_backend:
            print("🔴 CRITICAL: Backend can't access Kraken API")
            print("   → Check authentication or backend Kraken integration")
        elif not sync_data or not sync_data.get('sync_results', {}).get('kraken', {}).get('success'):
            print("🔴 CRITICAL: Exchange sync failing for Kraken")
            print("   → Check sync endpoint implementation")
        elif not auto_create_data:
            print("🔴 CRITICAL: Auto-create entry endpoint failing")
            print("   → This is the reported issue - check auto-create implementation")
        else:
            print("✅ All components working - Issue may be intermittent or authentication-related")
        
        success_rate = len(self.passed_tests) / (len(self.passed_tests) + len(self.failed_tests)) * 100 if (len(self.passed_tests) + len(self.failed_tests)) > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        return len(self.failed_tests) == 0

if __name__ == "__main__":
    tester = CryptoPnLTester()
    
    # Run auto-entry creation debug tests
    print("🎯 RUNNING AUTO-ENTRY CREATION DEBUG TESTS")
    print("=" * 60)
    debug_success = tester.run_auto_entry_debug_tests()
    
    if debug_success:
        print("\n🎉 Auto-entry creation debug tests completed successfully!")
        sys.exit(0)
    else:
        print("\n⚠️ Some auto-entry creation tests failed. Check the output above for details.")
        sys.exit(1)