#!/usr/bin/env python3
"""
Comprehensive Database Status Check for ICSS
Single file to check all database operations and status
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

class DatabaseStatusChecker:
    """Complete database status checker for ICSS"""
    
    def __init__(self):
        self.client = None
        self.url = ""
        self.key = ""
        self.connected = False
        
    def load_credentials(self):
        """Load and validate database credentials"""
        print("=== DATABASE CREDENTIALS CHECK ===")
        
        # Load environment variables
        load_dotenv()
        
        # Get credentials
        self.url = os.environ.get("SUPABASE_URL", "").strip()
        self.key = os.environ.get("SUPABASE_ANON_KEY", "").strip()
        
        print(f"URL: {self.url}")
        print(f"Key: {'SET' if self.key else 'NOT SET'}")
        
        # Check if credentials are valid
        if not self.url or not self.key:
            print("STATUS: CREDENTIALS NOT CONFIGURED")
            print("\nSETUP INSTRUCTIONS:")
            print("1. Edit your .env file")
            print("2. Add your Supabase URL and ANON key")
            print("3. Restart this check")
            return False
        
        if "your-project-id" in self.url or "your-supabase-anon-key" in self.key:
            print("STATUS: PLACEHOLDER CREDENTIALS DETECTED")
            print("\nSETUP INSTRUCTIONS:")
            print("1. Replace placeholder values in .env")
            print("2. Use your actual Supabase project URL and key")
            return False
        
        return True
    
    def test_connection(self):
        """Test database connection"""
        print("\n=== CONNECTION TEST ===")
        
        try:
            self.client = create_client(self.url, self.key)
            print("SUCCESS: Supabase client created")
            self.connected = True
            return True
        except Exception as e:
            print(f"ERROR: Connection failed - {e}")
            self.connected = False
            return False
    
    def check_table_structure(self):
        """Check table structures and columns"""
        print("\n=== TABLE STRUCTURE CHECK ===")
        
        if not self.connected:
            print("ERROR: Not connected to database")
            return False
        
        tables_status = {}
        
        # Check crowd_metrics table
        print("\nCROWD_METRICS table:")
        try:
            response = self.client.table('crowd_metrics').select('*').limit(1).execute()
            if response.data:
                columns = list(response.data[0].keys())
                print(f"  STATUS: EXISTS")
                print(f"  COLUMNS: {', '.join(columns)}")
                tables_status['crowd_metrics'] = {'exists': True, 'columns': columns}
            else:
                print("  STATUS: EXISTS (no data)")
                tables_status['crowd_metrics'] = {'exists': True, 'columns': []}
        except Exception as e:
            if "does not exist" in str(e):
                print("  STATUS: NOT FOUND - Schema needs setup")
                tables_status['crowd_metrics'] = {'exists': False, 'error': str(e)}
            else:
                print(f"  ERROR: {e}")
                tables_status['crowd_metrics'] = {'exists': False, 'error': str(e)}
        
        # Check alerts table
        print("\nALERTS table:")
        try:
            response = self.client.table('alerts').select('*').limit(1).execute()
            if response.data:
                columns = list(response.data[0].keys())
                print(f"  STATUS: EXISTS")
                print(f"  COLUMNS: {', '.join(columns)}")
                tables_status['alerts'] = {'exists': True, 'columns': columns}
            else:
                print("  STATUS: EXISTS (no data)")
                tables_status['alerts'] = {'exists': True, 'columns': []}
        except Exception as e:
            if "does not exist" in str(e):
                print("  STATUS: NOT FOUND - Schema needs setup")
                tables_status['alerts'] = {'exists': False, 'error': str(e)}
            else:
                print(f"  ERROR: {e}")
                tables_status['alerts'] = {'exists': False, 'error': str(e)}
        
        return tables_status
    
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
                'people_count': 15,
                'density': 0.6,
                'flow_direction': 'Test-Direction',
                'risk_level': 'Medium',
                'crowd_level': 'Moderate',
                'peak_count': 20,
                'average_count': 12.5
            }
            
            insert_response = self.client.table('crowd_metrics').insert(test_data).execute()
            record_id = insert_response.data[0]['id']
            print(f"  INSERT: SUCCESS (ID: {record_id})")
            
            # Select test data
            select_response = self.client.table('crowd_metrics').select('*').eq('id', record_id).execute()
            if select_response.data:
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
                'message': 'Test alert message for database check',
                'severity': 'MEDIUM',
                'people_count': 15,
                'density': 0.6
            }
            
            alert_response = self.client.table('alerts').insert(alert_data).execute()
            alert_id = alert_response.data[0]['id']
            print(f"  INSERT: SUCCESS (ID: {alert_id})")
            
            # Select test alert
            alert_select = self.client.table('alerts').select('*').eq('id', alert_id).execute()
            if alert_select.data:
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
            metrics_count = self.client.table('crowd_metrics').select('count', count='exact').execute()
            alerts_count = self.client.table('alerts').select('count', count='exact').execute()
            
            summary['total_metrics'] = metrics_count.count or 0
            summary['total_alerts'] = alerts_count.count or 0
            
            print(f"Total crowd_metrics records: {summary['total_metrics']}")
            print(f"Total alerts records: {summary['total_alerts']}")
            
            # Get latest records
            if summary['total_metrics'] > 0:
                latest_metrics = self.client.table('crowd_metrics').select('*').order('created_at', desc=True).limit(1).execute()
                if latest_metrics.data:
                    record = latest_metrics.data[0]
                    summary['latest_metrics'] = {
                        'people_count': record['people_count'],
                        'risk_level': record['risk_level'],
                        'density': record['density'],
                        'timestamp': record['created_at']
                    }
                    print(f"\nLatest crowd metrics:")
                    print(f"  People count: {record['people_count']}")
                    print(f"  Risk level: {record['risk_level']}")
                    print(f"  Density: {record['density']}")
                    print(f"  Time: {record['created_at']}")
            
            if summary['total_alerts'] > 0:
                latest_alerts = self.client.table('alerts').select('*').order('timestamp', desc=True).limit(1).execute()
                if latest_alerts.data:
                    record = latest_alerts.data[0]
                    summary['latest_alert'] = {
                        'message': record['message'],
                        'severity': record['severity'],
                        'timestamp': record['timestamp']
                    }
                    print(f"\nLatest alert:")
                    print(f"  Message: {record['message'][:50]}...")
                    print(f"  Severity: {record['severity']}")
                    print(f"  Time: {record['timestamp']}")
            
            return summary
            
        except Exception as e:
            print(f"ERROR getting summary: {e}")
            return None
    
    def provide_setup_instructions(self):
        """Provide setup instructions if needed"""
        print("\n=== SETUP INSTRUCTIONS ===")
        print("If tables are missing, run this SQL in your Supabase dashboard:")
        print(f"1. Open: https://supabase.com/dashboard/project/{self.url.split('//')[1].split('.')[0]}/sql")
        print("2. Copy the SQL from supabase_schema.sql")
        print("3. Click 'Run' to create tables")
        print("\nFor credential issues:")
        print("1. Check your .env file")
        print("2. Ensure SUPABASE_URL and SUPABASE_ANON_KEY are correct")
        print("3. Restart the application")
    
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
        
        # Step 3: Check table structure
        table_status = self.check_table_structure()
        
        # Step 4: Test operations
        operations_status = self.test_operations()
        
        # Step 5: Get summary
        summary = self.get_database_summary()
        
        # Step 6: Final status
        print("\n" + "=" * 50)
        print("FINAL STATUS:")
        
        # Overall status
        all_tables_exist = all(status.get('exists', False) for status in table_status.values())
        all_operations_work = all(status == 'WORKING' for status in operations_status.values())
        
        if all_tables_exist and all_operations_work:
            print("DATABASE: FULLY OPERATIONAL")
            print("Your ICSS application is ready to use!")
        elif all_tables_exist:
            print("DATABASE: PARTIALLY WORKING")
            print("Tables exist but some operations may have issues")
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
