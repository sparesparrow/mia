# Car Assistant Configuration
CAR_ASSISTANT_CONFIG = {
    "name": "Mobile Intelligent Assistant",
    "mcp_servers": {
        "hardware": "mia-hardware",
        "prompts": "mcp-prompts-memory",
        "orchestrator": "mia-orchestrator"
    },
    "capabilities": {
        "gpio_control": True,
        "obd_diagnostics": True,
        "rf_communication": True,
        "audio_control": True,
        "climate_control": True
    },
    "safety": {
        "distracted_driving_protection": True,
        "emergency_detection": True,
        "diagnostic_monitoring": True
    }
}