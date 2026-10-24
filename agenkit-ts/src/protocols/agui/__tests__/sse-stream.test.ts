/**
 * Tests for the AG-UI SSE stream.
 */

import { describe, it, expect } from 'vitest';
import { Agent, Message } from '../../../core/interfaces';
import { AGUIAdapter } from '../index';
import { AGUISSEStream } from '../transports/http';

class EchoAgent implements Agent {
  readonly name = 'EchoAgent';
  readonly capabilities = [];

  async process(message: Message): Promise<Message> {
    return { role: 'assistant', content: message.content };
  }
}

async function collectMessageIds(stream: AGUISSEStream): Promise<Set<unknown>> {
  const ids = new Set<unknown>();
  for await (const chunk of stream) {
    if (!chunk.startsWith('data: ')) continue;
    const event = JSON.parse(chunk.slice('data: '.length));
    if ('message_id' in event) ids.add(event.message_id);
  }
  return ids;
}

describe('AGUISSEStream', () => {
  const message: Message = { role: 'user', content: 'hello' };

  it('uses the configured messageId for emitted events', async () => {
    const adapter = new AGUIAdapter(new EchoAgent());
    const stream = new AGUISSEStream(adapter, message, { messageId: 'client-msg-1' });

    expect(await collectMessageIds(stream)).toEqual(new Set(['client-msg-1']));
  });

  it('generates a messageId when none is configured', async () => {
    const adapter = new AGUIAdapter(new EchoAgent());
    const ids = await collectMessageIds(new AGUISSEStream(adapter, message));

    expect(ids.size).toBe(1);
    expect([...ids][0]).not.toBe('client-msg-1');
  });
});
