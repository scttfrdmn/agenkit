package io.agenkit.core;

import java.util.concurrent.Flow;

/**
 * Extension of Agent that supports streaming responses.
 */
public interface StreamingAgent extends Agent {

    /**
     * Stream a message response as a sequence of partial messages.
     *
     * @param message the incoming message
     * @return a Flow.Publisher that emits partial response chunks
     */
    Flow.Publisher<Message> stream(Message message);
}
