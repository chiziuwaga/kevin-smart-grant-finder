"""
DeepSeek AI client for grant analysis, research, and application generation.
Replaces Perplexity and serves as primary AI provider.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from datetime import datetime

from config.settings import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class DeepSeekClient:
    """
    Client for interacting with DeepSeek API for:
    - Grant research and analysis
    - Compliance checking
    - Application generation using RAG
    - Embeddings generation
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepSeek client.

        Args:
            api_key: Optional API key (defaults to settings)
        """
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.api_base = settings.DEEPSEEK_API_BASE
        self.chat_endpoint = f"{self.api_base}/v1/chat/completions"
        self.embeddings_endpoint = f"{self.api_base}/v1/embeddings"

        if not self.api_key:
            logger.warning("DeepSeek API key not configured")

        self.default_model = "deepseek-chat"  # Main reasoning model
        self.embedding_model = "deepseek-embeddings-v1"  # For embeddings

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat completion request to DeepSeek.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to deepseek-chat)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional API parameters

        Returns:
            API response dict with generated text

        Raises:
            Exception: If API call fails
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.chat_endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.info(f"DeepSeek chat completion: {result.get('usage', {})}")

                return result

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"DeepSeek API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"DeepSeek client error: {str(e)}")
            raise

    async def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion response from DeepSeek.

        Args:
            messages: List of message dicts
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            **kwargs: Additional parameters

        Yields:
            Content chunks as they arrive
        """
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", self.chat_endpoint, json=payload, headers=headers) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data == "[DONE]":
                                break

                            try:
                                import json
                                chunk = json.loads(data)
                                if "choices" in chunk and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"DeepSeek streaming error: {str(e)}")
            raise

    async def analyze_grant(
        self,
        grant_data: Dict[str, Any],
        business_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a grant for relevance and compliance using DeepSeek.

        Args:
            grant_data: Dict containing grant information
            business_context: Optional business profile context

        Returns:
            Analysis results with scores and recommendations
        """
        system_prompt = """You are an expert grant analyst. Analyze the provided grant opportunity
        and determine its relevance, eligibility, and strategic fit. Provide structured analysis."""

        user_message = f"""
        Analyze this grant opportunity:

        Title: {grant_data.get('title', 'N/A')}
        Description: {grant_data.get('description', 'N/A')}
        Funding Amount: {grant_data.get('funding_amount', 'N/A')}
        Deadline: {grant_data.get('deadline', 'N/A')}
        Eligibility: {grant_data.get('eligibility_summary_llm', 'N/A')}
        """

        if business_context:
            user_message += f"\n\nBusiness Context:\n{business_context}"

        user_message += """

        Provide analysis in the following format:
        1. Relevance Score (0-100): How relevant is this grant?
        2. Eligibility Assessment: Does the applicant meet requirements?
        3. Strategic Fit: How well does this align with business goals?
        4. Key Strengths: What makes this a good opportunity?
        5. Potential Challenges: What obstacles might exist?
        6. Recommendation: Should they apply? (Yes/No/Maybe)
        7. Priority Level: (High/Medium/Low)
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat_completion(messages, temperature=0.3, max_tokens=2000)

            content = response["choices"][0]["message"]["content"]

            # Parse response (basic parsing, can be enhanced)
            analysis = {
                "analysis_text": content,
                "analyzed_at": datetime.utcnow().isoformat(),
                "model_used": response.get("model", self.default_model),
                "tokens_used": response.get("usage", {}).get("total_tokens", 0)
            }

            # Try to extract structured data (simple regex parsing)
            import re

            score_match = re.search(r'Relevance Score.*?(\d+)', content, re.IGNORECASE)
            if score_match:
                analysis["relevance_score"] = int(score_match.group(1)) / 100.0

            priority_match = re.search(r'Priority Level.*?(High|Medium|Low)', content, re.IGNORECASE)
            if priority_match:
                analysis["priority_level"] = priority_match.group(1).lower()

            recommendation_match = re.search(r'Recommendation.*?(Yes|No|Maybe)', content, re.IGNORECASE)
            if recommendation_match:
                analysis["recommendation"] = recommendation_match.group(1).lower()

            return analysis

        except Exception as e:
            logger.error(f"Grant analysis failed: {str(e)}")
            return {
                "error": str(e),
                "analysis_text": "Analysis failed",
                "relevance_score": 0.5  # Default neutral score
            }

    async def generate_embeddings(
        self,
        texts: List[str],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for texts using DeepSeek.

        Args:
            texts: List of text strings to embed
            model: Model to use (defaults to embedding model)

        Returns:
            List of embedding vectors
        """
        model = model or self.embedding_model

        payload = {
            "model": model,
            "input": texts
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.embeddings_endpoint,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                embeddings = [item["embedding"] for item in result["data"]]

                logger.info(f"Generated {len(embeddings)} embeddings")
                return embeddings

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek embeddings error: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Embeddings generation failed: {str(e)}")
            raise

    async def search_with_reasoning(
        self,
        query: str,
        context: Optional[str] = None,
        search_depth: str = "standard"
    ) -> Dict[str, Any]:
        """
        Perform reasoning-based search for grants using DeepSeek's advanced reasoning.
        Implements "thermodynamic prompting" - structured reasoning with exploration.

        Args:
            query: Search query
            context: Optional business context
            search_depth: "quick", "standard", or "deep"

        Returns:
            Structured search results with reasoning
        """
        # Thermodynamic prompting: Guide the model through structured exploration
        system_prompt = """You are an expert grant researcher with deep knowledge of funding opportunities.
        Use structured reasoning to explore the search space comprehensively.

        Think step-by-step:
        1. Decompose the query into key search dimensions
        2. Explore each dimension thoroughly (thermodynamic exploration)
        3. Synthesize findings into actionable insights
        4. Rank opportunities by relevance and feasibility
        """

        temp_settings = {
            "quick": (0.3, 1000),
            "standard": (0.7, 2000),
            "deep": (0.9, 4000)
        }

        temperature, max_tokens = temp_settings.get(search_depth, temp_settings["standard"])

        user_message = f"""
        Search Query: {query}
        """

        if context:
            user_message += f"\nBusiness Context: {context}"

        user_message += """

        Provide:
        1. Search strategy decomposition
        2. Key grant sources to explore
        3. Specific search terms and filters
        4. Expected grant types and categories
        5. Priority ordering of search actions
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat_completion(
                messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

            content = response["choices"][0]["message"]["content"]

            return {
                "reasoning": content,
                "search_depth": search_depth,
                "model_used": response.get("model"),
                "tokens_used": response.get("usage", {}).get("total_tokens", 0),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Reasoning search failed: {str(e)}")
            raise

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost in cents for DeepSeek API call.

        Pricing: $0.14/M input, $0.28/M output

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in cents
        """
        input_cost = (input_tokens / 1_000_000) * 0.14 * 100  # cents
        output_cost = (output_tokens / 1_000_000) * 0.28 * 100  # cents
        return input_cost + output_cost


# Singleton instance
_deepseek_client = None


def get_deepseek_client() -> DeepSeekClient:
    """Get or create DeepSeek client singleton."""
    global _deepseek_client
    if _deepseek_client is None:
        _deepseek_client = DeepSeekClient()
    return _deepseek_client
