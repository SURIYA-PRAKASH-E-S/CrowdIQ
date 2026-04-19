#!/usr/bin/env python3
"""
Comprehensive Database Status Check for ICSS
Single file to check all database operations and status
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from firebase_client import get_db

class DatabaseStatusChecker:
    """Complete database status checker for ICSS"""
    
    def __init__(self):
        self.db = None
        self.connected = False
        
    def load_credentials(self):
        """Load and validate database credentials"""
        print("=== DATABASE CREDENTIALS CHECK ===")
        
        # Load environment variables
        load_dotenv()
        
        # Get credentials
        database_url = os.environ.get("FIREBASE_DATABASE_URL", "").strip()
        credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
        
        print(f"Database URL: {database_url}")
        print(f"Credentials Path: {credentials_path}")
        print(f"Credentials File Exists: {os.path.exists(credentials_path) if credentials_path else 'N/A'}")
        
        # Check if credentials are valid
        if not database_url or not credentials_path:
            print("STATUS: CREDENTIALS NOT CONFIGURED")
            print("\nSETUP INSTRUCTIONS:")
            print("1. Edit your .env file")
            print("2. Add your Firebase Database URL and service account path")
            print("3. Download your service account JSON from Firebase Console")
            print("4. Restart this check")
            return False
        
        if "your-project-id" in database_url or "firebase-service-account.json" in credentials_path and not os.path.exists(credentials_path):
            print("STATUS: PLACEHOLDER CREDENTIALS DETECTED")
            print("\nSETUP INSTRUCTIONS:")
            print("1. Replace placeholder values in .env")
            print("2. Use your actual Firebase project URL and service account path")
            return False
        
        if not os.path.exists(credentials_path):
            print("STATUS: SERVICE ACCOUNT FILE NOT FOUND")
            print("\nSETUP INSTRUCTIONS:")
            print("1. Download service account JSON from Firebase Console")
            print("2. Place it at the path specified in GOOGLE_APPLICATION_CREDENTIALS")
            return False
        
        return True
    
    def test_connection(self):
        """Test database connection"""
        print("\n=== CONNECTION TEST ===")
        
        try:
            self.db = get_db()
            if self.db:
                print("SUCCESS: Firebase client created")
                self.connected = True
                return True
            else:
                print("ERROR: Firebase client is None")
                self.connected = False
                return False
        except Exception as e:
            print(f"ERROR: Connection failed - {e}")
            self.connected = False
            return False
    
    def check_table_structure(self):
        """Check collection structures and data"""
        print("\n=== COLLECTION STRUCTURE CHECK ===")
        
        if not self.connected:
            print("ERROR: Not connected to database")
            return False
        
        collections_status = {}
        
        # Check crowd_metrics collection
        print("\nCROWD_METRICS collection:")
        try:
            data = self.db.child('crowd_metrics').limit_to_first(1).get()
            if data:
                columns = list(data.values())[0].keys() if data else []
                print(f"  STATUS: EXISTS")
                print(f"  FIELDS: {', '.join(columns)}")
                collections_status['crowd_metrics'] = {'exists': True, 'fields': columns}
            else:
                print("  STATUS: EXISTS (no data)")
                collections_status['crowd_metrics'] = {'exists': True, 'fields': []}
        except Exception as e:
            print(f"  ERROR: {e}")
            collections_status['crowd_metrics'] = {'exists': False, 'error': str(e)}
        
        # Check alerts collection
        print("\nALERTS collection:")
        try:
            data = self.db.child('alerts').limit_to_first(1).get()
            if data:
                columns = list(data.values())[0].keys() if data else []
                print(f"  STATUS: EXISTS")
                print(f"  FIELDS: {', '.join(columns)}")
                collections_status['alerts'] = {'exists': True, 'fields': columns}
            else:
                print("  STATUS: EXISTS (no data)")
                collections_status['alerts'] = {'exists': True, 'fields': []}
        except Exception as e:
            print(f"  ERROR: {e}")
            collections_status['alerts'] = {'exists': False, 'error': str(e)}
        
        return collections_status
    
    def test_operations(self):
        """Test database insert and select operations"""
        print("\n=== OPERATIONS TEST ===")
        
        if not self.connected:
            print("ERROR: Not connected to database")
            return False
        
        operations_status = {}
        
        # Test crowd_metrics operations
        print("\n1. CROWD_METRICS OPERATIONS:")
        try:
            # Insert test data
            test_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'people_count': 15,
                'density': 0.6,
                'flow_direction': 'Test-Direction',
                'risk_level': 'Medium',
                'crowd_level': 'Moderate',
                'peak_count': 20,
                'average_count': 12.5
            }
            
            result = self.db.child('crowd_metrics').push(test_data)
            record_id = result['name']  # Firebase returns the new key as 'name'
            print(f"  INSERT: SUCCESS (ID: {record_id})")
            
            # Select test data
            select_data = self.db.child('crowd_metrics').child(record_id).get()
            if select_data:
                print(f"  SELECT: SUCCESS")
                operations_status['crowd_metrics'] = 'WORKING'
            else:
                print(f"  SELECT: FAILED (no data returned)")
                operations_status['crowd_metrics'] = 'PARTIAL'
                
        except Exception as e:
            print(f"  ERROR: {e}")
            operations_status['crowd_metrics'] = 'FAILED'
        
        # Test alerts operations
        print("\n2. ALERTS OPERATIONS:")
        try:
            # Insert test alert
            alert_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'message': 'Test alert message for database check',
                'severity': 'MEDIUM',
                'count': 15,
                'density': 0.6
            }
            
            alert_result = self.db.child('alerts').push(alert_data)
            alert_id = alert_result['name']
            print(f"  INSERT: SUCCESS (ID: {alert_id})")
            
            # Select test alert
            alert_select = self.db.child('alerts').child(alert_id).get()
            if alert_select:
                print(f"  SELECT: SUCCESS")
                operations_status['alerts'] = 'WORKING'
            else:
                print(f"  SELECT: FAILED (no data returned)")
                operations_status['alerts'] = 'PARTIAL'
                
        except Exception as e:
            print(f"  ERROR: {e}")
            operations_status['alerts'] = 'FAILED'
        
        return operations_status
    
    def get_database_summary(self):
        """Get comprehensive database summary"""
        print("\n=== DATABASE SUMMARY ===")
        
        if not self.connected:
            print("ERROR: Not connected to database")
            return None
        
        summary = {}
        
        try:
            # Get record counts
            metrics_data = self.db.child('crowd_metrics').get()
            alerts_data = self.db.child('alerts').get()
            
            summary['total_metrics'] = len(metrics_data) if metrics_data else 0
            summary['total_alerts'] = len(alerts_data) if alerts_data else 0
            
            print(f"Total crowd_metrics records: {summary['total_metrics']}")
            print(f"Total alerts records: {summary['total_alerts']}")
            
            # Get latest records
            if summary['total_metrics'] > 0:
                latest_metrics = self.db.child('crowd_metrics').order_by_child('timestamp').limit_to_last(1).get()
                if latest_metrics:
                    for key, record in latest_metrics.items():
                        summary['latest_metrics'] = {
                            'people_count': record['people_count'],
                            'risk_level': record['risk_level'],
                            'density': record['density'],
                            'timestamp': record['timestamp']
                        }
                        print(f"\nLatest crowd metrics:")
                        print(f"  People count: {record['people_count']}")
                        print(f"  Risk level: {record['risk_level']}")
                        print(f"  Density: {record['density']}")
                        print(f"  Time: {record['timestamp']}")
                        break
            
            if summary['total_alerts'] > 0:
                latest_alerts = self.db.child('alerts').order_by_child('timestamp').limit_to_last(1).get()
                if latest_alerts:
                    for key, record in latest_alerts.items():
                        summary['latest_alert'] = {
                            'message': record['message'],
                            'severity': record['severity'],
                            'timestamp': record['timestamp']
                        }
                        print(f"\nLatest alert:")
                        print(f"  Message: {record['message'][:50]}...")
                        print(f"  Severity: {record['severity']}")
                        print(f"  Time: {record['timestamp']}")
                        break
            
            return summary
            
        except Exception as e:
            print(f"ERROR getting summary: {e}")
            return None
    
    def provide_setup_instructions(self):
        """Provide setup instructions if needed"""
        print("\n=== SETUP INSTRUCTIONS ===")
        print("Firebase Realtime Database requires no schema setup.")
        print("Collections are created automatically when you first write data.")
        print("\nFor credential issues:")
        print("1. Check your .env file")
        print("2. Ensure FIREBASE_DATABASE_URL and GOOGLE_APPLICATION_CREDENTIALS are correct")
        print("3. Ensure the service account JSON file exists at the specified path")
        print("4. Restart the application")
    
    def run_full_check(self):
        """Run complete database status check"""
        print("ICSS DATABASE STATUS CHECK")
        print("=" * 50)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Check credentials
        if not self.load_credentials():
            return False
        
        # Step 2: Test connection
        if not self.test_connection():
            return False
        
        # Step 3: Check collection structure
        collection_status = self.check_table_structure()
        
        # Step 4: Test operations
        operations_status = self.test_operations()
        
        # Step 5: Get summary
        summary = self.get_database_summary()
        
        # Step 6: Final status
        print("\n" + "=" * 50)
        print("FINAL STATUS:")
        
        # Overall status
        all_collections_exist = all(status.get('exists', False) for status in collection_status.values())
        all_operations_work = all(status == 'WORKING' for status in operations_status.values())
        
        if all_collections_exist and all_operations_work:
            print("DATABASE: FULLY OPERATIONAL")
            print("Your ICSS application is ready to use!")
        elif all_collections_exist:
            print("DATABASE: PARTIALLY WORKING")
            print("Collections exist but some operations may have issues")
        else:
            print("DATABASE: NEEDS SETUP")
            self.provide_setup_instructions()
        
        print("=" * 50)
        
        return True

def main():
    """Main function to run database status check"""
    checker = DatabaseStatusChecker()
    success = checker.run_full_check()
    
    if not success:
        print("\nDatabase check failed. Please fix the issues above.")
        sys.exit(1)
    else:
        print("\nDatabase check completed successfully!")

if __name__ == "__main__":
    main()
