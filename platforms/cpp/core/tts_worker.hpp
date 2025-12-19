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
struct piper_speaker;
typedef struct piper_speaker piper_speaker_t;

class TTSWorker {
public:
    using OnResultCallback = std::function<void(const std::string&)>;
    using OnErrorCallback = std::function<void(const std::string&)>;

    struct TTSTRequest {
        std::string text;
        OnResultCallback on_result;
        OnErrorCallback on_error;
    };

    TTSWorker();
    ~TTSWorker();

    // Initialize with model/voice path
    bool initialize(const std::string& model_path = "models/tts/en_US-lessac-medium.onnx",
                   const std::string& voice_path = "");

    // Synthesize speech from text
    void synthesize_speech(const std::string& text,
                          OnResultCallback on_result,
                          OnErrorCallback on_error = nullptr);

    // Check if worker is busy
    bool is_processing() const { return processing_; }

    // Stop all processing
    void stop();

private:
    std::atomic<bool> processing_{false};
    std::atomic<bool> should_stop_{false};

    std::queue<TTSTRequest> request_queue_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    std::thread worker_thread_;

    std::string model_path_;
    std::string voice_path_;

    // Piper context (forward declaration to avoid including piper.h)
    struct PiperContext;
    std::unique_ptr<PiperContext> piper_ctx_;

    // Worker thread function
    void worker_thread_func();

    // Process single TTS request
    bool process_tts(const TTSTRequest& request);

    // Load piper model
    bool load_model(const std::string& model_path, const std::string& voice_path);

    // Run piper command (fallback method)
    std::string run_piper_cli(const std::string& text);
};