#include "DownloadTask.h"

// Local includes
#include "WebGrabClientWrapper.h"

// Third-party includes
#include <Public/PublicDef.h>
#include <Public/StringHelper.h>

namespace MCPIntegration {

DownloadTask::DownloadTask(const std::shared_ptr<MCP::Request>& spRequest, WebGrabClientWrapper* clientWrapper)
    : ProcessCallToolRequest(spRequest), clientWrapper(clientWrapper) {
}

std::shared_ptr<MCP::CMCPTask> DownloadTask::Clone() const {
    auto spClone = std::make_shared<DownloadTask>(nullptr, clientWrapper);
    if (spClone) {
        *spClone = *this;
    }
    return spClone;
}

int DownloadTask::Cancel() {
    return MCP::ERRNO_OK;
}

int DownloadTask::Execute() {
    int iErrCode = MCP::ERRNO_INTERNAL_ERROR;
    if (!IsValid() || !clientWrapper) {
        return iErrCode;
    }

    Json::Value jArgument;
    std::string strUrl;
    auto spCallToolRequest = std::dynamic_pointer_cast<MCP::CallToolRequest>(m_spRequest);
    if (!spCallToolRequest) {
        goto PROC_END;
    }
    if (spCallToolRequest->strName.compare(TOOL_NAME) != 0) {
        goto PROC_END;
    }
    jArgument = spCallToolRequest->jArguments;
    if (!jArgument.isMember(TOOL_ARGUMENT_URL) || !jArgument[TOOL_ARGUMENT_URL].isString()) {
        goto PROC_END;
    }
    strUrl = jArgument[TOOL_ARGUMENT_URL].asString();

    // Execute download
    uint32_t sessionId = 0;
    if (clientWrapper->download(strUrl, sessionId)) {
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
            textContent.strText = "Download started successfully. Session ID: " + std::to_string(sessionId);
        } else {
            spExecuteResult->bIsError = true;
            textContent.strText = "Failed to start download for URL: " + strUrl;
        }
        spExecuteResult->vecTextContent.push_back(textContent);
        iErrCode = NotifyResult(spExecuteResult);
    }

    return iErrCode;
}

} // namespace MCPIntegration