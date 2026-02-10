#include "AbortTask.h"

// Local includes
#include "WebGrabClientWrapper.h"

// Third-party includes
#include <Public/PublicDef.h>
#include <Public/StringHelper.h>

namespace MCPIntegration {

AbortTask::AbortTask(const std::shared_ptr<MCP::Request>& spRequest, WebGrabClientWrapper* clientWrapper)
    : ProcessCallToolRequest(spRequest), clientWrapper(clientWrapper) {
}

std::shared_ptr<MCP::CMCPTask> AbortTask::Clone() const {
    auto spClone = std::make_shared<AbortTask>(nullptr, clientWrapper);
    if (spClone) {
        *spClone = *this;
    }
    return spClone;
}

int AbortTask::Cancel() {
    return MCP::ERRNO_OK;
}

int AbortTask::Execute() {
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

    // Abort download
    if (clientWrapper->abort(sessionId)) {
        iErrCode = MCP::ERRNO_OK;
    } else {
        iErrCode = MCP::ERRNO_INTERNAL_ERROR;
    }

PROC_END:
    auto spExecuteResult = BuildResult();
    if (spExecuteResult) {
        MCP::TextContent textContent;
        textContent.strType = MCP::CONST_TEXT;
        if (MCP::ERRNO_OK == iErrCode) {
            spExecuteResult->bIsError = false;
            textContent.strText = "Download aborted for session " + std::to_string(sessionId);
        } else {
            spExecuteResult->bIsError = true;
            textContent.strText = "Failed to abort download for session " + std::to_string(sessionId);
        }
        spExecuteResult->vecTextContent.push_back(textContent);
        iErrCode = NotifyResult(spExecuteResult);
    }

    return iErrCode;
}

} // namespace MCPIntegration