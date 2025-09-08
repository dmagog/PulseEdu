"""
Markdown rendering service with sanitization for LLM recommendations.
"""
import logging
import markdown
import bleach
from typing import List, Dict, Any

logger = logging.getLogger("app.markdown")

class MarkdownService:
    def __init__(self):
        # Configure markdown extensions
        self.md = markdown.Markdown(
            extensions=[
                'markdown.extensions.extra',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
                'markdown.extensions.nl2br',
                'markdown.extensions.sane_lists'
            ],
            extension_configs={
                'markdown.extensions.codehilite': {
                    'css_class': 'highlight'
                }
            }
        )
        
        # Configure bleach for HTML sanitization
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'b', 'i',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'blockquote',
            'code', 'pre', 'span',
            'a', 'img',
            'table', 'thead', 'tbody', 'tr', 'th', 'td'
        ]
        
        self.allowed_attributes = {
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'span': ['class'],
            'code': ['class'],
            'pre': ['class'],
            'table': ['class'],
            'th': ['class'],
            'td': ['class']
        }
        
        self.allowed_protocols = ['http', 'https', 'mailto']
    
    def render_recommendations(self, recommendations: List[str]) -> List[Dict[str, Any]]:
        """
        Render a list of recommendations with markdown support.
        
        Args:
            recommendations: List of recommendation strings (may contain markdown)
            
        Returns:
            List of dicts with 'text' and 'html' keys
        """
        rendered = []
        
        for i, recommendation in enumerate(recommendations):
            try:
                # Convert markdown to HTML
                html = self.md.convert(recommendation)
                
                # Sanitize HTML
                clean_html = bleach.clean(
                    html,
                    tags=self.allowed_tags,
                    attributes=self.allowed_attributes,
                    protocols=self.allowed_protocols
                )
                
                rendered.append({
                    'id': i + 1,
                    'text': recommendation,
                    'html': clean_html,
                    'preview': self._create_preview(recommendation)
                })
                
            except Exception as e:
                logger.error(f"Error rendering recommendation {i + 1}: {e}")
                # Fallback to plain text
                rendered.append({
                    'id': i + 1,
                    'text': recommendation,
                    'html': self._escape_html(recommendation),
                    'preview': self._create_preview(recommendation)
                })
        
        return rendered
    
    def render_single_recommendation(self, recommendation: str) -> Dict[str, Any]:
        """
        Render a single recommendation with markdown support.
        
        Args:
            recommendation: Recommendation string (may contain markdown)
            
        Returns:
            Dict with 'text' and 'html' keys
        """
        try:
            # Convert markdown to HTML
            html = self.md.convert(recommendation)
            
            # Sanitize HTML
            clean_html = bleach.clean(
                html,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                protocols=self.allowed_protocols
            )
            
            return {
                'text': recommendation,
                'html': clean_html,
                'preview': self._create_preview(recommendation)
            }
            
        except Exception as e:
            logger.error(f"Error rendering recommendation: {e}")
            # Fallback to plain text
            return {
                'text': recommendation,
                'html': self._escape_html(recommendation),
                'preview': self._create_preview(recommendation)
            }
    
    def _create_preview(self, text: str, max_length: int = 150) -> str:
        """Create a preview of the recommendation text."""
        # Remove markdown formatting for preview
        import re
        
        # Remove markdown headers
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Remove markdown bold/italic
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        
        # Remove markdown links
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove markdown lists
        text = re.sub(r'^\s*[-*+]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length].rsplit(' ', 1)[0] + '...'
        
        return text
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML characters in plain text."""
        import html
        return html.escape(text)
    
    def validate_markdown(self, text: str) -> Dict[str, Any]:
        """
        Validate markdown text and return validation results.
        
        Args:
            text: Markdown text to validate
            
        Returns:
            Dict with validation results
        """
        try:
            # Try to convert markdown
            html = self.md.convert(text)
            
            # Check for potentially dangerous content
            dangerous_patterns = [
                r'<script[^>]*>',
                r'javascript:',
                r'data:text/html',
                r'vbscript:',
                r'on\w+\s*='
            ]
            
            import re
            issues = []
            for pattern in dangerous_patterns:
                if re.search(pattern, html, re.IGNORECASE):
                    issues.append(f"Potentially dangerous content: {pattern}")
            
            # Check HTML after sanitization
            clean_html = bleach.clean(
                html,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                protocols=self.allowed_protocols
            )
            
            return {
                'valid': True,
                'issues': issues,
                'html_length': len(html),
                'clean_html_length': len(clean_html),
                'sanitized': html != clean_html
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': str(e),
                'issues': [f"Markdown parsing error: {e}"]
            }
