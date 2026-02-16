#include "stt_worker.hpp"
#include <iostream>
#include <sstream>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <algorithm>

// Forward declarations for whisper.h (may not be available)
// Stub implementations - will be replaced with actual calls when library is available
extern "C" {
    struct whisper_context;
    typedef struct whisper_context whisper_context_t;

    inline whisper_context_t* whisper_init_from_file(const char* path) { return nullptr; }
    inline void whisper_free(whisper_context_t* ctx) {}
    inline int whisper_full(whisper_context_t* ctx, void* params, const float* samples, int n_samples) { return -1; }
    inline int whisper_full_n_segments(whisper_context_t* ctx) { return 0; }
    inline const char* whisper_full_get_segment_text(whisper_context_t* ctx, int i) { return ""; }
}

struct STTWorker::WhisperContext {
    whisper_context_t* ctx = nullptr;

    WhisperContext(const std::string& model_path) {
        ctx = whisper_init_from_file(model_path.c_str());
    }

    ~WhisperContext() {
        if (ctx) {
            whisper_free(ctx);
        }
    }

    bool is_valid() const { return ctx != nullptr; }
};

STTWorker::STTWorker() {
    worker_thread_ = std::thread(&STTWorker::worker_thread_func, this);
}

STTWorker::~STTWorker() {
    stop();
    if (worker_thread_.joinable()) {
        worker_thread_.join();
    }
}

bool STTWorker::initialize(const std::string& model_path) {
    return load_model(model_path);
}

void STTWorker::transcribe_file(const std::string& wav_path,
                               OnResultCallback on_result,
                               OnErrorCallback on_error) {
    STTRequest request{wav_path, on_result, on_error};

    {
        std::unique_lock<std::mutex> lock(queue_mutex_);
        request_queue_.push(request);
    }

    queue_cv_.notify_one();
}

void STTWorker::stop() {
    should_stop_ = true;
    queue_cv_.notify_all();
}

void STTWorker::worker_thread_func() {
    while (!should_stop_) {
        STTRequest request;

        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            queue_cv_.wait(lock, [this]() {
                return !request_queue_.empty() || should_stop_;
            });

            if (should_stop_) break;

            if (!request_queue_.empty()) {
                request = request_queue_.front();
                request_queue_.pop();
            } else {
                continue;
            }
        }

        processing_ = true;
        bool success = process_transcription(request);
        processing_ = false;

        if (!success && request.on_error) {
            request.on_error("Transcription failed");
        }
    }
}

bool STTWorker::process_transcription(const STTRequest& request) {
    // Check if file exists
    if (!std::filesystem::exists(request.wav_path)) {
        if (request.on_error) {
            request.on_error("Audio file does not exist: " + request.wav_path);
        }
        return false;
    }

    std::string transcription;

    // Try native whisper processing first
    if (whisper_ctx_ && whisper_ctx_->is_valid()) {
        // TODO: Implement native whisper processing
        // For now, fall back to CLI method
        transcription = run_whisper_cli(request.wav_path);
    } else {
        // Fall back to CLI method
        transcription = run_whisper_cli(request.wav_path);
    }

    if (!transcription.empty()) {
        if (request.on_result) {
            request.on_result(transcription);
        }
        return true;
    }

    return false;
}

bool STTWorker::load_model(const std::string& model_path) {
    try {
        whisper_ctx_ = std::make_unique<WhisperContext>(model_path);
        return whisper_ctx_->is_valid();
    } catch (const std::exception& e) {
        std::cerr << "Failed to load whisper model: " << e.what() << std::endl;
        return false;
    }
}

std::string STTWorker::run_whisper_cli(const std::string& wav_path) {
    // Build command - assuming whisper-cli is available
    std::string cmd = "whisper-cli";
    if (!whisper_ctx_) {
        // Use default model if no context loaded
        cmd += " -m models/ggml-tiny.en.bin";
    }
    cmd += " -f " + wav_path + " -otxt";  // Output to text file

    // Execute command
    FILE* pipe = popen(cmd.c_str(), "r");
    if (!pipe) {
        return "";
    }

    // Read output (though whisper-cli might write to file)
    std::string result;
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        result += buffer;
    }

    int status = pclose(pipe);
    if (status != 0) {
        return "";
    }

    // Try to read from output text file
    std::string txt_path = wav_path;
    size_t dot_pos = txt_path.find_last_of('.');
    if (dot_pos != std::string::npos) {
        txt_path = txt_path.substr(0, dot_pos) + ".txt";
    } else {
        txt_path += ".txt";
    }

    std::ifstream txt_file(txt_path);
    if (txt_file.is_open()) {
        std::stringstream ss;
        ss << txt_file.rdbuf();
        result = ss.str();
        txt_file.close();

        // Clean up the temporary text file
        std::filesystem::remove(txt_path);
    }

    // Trim whitespace
    result.erase(result.begin(), std::find_if(result.begin(), result.end(),
              [](unsigned char ch) { return !std::isspace(ch); }));
    result.erase(std::find_if(result.rbegin(), result.rend(),
              [](unsigned char ch) { return !std::isspace(ch); }).base(), result.end());

    return result;
}