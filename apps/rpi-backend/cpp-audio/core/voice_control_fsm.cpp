#include "voice_control_fsm.hpp"
#include <iostream>

// VoiceControlFSM implementation
void VoiceControlFSM::process_event(const wake_word& event) {
    switch (state_) {
        case VoiceState::Idle:
            if (has_wake_word(event.word)) {
                // Action: start recording
                ctx_.on_audio_ready("start");
                state_ = VoiceState::Listening;
                std::cout << "FSM: Idle -> Listening (wake word: " << event.word << ")" << std::endl;
            }
            break;
        default:
            // Invalid transition, stay in current state
            break;
    }
}

void VoiceControlFSM::process_event(const audio_recorded& event) {
    switch (state_) {
        case VoiceState::Listening:
            // Action: transcribe audio
            ctx_.on_audio_ready(event.wav_path);
            state_ = VoiceState::Processing;
            std::cout << "FSM: Listening -> Processing (audio recorded)" << std::endl;
            break;
        default:
            // Invalid transition
            break;
    }
}

void VoiceControlFSM::process_event(const text_transcribed& event) {
    switch (state_) {
        case VoiceState::Processing:
            // Action: parse intent
            ctx_.last_transcription = event.text;
            ctx_.on_intent_recognized(event.text);
            // Stay in processing state for intent parsing
            std::cout << "FSM: Processing (text transcribed: " << event.text << ")" << std::endl;
            break;
        default:
            // Invalid transition
            break;
    }
}

void VoiceControlFSM::process_event(const intent_parsed& event) {
    switch (state_) {
        case VoiceState::Processing:
            // Action: execute command
            // ctx_.on_command_execute(event.tool, event.args); // TODO: implement
            // Stay in processing state
            std::cout << "FSM: Processing (intent parsed: " << event.tool << ")" << std::endl;
            break;
        default:
            // Invalid transition
            break;
    }
}

void VoiceControlFSM::process_event(const command_executed& event) {
    switch (state_) {
        case VoiceState::Processing:
            // Action: prepare response
            ctx_.pending_response = event.result;
            ctx_.on_response_ready(event.result);
            state_ = VoiceState::Speaking;
            std::cout << "FSM: Processing -> Speaking (command executed)" << std::endl;
            break;
        default:
            // Invalid transition
            break;
    }
}

void VoiceControlFSM::process_event(const response_ready& event) {
    switch (state_) {
        case VoiceState::Speaking:
            // Action: speak response
            ctx_.on_response_ready(event.text);
            // Stay in speaking state until playback finished
            std::cout << "FSM: Speaking (response ready)" << std::endl;
            break;
        default:
            // Invalid transition
            break;
    }
}

void VoiceControlFSM::process_event(const playback_finished& event) {
    switch (state_) {
        case VoiceState::Speaking:
            state_ = VoiceState::Idle;
            std::cout << "FSM: Speaking -> Idle (playback finished)" << std::endl;
            break;
        default:
            // Invalid transition
            break;
    }
}

void VoiceControlFSM::process_event(const error_occurred& event) {
    // From any state, go to error state and then back to idle
    state_ = VoiceState::Error;
    std::cout << "FSM: -> Error (error: " << event.message << ")" << std::endl;
    // Immediately transition back to idle
    state_ = VoiceState::Idle;
    std::cout << "FSM: Error -> Idle" << std::endl;
}