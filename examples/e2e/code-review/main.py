"""
Code Review System - Multi-Agent Team Example

Demonstrates parallel agent execution for code review.

Usage:
    python main.py
"""

import asyncio

from agents.review_types import CodeSubmission
from orchestration import ReviewOrchestrator

# Sample code submissions for demo
GOOD_CODE = '''def calculate_sum(numbers):
    """Calculate sum of numbers."""
    return sum(numbers)


def greet_user(name):
    """Greet user by name."""
    return f"Hello, {name}!"
'''

BAD_CODE = """import os

password = "admin123"  # Hardcoded password
api_key = "sk_test_1234567890"  # Hardcoded API key

def getUserData(userId):  # camelCase instead of snake_case
    query = "SELECT * FROM users WHERE id = " + str(userId)  # SQL injection
    cursor.execute(query)
    return cursor.fetchall()

def process_items(items=[]):  # Mutable default argument
    for item in items:
        result += item  # String concat in loop
    return result

class user_account:  # snake_case instead of PascalCase
    def __init__(self):
        try:
            risky_operation()
        except:  # Bare except
            pass
"""

MEDIUM_CODE = """def find_duplicates(lst):
    duplicates = []
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):  # Nested loop - O(n²)
            if lst[i] == lst[j]:
                duplicates.append(lst[i])
    return duplicates


def format_data(items):
    result = ""
    for item in items:
        result += str(item) + "\\n"  # String concat in loop
    return result
"""


async def demo():
    """Run code review demos."""
    print("=" * 70)
    print("CODE REVIEW SYSTEM - MULTI-AGENT DEMO")
    print("=" * 70)
    print("\nDemonstrating parallel agent execution for code review.")
    print("4 specialized agents: Style, Security, Performance, Correctness")
    print()

    orchestrator = ReviewOrchestrator(verbose=True)

    test_cases = [
        {
            "name": "Good Code",
            "description": "Clean, well-written code",
            "code": GOOD_CODE,
        },
        {
            "name": "Bad Code",
            "description": "Multiple critical issues",
            "code": BAD_CODE,
        },
        {
            "name": "Medium Quality Code",
            "description": "Performance issues",
            "code": MEDIUM_CODE,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'*' * 70}")
        print(f"TEST CASE #{i}: {test_case['name']}")
        print(f"Description: {test_case['description']}")
        print(f"{'*' * 70}")

        submission = CodeSubmission(
            content=test_case["code"],
            file_path=f"example_{i}.py",
            language="python",
        )

        report = await orchestrator.review_code(submission)
        print(f"\n{report}")

        await asyncio.sleep(0.5)

    print(f"\n\n{'=' * 70}")
    print("DEMO COMPLETE")
    print(f"{'=' * 70}")


async def review_file(filepath: str):
    """Review a specific file."""
    with open(filepath) as f:
        content = f.read()

    submission = CodeSubmission(
        content=content,
        file_path=filepath,
        language="python" if filepath.endswith(".py") else None,
    )

    orchestrator = ReviewOrchestrator(verbose=True)
    report = await orchestrator.review_code(submission)
    print(f"\n{report}")


async def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1:
        # Review specific file
        filepath = sys.argv[1]
        await review_file(filepath)
    else:
        # Run demo
        await demo()


if __name__ == "__main__":
    asyncio.run(main())
