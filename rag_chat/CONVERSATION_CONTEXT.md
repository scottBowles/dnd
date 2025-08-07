# Enhanced RAG Conversation Context Management

## Overview

The RAG chat system now includes sophisticated conversation context management that goes beyond simple truncation to preserve conversational continuity through intelligent LLM-based summarization.

## Key Features

### 🧠 Intelligent Context Strategies

The system supports three strategies for managing conversation context:

1. **TRUNCATE**: Simple removal of older messages (original behavior)
2. **SUMMARIZE**: LLM-powered summarization of conversation history
3. **HYBRID**: Smart combination that chooses the best approach based on context

### 📝 LLM-Based Summarization

When conversation history becomes too long for the context window, the system can intelligently summarize older exchanges while preserving recent detailed interactions:

- **D&D-Optimized Prompts**: Specialized prompts that preserve campaign elements like characters, locations, events, and decisions
- **Configurable Token Targets**: Control how concise or detailed summaries should be
- **Graceful Fallback**: Automatically falls back to truncation if summarization fails

### ⚙️ Configurable Behavior

```python
from rag_chat.conversation_context import ContextStrategy, ContextConfiguration

# Configure conversation context management
config = ContextConfiguration(
    max_conversation_tokens=2000,     # Total token budget for conversation
    max_recent_messages=6,            # Keep this many recent messages verbatim
    summarization_threshold=1500,     # Start summarizing when history > this
    summary_target_tokens=400,        # Target token count for summaries
    strategy=ContextStrategy.HYBRID   # Use intelligent hybrid approach
)
```

### 🔮 Future-Ready Architecture

The modular design supports future enhancements:

- Extensible `ConversationContextManager` class
- Support for multi-step LLM workflows
- Integration points for decision trees and context augmentation
- Clean separation of concerns

## Usage Examples

### Basic Usage

```python
from rag_chat.services import RAGService

# Initialize with default configuration
rag_service = RAGService()

# Generate response with conversation context
response = rag_service.generate_response(
    query="What should we do about the Shadowblight?",
    session=chat_session  # Includes conversation history
)

# Response includes context statistics
print(response['context_stats'])
```

### Dynamic Configuration

```python
# Configure summarization strategy
rag_service.configure_conversation_strategy(
    strategy=ContextStrategy.SUMMARIZE,
    max_recent_messages=4,
    summarization_threshold=1200
)

# Get conversation statistics
stats = rag_service.get_conversation_stats(session, current_message)
```

## Context Strategies in Detail

### TRUNCATE Strategy

Simple removal of older messages to fit within token limits:

- **Pros**: Fast, predictable, preserves exact message content
- **Cons**: Loses conversation continuity, may remove important context
- **Best for**: Short conversations, debugging, when summarization is unavailable

### SUMMARIZE Strategy

LLM-powered summarization of older conversation history:

- **Pros**: Preserves conversation continuity, better context utilization
- **Cons**: Requires additional API calls, potential summarization errors
- **Best for**: Long campaign discussions, complex narrative threads

### HYBRID Strategy (Recommended)

Intelligent decision-making that chooses the best approach:

- **Pros**: Optimizes for each situation, balances speed and continuity
- **Cons**: More complex logic, less predictable behavior
- **Best for**: General use, production environments

## D&D Campaign Optimization

The summarization system is specifically optimized for D&D campaigns:

### Campaign Element Preservation

- **Characters**: Names, relationships, character development
- **Locations**: Hierarchical location context (planet > region > city > building)
- **Items & Artifacts**: Significance, powers, quest relevance
- **NPCs**: Interactions, knowledge, motivations
- **Events**: Story progression, consequences, unresolved threads

### Example Summary

```
Previous conversation summary: The party explored the Crystal Caves and discovered 
ancient dwarven ruins containing the Heart of the Mountain artifact. They encountered 
Keeper Thalnor, an ancient dwarven spirit who explained the artifact's power to 
control magical ley lines and its potential use against the Shadowblight, a primordial 
evil beginning to escape its prison. The group is considering whether to take the 
artifact despite the risks.
```

## Configuration Options

### ContextConfiguration

```python
@dataclass
class ContextConfiguration:
    max_conversation_tokens: int = 2000        # Token budget for conversation
    max_recent_messages: int = 6               # Recent messages kept verbatim
    summarization_threshold: int = 1500        # When to start summarizing
    summary_target_tokens: int = 400           # Target summary length
    strategy: ContextStrategy = HYBRID         # Context management strategy
```

### Tuning Guidelines

- **Short Sessions**: Use TRUNCATE with higher `max_recent_messages`
- **Long Campaigns**: Use SUMMARIZE or HYBRID with lower `summarization_threshold`
- **Token Efficiency**: Reduce `summary_target_tokens` for more concise summaries
- **Detail Preservation**: Increase `max_recent_messages` for more verbatim context

## Monitoring and Statistics

The system provides detailed statistics for monitoring and optimization:

```python
stats = rag_service.get_conversation_stats(session, current_message)
# Returns:
{
    "total_messages": 12,
    "total_tokens": 1850,
    "summary_count": 1,
    "strategy_used": "hybrid",
    "within_limits": True,
    "conversation_length": 6
}
```

## Future Enhancements

The architecture supports upcoming features:

1. **Multi-Step Workflows**: Support for complex AI decision trees
2. **Context Augmentation**: Automatic injection of relevant campaign information
3. **Adaptive Strategies**: Machine learning-based strategy selection
4. **Real-time Optimization**: Dynamic adjustment based on conversation patterns

## Migration Notes

The enhanced system is backward compatible:

- Existing conversations continue to work without changes
- Session parameter remains optional in `generate_response()`
- Default behavior preserves original functionality
- New features are opt-in through configuration