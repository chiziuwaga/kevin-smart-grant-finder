/**
 * DeepSeek API Client
 * Replaces Perplexity API with 95% cost savings
 *
 * Pricing:
 * - deepseek-chat: $0.14/M input tokens, $0.28/M output tokens
 * - deepseek-reasoner: $0.55/M input tokens, $2.19/M output tokens
 */

import { APIUsageLog } from '@/lib/services/cost-tracker';

export interface DeepSeekMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface DeepSeekResponse {
  id: string;
  model: string;
  choices: {
    index: number;
    message: {
      role: string;
      content: string;
    };
    finish_reason: string;
  }[];
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface GrantData {
  title: string;
  description: string;
  deadline?: string;
  funding_amount?: number;
  eligibility_criteria?: string;
  category?: string;
  source_url?: string;
  source_name?: string;
  score?: number;
}

export interface DeepSeekSearchResult {
  grants: GrantData[];
  cost: number;
  tokensUsed: number;
}

export class DeepSeekClient {
  private apiKey: string;
  private baseUrl: string;
  private model: string;

  // Cost per million tokens
  private static readonly COSTS = {
    'deepseek-chat': {
      input: 0.14,
      output: 0.28,
    },
    'deepseek-reasoner': {
      input: 0.55,
      output: 2.19,
    },
  };

  constructor(
    apiKey?: string,
    model: 'deepseek-chat' | 'deepseek-reasoner' = 'deepseek-chat'
  ) {
    this.apiKey = apiKey || process.env.DEEPSEEK_API_KEY || '';
    this.baseUrl = process.env.DEEPSEEK_BASE_URL || 'https://api.deepseek.com';
    this.model = model;

    if (!this.apiKey) {
      throw new Error('DeepSeek API key not found');
    }
  }

  /**
   * Calculate cost based on token usage
   */
  private calculateCost(
    inputTokens: number,
    outputTokens: number,
    model: string
  ): number {
    const costs = DeepSeekClient.COSTS[model as keyof typeof DeepSeekClient.COSTS];
    if (!costs) throw new Error(`Unknown model: ${model}`);

    const inputCost = (inputTokens / 1_000_000) * costs.input;
    const outputCost = (outputTokens / 1_000_000) * costs.output;

    return inputCost + outputCost;
  }

  /**
   * Search for grants using DeepSeek
   */
  async searchGrants(query: string, userId?: string): Promise<DeepSeekSearchResult> {
    const systemPrompt = `You are a grant discovery assistant. Search for grant opportunities based on the user's query.

For each grant found, extract:
- title (required): Clear, concise grant name
- description (required): Detailed description of the grant
- deadline (optional): Format as YYYY-MM-DD
- funding_amount (optional): Numeric value (no currency symbols)
- eligibility_criteria (optional): Who can apply
- category (optional): Grant type (research, education, nonprofit, etc.)
- source_url (required): Valid URL to the grant
- source_name (required): Name of the granting organization

Return ONLY valid JSON in this exact format:
{
  "grants": [
    {
      "title": "Grant Name",
      "description": "Detailed description...",
      "deadline": "2025-06-30",
      "funding_amount": 50000,
      "eligibility_criteria": "Nonprofits in NYC",
      "category": "nonprofit",
      "source_url": "https://example.com/grant",
      "source_name": "Example Foundation"
    }
  ]
}

If no grants found, return: {"grants": []}`;

    const messages: DeepSeekMessage[] = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: query },
    ];

    const startTime = Date.now();

