#pragma once

// Local includes
#include <Task/BasicTask.h>
#include <Message/Request.h>

// Third-party includes
#include <gpiod.hpp>

// Standard library includes
#include <string>
#include <memory>

namespace MCPIntegration {

/**
 * @brief MCP tool for GPIO pin control
 *
 * This tool handles GPIO pin control requests from MCP clients,
 * allowing setting pin direction and values.
 */
class GPIOTask : public MCP::ProcessCallToolRequest {
public:
    static constexpr const char* TOOL_NAME = "gpio_control";
    static constexpr const char* TOOL_DESCRIPTION = "Control GPIO pins on Raspberry Pi. Set pin direction and value.";
    static constexpr const char* TOOL_INPUT_SCHEMA = R"({
        "type": "object",
        "properties": {
            "pin": {
                "type": "integer",
                "description": "GPIO pin number",
                "minimum": 0,
                "maximum": 40
            },
            "direction": {
                "type": "string",
                "enum": ["input", "output"],
                "description": "Pin direction"
            },
            "value": {
                "type": "integer",
                "description": "Pin value (0 or 1) for output pins",
                "minimum": 0,
                "maximum": 1
            }
        },
        "required": ["pin", "direction"]
    })";
    static constexpr const char* TOOL_ARGUMENT_PIN = "pin";
    static constexpr const char* TOOL_ARGUMENT_DIRECTION = "direction";
    static constexpr const char* TOOL_ARGUMENT_VALUE = "value";

    GPIOTask(const std::shared_ptr<MCP::Request>& spRequest);

    std::shared_ptr<CMCPTask> Clone() const override;
    int Execute() override;
    int Cancel() override;

private:
    std::unique_ptr<gpiod::chip> chip;
    std::unordered_map<int, gpiod::line> active_lines;
};

} // namespace MCPIntegration