/**
 * @file result.hpp
 * @brief Result type for error handling (similar to Rust's Result<T, E>)
 *
 * Provides a type-safe way to return either a value or an error.
 * In C++23, std::expected can be used instead.
 */

#ifndef AGENKIT_CORE_RESULT_HPP
#define AGENKIT_CORE_RESULT_HPP

#include <variant>
#include <stdexcept>
#include <utility>

namespace agenkit {
namespace core {

/**
 * @brief Result type for operations that may fail
 *
 * A Result<T, E> can hold either:
 * - Ok(T): A successful value of type T
 * - Err(E): An error of type E
 *
 * This is similar to Rust's Result<T, E> or C++23's std::expected.
 *
 * @tparam T Value type for success case
 * @tparam E Error type for failure case
 *
 * @example
 * @code
 * Result<int, std::string> divide(int a, int b) {
 *     if (b == 0) {
 *         return Result<int, std::string>::err("division by zero");
 *     }
 *     return Result<int, std::string>::ok(a / b);
 * }
 *
 * auto result = divide(10, 2);
 * if (result.is_ok()) {
 *     std::cout << "Result: " << result.unwrap() << std::endl;
 * } else {
 *     std::cout << "Error: " << result.unwrap_err() << std::endl;
 * }
 * @endcode
 */
template<typename T, typename E>
class Result {
public:
    /**
     * @brief Create a successful result
     * @param value Success value
     * @return Result containing the value
     */
    static Result ok(T value) {
        return Result(std::move(value), true);
    }

    /**
     * @brief Create an error result
     * @param error Error value
     * @return Result containing the error
     */
    static Result err(E error) {
        return Result(std::move(error), false);
    }

    /**
     * @brief Check if result is ok
     * @return true if ok, false if error
     */
    bool is_ok() const {
        return std::holds_alternative<T>(value_);
    }

    /**
     * @brief Check if result is error
     * @return true if error, false if ok
     */
    bool is_err() const {
        return std::holds_alternative<E>(value_);
    }

    /**
     * @brief Get value (throws if error)
     * @return Reference to contained value
     * @throws std::logic_error if result is error
     */
    T& unwrap() {
        if (is_err()) {
            throw std::logic_error("called unwrap() on an error Result");
        }
        return std::get<T>(value_);
    }

    /**
     * @brief Get value (const version)
     * @return Const reference to contained value
     * @throws std::logic_error if result is error
     */
    const T& unwrap() const {
        if (is_err()) {
            throw std::logic_error("called unwrap() on an error Result");
        }
        return std::get<T>(value_);
    }

    /**
     * @brief Get error (throws if ok)
     * @return Reference to contained error
     * @throws std::logic_error if result is ok
     */
    E& unwrap_err() {
        if (is_ok()) {
            throw std::logic_error("called unwrap_err() on an ok Result");
        }
        return std::get<E>(value_);
    }

    /**
     * @brief Get error (const version)
     * @return Const reference to contained error
     * @throws std::logic_error if result is ok
     */
    const E& unwrap_err() const {
        if (is_ok()) {
            throw std::logic_error("called unwrap_err() on an ok Result");
        }
        return std::get<E>(value_);
    }

    /**
     * @brief Get value or default
     * @param default_value Default value if error
     * @return Value if ok, otherwise default_value
     */
    T unwrap_or(T default_value) const {
        if (is_ok()) {
            return std::get<T>(value_);
        }
        return default_value;
    }

private:
    std::variant<T, E> value_;

    Result(T value, bool /* ok_marker */)
        : value_(std::move(value))
    {}

    Result(E error, bool /* err_marker */)
        : value_(std::move(error))
    {}
};

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_RESULT_HPP
