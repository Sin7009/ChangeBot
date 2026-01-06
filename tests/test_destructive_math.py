
from src.services.recognizer import CurrencyRecognizer

"""
Destructive testing for mathematical boundaries and logic flaws in currency recognition.
Focus: Multiplier logic collision and overwriting.
"""

def test_chained_multiplier_overwriting():
    """
    Test Case: '10k косарей'

    Logic Flaw Analysis:
    The parser identifies '10' as amount, 'k' as multiplier (1000).
    It then identifies 'косарей' as the 'currency_raw'.
    However, 'косарей' is also mapped in MULTIPLIER_MAP (1000).
    The code detects this implies RUB, but it OVERWRITES the existing 'multiplier' variable
    instead of multiplying it.

    Mathematical Expectation:
    10 * 1,000 (k) * 1,000 (косарей) = 10,000,000 RUB.

    Current Behavior (Destructive):
    10 * 1,000 (косарей) = 10,000 RUB.
    (The 'k' is effectively ignored/lost).

    Additionally, the parser might redundantly match 'косарей' as a standalone slang term,
    producing a second incorrect price.
    """
    text = "10k косарей"
    results = CurrencyRecognizer.parse(text)

    # Verify we get at least one result
    assert len(results) > 0, "Should find at least one price"

    # Find the result that corresponds to the main phrase (amount ~ 10000 or 10000000)
    # We look for the one derived from "10..."
    main_result = results[0]

    # Check currency
    assert main_result.currency == "RUB"

    # Destructive Assertion:
    # We assert the CORRECT value, expecting this to FAIL if the bug exists.
    expected_value = 10 * 1000 * 1000 # 10,000,000

    assert main_result.amount == expected_value, (
        f"Logic Error: Expected {expected_value}, but got {main_result.amount}. "
        "The parser likely overwrote the 'k' multiplier with the 'косарей' multiplier."
    )
