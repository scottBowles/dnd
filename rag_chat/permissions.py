"""
Permission classes for RAG chat functionality.
"""
from strawberry.permission import BasePermission
from strawberry.types import Info
from typing import Any


class CanUseRAGChat(BasePermission):
    """Permission to check if user can use RAG chat functionality."""
    
    message = "You don't have permission to use RAG chat."
    
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        user = info.context.request.user
        
        if not user.is_authenticated:
            return False
        
        # Superusers always have access
        if user.is_superuser:
            return True
        
        # Check if user has the specific permission or is in the RAG Chat Users group
        return (
            user.has_perm('rag_chat.can_use_rag_chat') or
            user.groups.filter(name='RAG Chat Users').exists()
        )


class CanStartChatSession(BasePermission):
    """Permission to check if user can start new chat sessions."""
    
    message = "You don't have permission to start chat sessions."
    
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        user = info.context.request.user
        
        if not user.is_authenticated:
            return False
        
        # Superusers always have access
        if user.is_superuser:
            return True
        
        # Check if user has the specific permission or is in the RAG Chat Users group
        return (
            user.has_perm('rag_chat.can_start_chat_session') or
            user.groups.filter(name='RAG Chat Users').exists()
        )


class CanSendChatMessage(BasePermission):
    """Permission to check if user can send chat messages."""
    
    message = "You don't have permission to send chat messages."
    
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        user = info.context.request.user
        
        if not user.is_authenticated:
            return False
        
        # Superusers always have access
        if user.is_superuser:
            return True
        
        # Check if user has the specific permission or is in the RAG Chat Users group
        return (
            user.has_perm('rag_chat.can_send_chat_message') or
            user.groups.filter(name='RAG Chat Users').exists()
        )
