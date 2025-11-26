/**
 * @file test_result.cpp
 * @brief Tests for Result<T, E> type
 */

#include <gtest/gtest.h>
#include "agenkit/core/result.hpp"
#include <string>

using namespace agenkit::core;

TEST(ResultTest, CreateOkResult) {
    auto result = Result<int, std::string>::ok(42);

    EXPECT_TRUE(result.is_ok());
    EXPECT_FALSE(result.is_err());
    EXPECT_EQ(result.unwrap(), 42);
}

TEST(ResultTest, CreateErrResult) {
    auto result = Result<int, std::string>::err("error message");

    EXPECT_FALSE(result.is_ok());
    EXPECT_TRUE(result.is_err());
    EXPECT_EQ(result.unwrap_err(), "error message");
}

TEST(ResultTest, UnwrapOnOk) {
    auto result = Result<std::string, int>::ok("success");

    EXPECT_EQ(result.unwrap(), "success");
}

TEST(ResultTest, UnwrapOnErrThrows) {
    auto result = Result<int, std::string>::err("error");

    EXPECT_THROW(result.unwrap(), std::logic_error);
}

TEST(ResultTest, UnwrapErrOnErr) {
    auto result = Result<int, std::string>::err("error");

    EXPECT_EQ(result.unwrap_err(), "error");
}

TEST(ResultTest, UnwrapErrOnOkThrows) {
    auto result = Result<int, std::string>::ok(42);

    EXPECT_THROW(result.unwrap_err(), std::logic_error);
}

TEST(ResultTest, UnwrapOrWithOk) {
    auto result = Result<int, std::string>::ok(42);

    EXPECT_EQ(result.unwrap_or(0), 42);
}

TEST(ResultTest, UnwrapOrWithErr) {
    auto result = Result<int, std::string>::err("error");

    EXPECT_EQ(result.unwrap_or(99), 99);
}

TEST(ResultTest, WorksWithMoveOnlyTypes) {
    auto result = Result<std::unique_ptr<int>, std::string>::ok(
        std::make_unique<int>(42)
    );

    EXPECT_TRUE(result.is_ok());
    EXPECT_EQ(*result.unwrap(), 42);
}

TEST(ResultTest, WorksWithComplexTypes) {
    struct Data {
        int value;
        std::string name;
    };

    auto result = Result<Data, std::string>::ok(Data{42, "test"});

    EXPECT_TRUE(result.is_ok());
    EXPECT_EQ(result.unwrap().value, 42);
    EXPECT_EQ(result.unwrap().name, "test");
}
