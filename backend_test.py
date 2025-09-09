#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Crypto PnL Tracker
Tests all CRUD operations, calculations, and edge cases
"""

import requests
import json
from datetime import date, datetime, timedelta
import time
import sys

# Backend URL from frontend/.env
BACKEND_URL = "https://crypto-pnl-tracker.preview.emergentagent.com/api"

class CryptoPnLTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.test_entries = []
        self.failed_tests = []
        self.passed_tests = []
        
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