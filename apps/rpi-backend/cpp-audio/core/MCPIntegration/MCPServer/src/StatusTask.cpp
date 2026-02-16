#include "StatusTask.h"

// Local includes
#include "WebGrabClientWrapper.h"

// Third-party includes
#include <Public/PublicDef.h>
#include <Public/StringHelper.h>

namespace MCPIntegration {

StatusTask::StatusTask(const std::shared_ptr<MCP::Request>& spRequest, WebGrabClientWrapper* clientWrapper)
    : ProcessCallToolRequest(spRequest), clientWrapper(clientWrapper) {
}

std::shared_ptr<MCP::CMCPTask> StatusTask::Clone() const {
    auto spClone = std::make_shared<StatusTask>(nullptr, clientWrapper);
    if (spClone) {
        *spClone = *this;
    }
    return spClone;
}

int StatusTask::Cancel() {
    return MCP::ERRNO_OK;
}

int StatusTask::Execute() {
    int iErrCode = MCP::ERRNO_INTERNAL_ERROR;
    if (!IsValid() || !clientWrapper) {
        return iErrCode;
    }

    Json::Value jArgument;
    uint32_t sessionId = 0;
    auto spCallToolRequest = std::dynamic_pointer_cast<MCP::CallToolRequest>(m_spRequest);
    if (!spCallToolRequest) {
        goto PROC_END;
    }
    if (spCallToolRequest->strName.compare(TOOL_NAME) != 0) {
        goto PROC_END;
    }
    jArgument = spCallToolRequest->jArguments;
    if (!jArgument.isMember(TOOL_ARGUMENT_SESSION_ID) || !jArgument[TOOL_ARGUMENT_SESSION_ID].isConvertibleTo(Json::uintValue)) {
        goto PROC_END;
    }
    sessionId = jArgument[TOOL_ARGUMENT_SESSION_ID].asUInt();

    // Check status
    std::string status;
    if (clientWrapper->status(sessionId, status)) {
        iErrCode = MCP::ERRNO_OK;
    } else {
        iErrCode = MCP::ERRNO_INTERNAL_ERROR;
        status = "Failed to get status";
    }

PROC_END:
    auto spExecuteResult = BuildResult();
    if (spExecuteResult) {
        MCP::TextContent textContent;
        textContent.strType = MCP::CONST_TEXT;
        if (MCP::ERRNO_OK == iErrCode) {
            spExecuteResult->bIsError = false;
            textContent.strText = "Status for session " + std::to_string(sessionId) + ": " + status;
        } else {
            spExecuteResult->bIsError = true;
            textContent.strText = "Failed to check status for session " + std::to_string(sessionId);
        }
        spExecuteResult->vecTextContent.push_back(textContent);
        iErrCode = NotifyResult(spExecuteResult);
    }

    return iErrCode;
}

} // namespace MCPIntegration