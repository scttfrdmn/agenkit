package io.agenkit.memory;

import io.agenkit.core.Message;

import java.util.List;

/**
 * Interface for pluggable memory backends.
 */
public interface Memory {

    /** Store a message in memory. */
    void store(Message message);

    /** Retrieve up to topK relevant messages for a query. */
    List<Message> retrieve(String query, int topK);

    /** Return the total number of stored messages. */
    int size();

    /** Clear all stored messages. */
    void clear();
}
