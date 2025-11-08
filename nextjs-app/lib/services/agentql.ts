/**
 * AgentQL Client
 * Web scraping with virtual desktop for JavaScript-heavy grant portals
 *
 * Features:
 * - Virtual browser automation
 * - JavaScript execution
 * - Screenshot capabilities
 * - Form filling for authenticated sources
 */

import { APIUsageLog } from '@/lib/services/cost-tracker';

export interface AgentQLConfig {
  apiKey: string;
  timeout?: number;
  headless?: boolean;
}

export interface ScrapeOptions {
  url: string;
  waitForSelector?: string;
  screenshot?: boolean;
  scrollToBottom?: boolean;
  executeScript?: string;
}

export interface ScrapeResult {
  html: string;
  text: string;
  screenshot?: string; // Base64 encoded
  metadata: {
    title?: string;
    description?: string;
    url: string;
    scrapedAt: string;
  };
}

export interface GrantScrapeResult {
  grants: any[];
  cost: number;
  screenshotUrl?: string;
}

export class AgentQLClient {
  private apiKey: string;
  private baseUrl = 'https://api.agentql.com/v1';
  private timeout: number;

  // AgentQL pricing (estimate based on typical SaaS pricing)
  // Actual pricing may vary - check AgentQL documentation
  private static readonly COST_PER_SCRAPE = 0.01; // $0.01 per page scrape
  private static readonly COST_PER_SCREENSHOT = 0.005; // $0.005 per screenshot

  constructor(config?: AgentQLConfig) {
    this.apiKey = config?.apiKey || process.env.AGENTQL_API_KEY || '';
    this.timeout = config?.timeout || 30000;

    if (!this.apiKey) {
      throw new Error('AgentQL API key not found');
    }
  }

  /**
   * Scrape a single URL
   */
  async scrape(
    options: ScrapeOptions,
    userId?: string
  ): Promise<ScrapeResult> {
    const startTime = Date.now();
    let cost = AgentQLClient.COST_PER_SCRAPE;

    if (options.screenshot) {
      cost += AgentQLClient.COST_PER_SCREENSHOT;
    }

    try {
      const response = await fetch(`${this.baseUrl}/scrape`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          url: options.url,
          wait_for_selector: options.waitForSelector,
          screenshot: options.screenshot,
          scroll_to_bottom: options.scrollToBottom,
          execute_script: options.executeScript,
          timeout: this.timeout,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`AgentQL API error: ${response.status} - ${error}`);
      }

      const data = await response.json();
      const duration = Date.now() - startTime;

      // Log usage
      await APIUsageLog.log({
        userId,
        service: 'AGENTQL',
        operation: 'scrape',
        costUSD: cost,
        duration,
        success: true,
        requestData: { url: options.url },
        responseData: { screenshotTaken: !!options.screenshot },
      });

      return {
        html: data.html || '',
        text: data.text || '',
        screenshot: data.screenshot,
        metadata: {
          title: data.title,
          description: data.description,
          url: options.url,
          scrapedAt: new Date().toISOString(),
        },
      };
    } catch (error) {
      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'AGENTQL',
        operation: 'scrape',
        costUSD: 0,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * Scrape grants.gov
   */
  async scrapeGrantsGov(
    searchQuery: string,
    userId?: string
  ): Promise<GrantScrapeResult> {
    const url = `https://www.grants.gov/search-results-detail.html?keywords=${encodeURIComponent(searchQuery)}`;

    try {
      const result = await this.scrape(
        {
          url,
          waitForSelector: '.search-results',
          scrollToBottom: true,
          screenshot: true,
        },
        userId
      );

      // Parse grants from HTML
      const grants = this.parseGrantsGovHTML(result.html);

      return {
        grants,
        cost: AgentQLClient.COST_PER_SCRAPE + AgentQLClient.COST_PER_SCREENSHOT,
        screenshotUrl: result.screenshot,
      };
    } catch (error) {
      console.error('Failed to scrape grants.gov:', error);
      return {
        grants: [],
        cost: 0,
      };
    }
  }

  /**
   * Parse grants.gov HTML to extract grant data
   */
  private parseGrantsGovHTML(html: string): any[] {
    // This is a simplified parser
    // In production, use a proper HTML parser like cheerio
    const grants: any[] = [];

    // Example regex patterns for grants.gov
    // These would need to be adjusted based on actual HTML structure
    const titlePattern = /<h3[^>]*>([^<]+)<\/h3>/g;
    const titles = [...html.matchAll(titlePattern)].map((m) => m[1].trim());

    for (const title of titles) {
      grants.push({
        title,
        source_name: 'Grants.gov',
        source_url: 'https://www.grants.gov',
        category: 'federal',
      });
    }

    return grants;
  }

  /**
   * Scrape foundation website
   */
  async scrapeFoundationSite(
    url: string,
    userId?: string
  ): Promise<GrantScrapeResult> {
    try {
      const result = await this.scrape(
        {
          url,
          waitForSelector: 'body',
          scrollToBottom: true,
          screenshot: true,
        },
        userId
      );

      // Extract grant information from the page
      const grants = this.parseFoundationHTML(result.html, url);

      return {
        grants,
        cost: AgentQLClient.COST_PER_SCRAPE + AgentQLClient.COST_PER_SCREENSHOT,
        screenshotUrl: result.screenshot,
      };
    } catch (error) {
      console.error(`Failed to scrape ${url}:`, error);
      return {
        grants: [],
        cost: 0,
      };
    }
  }

  /**
   * Parse foundation website HTML
   */
  private parseFoundationHTML(html: string, sourceUrl: string): any[] {
    // Simplified parser - in production use DeepSeek to intelligently extract
    const grants: any[] = [];

    // Look for grant-related keywords
    const grantPattern = /grant[s]?\s+(?:program|opportunity|available)/gi;
    const matches = html.match(grantPattern);

    if (matches && matches.length > 0) {
      // Found potential grants - would need more sophisticated parsing
      grants.push({
        title: 'Grant opportunity found (needs detailed parsing)',
        source_url: sourceUrl,
        description: 'Use DeepSeek to extract detailed information',
      });
    }

    return grants;
  }

  /**
   * Scrape multiple URLs in parallel
   */
  async scrapeMultiple(
    urls: string[],
    userId?: string
  ): Promise<ScrapeResult[]> {
    const promises = urls.map((url) =>
      this.scrape({ url, scrollToBottom: true }, userId)
    );

    try {
      const results = await Promise.allSettled(promises);

      return results
        .filter((r) => r.status === 'fulfilled')
        .map((r: any) => r.value);
    } catch (error) {
      console.error('Failed to scrape multiple URLs:', error);
      return [];
    }
  }

  /**
   * Execute custom query on a page
   */
  async query(
    url: string,
    query: string,
    userId?: string
  ): Promise<any> {
    const startTime = Date.now();
    const cost = AgentQLClient.COST_PER_SCRAPE;

    try {
      const response = await fetch(`${this.baseUrl}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          url,
          query, // Natural language query
          timeout: this.timeout,
        }),
      });

      if (!response.ok) {
        throw new Error(`AgentQL API error: ${response.status}`);
      }

      const data = await response.json();
      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'AGENTQL',
        operation: 'query',
        costUSD: cost,
        duration,
        success: true,
      });

      return data.result;
    } catch (error) {
      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'AGENTQL',
        operation: 'query',
        costUSD: 0,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }
}

export default AgentQLClient;
