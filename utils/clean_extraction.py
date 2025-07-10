"""
Simple and clean grant extraction function to replace the problematic one
"""

import httpx
import json
import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)

async def extract_grant_data_clean(raw_perplexity_content: Optional[str], openai_api_key: str) -> List[Dict[str, Any]]:
    """Clean extraction function using GPT-4-turbo with temperature 0.9 and chunking."""
    if not raw_perplexity_content:
        logger.info("No content from Perplexity to extract grants from.")
        return []
    
    # Simple chunking - split into manageable pieces
    max_chunk_size = 8000
    chunks = []
    if len(raw_perplexity_content) <= max_chunk_size:
        chunks = [raw_perplexity_content]
    else:
        # Split by double newlines (paragraphs)
        paragraphs = raw_perplexity_content.split('\n\n')
        current_chunk = ""
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) + 2 > max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += ("\n\n" if current_chunk else "") + paragraph
        if current_chunk:
            chunks.append(current_chunk.strip())
    
    all_grants = []
    
    for chunk_idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {chunk_idx + 1}/{len(chunks)} for grant extraction")
        
        payload = {
            "model": "gpt-4-turbo",
            "temperature": 0.9,
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a grant data extraction assistant. Extract all grant opportunities from the text. "
                        "Use creative reasoning and flexibility to identify grants even when information is incomplete.\n\n"
                        "**CRITICAL: Only extract grants that have a valid, direct application URL. If no URL is provided, do not include the grant.**\n\n"
                        "Return a JSON object with this exact format:\n"
                        '{"grants": [{"title": "Grant Title", "description": "Grant description", "funding_amount": 50000, "deadline": "2024-12-31", "source_url": "https://example.com", "eligibility_criteria": "Requirements", "category": "nonprofit"}]}\n\n'
                        "Rules:\n"
                        "- title: Required string, clear title\n"
                        "- description: Required string, detailed description\n"
                        "- funding_amount: Number (max of range if range given), null if unclear\n"
                        "- deadline: YYYY-MM-DD format, null if unclear\n"
                        "- source_url: **MANDATORY** Complete URL starting with http/https. Skip grants without URLs.\n"
                        "- eligibility_criteria: String describing who can apply\n"
                        "- category: String like 'telecommunications', 'nonprofit', 'infrastructure'\n"
                        "**IMPORTANT: Only include grants that have a direct application or information URL. No URL = skip the grant.**"
                    )
                },
                {
                    "role": "user",
                    "content": f"Extract grants from this content (chunk {chunk_idx + 1} of {len(chunks)}):\n\n{chunk}"
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("choices") and len(data["choices"]) > 0:
                        content_str = data["choices"][0]["message"]["content"]
                        try:
                            extracted_data = json.loads(content_str)
                            if "grants" in extracted_data and isinstance(extracted_data["grants"], list):
                                chunk_grants = extracted_data["grants"]
                                all_grants.extend(chunk_grants)
                                logger.info(f"Extracted {len(chunk_grants)} grants from chunk {chunk_idx + 1}")
                            else:
                                logger.warning(f"No grants array in chunk {chunk_idx + 1} response")
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse JSON from chunk {chunk_idx + 1}: {e}")
                else:
                    logger.error(f"OpenAI API error for chunk {chunk_idx + 1}: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Error processing chunk {chunk_idx + 1}: {e}")
    
    logger.info(f"Total grants extracted: {len(all_grants)}")
    return all_grants

def extract_grants_with_basic_regex(content: Optional[str]) -> List[Dict[str, Any]]:
    """Basic regex fallback for grant extraction."""
    if not content:
        return []
    
    logger.warning("Using basic regex fallback for grant extraction.")
    grants = []
    
    try:
        # Split content into potential grant blocks
        grant_blocks = re.split(r'\n\s*(?:\d+\.|\*|-)\s+|\n---\n', content)
        if len(grant_blocks) <= 1:
            grant_blocks = content.split("\n\n")
        
        for block_text in grant_blocks:
            if len(block_text.strip()) < 75:
                continue
            
            # Extract title
            title_match = re.search(r"^(?:Title|Grant Name|Opportunity):\s*(.+?)(?:\n|$)", block_text, re.IGNORECASE | re.MULTILINE)
            if not title_match:
                first_line = block_text.strip().split('\n')[0]
                if len(first_line) < 150 and len(first_line) > 5:
                    title = first_line
                else:
                    continue
            else:
                title = title_match.group(1).strip()
            
            # Extract other fields
            description = block_text
            deadline_match = re.search(r"Deadline(?:s)?:\s*([^\n]+)", block_text, re.IGNORECASE)
            amount_match = re.search(r"(?:Funding Amount|Amount):\s*([^\n]+)", block_text, re.IGNORECASE)
            url_match = re.search(r"(?:URL|Link|Website|Source URL):\s*(https?://[^\s]+)", block_text, re.IGNORECASE)
            
            grant = {
                "title": title,
                "description": description[:500],  # Limit description length
                "funding_amount": None,
                "deadline": None,
                "source_url": url_match.group(1) if url_match else None,
                "eligibility_criteria": None,
                "category": "general"
            }
            
            # Process funding amount
            if amount_match:
                amount_str = amount_match.group(1)
                amount_nums = re.findall(r'[\d,]+', amount_str)
                if amount_nums:
                    try:
                        grant["funding_amount"] = float(amount_nums[-1].replace(',', ''))
                    except ValueError:
                        pass
            
            grants.append(grant)
    
    except Exception as e:
        logger.error(f"Error in regex fallback: {e}")
    
    return grants
