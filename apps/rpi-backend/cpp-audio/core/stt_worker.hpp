#pragma once

#include <string>
#include <functional>
#include <memory>
#include <thread>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>

// Forward declarations for external libraries (may not be available)
struct whisper_context;
typedef struct whisper_context whisper_context_t;

class STTWorker {
public:
    using OnResultCallback = std::function<void(const std::string&)>;
    using OnErrorCallback = std::function<void(const std::string&)>;

    struct STTRequest {
        std::string wav_path;
        OnResultCallback on_result;
        OnErrorCallback on_error;
    };

    STTWorker();
    ~STTWorker();

    // Initialize with model path
    bool initialize(const std::string& model_path = "models/ggml-tiny.en.bin");

    // Transcribe audio file
    void transcribe_file(const std::string& wav_path,
                        OnResultCallback on_result,
                        OnErrorCallback on_error = nullptr);

    // Check if worker is busy
    bool is_processing() const { return processing_; }

    // Stop all processing
    void stop();

private:
    std::atomic<bool> processing_{false};
    std::atomic<bool> should_stop_{false};

    std::queue<STTRequest> request_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    std::thread worker_thread_;

    // Whisper context (forward declaration to avoid including whisper.h)
    struct WhisperContext;
    std::unique_ptr<WhisperContext> whisper_ctx_;

    // Worker thread function
    void worker_thread_func();

    // Process single transcription request
    bool process_transcription(const STTRequest& request);

    // Load whisper model
    bool load_model(const std::string& model_path);

    // Run whisper command (fallback method)
    std::string run_whisper_cli(const std::string& wav_path);
};