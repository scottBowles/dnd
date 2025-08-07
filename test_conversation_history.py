#!/usr/bin/env python
"""
Test script to verify conversation history functionality
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website.settings')
django.setup()

from rag_chat.services import RAGService
from rag_chat.models import ChatSession, ChatMessage
from django.contrib.auth.models import User

def test_conversation_history():
    """Test the conversation history functionality"""
    
    # Create RAGService instance
    rag_service = RAGService()
    
    # Test token counting
    test_text = "Hello, this is a test message."
    token_count = rag_service._count_tokens(test_text)
    print(f"Token count for '{test_text}': {token_count}")
    
    # Test conversation history building (without actual database)
    print("\nTesting conversation history building...")
    
    # Mock conversation data
    mock_conversation = [
        {"role": "user", "content": "What is the capital of France?"},
        {"role": "assistant", "content": "The capital of France is Paris."},
        {"role": "user", "content": "What about Germany?"},
        {"role": "assistant", "content": "The capital of Germany is Berlin."},
        {"role": "user", "content": "Tell me about these cities."},
    ]
    
    # Test truncation
    truncated = rag_service._truncate_conversation(mock_conversation)
    print(f"Original conversation length: {len(mock_conversation)}")
    print(f"Truncated conversation length: {len(truncated)}")
    
    for i, msg in enumerate(truncated):
        print(f"  {i+1}. {msg['role']}: {msg['content'][:50]}...")
    
    print("\nConversation history functionality test completed successfully!")

if __name__ == "__main__":
    test_conversation_history()