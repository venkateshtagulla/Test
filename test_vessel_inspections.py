"""
Test script to verify inspection assignments are being fetched correctly for vessels.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from repository.inspection_assignment_repository import InspectionAssignmentRepository
from repository.vessel_repository import VesselRepository

def test_list_by_vessel():
    """Test listing inspection assignments by vessel."""
    
    # Initialize repositories
    assignment_repo = InspectionAssignmentRepository()
    vessel_repo = VesselRepository()
    
    # Get all vessels
    print("Fetching all vessels...")
    vessels, _ = vessel_repo.scan_items(limit=10)
    
    if not vessels:
        print("No vessels found in the database")
        return
    
    print(f"Found {len(vessels)} vessels")
    
    # Test with the first vessel
    for vessel in vessels:
        vessel_id = vessel.get("vessel_id")
        vessel_name = vessel.get("name", "Unknown")
        
        print(f"\n--- Testing vessel: {vessel_name} ({vessel_id}) ---")
        
        # Fetch inspection assignments for this vessel
        try:
            inspections, _ = assignment_repo.list_by_vessel(vessel_id=vessel_id, limit=100)
            print(f"Found {len(inspections)} inspection assignments")
            
            if inspections:
                for idx, inspection in enumerate(inspections, 1):
                    print(f"\n  Inspection {idx}:")
                    print(f"    - Assignment ID: {inspection.get('assignment_id')}")
                    print(f"    - Inspection Name: {inspection.get('inspection_name', 'N/A')}")
                    print(f"    - Form ID: {inspection.get('form_id')}")
                    print(f"    - Vessel ID: {inspection.get('vessel_id')}")
                    print(f"    - Assignee ID: {inspection.get('assignee_id')}")
                    print(f"    - Status: {inspection.get('status')}")
            else:
                print("  No inspections found for this vessel")
                
        except Exception as e:
            print(f"Error fetching inspections: {e}")

if __name__ == "__main__":
    test_list_by_vessel()
