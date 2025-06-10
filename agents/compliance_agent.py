# agents/compliance_agent.py
from app.schemas import EnrichedGrant, ComplianceScores, ResearchContextScores # Assuming EnrichedGrant is accessible
import yaml
import logging
from typing import Dict, Any, Optional, List
from utils.perplexity_client import PerplexityClient # For potential LLM use in compliance checks
import re # For text processing

logger = logging.getLogger(__name__)

class ComplianceAnalysisAgent:
    def __init__(self, compliance_config_path: str, profile_config_path: str, perplexity_client: Optional[PerplexityClient]): # Allow Optional PerplexityClient
        if perplexity_client is None:
            logger.error("Perplexity client cannot be None for ComplianceAnalysisAgent.")
            raise ValueError("Perplexity client cannot be None for ComplianceAnalysisAgent.")
        
        try:
            with open(compliance_config_path, 'r') as f:
                self.compliance_rules = yaml.safe_load(f)
            logger.info(f"Successfully loaded compliance rules from {compliance_config_path}")
        except FileNotFoundError:
            logger.error(f"Compliance config file not found: {compliance_config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing compliance config file {compliance_config_path}: {e}")
            raise

        try:
            with open(profile_config_path, 'r') as f:
                self.kevin_profile = yaml.safe_load(f)
            logger.info(f"Successfully loaded Kevin profile from {profile_config_path}")
        except FileNotFoundError:
            logger.error(f"Kevin profile config file not found: {profile_config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing Kevin profile config file {profile_config_path}: {e}")
            raise
        
        self.perplexity_client = perplexity_client # Available for future LLM-based checks
        
        self.weights = self.compliance_rules.get('scoring_weights', {})
        self.business_logic_weight = self.weights.get('business_logic_alignment', 0.3)
        self.feasibility_context_weight = self.weights.get('feasibility_context', 0.4)
        self.strategic_synergy_weight = self.weights.get('strategic_synergy', 0.3)

    async def analyze_grant(self, grant: EnrichedGrant) -> EnrichedGrant:
        # Orchestrate the 3 validation cycles
        # Calculate final composite score
        # Update and return the grant object
        
        # Ensure research_scores is initialized
        if grant.research_scores is None:
            grant.research_scores = ResearchContextScores() # Or handle as an error/default

        # Initialize compliance_scores if not present
        if grant.compliance_scores is None:
            grant.compliance_scores = ComplianceScores()

        # Calculate and store compliance scores
        grant.compliance_scores.business_logic_alignment = await self._calculate_business_logic_alignment(grant)
        grant.compliance_scores.feasibility_score = await self._calculate_feasibility_context(grant) # Changed feasibility_context to feasibility_score
        grant.compliance_scores.strategic_synergy = await self._calculate_strategic_synergy(grant)
        
        grant.compliance_scores.final_weighted_score = self._calculate_final_weighted_score(grant)
        # Update grant status
        grant.record_status = "COMPLIANCE_SCORED" # Or a more descriptive status
        
        logger.info(f"Compliance analysis complete for grant: {grant.title}. Final score: {grant.compliance_scores.final_weighted_score:.2f}")
        return grant

    def _normalize_score(self, score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
        """Helper to normalize score between 0 and 1."""
        return max(min_val, min(score, max_val))
    
    async def _calculate_business_logic_alignment(self, grant: EnrichedGrant) -> float:
        logger.debug(f"Calculating business logic alignment for {grant.title}")
        score = 1.0  # Start with a perfect score
        eligibility_text = grant.eligibility_criteria or grant.eligibility_summary_llm or ""
        text_to_search = f"{grant.title} {grant.description} {eligibility_text}".lower()

        rules = self.compliance_rules.get('business_logic_rules', {})
        profile = self.kevin_profile.get('business_profile', {})

        # 1. Check for prohibited grant keywords
        prohibited_keywords = rules.get('prohibited_grant_keywords', [])
        for keyword in prohibited_keywords:
            if keyword.lower() in text_to_search:
                logger.warning(f"Business Logic: Prohibited keyword '{keyword}' found for grant {grant.title}")
                score -= 0.5 # Significant penalty
                break 
        
        # 2. Check Kevin's required certifications (if grant specifies any implicitly or explicitly)
        # This is a simplified check. A more advanced version might parse grant requirements for specific certs.
        # For now, we assume if Kevin doesn't have a cert listed in *our* rules as required for *us*, it's a penalty.
        # This part of the logic might be better if the grant itself lists required certs.
        # kevin_certs = set(c.lower() for c in profile.get('certifications', []))
        # required_by_kevin_rules = rules.get('required_kevin_certifications_for_application', []) # Hypothetical rule
        # for req_cert in required_by_kevin_rules:
        #     if req_cert.lower() not in kevin_certs:
        #         score -= 0.2 
        #         logger.warning(f"Business Logic: Kevin missing required cert '{req_cert}' for grant {grant.title}")

        # 3. Align with business type (e.g., for-profit vs. non-profit)
        kevin_type = profile.get('type', "For-Profit").lower()
        grant_eligibility_text = eligibility_text.lower()

        if "non-profit" in grant_eligibility_text and kevin_type != "non-profit":
            logger.warning(f"Business Logic: Grant for non-profits, Kevin is {kevin_type} for grant {grant.title}")
            score -= 0.3
        elif "for-profit" in grant_eligibility_text and kevin_type != "for-profit":
            logger.warning(f"Business Logic: Grant for for-profits, Kevin is {kevin_type} for grant {grant.title}")
            score -= 0.3
        
        # 4. Check for ethical red flags
        ethical_flags = rules.get('ethical_red_flags_keywords', [])
        for flag in ethical_flags:
            if flag.lower() in text_to_search:
                logger.warning(f"Business Logic: Ethical red flag '{flag}' found for grant {grant.title}")
                score -= 0.4 # Significant penalty
                break
        
        # Could add LLM call here for nuanced ethical assessment if rules are not enough
        # e.g., prompt = f"Assess if the following grant text has ethical concerns for a company like Kevin Inc.: {text_to_search}"
        # ethical_assessment = await self.perplexity_client.ask(prompt, model="sonar-small-online")
        
        return self._normalize_score(score)

    async def _calculate_feasibility_context(self, grant: EnrichedGrant) -> float:
        logger.debug(f"Calculating feasibility context for {grant.title}")
        score = 1.0
        
        rules = self.compliance_rules.get('feasibility_context_rules', {})
        profile_ops = self.kevin_profile.get('operational_capacity', {})
        
        # 1. Match funding (Simplified: assumes grant.funding_amount is total and we need to find match % if specified)
        # This needs better grant data: e.g. grant.match_funding_required_percentage
        # For now, let's assume a hypothetical grant field `grant.match_percentage_required`
        # match_required_percentage = getattr(grant, 'match_percentage_required', 0) 
        # if match_required_percentage > 0:
        #    max_kevin_can_match_perc = rules.get('max_match_funding_percentage', 0)
        #    if match_required_percentage > max_kevin_can_match_perc:
        #        score -= 0.3
        #        logger.warning(f"Feasibility: Grant match funding {match_required_percentage}% > Kevin\\'s max {max_kevin_can_match_perc}% for {grant.title}") # Corrected grant.grant_name to grant.title

        # 2. Team commitment (Simplified)
        # Needs grant data: e.g. grant.required_fte_commitment
        # required_fte = getattr(grant, 'required_fte_commitment', 0)
        # min_team_commitment_fte_rule = rules.get('min_team_commitment_fte_if_specified', 1) # if grant specifies, Kevin must meet this
        # if required_fte > 0 and profile_ops.get('team_size_fte',0) < required_fte :
        #    score -= 0.25
        #    logger.warning(f"Feasibility: Grant requires {required_fte} FTE, Kevin has {profile_ops.get('team_size_fte',0)} for {grant.title}") # Corrected grant.grant_name to grant.title        
        # 3. Reporting frequency
        # Check if grant description mentions reporting requirements
        grant_reporting_freq = ""
        grant_text = f"{grant.title} {grant.description} {grant.eligibility_criteria or ''}"
        if "monthly" in grant_text.lower():
            grant_reporting_freq = "monthly"
        elif "quarterly" in grant_text.lower():
            grant_reporting_freq = "quarterly"
        elif "annual" in grant_text.lower(): # Corrected "annually" to "annual" for consistency
            grant_reporting_freq = "annual"
        acceptable_freqs = rules.get('acceptable_reporting_frequencies', ["quarterly", "annual"]) # Corrected "annually"
        
        found_acceptable_freq = False
        if not grant_reporting_freq: # If not specified, assume acceptable
            found_acceptable_freq = True
        else:
            for freq in acceptable_freqs:
                if freq in grant_reporting_freq:
                    found_acceptable_freq = True
                    break
        if not found_acceptable_freq and grant_reporting_freq: # Penalize if specified and not in our acceptable list
            # More nuanced: check if Kevin's capacity (e.g. "quarterly") can handle grant's (e.g. "monthly")
            kevin_reporting_capacity = profile_ops.get('reporting_capacity', "annual") # Corrected "annually"
            # This logic needs a hierarchy of frequencies (monthly > quarterly > annual)
            if "monthly" in grant_reporting_freq and kevin_reporting_capacity not in ["monthly"]:
                score -= 0.2
                logger.warning(f"Feasibility: Grant reporting is monthly, Kevin\\'s capacity is {kevin_reporting_capacity} for {grant.title}") # Corrected grant.grant_name to grant.title
            elif "quarterly" in grant_reporting_freq and kevin_reporting_capacity not in ["monthly", "quarterly"]:
                score -= 0.15
                logger.warning(f"Feasibility: Grant reporting is quarterly, Kevin\\'s capacity is {kevin_reporting_capacity} for {grant.title}") # Corrected grant.grant_name to grant.title


        # 4. Technical expertise
        # Needs grant data: e.g., grant.required_expertise (list of strings)
        # grant_req_expertise = getattr(grant.details, 'required_technical_expertise', [])
        # kevin_expertise = set(e.lower() for e in profile_ops.get('technical_expertise', []))
        # if grant_req_expertise:
        #    match_count = 0
        #    for req_exp in grant_req_expertise:
        #        if req_exp.lower() in kevin_expertise:
        #            match_count +=1
        #    if len(grant_req_expertise) > 0 :
        #        expertise_match_ratio = match_count / len(grant_req_expertise)
        #        if expertise_match_ratio < 0.5: # Less than 50% match
        #            score -= 0.3
        #            logger.warning(f"Feasibility: Low technical expertise match ({expertise_match_ratio*100:.0f}%) for {grant.title}") # Corrected grant.grant_name to grant.title
        #        elif expertise_match_ratio < 0.75: # Less than 75% match
        #            score -= 0.15        
        # Placeholder for LLM-based feasibility check on complex requirements
        # prompt = f"Assess Kevin Inc.\\'s feasibility for this grant based on their profile and grant requirements: {grant.description}. Kevin\\'s profile: {self.kevin_profile['operational_capacity']}"
        # feasibility_assessment = await self.perplexity_client.ask(prompt, model="sonar-small-online")
        # Parse assessment and adjust score

        return self._normalize_score(score)

    async def _calculate_strategic_synergy(self, grant: EnrichedGrant) -> float:
        logger.debug(f"Calculating strategic synergy for {grant.title}")
        score = 0.0 # Start low and build up for positive synergy
        text_to_search = f"{grant.title} {grant.description}".lower()

        rules = self.compliance_rules.get('strategic_synergy_rules', {})
        profile_strat = self.kevin_profile.get('strategic_goals', {})

        # 1. Alignment with Kevin's primary objectives and target sectors
        primary_objectives = profile_strat.get('primary_objectives', [])
        target_sectors = profile_strat.get('target_sectors', [])
        
        for objective in primary_objectives:
            if objective.lower() in text_to_search:
                score += 0.25
        
        for sector in target_sectors:
            # Check if grant's sector (if available) or keywords match Kevin's target sectors
            # grant_sector = getattr(grant.details, 'sector', "").lower()
            # if sector.lower() == grant_sector or sector.lower() in text_to_search:
            if sector.lower() in text_to_search: # Simplified for now
                score += 0.25
        
        # 2. Check for synergistic keywords
        synergistic_keywords = rules.get('synergistic_keywords', [])
        for keyword in synergistic_keywords:
            if keyword.lower() in text_to_search:
                score += 0.15 # Incremental boosts

        # 3. Penalize if grant focuses on misaligned areas
        misaligned_areas = rules.get('misaligned_focus_areas', [])
        for area in misaligned_areas:
            if area.lower() in text_to_search:
                score -= 0.3 # Penalty
                logger.warning(f"Strategic Synergy: Grant aligns with a misaligned focus area '{area}' for {grant.title}")
        
        # LLM for nuanced strategic fit:
        # prompt = f"Does this grant: '{grant.purpose}' strategically align with a company focused on {profile_strat.get('long_term_vision','')} and objectives like {primary_objectives}? Explain."
        # strategic_fit_assessment = await self.perplexity_client.ask(prompt, model="sonar-small-online")
        # Parse and adjust score        return self._normalize_score(score)

    def _calculate_final_weighted_score(self, grant: EnrichedGrant) -> float:
        # Implementation for Task 3.7
        # This will use the weights from self.compliance_rules['scoring_weights']
        if grant.compliance_scores is None:
            logger.warning(f"Compliance scores not calculated for {grant.title}. Cannot compute final weighted score.") # Corrected grant.grant_name to grant.title
            return 0.0

        # Ensure scores are not None, default to 0.0 if they are
        business_logic_score = grant.compliance_scores.business_logic_alignment if grant.compliance_scores.business_logic_alignment is not None else 0.0
        feasibility_score = grant.compliance_scores.feasibility_score if grant.compliance_scores.feasibility_score is not None else 0.0
        strategic_synergy_score = grant.compliance_scores.strategic_synergy if grant.compliance_scores.strategic_synergy is not None else 0.0
        final_score = (
            (business_logic_score * self.business_logic_weight) +
            (feasibility_score * self.feasibility_context_weight) +
            (strategic_synergy_score * self.strategic_synergy_weight)
        )
        logger.info(f"Calculated final weighted score for {grant.title}: {final_score:.4f}") # Corrected grant.grant_name to grant.title
        return round(final_score, 4)
