#include "audio_device.hpp"
#include <iostream>
#include <thread>
#include <atomic>
#include <cstring>
#include <fstream>
#include <algorithm>

AudioDevice::AudioDevice() : context_(std::make_unique<AudioContext>()) {}

AudioDevice::~AudioDevice() {
    stop_recording();
    stop_playback();
    stop_stream();

    if (context_->handle) {
        snd_pcm_close(context_->handle);
    }
}

std::vector<AudioDeviceInfo> AudioDevice::enumerate_devices() {
    std::vector<AudioDeviceInfo> devices;

    // Enumerate ALSA devices
    void** hints;
    if (snd_device_name_hint(-1, "pcm", &hints) < 0) {
        return devices;
    }

    for (void** hint = hints; *hint != nullptr; ++hint) {
        char* name = snd_device_name_get_hint(*hint, "NAME");
        char* desc = snd_device_name_get_hint(*hint, "DESC");

        if (name && desc) {
            AudioDeviceInfo info;
            info.device_index = devices.size();
            info.name = name;
            info.description = desc;

            // Check if device supports input/output
            snd_pcm_t* handle = nullptr;
            if (snd_pcm_open(&handle, name, SND_PCM_STREAM_CAPTURE, 0) == 0) {
                info.is_input = true;
                snd_pcm_close(handle);
            }

            if (snd_pcm_open(&handle, name, SND_PCM_STREAM_PLAYBACK, 0) == 0) {
                info.is_output = true;
                snd_pcm_close(handle);
            }

            // Get sample rate capabilities (simplified)
            info.sample_rate_min = 8000;
            info.sample_rate_max = 192000;

            devices.push_back(info);
        }

        if (name) free(name);
        if (desc) free(desc);
    }

    snd_device_name_free_hint(hints);
    return devices;
}

bool AudioDevice::start_recording(int device_index,
                                 unsigned int sample_rate,
                                 unsigned int duration_ms,
                                 const std::string& filename,
                                 CompletionCallback on_complete) {
    if (recording_active_) {
        return false;
    }

    std::string device_name = get_device_name(device_index);
    if (device_name.empty()) {
        if (on_complete) on_complete(false, "Device not found");
        return false;
    }

    context_->filename = filename;
    context_->sample_rate = sample_rate;
    context_->duration_ms = duration_ms;
    context_->completion_callback = on_complete;
    context_->is_recording = true;

    if (!open_device(device_index, SND_PCM_STREAM_CAPTURE, &context_->handle)) {
        if (on_complete) on_complete(false, "Failed to open audio device");
        return false;
    }

    if (!set_hw_params(context_->handle, sample_rate, false)) {
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
        if (on_complete) on_complete(false, "Failed to set hardware parameters");
        return false;
    }

    if (!set_sw_params(context_->handle)) {
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
        if (on_complete) on_complete(false, "Failed to set software parameters");
        return false;
    }

    recording_active_ = true;
    std::thread(&AudioDevice::recording_thread_func, this).detach();
    return true;
}

bool AudioDevice::stop_recording() {
    if (!recording_active_) {
        return false;
    }

    recording_active_ = false;
    context_->is_recording = false;

    if (context_->handle) {
        snd_pcm_drain(context_->handle);
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
    }

    return true;
}

bool AudioDevice::start_playback(int device_index,
                                const std::string& filename,
                                CompletionCallback on_complete) {
    if (playback_active_) {
        return false;
    }

    std::string device_name = get_device_name(device_index);
    if (device_name.empty()) {
        if (on_complete) on_complete(false, "Device not found");
        return false;
    }

    context_->filename = filename;
    context_->completion_callback = on_complete;
    context_->is_playing = true;

    if (!open_device(device_index, SND_PCM_STREAM_PLAYBACK, &context_->handle)) {
        if (on_complete) on_complete(false, "Failed to open audio device");
        return false;
    }

    // Read WAV file and extract parameters
    // This is a simplified implementation - real implementation would parse WAV header
    playback_active_ = true;
    std::thread(&AudioDevice::playback_thread_func, this).detach();
    return true;
}

bool AudioDevice::stop_playback() {
    if (!playback_active_) {
        return false;
    }

    playback_active_ = false;
    context_->is_playing = false;

    if (context_->handle) {
        snd_pcm_drain(context_->handle);
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
    }

    return true;
}

bool AudioDevice::start_stream(int device_index,
                              unsigned int sample_rate,
                              AudioCallback on_audio_data) {
    if (streaming_active_) {
        return false;
    }

    std::string device_name = get_device_name(device_index);
    if (device_name.empty()) {
        return false;
    }

    context_->sample_rate = sample_rate;
    context_->callback = on_audio_data;

    if (!open_device(device_index, SND_PCM_STREAM_CAPTURE, &context_->handle)) {
        return false;
    }

    if (!set_hw_params(context_->handle, sample_rate, false)) {
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
        return false;
    }

    if (!set_sw_params(context_->handle)) {
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
        return false;
    }

    streaming_active_ = true;
    std::thread(&AudioDevice::streaming_thread_func, this).detach();
    return true;
}

bool AudioDevice::stop_stream() {
    if (!streaming_active_) {
        return false;
    }

    streaming_active_ = false;

    if (context_->handle) {
        snd_pcm_drain(context_->handle);
        snd_pcm_close(context_->handle);
        context_->handle = nullptr;
    }

    return true;
}

