#pragma once

#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <alsa/asoundlib.h>

struct AudioDeviceInfo {
    int device_index;
    std::string name;
    std::string description;
    bool is_input;
    bool is_output;
    unsigned int sample_rate_min;
    unsigned int sample_rate_max;
};

class AudioDevice {
public:
    using AudioCallback = std::function<void(const std::vector<int16_t>& data)>;
    using CompletionCallback = std::function<void(bool success, const std::string& message)>;

    AudioDevice();
    ~AudioDevice();

    // Device enumeration
    std::vector<AudioDeviceInfo> enumerate_devices();

    // Recording operations
    bool start_recording(int device_index,
                        unsigned int sample_rate,
                        unsigned int duration_ms,
                        const std::string& filename,
                        CompletionCallback on_complete = nullptr);

    bool stop_recording();

    // Playback operations
    bool start_playback(int device_index,
                       const std::string& filename,
                       CompletionCallback on_complete = nullptr);

    bool stop_playback();

    // Streaming operations
    bool start_stream(int device_index,
                     unsigned int sample_rate,
                     AudioCallback on_audio_data);

    bool stop_stream();

    // Status
    bool is_recording() const { return recording_active_; }
    bool is_playing() const { return playback_active_; }
    bool is_streaming() const { return streaming_active_; }

private:
    struct AudioContext {
        snd_pcm_t* handle = nullptr;
        AudioCallback callback;
        CompletionCallback completion_callback;
        std::string filename;
        unsigned int sample_rate = 44100;
        unsigned int duration_ms = 0;
        bool is_recording = false;
        bool is_playing = false;
        std::vector<int16_t> buffer;
    };

    std::unique_ptr<AudioContext> context_;
    bool recording_active_ = false;
    bool playback_active_ = false;
    bool streaming_active_ = false;

    // ALSA helper functions
    bool open_device(int device_index, snd_pcm_stream_t stream_type, snd_pcm_t** handle);
    bool set_hw_params(snd_pcm_t* handle, unsigned int sample_rate, bool is_playback);
    bool set_sw_params(snd_pcm_t* handle);
    bool write_wav_header(const std::string& filename, unsigned int sample_rate, unsigned int data_size);
    bool finalize_wav_file(const std::string& filename, const std::vector<int16_t>& data);

    // Thread functions
    void recording_thread_func();
    void playback_thread_func();
    void streaming_thread_func();

    // Helper functions
    std::string get_device_name(int index);
    bool device_exists(int index);
};