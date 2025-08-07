# Conversation Memory Documentation

## Overview

The conversation memory system provides extended conversation capabilities for the RAG chat system using a sliding window approach with automatic summarization. This allows users to have long conversations without losing important context while staying within LLM token limits.

## Architecture

### Database Schema

The `ChatSession` model has been extended with three new fields:

- `summary` (TextField): Auto-generated conversation summary
- `summary_up_to_message_id` (IntegerField): Last message ID included in the summary
- `last_summarized_at` (DateTimeField): Timestamp of last summarization

### Core Service

The `ConversationMemoryService` class provides the main functionality:

```python
from rag_chat.services import ConversationMemoryService

memory_service = ConversationMemoryService()
```

#### Key Methods

- `get_conversation_context(session_id, max_recent_messages=20, max_tokens=2000)`: Returns optimized message context for LLM
- `should_summarize_conversation(session_id)`: Checks if conversation needs summarization
- `create_conversation_summary(session_id, up_to_message_id=None)`: Generates conversation summary
- `estimate_token_count(messages)`: Estimates token count for context management

## Configuration

Configure the conversation memory system in `settings.py`:

```python
CONVERSATION_MEMORY_CONFIG = {
    'MAX_RECENT_MESSAGES': 20,        # Number of recent messages to keep
    'MAX_CONTEXT_TOKENS': 2000,       # Maximum tokens in context
    'SUMMARIZATION_TRIGGER_THRESHOLD': 25,  # Trigger summarization after N messages
    'SUMMARY_TARGET_LENGTH': 200,     # Target summary length in words
}
```

## How It Works

### For Short Conversations (≤ 20 messages)
- Returns all messages in chronological order
- No summarization needed

### For Long Conversations (> 25 messages)
1. Automatically triggers summarization when threshold is reached
2. Summarizes older messages (keeping recent 20 messages unsummarized)
3. Returns: [Summary] + [Recent Messages]
4. Updates session with summary and metadata

### Context Assembly Priority
1. System prompt (if any)
2. Conversation summary (if exists)
3. Recent messages (chronological order)
4. Current user message

### Token Management
- Uses `tiktoken` for accurate token counting
- Falls back to character-based estimation if tiktoken unavailable
- Progressively trims context if it exceeds token limits
- Removes oldest messages first (preserving summary)

## Integration

### GraphQL Mutation

The conversation memory is automatically integrated into the `send_chat_message` mutation:

```python
@strawberry.mutation
def send_chat_message(self, info, input: SendChatMessageInput):
    # ... existing authentication and validation
    
    memory_service = ConversationMemoryService(model=model)
    
    # Check if summarization is needed before processing
    if memory_service.should_summarize_conversation(session.id):
        memory_service.create_conversation_summary(session.id)
    
    # ... continue with RAG processing
```

### Error Handling

The system includes comprehensive error handling:

- **Summarization Failures**: Logs error but continues chat functionality
- **Network Issues**: Falls back to character-based token estimation
- **Database Errors**: Returns empty context with graceful degradation

## Usage Examples

### Basic Usage (Automatic)

The conversation memory works automatically. Users simply send messages through the existing GraphQL mutation, and the system handles everything behind the scenes.

### Manual Summarization

```python
from rag_chat.services import ConversationMemoryService

memory_service = ConversationMemoryService()

# Check if summarization is needed
if memory_service.should_summarize_conversation(session_id):
    summary = memory_service.create_conversation_summary(session_id)
    print(f"Generated summary: {summary}")
```

### Custom Context Retrieval

```python
# Get optimized conversation context
context_messages = memory_service.get_conversation_context(
    session_id=123,
    max_recent_messages=15,  # Override default
    max_tokens=1500         # Override default
)
```

## Monitoring

The system logs important events:

- Summarization triggers and completions
- Token count estimations
- Error conditions and fallbacks
- Context assembly decisions

Check Django logs for conversation memory operations:

```bash
# Look for log entries with "conversation memory", "summarization", etc.
grep -i "summary\|memory" logs/django.log
```

## Performance Considerations

- **Summarization**: Only runs when needed (configurable threshold)
- **Token Counting**: Cached encoding models for efficiency
- **Database Queries**: Optimized queries for message retrieval
- **Caching**: Consider adding Redis caching for active conversations

## Tuning Guidelines

### For Different Use Cases

**Short Sessions (Customer Support)**
```python
CONVERSATION_MEMORY_CONFIG = {
    'MAX_RECENT_MESSAGES': 10,
    'SUMMARIZATION_TRIGGER_THRESHOLD': 15,
    'MAX_CONTEXT_TOKENS': 1500,
}
```

**Long Sessions (Research/Analysis)**
```python
CONVERSATION_MEMORY_CONFIG = {
    'MAX_RECENT_MESSAGES': 30,
    'SUMMARIZATION_TRIGGER_THRESHOLD': 40,
    'MAX_CONTEXT_TOKENS': 3000,
}
```

### Model Considerations

- **GPT-3.5**: Lower token limits, more aggressive summarization
- **GPT-4**: Higher token limits, can maintain more context
- **Claude**: Different tokenization, may need adjusted estimates

## Migration

To apply the database changes:

```bash
python manage.py migrate rag_chat
```

This adds the new fields to existing `ChatSession` records with appropriate defaults.

## Testing

Run the conversation memory tests:

```bash
python manage.py test rag_chat.tests.ConversationMemoryServiceTest
```

Or use the standalone test script for environments without full database setup:

```bash
python /tmp/test_conversation_memory.py
```

## Future Enhancements

Possible future improvements (not in current scope):

- User-controlled memory settings
- Semantic search through conversation history
- Conversation analytics and insights
- Multi-conversation context (related sessions)
- Advanced summarization strategies (topic-based, importance-weighted)