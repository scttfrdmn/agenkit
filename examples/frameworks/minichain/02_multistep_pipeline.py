"""
MiniChain Example 2: Multi-Step Pipeline

Demonstrates:
- Research → Write → Edit pipeline
- Multiple specialized chains
- Data transformation between steps
- Real-world content generation workflow

~150 LOC
"""

import asyncio
import os

from agenkit.adapters.llm import OpenAILLM
from minichain import LLMChain, RunnableLambda


async def research_write_edit_pipeline():
    """
    Three-step content generation pipeline:
    1. Research: Gather key points
    2. Write: Generate draft
    3. Edit: Polish and refine
    """
    print("=" * 60)
    print("Research → Write → Edit Pipeline")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Step 1: Research - Gather key points
    research_chain = LLMChain(
        agent=llm,
        prompt_template="""Research {topic} and list 3 key points to cover.
Format as a bulleted list.""",
        system_message="You are a thorough researcher.",
    )

    # Transform research output into writing input
    def prepare_writing(research: str) -> dict:
        return {"topic": "artificial intelligence", "research": research}

    # Step 2: Write - Generate draft
    write_chain = LLMChain(
        agent=llm,
        prompt_template="""Write a short blog post about {topic}.

Use these key points:
{research}

Keep it under 150 words.""",
        system_message="You are a skilled tech writer.",
    )

    # Transform draft into editing input
    def prepare_editing(draft: str) -> dict:
        return {"draft": draft}

    # Step 3: Edit - Polish and refine
    edit_chain = LLMChain(
        agent=llm,
        prompt_template="""Edit this draft to be more engaging and clear:

{draft}

Maintain the length but improve clarity and flow.""",
        system_message="You are a professional editor.",
    )

    # Compose full pipeline
    pipeline = (
        research_chain
        | RunnableLambda(prepare_writing)
        | write_chain
        | RunnableLambda(prepare_editing)
        | edit_chain
    )

    # Execute
    print("\n📝 Starting content generation pipeline...\n")
    result = await pipeline.invoke({"topic": "artificial intelligence"})

    print("=" * 60)
    print("FINAL OUTPUT")
    print("=" * 60)
    print(result)
    print()


async def data_analysis_pipeline():
    """
    Data analysis workflow:
    1. Extract: Parse raw data
    2. Analyze: Find insights
    3. Summarize: Create executive summary
    """
    print("=" * 60)
    print("Extract → Analyze → Summarize Pipeline")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Sample raw data
    raw_data = """
    Sales Q1: $1.2M, Q2: $1.8M, Q3: $2.1M, Q4: $2.5M
    Customers: 1500 → 2200 → 2800 → 3100
    Churn: 5%, 4%, 3%, 3%
    """

    # Step 1: Extract key metrics
    extract_chain = LLMChain(
        agent=llm,
        prompt_template="""Extract and structure these key metrics:

{data}

Format as: Metric | Q1 | Q2 | Q3 | Q4""",
        system_message="You are a data analyst.",
    )

    # Step 2: Analyze trends
    def prepare_analysis(extracted: str) -> dict:
        return {"metrics": extracted}

    analyze_chain = LLMChain(
        agent=llm,
        prompt_template="""Analyze these metrics and identify 3 key trends:

{metrics}

Be specific and data-driven.""",
        system_message="You are a business analyst.",
    )

    # Step 3: Create executive summary
    def prepare_summary(analysis: str) -> dict:
        return {"analysis": analysis}

    summarize_chain = LLMChain(
        agent=llm,
        prompt_template="""Create a 2-paragraph executive summary of this analysis:

{analysis}

Focus on business implications.""",
        system_message="You are an executive communications specialist.",
    )

    # Compose pipeline
    pipeline = (
        extract_chain
        | RunnableLambda(prepare_analysis)
        | analyze_chain
        | RunnableLambda(prepare_summary)
        | summarize_chain
    )

    # Execute
    print("\n📊 Starting data analysis pipeline...\n")
    result = await pipeline.invoke({"data": raw_data})

    print("=" * 60)
    print("EXECUTIVE SUMMARY")
    print("=" * 60)
    print(result)
    print()


async def translation_pipeline():
    """
    Multi-step translation with quality checks:
    1. Translate: Convert to target language
    2. Review: Check for errors
    3. Refine: Improve naturalness
    """
    print("=" * 60)
    print("Translate → Review → Refine Pipeline")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        return

    llm = OpenAILLM(api_key=api_key, model="gpt-4o-mini")

    # Original text
    text = "The quick brown fox jumps over the lazy dog."

    # Step 1: Translate
    translate_chain = LLMChain(
        agent=llm,
        prompt_template="Translate this to French: {text}",
        system_message="You are a professional translator.",
    )

    # Step 2: Review translation
    def prepare_review(translation: str) -> dict:
        return {"translation": translation, "original": text}

    review_chain = LLMChain(
        agent=llm,
        prompt_template="""Review this translation for accuracy:

Original: {original}
Translation: {translation}

Is it accurate? Suggest improvements if needed.""",
        system_message="You are a translation quality expert.",
    )

    # Step 3: Refine based on review
    def prepare_refinement(review: str) -> dict:
        return {"review": review}

    refine_chain = LLMChain(
        agent=llm,
        prompt_template="""Based on this review, provide the final refined translation:

{review}

Output only the final French translation.""",
        system_message="You are a professional translator.",
    )

    # Compose pipeline
    pipeline = (
        translate_chain
        | RunnableLambda(prepare_review)
        | review_chain
        | RunnableLambda(prepare_refinement)
        | refine_chain
    )

    # Execute
    print(f"\n🌐 Translating: '{text}'\n")
    result = await pipeline.invoke({"text": text})

    print("=" * 60)
    print("FINAL TRANSLATION")
    print("=" * 60)
    print(result)
    print()


async def main():
    """Run all pipeline examples."""
    try:
        await research_write_edit_pipeline()
        await data_analysis_pipeline()
        await translation_pipeline()

        print("=" * 60)
        print("✅ All pipeline examples completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
