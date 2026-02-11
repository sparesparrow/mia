#pragma once

#include <string>
#include <functional>
#include <variant>

// Context for voice control state machine
struct VoiceControlContext {
    // Callbacks to worker threads
    std::function<void(const std::string&)> on_audio_ready;
    std::function<void(const std::string&)> on_intent_recognized;
    std::function<void(const std::string&)> on_response_ready;
    std::function<void()> on_playback_finished;

    // State data
    std::string last_transcription;
    std::string pending_response;
    bool wake_word_detected = false;
};

// Events
struct wake_word { std::string word; };
struct audio_recorded { std::string wav_path; };
struct text_transcribed { std::string text; };
struct intent_parsed { std::string tool; std::string args; };
struct command_executed { std::string result; };
struct response_ready { std::string text; };
struct playback_finished {};
struct error_occurred { std::string message; };

// States
enum class VoiceState {
    Idle,
    Listening,
    Processing,
    Speaking,
    Error
};

// Lightweight FSM implementation without Boost dependency
class VoiceControlFSM {
public:
    explicit VoiceControlFSM(VoiceControlContext& ctx) : ctx_(ctx), state_(VoiceState::Idle) {}

    // Process events and transition states
    void process_event(const wake_word& event);
    void process_event(const audio_recorded& event);
    void process_event(const text_transcribed& event);
    void process_event(const intent_parsed& event);
    void process_event(const command_executed& event);
    void process_event(const response_ready& event);
    void process_event(const playback_finished& event);
    void process_event(const error_occurred& event);

    // Check current state
    bool is_in_state(VoiceState state) const { return state_ == state; }

    // Get current state
    VoiceState get_state() const { return state_; }

private:
    VoiceControlContext& ctx_;
    VoiceState state_;

    // Helper function to check wake words
    bool has_wake_word(const std::string& word) const {
        return word == "hey mia" || word == "computer";
    }
};