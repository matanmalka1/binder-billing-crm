from typing import Optional


class WhatsAppChannel:
    """WhatsApp notification channel (stub for Sprint 4)."""

    def send(self, recipient: str, content: str) -> tuple[bool, Optional[str]]:
        """
        Send WhatsApp message.
        
        Note: This is a stub implementation.
        Production would integrate with WhatsApp Business API.
        """
        # Stub: always succeed in development
        return (True, None)


class EmailChannel:
    """Email notification channel (stub for Sprint 4)."""

    def send(self, recipient: str, content: str) -> tuple[bool, Optional[str]]:
        """
        Send email message.
        
        Note: This is a stub implementation.
        Production would integrate with email service.
        """
        # Stub: always succeed in development
        return (True, None)
