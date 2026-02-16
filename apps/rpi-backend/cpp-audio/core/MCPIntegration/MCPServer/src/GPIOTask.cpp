#include "GPIOTask.h"

// Third-party includes
#include <Public/PublicDef.h>
#include <Public/StringHelper.h>

// Standard library includes
#include <iostream>

namespace MCPIntegration {

GPIOTask::GPIOTask(const std::shared_ptr<MCP::Request>& spRequest)
    : ProcessCallToolRequest(spRequest) {
    try {
        chip = std::make_unique<gpiod::chip>("gpiochip0");
    } catch (const std::exception& e) {
        std::cerr << "Failed to open GPIO chip: " << e.what() << std::endl;
    }
}

std::shared_ptr<MCP::CMCPTask> GPIOTask::Clone() const {
    auto spClone = std::make_shared<GPIOTask>(nullptr);
    if (spClone) {
        *spClone = *this;
    }
    return spClone;
}

int GPIOTask::Cancel() {
    return MCP::ERRNO_OK;
}

int GPIOTask::Execute() {
    int iErrCode = MCP::ERRNO_INTERNAL_ERROR;
    if (!IsValid() || !chip) {
        return iErrCode;
    }

    Json::Value jArgument;
    int pin = -1;
    std::string direction;
    int value = -1;

    auto spCallToolRequest = std::dynamic_pointer_cast<MCP::CallToolRequest>(m_spRequest);
    if (!spCallToolRequest) {
        goto PROC_END;
    }
    if (spCallToolRequest->strName.compare(TOOL_NAME) != 0) {
        goto PROC_END;
    }
    jArgument = spCallToolRequest->jArguments;

    // Validate pin
    if (!jArgument.isMember(TOOL_ARGUMENT_PIN) || !jArgument[TOOL_ARGUMENT_PIN].isInt()) {
        goto PROC_END;
    }
    pin = jArgument[TOOL_ARGUMENT_PIN].asInt();
    if (pin < 0 || pin > 40) {
        goto PROC_END;
    }

    // Validate direction
    if (!jArgument.isMember(TOOL_ARGUMENT_DIRECTION) || !jArgument[TOOL_ARGUMENT_DIRECTION].isString()) {
        goto PROC_END;
    }
    direction = jArgument[TOOL_ARGUMENT_DIRECTION].asString();
    if (direction != "input" && direction != "output") {
        goto PROC_END;
    }

    // Validate value for output
    if (direction == "output") {
        if (!jArgument.isMember(TOOL_ARGUMENT_VALUE) || !jArgument[TOOL_ARGUMENT_VALUE].isInt()) {
            goto PROC_END;
        }
        value = jArgument[TOOL_ARGUMENT_VALUE].asInt();
        if (value != 0 && value != 1) {
            goto PROC_END;
        }
    }

    // Execute GPIO operation
    try {
        gpiod::line line = chip->get_line(pin);

        if (direction == "output") {
            line.request({"mcp_gpio", gpiod::line::direction::OUTPUT});
            line.set_value(value);
            iErrCode = MCP::ERRNO_OK;
        } else if (direction == "input") {
            line.request({"mcp_gpio", gpiod::line::direction::INPUT});
            int current_value = line.get_value();
            iErrCode = MCP::ERRNO_OK;
            // Store the value for response
            value = current_value;
        }

        // Keep track of active lines
        active_lines[pin] = std::move(line);

    } catch (const std::exception& e) {
        std::cerr << "GPIO operation failed: " << e.what() << std::endl;
        iErrCode = MCP::ERRNO_INTERNAL_ERROR;
    }

PROC_END:
    auto spExecuteResult = BuildResult();
    if (spExecuteResult) {
        MCP::TextContent textContent;
        textContent.strType = MCP::CONST_TEXT;
        if (MCP::ERRNO_OK == iErrCode) {
            spExecuteResult->bIsError = false;
            if (direction == "output") {
                textContent.strText = "GPIO pin " + std::to_string(pin) + " set to output with value " + std::to_string(value);
            } else {
                textContent.strText = "GPIO pin " + std::to_string(pin) + " configured as input. Current value: " + std::to_string(value);
            }
        } else {
            spExecuteResult->bIsError = true;
            textContent.strText = "Failed to control GPIO pin " + std::to_string(pin);
        }
        spExecuteResult->vecTextContent.push_back(textContent);
        iErrCode = NotifyResult(spExecuteResult);
    }

    return iErrCode;
}

} // namespace MCPIntegration