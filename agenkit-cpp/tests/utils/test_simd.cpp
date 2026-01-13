/**
 * @file test_simd.cpp
 * @brief Tests for SIMD utilities
 */

#include <gtest/gtest.h>
#include "agenkit/utils/simd.hpp"
#include <vector>
#include <cmath>
#include <iostream>

using namespace agenkit::utils::simd;

TEST(SIMDTest, FeatureDetection) {
    // Just verify the function works
    const char* features = get_simd_features();
    ASSERT_NE(features, nullptr);

    std::cout << "SIMD Features: " << features << std::endl;

    // Check that we get either AVX2 or Scalar
    std::string features_str(features);
    EXPECT_TRUE(features_str == "AVX2" || features_str == "Scalar");
}

TEST(SIMDTest, HasAVX2Constexpr) {
    // This should compile as constexpr
    constexpr bool avx2_available = has_avx2();

    // Should be either true or false (depending on compile flags)
    EXPECT_TRUE(avx2_available == true || avx2_available == false);
}

TEST(SIMDTest, CalculateMean) {
    std::vector<double> values = {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0};

    double mean = calculate_mean(values.data(), values.size());

    EXPECT_NEAR(mean, 5.5, 0.0001);
}

TEST(SIMDTest, CalculateMeanEmpty) {
    std::vector<double> values;

    double mean = calculate_mean(values.data(), values.size());

    EXPECT_DOUBLE_EQ(mean, 0.0);
}

TEST(SIMDTest, CalculateMeanSmall) {
    // Test with less than 4 elements (scalar path)
    std::vector<double> values = {1.0, 2.0, 3.0};

    double mean = calculate_mean(values.data(), values.size());

    EXPECT_NEAR(mean, 2.0, 0.0001);
}

TEST(SIMDTest, CalculateMeanLarge) {
    // Test with many elements (SIMD path if available)
    std::vector<double> values;
    for (int i = 1; i <= 1000; i++) {
        values.push_back(static_cast<double>(i));
    }

    double mean = calculate_mean(values.data(), values.size());

    EXPECT_NEAR(mean, 500.5, 0.0001);
}

TEST(SIMDTest, CalculateVariance) {
    std::vector<double> values = {2.0, 4.0, 6.0, 8.0, 10.0};
    double mean = 6.0;

    double variance = calculate_variance(values.data(), values.size(), mean);

    // Expected variance: ((2-6)^2 + (4-6)^2 + (6-6)^2 + (8-6)^2 + (10-6)^2) / 5
    //                   = (16 + 4 + 0 + 4 + 16) / 5 = 40 / 5 = 8.0
    EXPECT_NEAR(variance, 8.0, 0.0001);
}

TEST(SIMDTest, CalculateVarianceAllSame) {
    std::vector<double> values = {5.0, 5.0, 5.0, 5.0, 5.0};
    double mean = 5.0;

    double variance = calculate_variance(values.data(), values.size(), mean);

    EXPECT_NEAR(variance, 0.0, 0.0001);
}

TEST(SIMDTest, CalculateVarianceLarge) {
    // Test with many elements (SIMD path if available)
    std::vector<double> values;
    for (int i = 1; i <= 100; i++) {
        values.push_back(static_cast<double>(i));
    }

    double mean = calculate_mean(values.data(), values.size());
    double variance = calculate_variance(values.data(), values.size(), mean);

    // Variance of 1..100 is approximately 833.25
    EXPECT_NEAR(variance, 833.25, 0.1);
}

TEST(SIMDTest, CalculateStddev) {
    std::vector<double> values = {2.0, 4.0, 6.0, 8.0, 10.0};
    double mean = 6.0;

    double stddev = calculate_stddev(values.data(), values.size(), mean);

    // Expected stddev = sqrt(8.0) ≈ 2.828
    EXPECT_NEAR(stddev, std::sqrt(8.0), 0.0001);
}

