"""
Script to run grant searches using the research and analysis agents.
"""

from agents.research_agent import GrantResearchAgent
from agents.analysis_agent import GrantAnalysisAgent

def main():
    # Initialize agents
    research_agent = GrantResearchAgent()
    analysis_agent = GrantAnalysisAgent()

    # Set up search criteria
    search_criteria = {
        'keywords': ['technology', 'education', 'innovation'],
        'min_amount': 10000,
        'deadline_after': 'today'
    }

    # Search for grants
    grants = research_agent.search_grants(search_criteria)

    # Analyze each grant
    results = []
    for grant in grants:
        analysis = analysis_agent.analyze_grant(grant)
        results.append(analysis)

    # Output results
    print(f'Found {len(results)} matching grants')
    for result in results:
        print(f'Grant: {result.get('title')}')