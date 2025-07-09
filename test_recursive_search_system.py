"""
Test script for the new recursive research system with sonar-reasoning-pro
"""

import asyncio
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.recursive_research_agent import RecursiveResearchAgent
from app.models import GrantFilter
from database.session import AsyncSessionLocal
from agents.integrated_research_agent import IntegratedResearchAgent

async def test_recursive_search():
    """Test the new recursive search system."""
    print("🔍 Testing Recursive Research Agent with sonar-reasoning-pro")
    print(f"⏰ Test started at: {datetime.now()}")
    
    try:
        # Create integrated research agent with database sessionmaker
        agent = IntegratedResearchAgent(AsyncSessionLocal)
        print(f"✅ Agent initialized with recursive search approach")
        
        # Create test filter for Kevin's focus areas
        test_filter = GrantFilter(
            keywords="telecommunications infrastructure, women-owned nonprofit, community shelter",
            min_score=0.0,
            min_funding=5000,
            max_funding=100000,
            deadline_before=None,
            deadline_after=None,
            geographic_focus="Natchitoches Parish Louisiana",
            sites_to_focus=None
        )
        
        print("🎯 Testing with focus areas:")
        print(f"   - Keywords: {test_filter.keywords}")
        print(f"   - Geographic: {test_filter.geographic_focus}")
        print(f"   - Funding range: ${test_filter.min_funding:,} - ${test_filter.max_funding:,}")
        
        # Run recursive search
        print("\n🚀 Starting recursive search...")
        grants = await agent.search_grants(test_filter)
        
        print(f"\n📊 Search Results:")
        print(f"   - Total grants found: {len(grants)}")
        
        if grants:
            print(f"\n📝 Sample grants:")
            for i, grant in enumerate(grants[:3]):  # Show first 3
                print(f"   {i+1}. {grant.title}")
                print(f"      Funder: {grant.funder_name or 'Unknown'}")
                print(f"      Amount: {grant.funding_amount_display or 'Not specified'}")
                print(f"      Score: {grant.overall_composite_score or 'Not scored'}")
                print(f"      Sector: {grant.identified_sector or 'Unknown'}")
                print("")
        
        # Test statistics
        stats = await agent.get_search_statistics()
        print(f"📈 Search Statistics:")
        for key, value in stats.items():
            print(f"   - {key}: {value}")
        
        print(f"\n✅ Test completed successfully at: {datetime.now()}")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_recursive_search())
    sys.exit(0 if success else 1)
