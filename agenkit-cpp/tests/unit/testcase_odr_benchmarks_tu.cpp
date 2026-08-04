/**
 * @file testcase_odr_benchmarks_tu.cpp
 * @brief Half of the #831 ODR regression test: the benchmarks.hpp view of TestCase.
 *
 * See testcase_odr_ab_tu.cpp for why the two includes must live in separate
 * translation units.
 */

#include "agenkit/evaluation/benchmarks.hpp"

#include <cstddef>
#include <string>

namespace agenkit_test_odr {

std::size_t benchmarks_tu_sizeof_testcase() {
    return sizeof(agenkit::evaluation::TestCase);
}

// Copies a TestCase carrying members the ab_testing.hpp struct did not have (`tags`,
// and a variant rather than a plain string `expected`). Those are the bytes past offset
// 72 that the coalesced 72-byte copy constructor never touched, leaving the copy's
// std::vector and std::variant uninitialised.
std::size_t benchmarks_tu_copy_tag_count() {
    agenkit::evaluation::TestCase original("What is 2+2?", "4");
    original.tags = {"math", "reasoning"};
    agenkit::evaluation::TestCase copy(original);
    return copy.tags.size();
}

// validate() only exists on this struct, so calling it through a TestCase that a
// sibling TU also constructs pins down that both TUs agree on the type.
bool benchmarks_tu_copy_validates() {
    agenkit::evaluation::TestCase original("What is 2+2?", "4");
    agenkit::evaluation::TestCase copy(original);
    return copy.validate("The answer is 4.");
}

// The canonical `expected` is a std::variant, not a plain std::string. Checked from
// this TU because it is the one whose header defines the canonical type either way.
bool benchmarks_tu_expected_is_variant() {
    const agenkit::evaluation::TestCase test_case("What is 2+2?", "4");
    return std::holds_alternative<std::string>(test_case.expected);
}

}  // namespace agenkit_test_odr
