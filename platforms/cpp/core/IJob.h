#pragma once

class IJob {
public:
    virtual ~IJob() = default;
    virtual void execute() = 0;
};