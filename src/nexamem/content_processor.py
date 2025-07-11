"""
Content processor chain for redaction and enrichment.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


class ContentProcessor(Protocol):
    """Protocol for content processors."""
    
    def process(self, content: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """
        Process content and return modified content and updated metadata.
        
        Args:
            content: Original content
            metadata: Content metadata
            
        Returns:
            Tuple of (processed_content, updated_metadata)
        """
        ...


class PIIRedactor:
    """Basic PII redaction processor."""
    
    def __init__(self):
        # Basic PII patterns - in production this would be more sophisticated
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b\d{3}-\d{3}-\d{4}\b|\b\(\d{3}\)\s*\d{3}-\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b')
        }
    
    def process(self, content: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Redact PII from content."""
        processed_content = content
        detected_pii = []
        
        for pii_type, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if matches:
                detected_pii.append(pii_type)
                processed_content = pattern.sub(f'[REDACTED_{pii_type.upper()}]', processed_content)
        
        # Update metadata
        metadata = metadata.copy()
        metadata['pii_detected'] = detected_pii
        metadata['pii_redacted'] = len(detected_pii) > 0
        
        return processed_content, metadata


class ContentEnricher:
    """Basic content enrichment processor."""
    
    def process(self, content: str, metadata: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Enrich content with metadata."""
        metadata = metadata.copy()
        metadata['content_length'] = len(content)
        metadata['word_count'] = len(content.split())
        
        # Could add sentiment analysis, topic classification, etc.
        return content, metadata


class ContentProcessorChain:
    """Chain of content processors."""
    
    def __init__(self, processors: Optional[List[ContentProcessor]] = None):
        self.processors = processors or []
        self.enabled = len(self.processors) > 0
    
    def add_processor(self, processor: ContentProcessor) -> None:
        """Add a processor to the chain."""
        self.processors.append(processor)
        self.enabled = True
    
    def process(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Process content through the entire chain.
        
        Args:
            content: Original content
            metadata: Initial metadata
            
        Returns:
            Tuple of (processed_content, final_metadata)
        """
        if not self.enabled:
            return content, metadata or {}
        
        current_content = content
        current_metadata = metadata or {}
        
        for processor in self.processors:
            try:
                current_content, current_metadata = processor.process(current_content, current_metadata)
            except Exception as e:
                logger.warning(f"Content processor {type(processor).__name__} failed: {e}")
                continue
        
        return current_content, current_metadata


# Default chain for MVP
def create_default_chain(auto_pii: bool = False) -> ContentProcessorChain:
    """Create default content processor chain."""
    chain = ContentProcessorChain()
    
    if auto_pii:
        chain.add_processor(PIIRedactor())
    
    chain.add_processor(ContentEnricher())
    
    return chain
