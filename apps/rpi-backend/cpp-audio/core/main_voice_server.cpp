#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include "audio_device.hpp"
#include "stt_worker.hpp"
#include "tts_worker.hpp"
#include "voice_control_fsm.hpp"

volatile std::sig_atomic_t g_signal_status = 0;

void signal_handler(int signal) {
    g_signal_status = signal;
}

int main(int argc, char* argv[]) {
    std::cout << "MIA Voice Control Server Starting..." << std::endl;

    // Register signal handlers
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    try {
        // Initialize audio device
        AudioDevice audio_device;

        // Initialize STT worker
        STTWorker stt_worker;
        if (!stt_worker.initialize()) {
            std::cerr << "Failed to initialize STT worker" << std::endl;
            return 1;
        }

        // Initialize TTS worker
        TTSWorker tts_worker;
        if (!tts_worker.initialize()) {
            std::cerr << "Failed to initialize TTS worker" << std::endl;
            return 1;
        }

        // Enumerate audio devices
        auto devices = audio_device.enumerate_devices();
        std::cout << "Available audio devices:" << std::endl;
        for (size_t i = 0; i < devices.size(); ++i) {
            const auto& device = devices[i];
            std::cout << "  " << i << ": " << device.name
                      << " (" << device.description << ")"
                      << " [Input: " << (device.is_input ? "Yes" : "No")
                      << ", Output: " << (device.is_output ? "Yes" : "No") << "]"
                      << std::endl;
        }

        // Set up voice control context
        VoiceControlContext voice_ctx;

        voice_ctx.on_audio_ready = [&](const std::string& event) {
            if (event == "start") {
                std::cout << "Starting audio recording..." << std::endl;
                // Start recording for 5 seconds
                audio_device.start_recording(0, 44100, 5000, "/tmp/mia_audio.wav",
                    [&](bool success, const std::string& message) {
                        if (success) {
                            std::cout << "Recording completed: " << message << std::endl;
                            // Process the recorded audio
                            VoiceControlFSM fsm(voice_ctx);
                            fsm.process_event(audio_recorded{"/tmp/mia_audio.wav"});
                        } else {
                            std::cerr << "Recording failed: " << message << std::endl;
                        }
                    });
            } else {
                // Process recorded audio file with STT
                stt_worker.transcribe_file(event,
                    [&](const std::string& transcription) {
                        std::cout << "Transcription: " << transcription << std::endl;
                        VoiceControlFSM fsm(voice_ctx);
                        fsm.process_event(text_transcribed{transcription});
                    },
                    [&](const std::string& error) {
                        std::cerr << "STT Error: " << error << std::endl;
                    });
            }
        };

        voice_ctx.on_intent_recognized = [&](const std::string& text) {
            std::cout << "Intent recognized: " << text << std::endl;
            // Simple intent parsing - in real implementation, use NLP
            std::string response = "I heard you say: " + text;

            VoiceControlFSM fsm(voice_ctx);
            fsm.process_event(command_executed{response});
        };

        voice_ctx.on_response_ready = [&](const std::string& response) {
            std::cout << "Generating speech for: " << response << std::endl;
            tts_worker.synthesize_speech(response,
                [&](const std::string& audio_file) {
                    std::cout << "Speech synthesized: " << audio_file << std::endl;
                    // Play the audio file
                    audio_device.start_playback(0, audio_file,
                        [&](bool success, const std::string& message) {
                            std::cout << "Playback " << (success ? "completed" : "failed") << ": " << message << std::endl;
                            VoiceControlFSM fsm(voice_ctx);
                            fsm.process_event(playback_finished{});
                        });
                },
                [&](const std::string& error) {
                    std::cerr << "TTS Error: " << error << std::endl;
                });
        };

        voice_ctx.on_playback_finished = [&]() {
            std::cout << "Voice interaction completed" << std::endl;
        };

        // Initialize FSM
        VoiceControlFSM voice_fsm(voice_ctx);

        std::cout << "Voice control server ready. Say 'hey mia' or 'computer' to start interaction." << std::endl;
        std::cout << "Press Ctrl+C to exit." << std::endl;

        // Main loop - simulate wake word detection
        while (g_signal_status == 0) {
            // In a real implementation, this would be wake word detection
            // For demo purposes, we'll simulate wake word every 30 seconds
            std::this_thread::sleep_for(std::chrono::seconds(30));

            std::cout << "Wake word detected!" << std::endl;
            voice_fsm.process_event(wake_word{"hey mia"});
        }

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "Voice control server shutting down..." << std::endl;
    return 0;
}