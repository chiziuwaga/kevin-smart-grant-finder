/**
 * Resend Email Service
 * Transactional emails for whitelisting, payments, notifications
 */

import { Resend } from 'resend';
import { APIUsageLog } from './cost-tracker';

const resend = new Resend(process.env.RESEND_API_KEY);

const FROM_EMAIL =
  process.env.RESEND_FROM_EMAIL || 'Smart Grant Finder <noreply@yourdomain.com>';

export interface EmailOptions {
  to: string | string[];
  subject: string;
  html: string;
  text?: string;
}

export class ResendService {
  /**
   * Send generic email
   */
  static async sendEmail(options: EmailOptions, userId?: string): Promise<void> {
    const startTime = Date.now();

    try {
      await resend.emails.send({
        from: FROM_EMAIL,
        to: Array.isArray(options.to) ? options.to : [options.to],
        subject: options.subject,
        html: options.html,
        text: options.text,
      });

      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'RESEND',
        operation: 'send_email',
        costUSD: 0.0001, // Approximate cost per email
        duration,
        success: true,
        requestData: { subject: options.subject, to: options.to },
      });
    } catch (error) {
      const duration = Date.now() - startTime;

      await APIUsageLog.log({
        userId,
        service: 'RESEND',
        operation: 'send_email',
        costUSD: 0,
        duration,
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      });

      throw error;
    }
  }

  /**
   * Send whitelist approval email with payment link
   */
  static async sendWhitelistApprovalEmail(
    userEmail: string,
    userName: string,
    paymentLink: string
  ): Promise<void> {
    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #1976d2 0%, #4caf50 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
            .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
            .button { display: inline-block; background: #1976d2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
            .footer { text-align: center; margin-top: 30px; color: #666; font-size: 12px; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>🎉 Welcome to Smart Grant Finder!</h1>
            </div>
            <div class="content">
              <p>Hi ${userName},</p>

              <p>Great news! Your account has been approved and you're ready to start finding grants.</p>

              <p><strong>Next steps:</strong></p>
              <ol>
                <li>Complete your payment to activate your account</li>
                <li>Upload your documents and complete onboarding</li>
                <li>Start finding grants with AI-powered search</li>
              </ol>

              <p><strong>Pricing:</strong></p>
              <ul>
                <li>Tier 1: $10 for 10 credits</li>
                <li>Tier 2: $20 for 22 credits (11% bonus! 🎁)</li>
                <li>Top-ups: Minimum $5</li>
              </ul>

              <a href="${paymentLink}" class="button">Complete Payment & Get Started</a>

              <p>Once payment is complete, you'll have access to:</p>
              <ul>
                <li>✨ AI-powered grant discovery</li>
                <li>🔍 Smart filtering and matching</li>
                <li>📅 Deadline tracking and reminders</li>
                <li>📝 One-click application assistance</li>
                <li>⏰ Automated grant searches (up to 2x daily)</li>
              </ul>

              <p>Questions? Just reply to this email - we're here to help!</p>

              <p>Best regards,<br>The Smart Grant Finder Team</p>
            </div>
            <div class="footer">
              <p>Smart Grant Finder | AI-Powered Grant Discovery</p>
            </div>
          </div>
        </body>
      </html>
    `;

    const text = `
Hi ${userName},

Great news! Your account has been approved and you're ready to start finding grants.

Next steps:
1. Complete your payment to activate your account
2. Upload your documents and complete onboarding
3. Start finding grants with AI-powered search

Pricing:
- Tier 1: $10 for 10 credits
- Tier 2: $20 for 22 credits (11% bonus!)
- Top-ups: Minimum $5

Complete payment here: ${paymentLink}

Questions? Just reply to this email - we're here to help!

Best regards,
The Smart Grant Finder Team
    `;

    await this.sendEmail({
      to: userEmail,
      subject: '🎉 Your Smart Grant Finder Account is Approved!',
      html,
      text,
    });
  }

  /**
   * Send low credit warning email
   */
  static async sendLowCreditWarning(
    userEmail: string,
    userName: string,
    currentBalance: number,
    topUpLink: string
  ): Promise<void> {
    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: #ff9800; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
            .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
            .balance { font-size: 32px; font-weight: bold; color: #ff9800; text-align: center; margin: 20px 0; }
            .button { display: inline-block; background: #1976d2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>⚠️ Low Credit Balance</h1>
            </div>
            <div class="content">
              <p>Hi ${userName},</p>

              <p>Your Smart Grant Finder credit balance is running low:</p>

              <div class="balance">$${currentBalance.toFixed(2)}</div>

              <p>To continue using automated grant searches and AI-powered features, please top up your credits.</p>

              <a href="${topUpLink}" class="button">Top Up Credits</a>

              <p><strong>Reminder:</strong></p>
              <ul>
                <li>Tier 1: $10 for 10 credits</li>
                <li>Tier 2: $20 for 22 credits (11% bonus!)</li>
                <li>Minimum top-up: $5</li>
              </ul>

              <p>Best regards,<br>The Smart Grant Finder Team</p>
            </div>
          </div>
        </body>
      </html>
    `;

    await this.sendEmail({
      to: userEmail,
      subject: '⚠️ Your Smart Grant Finder Credits are Running Low',
      html,
    });
  }

  /**
   * Send grant search results email
   */
  static async sendGrantSearchResults(
    userEmail: string,
    userName: string,
    grantsFound: number,
    highPriority: number,
    dashboardLink: string
  ): Promise<void> {
    const html = `
      <!DOCTYPE html>
      <html>
        <head>
          <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .container { max-width: 600px; margin: 0 auto; padding: 20px; }
            .header { background: linear-gradient(135deg, #1976d2 0%, #4caf50 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
            .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
            .stats { display: flex; justify-content: space-around; margin: 20px 0; }
            .stat { text-align: center; }
            .stat-number { font-size: 36px; font-weight: bold; color: #1976d2; }
            .stat-label { color: #666; font-size: 14px; }
            .button { display: inline-block; background: #1976d2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>✨ New Grants Found!</h1>
            </div>
            <div class="content">
              <p>Hi ${userName},</p>

              <p>Your automated grant search has completed. Here's what we found:</p>

              <div class="stats">
                <div class="stat">
                  <div class="stat-number">${grantsFound}</div>
                  <div class="stat-label">Total Grants</div>
                </div>
                <div class="stat">
                  <div class="stat-number">${highPriority}</div>
                  <div class="stat-label">High Priority</div>
                </div>
              </div>

              <a href="${dashboardLink}" class="button">View Grants</a>

              <p>Don't miss out on these opportunities - review and apply soon!</p>

              <p>Best regards,<br>The Smart Grant Finder Team</p>
            </div>
          </div>
        </body>
      </html>
    `;

    await this.sendEmail({
      to: userEmail,
      subject: `✨ ${grantsFound} New Grants Found for You!`,
      html,
    });
  }
}

export default ResendService;
