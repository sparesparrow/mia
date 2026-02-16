#pragma once

#include <atomic>
#include <memory>
#include <string>
#include <thread>
#include <unordered_map>
#include <mutex>
#include <queue>
#include <condition_variable>

// Forward declarations for FlatBuffers
namespace Mia {
namespace Protocol {
    struct VideoStreamStart;
    struct VideoStreamData;
    struct VideoStreamStop;
    struct VideoStreamStatus;
    struct VideoStreamConfig;
}
}

namespace WebGrab {

/**
 * @brief Video Stream Session Information
 */
struct VideoStreamSession {
    std::string session_id;
    std::string camera_id;
    uint32_t width;
    uint32_t height;
    uint32_t frame_rate;
    std::string codec;
    uint32_t bitrate_kbps;
    uint32_t keyframe_interval;
    std::chrono::steady_clock::time_point start_time;
    uint32_t frames_sent;
    uint64_t bytes_sent;
    bool active;

    VideoStreamSession()
        : width(1280), height(720), frame_rate(30), bitrate_kbps(2000),
          keyframe_interval(30), frames_sent(0), bytes_sent(0), active(false) {}
};

/**
 * @brief Video Streaming Server
 *
 * This server manages video streaming sessions and coordinates with
 * the USB camera hardware and video encoding components. It handles
 * stream lifecycle management, frame processing, and data routing.
 */
class VideoStreamServer {
public:
    explicit VideoStreamServer(int port = 8082,
                              const std::string& mqtt_host = "localhost",
                              int mqtt_port = 1883);
    ~VideoStreamServer();

    bool Start();
    void Stop();

    // Stream management methods
    bool StartStream(const std::string& session_id,
                    const std::string& camera_id,
                    const Mia::Protocol::VideoStreamConfig* config);
    bool StopStream(const std::string& session_id,
                   const std::string& reason = "user_request");
    VideoStreamSession* GetStreamStatus(const std::string& session_id);

    // Frame processing methods
    void ProcessVideoFrame(const std::string& session_id,
                          const uint8_t* frame_data,
                          size_t frame_size,
                          uint32_t frame_number,
                          bool is_keyframe);

private:
    // Server configuration
    int port;
    std::string mqtt_host;
    int mqtt_port;

    // Server state
    std::atomic<bool> running;
    int server_socket;
    std::thread accept_thread;
    std::thread process_thread;

    // MQTT client (forward declared)
    struct mosquitto* mqtt_client;
    std::thread mqtt_thread;

    // Stream management
    std::unordered_map<std::string, std::unique_ptr<VideoStreamSession>> active_streams;
    std::mutex streams_mutex;

    // Frame processing queue
    struct VideoFrame {
        std::string session_id;
        std::vector<uint8_t> frame_data;
        uint32_t frame_number;
        bool is_keyframe;
        std::chrono::steady_clock::time_point timestamp;
    };

    std::queue<std::unique_ptr<VideoFrame>> frame_queue;
    std::mutex frame_queue_mutex;
    std::condition_variable frame_queue_cv;

    // Private methods
    bool SetupServerSocket();
    void AcceptConnections();
    void ProcessFrames();

    bool InitializeMQTT();
    void CleanupMQTT();

    void HandleClientConnection(int client_socket);
    bool SendVideoFrameMQTT(const std::string& session_id,
                           const VideoFrame& frame);

    // Stream lifecycle helpers
    VideoStreamSession* CreateStreamSession(const std::string& session_id,
                                          const std::string& camera_id,
                                          const Mia::Protocol::VideoStreamConfig* config);
    void DestroyStreamSession(const std::string& session_id);

    // Utility methods
    std::string GenerateSessionId();
    double CalculateAverageFPS(const VideoStreamSession& session);
};

} // namespace WebGrab