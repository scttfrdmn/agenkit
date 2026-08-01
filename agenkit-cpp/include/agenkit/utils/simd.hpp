/**
 * @file simd.hpp
 * @brief SIMD (Single Instruction Multiple Data) utilities for performance optimization
 *
 * Provides AVX2 vectorization utilities with automatic fallback to scalar implementations
 * on platforms that don't support AVX2. Enables 4-8x speedup for numerical operations.
 */

#ifndef AGENKIT_UTILS_SIMD_HPP
#define AGENKIT_UTILS_SIMD_HPP

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <algorithm>

// Detect AVX2 support at compile time
#if defined(__AVX2__) || (defined(_MSC_VER) && defined(__AVX2__))
    #define AGENKIT_HAS_AVX2 1
    #include <immintrin.h>  // AVX2 intrinsics
#else
    #define AGENKIT_HAS_AVX2 0
#endif

namespace agenkit {
namespace utils {
namespace simd {

/**
 * @brief Check if AVX2 is available at compile time
 * @return True if AVX2 support is compiled in
 */
constexpr bool has_avx2() {
    return AGENKIT_HAS_AVX2;
}

#if AGENKIT_HAS_AVX2

/**
 * @brief Horizontal sum of 4 doubles in AVX2 register
 *
 * Efficiently sums all 4 elements of a __m256d register.
 *
 * @param vec AVX2 register with 4 doubles
 * @return Sum of all 4 elements
 */
inline double horizontal_sum_pd(__m256d vec) {
    // Horizontal add: [a,b,c,d] -> [a+b, c+d, a+b, c+d]
    __m256d hadd = _mm256_hadd_pd(vec, vec);

    // Extract high 128 bits
    __m128d high = _mm256_extractf128_pd(hadd, 1);

    // Extract low 128 bits
    __m128d low = _mm256_castpd256_pd128(hadd);

    // Add high and low
    __m128d sum128 = _mm_add_pd(high, low);

    // Extract result
    return _mm_cvtsd_f64(sum128);
}

/**
 * @brief Horizontal sum of 4 64-bit integers in AVX2 register
 *
 * @param vec AVX2 register with 4 int64_t values
 * @return Sum of all 4 elements
 */
inline int64_t horizontal_sum_epi64(__m256i vec) {
    // Extract elements into array
    int64_t temp[4];
    _mm256_storeu_si256(reinterpret_cast<__m256i*>(temp), vec);
    return temp[0] + temp[1] + temp[2] + temp[3];
}

/**
 * @brief Load 4 doubles from unaligned memory
 *
 * @param ptr Pointer to array of at least 4 doubles
 * @return AVX2 register with 4 loaded doubles
 */
inline __m256d load_4_doubles(const double* ptr) {
    return _mm256_loadu_pd(ptr);
}

/**
 * @brief Store 4 doubles to unaligned memory
 *
 * @param ptr Pointer to array of at least 4 doubles
 * @param vec AVX2 register with 4 doubles
 */
inline void store_4_doubles(double* ptr, __m256d vec) {
    _mm256_storeu_pd(ptr, vec);
}

/**
 * @brief Set all 4 doubles in register to same value
 *
 * @param value Value to broadcast
 * @return AVX2 register with value in all 4 positions
 */
inline __m256d set1_pd(double value) {
    return _mm256_set1_pd(value);
}

/**
 * @brief Vectorized variance calculation using AVX2
 *
 * Computes variance of array of doubles using SIMD instructions.
 *
 * @param values Array of doubles
 * @param size Number of elements
 * @param mean Pre-computed mean value
 * @return Variance of the values
 */
inline double variance_avx2(const double* values, size_t size, double mean) {
    __m256d mean_vec = _mm256_set1_pd(mean);
    __m256d variance_vec = _mm256_setzero_pd();

    size_t i = 0;

    // Process 4 elements at a time
    for (; i + 4 <= size; i += 4) {
        __m256d vals = _mm256_loadu_pd(&values[i]);
        __m256d diff = _mm256_sub_pd(vals, mean_vec);
        __m256d sq = _mm256_mul_pd(diff, diff);
        variance_vec = _mm256_add_pd(variance_vec, sq);
    }

    // Horizontal sum of variance_vec
    double variance = horizontal_sum_pd(variance_vec);

    // Handle remaining elements (scalar)
    for (; i < size; i++) {
        double diff = values[i] - mean;
        variance += diff * diff;
    }

    return variance / static_cast<double>(size);
}

/**
 * @brief Vectorized mean calculation using AVX2
 *
 * Computes mean of array of doubles using SIMD instructions.
 *
 * @param values Array of doubles
 * @param size Number of elements
 * @return Mean of the values
 */
inline double mean_avx2(const double* values, size_t size) {
    if (size == 0) return 0.0;

    __m256d sum_vec = _mm256_setzero_pd();

    size_t i = 0;

    // Process 4 elements at a time
    for (; i + 4 <= size; i += 4) {
        __m256d vals = _mm256_loadu_pd(&values[i]);
        sum_vec = _mm256_add_pd(sum_vec, vals);
    }

    // Horizontal sum
    double sum = horizontal_sum_pd(sum_vec);

    // Handle remaining elements (scalar)
    for (; i < size; i++) {
        sum += values[i];
    }

    return sum / static_cast<double>(size);
}

#endif // AGENKIT_HAS_AVX2

/**
 * @brief Calculate variance (with automatic SIMD selection)
 *
 * Uses AVX2 if available, otherwise falls back to scalar implementation.
 *
 * @param values Array of doubles
 * @param size Number of elements
 * @param mean Pre-computed mean value
 * @return Variance of the values
 */
inline double calculate_variance(const double* values, size_t size, double mean) {
#if AGENKIT_HAS_AVX2
    return variance_avx2(values, size, mean);
#else
    // Scalar fallback
    double variance = 0.0;
    for (size_t i = 0; i < size; i++) {
        double diff = values[i] - mean;
        variance += diff * diff;
    }
    return variance / static_cast<double>(size);
#endif
}

/**
 * @brief Calculate mean (with automatic SIMD selection)
 *
 * Uses AVX2 if available, otherwise falls back to scalar implementation.
 *
 * @param values Array of doubles
 * @param size Number of elements
 * @return Mean of the values
 */
inline double calculate_mean(const double* values, size_t size) {
#if AGENKIT_HAS_AVX2
    return mean_avx2(values, size);
#else
    // Scalar fallback
    if (size == 0) return 0.0;
    double sum = 0.0;
    for (size_t i = 0; i < size; i++) {
        sum += values[i];
    }
    return sum / static_cast<double>(size);
#endif
}

/**
 * @brief Calculate standard deviation (with automatic SIMD selection)
 *
 * @param values Array of doubles
 * @param size Number of elements
 * @param mean Pre-computed mean value
 * @return Standard deviation of the values
 */
inline double calculate_stddev(const double* values, size_t size, double mean) {
    return std::sqrt(calculate_variance(values, size, mean));
}

/**
 * @brief Check if timestamp is expired (batch SIMD-friendly function)
 *
 * This is a helper for checking multiple timestamps against a threshold.
 * The actual SIMD implementation will be in the memory expiration code.
 *
 * @param timestamp Timestamp to check (as int64_t)
 * @param now Current time (as int64_t)
 * @param ttl Time-to-live threshold (as int64_t)
 * @return True if expired
 */
inline bool is_expired(int64_t timestamp, int64_t now, int64_t ttl) {
    return (now - timestamp) > ttl;
}

/**
 * @brief Get compiler and feature information string
 *
 * Returns a string describing the SIMD capabilities compiled in.
 *
 * @return Feature string (e.g., "AVX2" or "Scalar")
 */
inline const char* get_simd_features() {
#if AGENKIT_HAS_AVX2
    return "AVX2";
#else
    return "Scalar";
#endif
}

} // namespace simd
} // namespace utils
} // namespace agenkit

#endif // AGENKIT_UTILS_SIMD_HPP
