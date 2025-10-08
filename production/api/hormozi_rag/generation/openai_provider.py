"""
OpenAI LLM provider implementation.

Follows ARCHITECTURE.md generation engine specification.
Implements DEVELOPMENT_RULES.md error handling with circuit breaker.
"""

import time
from typing import List, Dict, Any

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("openai not installed. Run: pip install openai")

from ..config.settings import settings
from ..core.logger import get_logger
from .interfaces import LLMInterface, GenerationRequest, GenerationResponse

logger = get_logger(__name__)


class OpenAIProvider(LLMInterface):
    """
    OpenAI GPT provider with error handling and rate limiting.
    
    Follows DEVELOPMENT_RULES.md: "Every operation can fail, plan for it"
    """
    
    def __init__(self):
        """Initialize OpenAI client."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key is required")
        
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4-turbo-preview"  # Production model
        self.max_retries = 3
        self.base_delay = 1  # seconds
        
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Generate response with retry logic and error handling.
        
        Follows ARCHITECTURE.md Generation Input/Output contracts
        """
        try:
            # Build context from retrieved chunks
            context_text = "\n\n".join([
                f"Source {i+1}: {chunk}" 
                for i, chunk in enumerate(request.context[:10])  # Limit context size
            ])
            
            # Build conversation history
            messages = [
                {
                    "role": "system",
                    "content": self._build_system_prompt()
                }
            ]
            
            # Add conversation history
            for msg in request.history[-5:]:  # Last 5 messages for context
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })
            
            # Add current query with context
            user_message = f"""Context from Hormozi's frameworks:
{context_text}

Question: {request.query}

Please provide a comprehensive answer based on the context above."""
            
            messages.append({
                "role": "user", 
                "content": user_message
            })
            
            # Generate response with retry
            response = self._generate_with_retry(messages, request)
            
            return self._parse_response(response, request.context)
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            
            # Return fallback response
            return GenerationResponse(
                answer="I apologize, but I'm unable to generate a response right now. Please try again.",
                sources=[],
                confidence=0.0,
                metadata={"error": str(e)},
                token_usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for Hormozi RAG."""
        return """You are an expert business consultant specializing in Alex Hormozi's frameworks from "$100M Offers" and related materials.

Your role:
- Provide actionable business advice based on Hormozi's proven frameworks
- Use the specific context provided to give detailed, practical answers
- Reference the exact frameworks and concepts from the source material
- Be direct and results-focused, matching Hormozi's communication style

Guidelines:
- Always ground your answers in the provided context
- Use specific examples from the frameworks when available
- Be concise but comprehensive
- Focus on practical implementation
- If the context doesn't contain relevant information, say so clearly"""
    
    def _generate_with_retry(self, messages: List[Dict[str, str]], request: GenerationRequest) -> Any:
        """Generate with exponential backoff retry."""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=request.max_tokens or 1000,
                    temperature=request.temperature or 0.7,
                    timeout=settings.MAX_RESPONSE_TIME_SECONDS
                )
                return response
                
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"Generation attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All generation attempts failed: {e}")
        
        raise last_exception
    
    def _parse_response(self, response: Any, context: List[str]) -> GenerationResponse:
        """Parse OpenAI response into GenerationResponse format."""
        try:
            content = response.choices[0].message.content
            usage = response.usage
            
            # Calculate confidence based on response quality indicators
            confidence = self._calculate_confidence(content, context)
            
            return GenerationResponse(
                answer=content,
                sources=context[:5],  # Reference top sources used
                confidence=confidence,
                metadata={
                    "model": self.model,
                    "finish_reason": response.choices[0].finish_reason
                },
                token_usage={
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens, 
                    "total_tokens": usage.total_tokens
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise
    
    def _calculate_confidence(self, answer: str, context: List[str]) -> float:
        """Calculate confidence score based on answer quality."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence if answer references specific frameworks
        frameworks = ["value equation", "offer stack", "guarantee", "pricing", "scarcity"]
        for framework in frameworks:
            if framework.lower() in answer.lower():
                confidence += 0.1
        
        # Increase confidence if answer is substantial
        if len(answer) > 200:
            confidence += 0.1
        
        # Increase confidence if answer uses context
        context_words = set()
        for chunk in context:
            context_words.update(chunk.lower().split()[:10])  # Key words from context
        
        answer_words = set(answer.lower().split())
        overlap = len(context_words.intersection(answer_words))
        if overlap > 5:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def health_check(self) -> bool:
        """Check OpenAI API health."""
        try:
            # Simple test request
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=1
            )
            return response is not None
            
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Rough estimation: ~4 characters per token for English
        return len(text) // 4