    try {
      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: this.model,
          messages,
          temperature: 0.7,
          max_tokens: 4000,
          response_format: { type: 'json_object' },
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`DeepSeek API error: ${response.status} - ${error}`);
      }

      const data: DeepSeekResponse = await response.json();
      const duration = Date.now() - startTime;

      // Calculate cost
      const cost = this.calculateCost(
        data.usage.prompt_tokens,
        data.usage.completion_tokens,
        this.model
      );

      // Log API usage
      await APIUsageLog.log({
        userId,
        service: 'DEEPSEEK',
        operation: 'search_grants',
        tokensUsed: data.usage.total_tokens,
        costUSD: cost,
        duration,
        success: true,
        requestData: { query, model: this.model },
        responseData: { grantsFound: 0 }, // Will update after parsing
      });

      // Parse response
      const content = data.choices[0]?.message?.content || '{"grants": []}';
      let parsedData: { grants: GrantData[] };

      try {
        parsedData = JSON.parse(content);
      } catch (parseError) {
        console.error('Failed to parse DeepSeek response:', content);
        parsedData = { grants: [] };
      }

      return {
        grants: parsedData.grants || [],
        cost,
        tokensUsed: data.usage.total_tokens,
      };
    } catch (error) {
      const duration = Date.now() - startTime;

      // Log error
      await APIUsageLog.log({
        userId,
        service: 'DEEPSEEK',
        operation: 'search_grants',
        tokensUsed: 0,
        costUSD: 0,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * Extract grant data from raw text using DeepSeek
   */
  async extractGrantData(
    rawText: string,
    userId?: string
  ): Promise<DeepSeekSearchResult> {
    const systemPrompt = `Extract grant opportunities from the provided text. Parse all available grant information.

For each grant, extract:
- title (required)
- description (required)
- deadline (YYYY-MM-DD format if available)
- funding_amount (numeric only)
- eligibility_criteria
- category
- source_url (if mentioned)
- source_name

Return ONLY valid JSON: {"grants": [...]}`;

    const messages: DeepSeekMessage[] = [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: rawText },
    ];

    const startTime = Date.now();

    try {
      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: this.model,
          messages,
          temperature: 0.3, // Lower temperature for extraction
          max_tokens: 4000,
          response_format: { type: 'json_object' },
        }),
      });

      if (!response.ok) {
        throw new Error(`DeepSeek API error: ${response.status}`);
      }

      const data: DeepSeekResponse = await response.json();
      const duration = Date.now() - startTime;
      const cost = this.calculateCost(
        data.usage.prompt_tokens,
        data.usage.completion_tokens,
        this.model
      );

      await APIUsageLog.log({
        userId,
        service: 'DEEPSEEK',
        operation: 'extract_grants',
        tokensUsed: data.usage.total_tokens,
        costUSD: cost,
        duration,
        success: true,
      });

      const content = data.choices[0]?.message?.content || '{"grants": []}';
      const parsedData: { grants: GrantData[] } = JSON.parse(content);

      return {
        grants: parsedData.grants || [],
        cost,
        tokensUsed: data.usage.total_tokens,
      };
    } catch (error) {
      await APIUsageLog.log({
        userId,
        service: 'DEEPSEEK',
        operation: 'extract_grants',
        tokensUsed: 0,
        costUSD: 0,
        duration: Date.now() - startTime,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * General chat completion
   */
  async chat(
    messages: DeepSeekMessage[],
    userId?: string,
    options?: {
      temperature?: number;
      maxTokens?: number;
    }
  ): Promise<{ response: string; cost: number; tokensUsed: number }> {
    const startTime = Date.now();

    try {
      const response = await fetch(`${this.baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: this.model,
          messages,
          temperature: options?.temperature ?? 0.7,
          max_tokens: options?.maxTokens ?? 2000,
        }),
      });

      if (!response.ok) {
        throw new Error(`DeepSeek API error: ${response.status}`);
      }

      const data: DeepSeekResponse = await response.json();
      const duration = Date.now() - startTime;
      const cost = this.calculateCost(
        data.usage.prompt_tokens,
        data.usage.completion_tokens,
        this.model
      );

      await APIUsageLog.log({
        userId,
        service: 'DEEPSEEK',
        operation: 'chat',
        tokensUsed: data.usage.total_tokens,
        costUSD: cost,
        duration,
        success: true,
      });

      return {
        response: data.choices[0]?.message?.content || '',
        cost,
        tokensUsed: data.usage.total_tokens,
      };
    } catch (error) {
      await APIUsageLog.log({
        userId,
        service: 'DEEPSEEK',
        operation: 'chat',
        tokensUsed: 0,
        costUSD: 0,
        duration: Date.now() - startTime,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }
}

export default DeepSeekClient;