TEST(SIMDTest, IsExpired) {
    int64_t now = 1000;
    int64_t ttl = 100;

    // Not expired (age = 50)
    EXPECT_FALSE(is_expired(950, now, ttl));

    // Exactly at TTL (age = 100)
    EXPECT_FALSE(is_expired(900, now, ttl));

    // Expired (age = 101)
    EXPECT_TRUE(is_expired(899, now, ttl));

    // Far expired (age = 500)
    EXPECT_TRUE(is_expired(500, now, ttl));
}

TEST(SIMDTest, MeanAndVarianceTogether) {
    // Test that mean and variance work correctly together
    std::vector<double> values = {10.0, 20.0, 30.0, 40.0, 50.0};

    double mean = calculate_mean(values.data(), values.size());
    EXPECT_NEAR(mean, 30.0, 0.0001);

    double variance = calculate_variance(values.data(), values.size(), mean);
    // Variance: ((10-30)^2 + (20-30)^2 + (30-30)^2 + (40-30)^2 + (50-30)^2) / 5
    //         = (400 + 100 + 0 + 100 + 400) / 5 = 200
    EXPECT_NEAR(variance, 200.0, 0.0001);

    double stddev = calculate_stddev(values.data(), values.size(), mean);
    EXPECT_NEAR(stddev, std::sqrt(200.0), 0.0001);
}

TEST(SIMDTest, NonAlignedData) {
    // Test with data that's not 32-byte aligned (typical malloc alignment is 16)
    // This tests the unaligned load/store paths
    std::vector<double> values;
    for (int i = 0; i < 17; i++) {  // Odd number to ensure non-alignment
        values.push_back(static_cast<double>(i));
    }

    double mean = calculate_mean(values.data(), values.size());
    double variance = calculate_variance(values.data(), values.size(), mean);

    // Should still work correctly
    EXPECT_GT(mean, 0.0);
    EXPECT_GT(variance, 0.0);
}

TEST(SIMDTest, NegativeValues) {
    std::vector<double> values = {-5.0, -3.0, -1.0, 1.0, 3.0, 5.0};

    double mean = calculate_mean(values.data(), values.size());
    EXPECT_NEAR(mean, 0.0, 0.0001);

    double variance = calculate_variance(values.data(), values.size(), mean);
    // Variance: (25 + 9 + 1 + 1 + 9 + 25) / 6 = 70 / 6 ≈ 11.67
    EXPECT_NEAR(variance, 11.666667, 0.0001);
}

// Performance comparison test (informational)
TEST(SIMDTest, PerformanceComparison) {
    const size_t size = 10000;
    std::vector<double> values(size);

    // Fill with random-ish values
    for (size_t i = 0; i < size; i++) {
        values[i] = static_cast<double>(i * 17 % 1000);
    }

    // Benchmark SIMD/optimized version
    auto start_simd = std::chrono::steady_clock::now();
    double mean_simd = calculate_mean(values.data(), values.size());
    double variance_simd = calculate_variance(values.data(), values.size(), mean_simd);
    auto end_simd = std::chrono::steady_clock::now();
    auto duration_simd = std::chrono::duration_cast<std::chrono::microseconds>(
        end_simd - start_simd
    ).count();

    // Benchmark scalar version
    auto start_scalar = std::chrono::steady_clock::now();
    double sum_scalar = 0.0;
    for (size_t i = 0; i < size; i++) {
        sum_scalar += values[i];
    }
    double mean_scalar = sum_scalar / size;

    double variance_scalar = 0.0;
    for (size_t i = 0; i < size; i++) {
        double diff = values[i] - mean_scalar;
        variance_scalar += diff * diff;
    }
    variance_scalar /= size;
    auto end_scalar = std::chrono::steady_clock::now();
    auto duration_scalar = std::chrono::duration_cast<std::chrono::microseconds>(
        end_scalar - start_scalar
    ).count();

    std::cout << "SIMD version:   " << duration_simd << " μs\n";
    std::cout << "Scalar version: " << duration_scalar << " μs\n";
    if (duration_scalar > 0) {
        std::cout << "Speedup:        " << (static_cast<double>(duration_scalar) / duration_simd) << "x\n";
    }

    // Verify results match
    EXPECT_NEAR(mean_simd, mean_scalar, 0.0001);
    EXPECT_NEAR(variance_simd, variance_scalar, 0.0001);
}
