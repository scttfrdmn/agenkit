/**
 * @file weather_tool.hpp
 * @brief Simulated weather lookup tool
 */

#ifndef AGENKIT_EXAMPLES_WEATHER_TOOL_HPP
#define AGENKIT_EXAMPLES_WEATHER_TOOL_HPP

#include "agenkit/patterns/react.hpp"
#include <string>
#include <unordered_map>
#include <algorithm>
#include <cctype>

namespace agenkit {
namespace examples {

/**
 * @brief Simulated weather lookup tool
 *
 * Provides fake weather data for demonstration purposes.
 * In production, this would call a real weather API.
 *
 * Supported cities:
 * - Paris, London, New York, Tokyo, Sydney, Berlin, Mumbai, Toronto, Dubai, Singapore
 */
class WeatherTool : public patterns::Tool {
public:
    WeatherTool() {
        // Simulated weather data
        weather_data_ = {
            {"paris", "15°C, partly cloudy with light winds"},
            {"london", "12°C, overcast with occasional drizzle"},
            {"new york", "8°C, clear skies and sunny"},
            {"newyork", "8°C, clear skies and sunny"},
            {"tokyo", "18°C, mostly sunny with light breeze"},
            {"sydney", "22°C, warm and sunny"},
            {"berlin", "10°C, cloudy with scattered showers"},
            {"mumbai", "28°C, hot and humid"},
            {"toronto", "5°C, cold with snow flurries"},
            {"dubai", "32°C, hot and sunny"},
            {"singapore", "30°C, tropical heat with high humidity"}
        };
    }

    std::string name() const override {
        return "weather";
    }

    std::string description() const override {
        return "Gets current weather for a city. Supported cities: Paris, London, "
               "New York, Tokyo, Sydney, Berlin, Mumbai, Toronto, Dubai, Singapore. "
               "Example: 'Paris' or 'New York'";
    }

    patterns::ToolResult execute(const std::string& input) override {
        // Normalize input (lowercase, trim)
        std::string city = input;
        std::transform(city.begin(), city.end(), city.begin(), ::tolower);

        // Trim whitespace
        city.erase(0, city.find_first_not_of(" \t\r\n"));
        city.erase(city.find_last_not_of(" \t\r\n") + 1);

        // Remove spaces for compound names
        std::string city_no_space = city;
        city_no_space.erase(std::remove(city_no_space.begin(), city_no_space.end(), ' '),
                           city_no_space.end());

        // Look up weather
        auto it = weather_data_.find(city);
        if (it == weather_data_.end()) {
            it = weather_data_.find(city_no_space);
        }

        if (it != weather_data_.end()) {
            return patterns::ToolResult::ok(
                "Weather in " + capitalize(input) + ": " + it->second
            );
        }

        return patterns::ToolResult::error(
            "Weather data not available for '" + input + "'. "
            "Supported cities: Paris, London, New York, Tokyo, Sydney, "
            "Berlin, Mumbai, Toronto, Dubai, Singapore"
        );
    }

private:
    std::unordered_map<std::string, std::string> weather_data_;

    std::string capitalize(const std::string& str) const {
        std::string result = str;
        bool capitalize_next = true;

        for (char& c : result) {
            if (std::isalpha(c)) {
                c = capitalize_next ? std::toupper(c) : std::tolower(c);
                capitalize_next = false;
            } else if (std::isspace(c)) {
                capitalize_next = true;
            }
        }

        return result;
    }
};

} // namespace examples
} // namespace agenkit

#endif // AGENKIT_EXAMPLES_WEATHER_TOOL_HPP
