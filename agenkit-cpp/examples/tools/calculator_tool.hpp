/**
 * @file calculator_tool.hpp
 * @brief Calculator tool for basic math operations
 */

#ifndef AGENKIT_EXAMPLES_CALCULATOR_TOOL_HPP
#define AGENKIT_EXAMPLES_CALCULATOR_TOOL_HPP

#include "agenkit/patterns/react.hpp"
#include <string>
#include <cmath>
#include <sstream>
#include <cctype>

namespace agenkit {
namespace examples {

/**
 * @brief Tool for basic mathematical calculations
 *
 * Supports: addition, subtraction, multiplication, division, percentages
 *
 * Example inputs:
 * - "15 + 25"
 * - "100 - 35"
 * - "12 * 8"
 * - "144 / 12"
 * - "15% of 80"
 * - "80 * 0.15" (for percentage)
 */
class CalculatorTool : public patterns::Tool {
public:
    std::string name() const override {
        return "calculator";
    }

    std::string description() const override {
        return "Performs basic math operations: addition (+), subtraction (-), "
               "multiplication (*), division (/), and percentages (% of). "
               "Example: '15 + 25' or '15% of 80'";
    }

    patterns::ToolResult execute(const std::string& input) override {
        try {
            // Try percentage calculation first
            if (input.find('%') != std::string::npos) {
                return calculate_percentage(input);
            }

            // Parse simple binary operations
            double a, b;
            char op;

            std::istringstream iss(input);
            if (!(iss >> a >> op >> b)) {
                return patterns::ToolResult::error(
                    "Invalid format. Use: 'number operator number' (e.g., '5 + 3')"
                );
            }

            double result;
            switch (op) {
                case '+': result = a + b; break;
                case '-': result = a - b; break;
                case '*': result = a * b; break;
                case '/':
                    if (b == 0) {
                        return patterns::ToolResult::error("Cannot divide by zero");
                    }
                    result = a / b;
                    break;
                default:
                    return patterns::ToolResult::error(
                        "Unknown operator '" + std::string(1, op) + "'. Use: +, -, *, /"
                    );
            }

            // Format result nicely
            std::ostringstream oss;
            if (std::floor(result) == result && std::abs(result) < 1e10) {
                // Integer result
                oss << static_cast<long long>(result);
            } else {
                // Decimal result
                oss.precision(2);
                oss << std::fixed << result;
            }

            return patterns::ToolResult::ok(oss.str());

        } catch (const std::exception& e) {
            return patterns::ToolResult::error(
                std::string("Calculation error: ") + e.what()
            );
        }
    }

private:
    patterns::ToolResult calculate_percentage(const std::string& input) {
        // Parse "X% of Y" format
        double percent, value;
        char percent_sign;
        std::string of_word;

        std::istringstream iss(input);
        if (!(iss >> percent >> percent_sign >> of_word >> value) ||
            percent_sign != '%' || of_word != "of") {
            return patterns::ToolResult::error(
                "Invalid percentage format. Use: 'X% of Y' (e.g., '15% of 80')"
            );
        }

        double result = (percent / 100.0) * value;

        std::ostringstream oss;
        oss.precision(2);
        oss << std::fixed << result;

        return patterns::ToolResult::ok(oss.str());
    }
};

} // namespace examples
} // namespace agenkit

#endif // AGENKIT_EXAMPLES_CALCULATOR_TOOL_HPP
