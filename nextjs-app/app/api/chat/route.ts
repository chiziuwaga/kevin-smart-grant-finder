/**
 * Chat API Route - Vercel AI SDK with DeepSeek
 * Main chat interface for grant finder
 */

import { deepseek } from '@/lib/ai/deepseek-provider';
import { streamText } from 'ai';
import { auth } from '@/auth';
import { prisma } from '@/lib/prisma';
import { CreditManager } from '@/lib/services/credit-manager';
import { GrantSearchOrchestrator } from '@/lib/services/grant-search-orchestrator';
import { NextResponse } from 'next/server';

export const runtime = 'edge';

const MAX_MESSAGES_PER_THREAD = 50;
const MAX_THREADS_PER_USER = 10;

export async function POST(req: Request) {
  try {
    const session = await auth();

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { messages, chatId } = await req.json();

    // Check credit balance
    const canUse = await CreditManager.canUseService(session.user.id);
    if (!canUse.allowed) {
      return NextResponse.json(
        { error: canUse.reason },
        { status: 402 } // Payment Required
      );
    }

    // Get or create chat history
    let chat = chatId
      ? await prisma.chatHistory.findFirst({
          where: { id: chatId, userId: session.user.id },
        })
      : null;

    if (!chat) {
      // Check thread limit
      const activeThreads = await prisma.chatHistory.count({
        where: { userId: session.user.id, isActive: true },
      });

      if (activeThreads >= MAX_THREADS_PER_USER) {
        return NextResponse.json(
          { error: `Maximum ${MAX_THREADS_PER_USER} active threads reached` },
          { status: 429 }
        );
      }

      chat = await prisma.chatHistory.create({
        data: {
          userId: session.user.id,
          title: 'New Chat',
          messages: [],
          messageCount: 0,
        },
      });
    }

    // Check message limit
    if (chat.messageCount >= MAX_MESSAGES_PER_THREAD) {
      return NextResponse.json(
        {
          error: `This thread has reached the maximum of ${MAX_MESSAGES_PER_THREAD} messages. Please start a new chat.`,
        },
        { status: 429 }
      );
    }

    // System prompt with grant finder context
    const systemPrompt = `You are an AI assistant for Smart Grant Finder, helping users discover and apply for grants.

You can help with:
- Finding grants based on user needs
- Explaining grant requirements
- Assisting with grant applications
- Tracking deadlines and opportunities
- Analyzing grant eligibility

When a user asks to search for grants, respond with a natural language confirmation and then trigger a search.

User context:
- User ID: ${session.user.id}
- Role: ${session.user.role}

Be conversational, helpful, and proactive in suggesting relevant grants.`;

    const allMessages = [
      { role: 'system' as const, content: systemPrompt },
      ...messages,
    ];

    // Detect if user is requesting a grant search
    const lastUserMessage = messages[messages.length - 1]?.content.toLowerCase() || '';
    const isSearchRequest =
      lastUserMessage.includes('find grant') ||
      lastUserMessage.includes('search grant') ||
      lastUserMessage.includes('look for grant') ||
      lastUserMessage.includes('grant for');

    let searchTriggered = false;

    // Stream response from DeepSeek
    const result = await streamText({
      model: deepseek.chat('deepseek-chat'),
      messages: allMessages,
      temperature: 0.7,
      maxTokens: 1500,
      async onFinish({ text, usage }) {
        // Calculate cost and deduct credits
        const inputTokens = usage.promptTokens || 0;
        const outputTokens = usage.completionTokens || 0;
        const cost = (inputTokens / 1_000_000) * 0.14 + (outputTokens / 1_000_000) * 0.28;

        await CreditManager.deductCredits(
          session.user.id!,
          cost,
          'Chat message',
          undefined,
          { inputTokens, outputTokens, model: 'deepseek-chat' }
        );

        // Update chat history
        const updatedMessages = [
          ...messages,
          { role: 'assistant', content: text },
        ];

        await prisma.chatHistory.update({
          where: { id: chat!.id },
          data: {
            messages: updatedMessages,
            messageCount: updatedMessages.length,
            lastMessageAt: new Date(),
            isActive: updatedMessages.length < MAX_MESSAGES_PER_THREAD,
          },
        });

        // If search was requested, trigger it
        if (isSearchRequest && !searchTriggered) {
          searchTriggered = true;

          try {
            const orchestrator = new GrantSearchOrchestrator();
            const searchId = await orchestrator.executeSearch({
              userId: session.user.id!,
              query: lastUserMessage,
              trigger: 'MANUAL',
            });

            // Store search ID in chat metadata
            await prisma.chatHistory.update({
              where: { id: chat!.id },
              data: {
                searchId,
              },
            });
          } catch (searchError) {
            console.error('Failed to execute search:', searchError);
          }
        }
      },
    });

    return result.toDataStreamResponse();
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
