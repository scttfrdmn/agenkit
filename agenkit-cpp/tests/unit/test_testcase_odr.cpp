/**
 * @file test_testcase_odr.cpp
 * @brief Regression test for #831 — two agenkit::evaluation::TestCase definitions.
 *
 * `agenkit::evaluation::TestCase` was defined twice, in the same namespace, with two
 * different layouts:
 *
 *   benchmarks.hpp:73   112 bytes, `expected` is a std::variant, has tags/validate()
 *   ab_testing.hpp:89    72 bytes, `expected` is a plain std::string, neither of those
 *
 * Both had an inline two-string constructor, so both emitted the same mangled symbol
 * for the implicit copy constructor:
 *
 *   _ZN7agenkit10evaluation8TestCaseC2ERKS1_   (weak external, in both objects)
 *
 * The linker coalesced them with no diagnostic, keeping one and discarding the other.
 * Any binary containing both then ran one type's copy constructor over the other type's
 * storage. A program that used a benchmark *and* an A/B test linked cleanly and aborted
 * in the allocator:
 *
 *   malloc: *** error for object 0x16fdfe740: pointer being freed was not allocated
 *
 * Both link orders aborted, so this was undefined behaviour either way rather than
 * order-dependent luck.
 *
 * No translation unit in the repo included both headers — verified with `c++ -MM` over
 * every TU that included either — and a static archive pulls only the object it needs,
 * so every existing binary happened to get a self-consistent TestCase. 68/68 ctest
 * green, with the corruption reachable only from user code.
 *
 * ## Why this driver includes neither evaluation header
 *
 * The bug was invisible to both the compiler and the linker, so a test that only fails
 * to *compile* when the duplicate returns is checking a different thing than the one
 * that shipped. This TU therefore includes only gtest and forward declarations, and the
 * two header views live in separate TUs (testcase_odr_ab_tu.cpp,
 * testcase_odr_benchmarks_tu.cpp). Restoring the duplicate then still builds, and these
 * assertions fail at runtime the way the original defect did — 72 against 112.
 */

#include <gtest/gtest.h>

#include <cstddef>
#include <string>

namespace agenkit_test_odr {

// Defined in testcase_odr_ab_tu.cpp (includes only ab_testing.hpp).
std::size_t ab_tu_sizeof_testcase();
std::string ab_tu_copy_input();

// Defined in testcase_odr_benchmarks_tu.cpp (includes only benchmarks.hpp).
std::size_t benchmarks_tu_sizeof_testcase();
std::size_t benchmarks_tu_copy_tag_count();
bool benchmarks_tu_copy_validates();
bool benchmarks_tu_expected_is_variant();

// Defined in testcase_odr_ab_tu.cpp; proves ABTest's own signatures take the canonical
// type. This is the seam that made #829 unfixable as filed: its recommended fix is
// "score via TestCase::validate", but the TestCase ABTest accepted had no validate().
bool ab_tu_testcase_supports_validate();
bool ab_tu_testcase_supports_validator_function();

}  // namespace agenkit_test_odr

// The two TUs must agree on the layout. Before the fix these were 72 and 112, and this
// assertion is the one that fires at runtime when the duplicate is reintroduced.
TEST(TestCaseODR, BothHeadersAgreeOnLayout) {
    EXPECT_EQ(agenkit_test_odr::ab_tu_sizeof_testcase(),
              agenkit_test_odr::benchmarks_tu_sizeof_testcase())
        << "ab_testing.hpp and benchmarks.hpp disagree on sizeof(TestCase); they are "
           "defining two different types under one name (#831)";
}

// Copying across the TU boundary is the operation that actually corrupted the heap.
// Under the coalesced 72-byte constructor the copy's `tags` vector and `expected`
// variant were never constructed, and destroying it freed pointers never allocated.
TEST(TestCaseODR, CopyingAcrossTranslationUnitsDoesNotCorruptTheHeap) {
    EXPECT_EQ(agenkit_test_odr::ab_tu_copy_input(), "What is 2+2?");
    EXPECT_EQ(agenkit_test_odr::benchmarks_tu_copy_tag_count(), 2u);
    EXPECT_TRUE(agenkit_test_odr::benchmarks_tu_copy_validates());
}

// ab_testing.hpp must expose the canonical TestCase, not a lookalike. `validate()` and
// the validator-function constructor exist only on the benchmarks.hpp struct, so a
// TestCase reached through ab_testing.hpp having them is what pins the unification.
TEST(TestCaseODR, ABTestingHeaderExposesTheCanonicalTestCase) {
    EXPECT_TRUE(agenkit_test_odr::ab_tu_testcase_supports_validate())
        << "TestCase reached through ab_testing.hpp must carry the docs/DEFAULTS.md "
           "substring contract";
    EXPECT_TRUE(agenkit_test_odr::ab_tu_testcase_supports_validator_function())
        << "TestCase reached through ab_testing.hpp must support the validator-function "
           "variant, which is what #829 needs to score `expected`";
    EXPECT_TRUE(agenkit_test_odr::benchmarks_tu_expected_is_variant());
}
