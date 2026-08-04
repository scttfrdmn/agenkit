/**
 * @file testcase_odr_ab_tu.cpp
 * @brief Half of the #831 ODR regression test: the ab_testing.hpp view of TestCase.
 *
 * This translation unit includes **only** ab_testing.hpp, and its sibling
 * testcase_odr_benchmarks_tu.cpp includes **only** benchmarks.hpp. That separation is
 * the whole point: when the two headers each defined their own
 * agenkit::evaluation::TestCase, no single TU ever saw both, so the compiler never
 * emitted a redefinition error. The two layouts (72 vs 112 bytes) instead reached the
 * linker as identically-mangled weak symbols, were coalesced silently, and any binary
 * containing both TUs ran one type's copy constructor over the other type's storage.
 *
 * The capability checks below use `requires` rather than calling `validate()` directly,
 * so this file still compiles if the duplicate struct is reintroduced. Otherwise the
 * regression test would fail at compile time, which is exactly the check that did *not*
 * catch the original bug — see the header comment in test_testcase_odr.cpp.
 */

#include "agenkit/evaluation/ab_testing.hpp"

#include <cstddef>
#include <functional>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

namespace agenkit_test_odr {
namespace {

using agenkit::evaluation::TestCase;

// SFINAE rather than C++20 `requires` — this core builds at C++17
// (CMAKE_CXX_STANDARD 17).

// True only if the TestCase reachable through ab_testing.hpp has the substring
// validator. The duplicate struct did not.
template <typename T, typename = void>
struct HasValidate : std::false_type {};

template <typename T>
struct HasValidate<T, decltype(void(std::declval<const T&>().validate(std::string{})))>
    : std::true_type {};

// True only if TestCase can be built from a validator function — the std::variant
// alternative that #829 needs in order to score `expected`.
template <typename T, typename = void>
struct HasValidatorCtor : std::false_type {};

template <typename T>
struct HasValidatorCtor<
    T,
    decltype(void(T(std::string{}, std::function<bool(const std::string&)>{})))>
    : std::true_type {};

}  // namespace

std::size_t ab_tu_sizeof_testcase() {
    return sizeof(TestCase);
}

// Exercises the implicit copy constructor — the symbol that was actually coalesced.
// Under the pre-#831 layout mismatch this corrupted the heap (SIGABRT in the
// allocator, "pointer being freed was not allocated").
std::string ab_tu_copy_input() {
    TestCase original("What is 2+2?", "4");
    TestCase copy(original);
    return copy.input;
}

namespace {

// Tag dispatch rather than `if constexpr`: in a non-template function both branches of
// an `if constexpr` are still instantiated, so the true-branch body would fail to
// compile against the duplicate struct — turning this runtime check back into the
// compile-time one that never caught the bug.

template <typename T>
bool check_validate(std::true_type) {
    // Assert the contract, not merely the method's existence: `expected` is a fragment
    // matched case-insensitively (docs/DEFAULTS.md).
    const T test_case("What is 2+2?", "4");
    return test_case.validate("The answer is 4.") && !test_case.validate("Five.");
}

template <typename T>
bool check_validate(std::false_type) {
    return false;
}

template <typename T>
bool check_validator_ctor(std::true_type) {
    // Also confirms ABTest's own signature takes the canonical type: this vector is
    // exactly what ABTest::run accepts.
    std::vector<T> cases;
    cases.emplace_back("Capital of France?",
                       std::function<bool(const std::string&)>{
                           [](const std::string& out) {
                               return out.find("Paris") != std::string::npos;
                           }});
    return cases[0].validate("It is Paris.") && !cases[0].validate("It is Berlin.");
}

template <typename T>
bool check_validator_ctor(std::false_type) {
    return false;
}

}  // namespace

bool ab_tu_testcase_supports_validate() {
    return check_validate<TestCase>(HasValidate<TestCase>{});
}

bool ab_tu_testcase_supports_validator_function() {
    return check_validator_ctor<TestCase>(HasValidatorCtor<TestCase>{});
}

}  // namespace agenkit_test_odr
