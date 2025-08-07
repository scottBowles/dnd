# RAG Chat Conversation History

This implementation adds conversation history awareness to the RAG chat system, enabling natural conversation flow while maintaining the retrieval-augmented generation capabilities.

## Key Features

### 1. **Conversation Context Preservation**
- Previous messages in a chat session are included when generating responses
- Conversation history is presented in chronological order to the LLM
- System maintains context across multiple exchanges

### 2. **Smart Token Management**
- Automatic token counting with fallback estimation
- Dynamic context window detection based on model (up to 128K tokens for newer models)
- Intelligent truncation when conversation exceeds limits

### 3. **Balanced Context**
- **Max conversation tokens**: 2000 tokens
- **Max context tokens**: 4000 tokens  
- **System prompt + response buffer**: ~1200 tokens
- **Total limit**: Model-dependent (8K to 128K tokens)

### 4. **Graceful Degradation**
- Recent messages prioritized when truncating conversation history
- Current message always preserved
- Retrieved content still included with each response

## Example Conversation Flow

```
User: "What happened in our last D&D session?"
Assistant: "In your last session, the party explored the Crystal Caves and encountered ancient dwarven ruins..."

User: "Who was with us?"  
Assistant: "Based on our previous discussion about the Crystal Caves session, your party included Thorin the Dwarf Fighter, Elara the Elf Wizard, and Gareth the Human Rogue."

User: "What did Elara discover?"
Assistant: "Continuing from our conversation about the Crystal Caves exploration, Elara discovered ancient magical runes that revealed..."
```

## Technical Implementation

### Core Methods Added to RAGService:

- `_build_conversation_history()`: Builds conversation from session messages
- `_truncate_conversation()`: Intelligently truncates to fit token limits  
- `_count_tokens()`: Accurate token counting with tiktoken
- `_get_model_context_window()`: Dynamic context window detection

### GraphQL Integration:

The `send_chat_message` mutation now passes the session to `generate_response()`:

```python
response_data = rag_service.generate_response(
    query=input.message,
    session=session,  # <-- New parameter for conversation history
    similarity_threshold=input.similarity_threshold,
    content_types=input.content_types,
)
```

### Message Flow:

1. **System Prompt**: Campaign-specific instructions
2. **Conversation History**: Previous user/assistant exchanges  
3. **Current Message**: User query with retrieved context
4. **LLM Response**: Generated with full conversation awareness

## Benefits

- **Natural Conversations**: Users can refer to previous topics and context
- **Better Understanding**: LLM has full conversation context for nuanced responses
- **Maintained Performance**: Smart token limits prevent context window overflow
- **Backward Compatible**: Existing API unchanged (session parameter is optional)