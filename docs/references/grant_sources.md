# Grant Sources and Search Strategy

## Overview
This document outlines the curated list of free grant search resources optimized for integration with the Smart Grant Finder system. The sources are categorized by focus area and include implementation details for automated searching.

## Telecommunications Grants

### Core Search Targets

1. **Grants.gov**
   - Focus: Federal telecom infrastructure grants (BEAD Program, Middle Mile)
   - Search Parameters: "telecommunications" OR "broadband" + "rural"
   - Priority: High

2. **USDA Community Connect Grants**
   - Focus: Rural broadband deployment
   - Priority Tag: community-shelter-connectivity
   - URL: https://www.rd.usda.gov/programs-services/telecommunications-programs/community-connect-grants

3. **USDA Distance Learning & Telemedicine Grants**
   - Focus: Event Wi-Fi infrastructure at shelters
   - Alert Configuration: "telemedicine" AND "distance learning"
   - URL: https://www.rd.usda.gov/programs-services/telecommunications-programs/distance-learning-telemedicine-grants

4. **NTIA BroadbandUSA**
   - Focus: Federal/state partnership opportunities
   - Search Strategy: Use geographic filters for Louisiana focus

5. **State Broadband Offices**
   - Focus: LA-08 district opportunities (Natchitoches focus)
   - Geographic Filter: Louisiana AND population <20,000

6. **FCC Funding Opportunities**
   - Focus: Affordable Connectivity Program extensions
   - Search Query: "FCC" AND "telecom grants" AFTER 2024

7. **Rural Health Information Hub**
   - Focus: Cross-sector connectivity grants
   - Tag: healthcare AND connectivity

## Women-Owned Nonprofit Grants

### Primary Sources

1. **IFundWomen Universal Grant Database**
   - Priority Filter: women-owned AND (nonprofit OR community-shelter)
   - Focus: Comprehensive grant listings

2. **Amber Grant Foundation**
   - Amount: Monthly $10K opportunities
   - Alert: deadline <30d AND "no theme restriction"

3. **SBA Women's Business Center**
   - Source: Grants.gov
   - Filter: agency:"SBA"

4. **HerRise Microgrant**
   - Focus: Shelter infrastructure
   - Tag: extreme-weather-response

5. **Cartier Women's Initiative**
   - Amount: Global $100K opportunities
   - Filter: social-impact AND revenue <$500K

6. **Terra Viva Grants Directory**
   - Focus: Shelter-related funding (heat/cold resilience)

7. **GrantStation via TechSoup**
   - Access: Free through nonprofit partnerships

## Implementation Strategy

### Search Configuration

```python
# Telecom grants configuration
telecom_params = {
    "search_terms": ["broadband deployment", "rural connectivity"],
    "filters": {
        "funding_type": ["grant", "cooperative agreement"],
        "eligible_entities": ["nonprofits", "municipalities"],
        "geo_restrictions": "LA-08"
    },
    "sources": ["Grants.gov", "USDA", "State portals"],
    "alert_rules": {
        "match_score": ">85%",
        "deadline_window": "30 days"
    }
}

# Women-owned nonprofit configuration
nonprofit_params = {
    "priority_keywords": ["women-led", "extreme weather shelter"],
    "exclusion_filters": ["religious-affiliation"],
    "funding_range": "$5k-$100k",
    "compliance_check": ["501(c)(3) eligible", "Natchitoches partnerships"]
}
```

### Workflow Optimization

1. **API Integration**
   - Use deep_search mode with site:gov OR site:org domain restrictions
   - Weight distribution: 70% local/30% federal

2. **Automated Triage**
   - Priority 1: Grants matching both telecom + shelter criteria
   - Priority 2: Women-owned grants with fast turnaround (<45 days)

3. **State-Specific Data Collection**
   ```sql
   SELECT * FROM louisiana.gov
   WHERE ("grant" IN title)
   AND ("telecom" OR "shelter" IN description)
   ```

## Limitations and Future Improvements

- Free sources miss approximately 22% of niche opportunities (per Peak Proposals data)
- Consider GrantForward API integration ($99/mo) for comprehensive coverage
- Regular updates needed for state-specific opportunities

## References

1. Peak Proposals Blog: https://www.peakproposals.com/blog/the-best-free-places-to-search-for-grant-funding
2. USDA Programs: https://www.rd.usda.gov/programs-services/telecommunications-programs
3. Grant Writing Resources: https://www.learngrantwriting.org/blog/best-grant-databases
4. Chamber of Commerce: https://www.uschamber.com/co/run/business-financing/small-business-grants-and-programs 