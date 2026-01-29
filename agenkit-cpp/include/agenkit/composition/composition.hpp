/**
 * @file composition.hpp
 * @brief Agent composition patterns
 *
 * Simple, lightweight building blocks for composing agents:
 * - Sequential: Execute agents in order (pipeline)
 * - Parallel: Execute agents concurrently (ensemble)
 * - Conditional: Route to different agents based on conditions
 * - Fallback: Try agents in order until one succeeds (fault tolerance)
 *
 * These are minimal composition primitives. For richer agent patterns
 * with advanced features, see the patterns module.
 */

#ifndef AGENKIT_COMPOSITION_HPP
#define AGENKIT_COMPOSITION_HPP

#include "agenkit/composition/sequential.hpp"
#include "agenkit/composition/parallel.hpp"
#include "agenkit/composition/conditional.hpp"
#include "agenkit/composition/fallback.hpp"

#endif // AGENKIT_COMPOSITION_HPP
