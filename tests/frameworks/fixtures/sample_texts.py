"""Reusable test string constants for framework compatibility tests."""

# Simple single-variable prompt templates
TRANSLATE_PROMPT = "Translate to French: {text}"
SUMMARIZE_PROMPT = "Summarize the following: {text}"
GREET_PROMPT = "Say hello to {name}"

# Multi-variable prompt templates
MULTI_VAR_PROMPT = "Write a {length} {style} about {topic}"

# Sample input texts
SAMPLE_TEXT = "The quick brown fox jumps over the lazy dog."
SAMPLE_ARTICLE = "AI has made remarkable progress in recent years, transforming industries."
SAMPLE_CODE = "def hello(): return 'Hello, World!'"

# Conversation inputs
GREETING = "Hello, how are you?"
FOLLOWUP = "What did I just say?"
FAREWELL = "Goodbye!"

# Router test inputs
BILLING_QUERY = "I have a question about my invoice and payment."
TECH_QUERY = "I'm getting an error in my application."
ACCOUNT_QUERY = "I need to reset my password."
GENERAL_QUERY = "What is the weather today?"

# Crew task descriptions
RESEARCH_TASK = "Research the latest AI trends."
ANALYSIS_TASK = "Analyze the research findings."
WRITING_TASK = "Write a blog post about the findings."

# Expected mock responses
MOCK_RESPONSE = "mock response"
MOCK_TRANSLATION = "Bonjour le monde"
MOCK_SUMMARY = "A concise summary."
MOCK_ANALYSIS = "Key insights identified."