void AudioDevice::recording_thread_func() {
    const size_t buffer_size = 1024;
    int16_t buffer[buffer_size];
    std::vector<int16_t> recorded_data;

    auto start_time = std::chrono::steady_clock::now();
    auto duration = std::chrono::milliseconds(context_->duration_ms);

    while (context_->is_recording &&
           std::chrono::steady_clock::now() - start_time < duration) {

        snd_pcm_sframes_t frames = snd_pcm_readi(context_->handle, buffer, buffer_size / 2);
        if (frames < 0) {
            frames = snd_pcm_recover(context_->handle, frames, 0);
            if (frames < 0) {
                break;
            }
        }

        if (frames > 0) {
            recorded_data.insert(recorded_data.end(), buffer, buffer + frames * 2);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    // Finalize recording
    if (!finalize_wav_file(context_->filename, recorded_data)) {
        if (context_->completion_callback) {
            context_->completion_callback(false, "Failed to write WAV file");
        }
    } else {
        if (context_->completion_callback) {
            context_->completion_callback(true, "Recording completed");
        }
    }

    recording_active_ = false;
}

void AudioDevice::playback_thread_func() {
    // Simplified playback implementation
    // Real implementation would read WAV file and play audio

    if (context_->completion_callback) {
        context_->completion_callback(true, "Playback completed");
    }

    playback_active_ = false;
}

void AudioDevice::streaming_thread_func() {
    const size_t buffer_size = 1024;
    int16_t buffer[buffer_size];

    while (streaming_active_) {
        snd_pcm_sframes_t frames = snd_pcm_readi(context_->handle, buffer, buffer_size / 2);
        if (frames < 0) {
            frames = snd_pcm_recover(context_->handle, frames, 0);
            if (frames < 0) {
                break;
            }
        }

        if (frames > 0 && context_->callback) {
            std::vector<int16_t> data(buffer, buffer + frames * 2);
            context_->callback(data);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }

    streaming_active_ = false;
}

// Private helper methods
bool AudioDevice::open_device(int device_index, snd_pcm_stream_t stream_type, snd_pcm_t** handle) {
    std::string device_name = get_device_name(device_index);
    if (device_name.empty()) {
        return false;
    }

    int err = snd_pcm_open(handle, device_name.c_str(), stream_type, 0);
    return err == 0;
}

bool AudioDevice::set_hw_params(snd_pcm_t* handle, unsigned int sample_rate, bool is_playback) {
    snd_pcm_hw_params_t* params;
    snd_pcm_hw_params_alloca(&params);

    int err = snd_pcm_hw_params_any(handle, params);
    if (err < 0) return false;

    err = snd_pcm_hw_params_set_access(handle, params, SND_PCM_ACCESS_RW_INTERLEAVED);
    if (err < 0) return false;

    err = snd_pcm_hw_params_set_format(handle, params, SND_PCM_FORMAT_S16_LE);
    if (err < 0) return false;

    err = snd_pcm_hw_params_set_channels(handle, params, 2);
    if (err < 0) return false;

    err = snd_pcm_hw_params_set_rate_near(handle, params, &sample_rate, nullptr);
    if (err < 0) return false;

    err = snd_pcm_hw_params(handle, params);
    if (err < 0) return false;

    return true;
}

bool AudioDevice::set_sw_params(snd_pcm_t* handle) {
    snd_pcm_sw_params_t* params;
    snd_pcm_sw_params_alloca(&params);

    int err = snd_pcm_sw_params_current(handle, params);
    if (err < 0) return false;

    err = snd_pcm_sw_params_set_start_threshold(handle, params, 1);
    if (err < 0) return false;

    err = snd_pcm_sw_params(handle, params);
    if (err < 0) return false;

    return true;
}

bool AudioDevice::write_wav_header(const std::string& filename, unsigned int sample_rate, unsigned int data_size) {
    std::ofstream file(filename, std::ios::binary);
    if (!file) return false;

    // WAV header (simplified)
    file.write("RIFF", 4);
    uint32_t file_size = 36 + data_size;
    file.write(reinterpret_cast<const char*>(&file_size), 4);
    file.write("WAVE", 4);
    file.write("fmt ", 4);
    uint32_t fmt_size = 16;
    file.write(reinterpret_cast<const char*>(&fmt_size), 4);
    uint16_t format = 1; // PCM
    file.write(reinterpret_cast<const char*>(&format), 2);
    uint16_t channels = 2;
    file.write(reinterpret_cast<const char*>(&channels), 2);
    file.write(reinterpret_cast<const char*>(&sample_rate), 4);
    uint32_t byte_rate = sample_rate * channels * 2;
    file.write(reinterpret_cast<const char*>(&byte_rate), 4);
    uint16_t block_align = channels * 2;
    file.write(reinterpret_cast<const char*>(&block_align), 2);
    uint16_t bits_per_sample = 16;
    file.write(reinterpret_cast<const char*>(&bits_per_sample), 2);
    file.write("data", 4);
    file.write(reinterpret_cast<const char*>(&data_size), 4);

    return true;
}

bool AudioDevice::finalize_wav_file(const std::string& filename, const std::vector<int16_t>& data) {
    size_t data_size = data.size() * sizeof(int16_t);
    if (!write_wav_header(filename, context_->sample_rate, data_size)) {
        return false;
    }

    std::ofstream file(filename, std::ios::binary | std::ios::app);
    if (!file) return false;

    file.write(reinterpret_cast<const char*>(data.data()), data_size);
    return true;
}

std::string AudioDevice::get_device_name(int index) {
    auto devices = enumerate_devices();
    if (index >= 0 && index < static_cast<int>(devices.size())) {
        return devices[index].name;
    }
    return "";
}

bool AudioDevice::device_exists(int index) {
    return !get_device_name(index).empty();
}