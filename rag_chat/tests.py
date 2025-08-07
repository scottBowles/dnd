from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import Mock, patch, MagicMock
from datetime import timedelta

from .models import ChatSession, ChatMessage
from .services import ConversationMemoryService


class ConversationMemoryServiceTest(TestCase):
    """Test conversation memory functionality"""
    
    def setUp(self):
        """Set up test data"""
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', email='test@example.com')
        self.service = ConversationMemoryService()
        
    def test_should_summarize_conversation_false_when_few_messages(self):
        """Test that summarization is not triggered for short conversations"""
        # Mock session with few messages
        mock_session = Mock()
        mock_session.messages.count.return_value = 10
        mock_session.summary_up_to_message_id = None
        
        with patch('rag_chat.services.ChatSession.objects.get') as mock_get:
            mock_get.return_value = mock_session
            result = self.service.should_summarize_conversation(1)
            self.assertFalse(result)
    
    def test_should_summarize_conversation_true_when_many_messages(self):
        """Test that summarization is triggered for long conversations"""
        # Mock session with many messages  
        mock_session = Mock()
        mock_session.messages.count.return_value = 30
        mock_session.summary_up_to_message_id = None
        
        with patch('rag_chat.services.ChatSession.objects.get') as mock_get:
            mock_get.return_value = mock_session
            result = self.service.should_summarize_conversation(1)
            self.assertTrue(result)
    
    def test_estimate_token_count_basic(self):
        """Test basic token counting functionality"""
        # Create mock messages
        mock_messages = [
            Mock(message="Hello", response="Hi there!"),
            Mock(message="How are you?", response="I'm doing well, thank you!"),
        ]
        
        token_count = self.service.estimate_token_count(mock_messages)
        self.assertGreater(token_count, 0)
        self.assertIsInstance(token_count, int)
    
    def test_get_conversation_context_short_conversation(self):
        """Test context retrieval for short conversations"""
        # Mock session with few messages
        mock_session = Mock()
        mock_messages = [
            Mock(created_at=timezone.now() - timedelta(hours=2)),
            Mock(created_at=timezone.now() - timedelta(hours=1)),
            Mock(created_at=timezone.now()),
        ]
        mock_session.messages.order_by.return_value = mock_messages
        
        with patch('rag_chat.services.ChatSession.objects.get') as mock_get:
            mock_get.return_value = mock_session
            result = self.service.get_conversation_context(1, max_recent_messages=20)
            self.assertEqual(len(result), 3)  # Should return all messages
    
    @patch('rag_chat.services.openai_client')
    def test_create_conversation_summary(self, mock_openai):
        """Test conversation summary creation"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test summary of the conversation"
        mock_openai.chat.completions.create.return_value = mock_response
        
        # Mock session and messages
        mock_session = Mock()
        mock_session.id = 1
        mock_session.summary = ""
        mock_session.save = Mock()
        
        mock_messages = [
            Mock(id=1, message="Hello", response="Hi"),
            Mock(id=2, message="How are you?", response="Good"),
        ]
        
        mock_queryset = Mock()
        mock_queryset.order_by.return_value = mock_queryset
        mock_queryset.filter.return_value = mock_messages
        mock_session.messages = mock_queryset
        
        with patch('rag_chat.services.ChatSession.objects.get') as mock_get:
            mock_get.return_value = mock_session
            
            result = self.service.create_conversation_summary(1, up_to_message_id=2)
            
            self.assertEqual(result, "Test summary of the conversation")
            mock_session.save.assert_called_once()
            mock_openai.chat.completions.create.assert_called_once()
    
    def test_conversation_memory_config_defaults(self):
        """Test that default configuration values are properly set"""
        service = ConversationMemoryService()
        
        self.assertIn('MAX_RECENT_MESSAGES', service.config)
        self.assertIn('MAX_CONTEXT_TOKENS', service.config)
        self.assertIn('SUMMARIZATION_TRIGGER_THRESHOLD', service.config)
        self.assertIn('SUMMARY_TARGET_LENGTH', service.config)
        
        # Test default values
        self.assertEqual(service.config['MAX_RECENT_MESSAGES'], 20)
        self.assertEqual(service.config['MAX_CONTEXT_TOKENS'], 2000)
        self.assertEqual(service.config['SUMMARIZATION_TRIGGER_THRESHOLD'], 25)
        self.assertEqual(service.config['SUMMARY_TARGET_LENGTH'], 200)
