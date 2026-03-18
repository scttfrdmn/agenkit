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
#include <optional>

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
        return Result(OkTag{}, std::move(value));
    }

    /**
     * @brief Create an error result
     * @param error Error value
     * @return Result containing the error
     */
    static Result err(E error) {
        return Result(ErrTag{}, std::move(error));
    }

    /**
     * @brief Check if result is ok
     * @return true if ok, false if error
     */
    bool is_ok() const {
        return value_.index() == 0;
    }

    /**
     * @brief Check if result is error
     * @return true if error, false if ok
     */
    bool is_err() const {
        return value_.index() == 1;
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
        return std::get<0>(value_);
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
        return std::get<0>(value_);
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
        return std::get<1>(value_);
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
        return std::get<1>(value_);
    }

    /**
     * @brief Get value or default
     * @param default_value Default value if error
     * @return Value if ok, otherwise default_value
     */
    T unwrap_or(T default_value) const {
        if (is_ok()) {
            return std::get<0>(value_);
        }
        return default_value;
    }

private:
    // Tag types for unambiguous construction even when T == E
    struct OkTag {};
    struct ErrTag {};

    std::variant<T, E> value_;

    Result(OkTag, T value)
        : value_(std::in_place_index<0>, std::move(value))
    {}

    Result(ErrTag, E error)
        : value_(std::in_place_index<1>, std::move(error))
    {}
};

/**
 * @brief Specialization of Result for void type
 *
 * This specialization allows Result<void, E> to represent operations
 * that don't return a value but may fail.
 *
 * @tparam E Error type for failure case
 *
 * @example
 * @code
 * Result<void, std::string> validate(int value) {
 *     if (value < 0) {
 *         return Result<void, std::string>::err("value must be positive");
 *     }
 *     return Result<void, std::string>::ok();
 * }
 * @endcode
 */
template<typename E>
class Result<void, E> {
public:
    /**
     * @brief Create a successful result (void)
     * @return Result indicating success
     */
    static Result ok() {
        return Result(true);
    }

    /**
     * @brief Create an error result
     * @param error Error value
     * @return Result containing the error
     */
    static Result err(E error) {
        return Result(std::move(error));
    }

    /**
     * @brief Check if result is ok
     * @return true if ok, false if error
     */
    bool is_ok() const {
        return !error_.has_value();
    }

    /**
     * @brief Check if result is error
     * @return true if error, false if ok
     */
    bool is_err() const {
        return error_.has_value();
    }

    /**
     * @brief Throw if result is error (void version)
     * @throws std::logic_error if result is error
     */
    void unwrap() const {
        if (is_err()) {
            throw std::logic_error("called unwrap() on an error Result");
        }
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
        return error_.value();
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
        return error_.value();
    }

private:
    std::optional<E> error_;

    explicit Result(bool /* ok_marker */)
        : error_(std::nullopt)
    {}

    explicit Result(E error)
        : error_(std::move(error))
    {}
};

} // namespace core
} // namespace agenkit

#endif // AGENKIT_CORE_RESULT_HPP
