# MIA Web Interface Development Plan

## Overview

This document outlines the plan to develop a comprehensive web interface for MIA that allows users to:
- View real-time dashboards of system status, hardware sensors, and vehicle telemetry
- Configure Raspberry Pi system settings and services
- Monitor and control MIA services (systemd)
- Manage hardware interfaces (GPIO, Bluetooth, Serial, I2C)
- Access the interface from any device on the network without requiring a display on the Raspberry Pi

## Inspiration: Kernun Web Interface Pattern

**Note**: Direct analysis of kernun web interface at `192.168.200.23:/home/sparrow/Desktop/kernun` requires SSH access setup. The following plan is based on common embedded system web interface patterns and best practices.

### Key Aspects to Analyze in Kernun (when access is available):

1. **Frontend Architecture**
   - Framework/library used (React, Vue, vanilla JS, etc.)
   - Build system and bundling approach
   - State management pattern
   - Component structure and organization

2. **Backend Integration**
   - How frontend communicates with backend (REST, WebSocket, both)
   - API endpoint structure and naming conventions
   - Authentication/authorization mechanism
   - Error handling patterns

3. **C++ Application Integration**
   - How web interface sends commands to C++ applications
   - IPC mechanism (D-Bus, ZeroMQ, Unix sockets, HTTP)
   - Message format and protocol
   - Response handling and error propagation

4. **System Integration**
   - How it manages Linux services (systemd integration)
   - System configuration management
   - Log viewing and monitoring
   - Hardware interface control

5. **Real-time Features**
   - WebSocket implementation details
   - Data streaming patterns
   - Update frequency and efficiency
   - Connection management

6. **UI/UX Patterns**
   - Dashboard layout and organization
   - Navigation structure
   - Configuration UI patterns
   - Status indicators and alerts

### Based on analysis of embedded system web interfaces (similar to kernun), the interface should:
1. **Lightweight Frontend**: Modern, responsive web UI that works on mobile and desktop
2. **Real-time Updates**: WebSocket connections for live data streaming
3. **Backend Integration**: REST API for configuration, WebSocket for telemetry
4. **System Integration**: Direct integration with systemd for service management
5. **C++ Application Control**: Ability to send commands to C++ applications via IPC/ZeroMQ
6. **No External Dependencies**: Self-contained, runs on the Raspberry Pi

## Architecture

### 1. Frontend Architecture

#### Technology Stack
- **Framework**: Vanilla JavaScript (ES6+) or lightweight framework (Vue.js 3 or Preact)
- **Styling**: CSS3 with CSS Grid/Flexbox, responsive design
- **Build Tool**: Vite or esbuild for fast development and minimal bundle size
- **State Management**: Custom lightweight state management or Pinia (if Vue)
- **Real-time**: WebSocket API for live updates

#### Directory Structure
```
web-interface/
├── public/
│   ├── index.html
│   ├── favicon.ico
│   └── assets/
├── src/
│   ├── components/
│   │   ├── Dashboard/
│   │   │   ├── SystemStatus.js
│   │   │   ├── ServiceStatus.js
│   │   │   ├── HardwareStatus.js
│   │   │   └── TelemetryChart.js
│   │   ├── Configuration/
│   │   │   ├── ServiceConfig.js
│   │   │   ├── HardwareConfig.js
│   │   │   └── SystemConfig.js
│   │   ├── Common/
│   │   │   ├── NavBar.js
│   │   │   ├── Sidebar.js
│   │   │   └── StatusIndicator.js
│   │   └── Layout/
│   │       ├── MainLayout.js
│   │       └── PageHeader.js
│   ├── services/
│   │   ├── api.js          # REST API client
│   │   ├── websocket.js    # WebSocket client
│   │   └── systemd.js      # Systemd service management
│   ├── stores/
│   │   ├── system.js       # System state
│   │   ├── services.js     # Service state
│   │   ├── hardware.js     # Hardware state
│   │   └── telemetry.js    # Telemetry state
│   ├── utils/
│   │   ├── formatters.js
│   │   └── validators.js
│   ├── styles/
│   │   ├── main.css
│   │   ├── components.css
│   │   └── themes.css
│   └── main.js
├── package.json
├── vite.config.js
└── README.md
```

### 2. Backend API Extensions

#### New FastAPI Endpoints

**System Management**
- `GET /api/system/status` - System health, CPU, memory, disk, network
- `GET /api/system/info` - OS version, kernel, uptime, hostname
- `GET /api/system/logs` - System logs (journalctl integration)
- `POST /api/system/reboot` - Reboot system (with authentication)
- `POST /api/system/shutdown` - Shutdown system (with authentication)

**Service Management**
- `GET /api/services` - List all MIA systemd services
- `GET /api/services/{service_name}/status` - Get service status
- `POST /api/services/{service_name}/start` - Start service
- `POST /api/services/{service_name}/stop` - Stop service
- `POST /api/services/{service_name}/restart` - Restart service
- `GET /api/services/{service_name}/logs` - Get service logs
- `GET /api/services/{service_name}/config` - Get service configuration
- `PUT /api/services/{service_name}/config` - Update service configuration

**Hardware Configuration**
- `GET /api/hardware/gpio/status` - GPIO pin status
- `POST /api/hardware/gpio/configure` - Configure GPIO pins
- `GET /api/hardware/bluetooth/status` - Bluetooth adapter status
- `POST /api/hardware/bluetooth/scan` - Scan for devices
- `GET /api/hardware/serial/ports` - List serial ports
- `GET /api/hardware/i2c/devices` - List I2C devices

**Configuration Management**
- `GET /api/config` - Get all configuration
- `PUT /api/config` - Update configuration
- `GET /api/config/schema` - Get configuration schema
- `POST /api/config/validate` - Validate configuration
- `POST /api/config/reset` - Reset to defaults

**Real-time Telemetry (WebSocket)**
- `WS /ws/telemetry` - Real-time telemetry stream
- `WS /ws/system` - Real-time system metrics
- `WS /ws/services` - Real-time service status updates

### 3. WebSocket Integration

#### WebSocket Endpoints

```python
# Real-time telemetry stream
@app.websocket("/ws/telemetry")
async def websocket_telemetry(websocket: WebSocket):
    await websocket.accept()
    # Subscribe to ZeroMQ telemetry PUB socket
    # Forward messages to WebSocket clients

# System metrics stream
@app.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    await websocket.accept()
    # Stream CPU, memory, disk, network metrics
    # Update every 1-2 seconds

# Service status updates
@app.websocket("/ws/services")
async def websocket_services(websocket: WebSocket):
    await websocket.accept()
    # Monitor systemd service status changes
    # Forward status updates to clients
```

### 4. Systemd Integration

#### Python Systemd Interface

```python
# rpi/api/systemd_client.py
import subprocess
import json
from typing import Dict, List, Optional

class SystemdClient:
    """Client for managing systemd services"""
    
    def get_service_status(self, service_name: str) -> Dict:
        """Get service status using systemctl"""
        result = subprocess.run(
            ['systemctl', 'show', service_name, '--no-pager', '--property=ActiveState,SubState,LoadState'],
            capture_output=True, text=True
        )
        # Parse output and return structured data
        
    def start_service(self, service_name: str) -> bool:
        """Start a systemd service"""
        result = subprocess.run(
            ['sudo', 'systemctl', 'start', service_name],
            capture_output=True
        )
        return result.returncode == 0
        
    def get_service_logs(self, service_name: str, lines: int = 100) -> List[str]:
        """Get service logs using journalctl"""
        result = subprocess.run(
            ['journalctl', '-u', service_name, '-n', str(lines), '--no-pager'],
            capture_output=True, text=True
        )
        return result.stdout.splitlines()
```

### 5. C++ Application Integration

#### ZeroMQ Command Interface

The existing ZeroMQ infrastructure can be extended to support web interface commands:

```python
# rpi/api/cpp_bridge.py
class CppApplicationBridge:
    """Bridge for communicating with C++ applications via ZeroMQ"""
    
    def send_command(self, app_name: str, command: Dict) -> Dict:
        """Send command to C++ application via ZeroMQ"""
        # Use existing ZeroMQ DEALER socket
        # Format: {"app": app_name, "command": command, "params": {...}}
        zmq_socket.send_json({
            "type": "WEB_COMMAND",
            "app": app_name,
            "command": command,
            "timestamp": datetime.now().isoformat()
        })
        # Wait for response
        return zmq_socket.recv_json()
```

### 6. Dashboard Views

#### Main Dashboard
- **System Overview**: CPU, memory, disk usage, network stats
- **Service Status**: All MIA services with start/stop controls
- **Hardware Status**: GPIO, Bluetooth, Serial, I2C status
- **Active Connections**: WebSocket connections, API requests
- **Recent Logs**: Last 50 log entries from all services

#### Telemetry Dashboard
- **Real-time Charts**: RPM, speed, temperature, DPF status
- **Historical Data**: Time-series charts (last hour, day, week)
- **Device Status**: Connected OBD devices, sensors
- **Alerts**: Warning and error notifications

#### Configuration Dashboard
- **Service Configuration**: Edit systemd service files
- **Hardware Configuration**: GPIO pin mapping, Bluetooth pairing
- **System Settings**: Network, timezone, hostname
- **API Keys**: Manage authentication keys

#### Logs Dashboard
- **Service Logs**: Filterable log viewer for each service
- **System Logs**: journalctl integration
- **Error Tracking**: Error log aggregation
- **Export**: Download logs as text/JSON

### 7. Security Considerations

#### Authentication
- **API Key Authentication**: Use existing `api.auth` module
- **Session Management**: JWT tokens for web sessions
- **Role-Based Access**: Read-only vs. admin roles

#### Authorization
- **Service Control**: Require admin role for start/stop/restart
- **System Control**: Require admin role for reboot/shutdown
- **Configuration Changes**: Require admin role for config updates

#### Network Security
- **HTTPS**: Use self-signed certificate or Let's Encrypt
- **CORS**: Configure CORS for local network access
- **Rate Limiting**: Prevent API abuse

### 8. Implementation Phases

#### Phase 1: Foundation (Week 1-2)
- [ ] Set up frontend project structure
- [ ] Create basic layout and navigation
- [ ] Implement REST API client
- [ ] Add system status endpoint
- [ ] Create system status dashboard component

#### Phase 2: Service Management (Week 2-3)
- [ ] Implement systemd client
- [ ] Add service management endpoints
- [ ] Create service status component
- [ ] Add start/stop/restart controls
- [ ] Implement service logs viewer

#### Phase 3: Real-time Updates (Week 3-4)
- [ ] Implement WebSocket server endpoints
- [ ] Create WebSocket client service
- [ ] Add real-time system metrics
- [ ] Implement telemetry streaming
- [ ] Add service status updates

#### Phase 4: Hardware Management (Week 4-5)
- [ ] Add hardware status endpoints
- [ ] Create hardware status components
- [ ] Implement GPIO configuration UI
- [ ] Add Bluetooth device management
- [ ] Create serial port configuration

#### Phase 5: Configuration Management (Week 5-6)
- [ ] Implement configuration API
- [ ] Create configuration editor
- [ ] Add configuration validation
- [ ] Implement configuration backup/restore
- [ ] Add configuration templates

#### Phase 6: Telemetry Dashboard (Week 6-7)
- [ ] Integrate charting library (Chart.js or similar)
- [ ] Create real-time telemetry charts
- [ ] Add historical data storage
- [ ] Implement data export
- [ ] Add alerting system

#### Phase 7: Polish & Testing (Week 7-8)
- [ ] Responsive design improvements
- [ ] Mobile optimization
- [ ] Error handling and user feedback
- [ ] Performance optimization
- [ ] Documentation
- [ ] Testing on physical hardware

### 9. Technical Specifications

#### Frontend Requirements
- **Browser Support**: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile Support**: iOS 14+, Android 10+
- **Bundle Size**: < 500KB gzipped
- **Load Time**: < 2 seconds on local network
- **Responsive**: Works on 320px to 4K displays

#### Backend Requirements
- **Python**: 3.8+
- **FastAPI**: Latest stable
- **WebSocket**: FastAPI WebSocket support
- **Systemd**: systemctl and journalctl access
- **Permissions**: sudo access for service management

#### Network Requirements
- **Port**: 8080 (configurable) for web interface
- **Protocol**: HTTP/HTTPS, WebSocket/WebSocket Secure
- **Access**: Local network (192.168.x.x) or localhost
- **Discovery**: Optional mDNS/Bonjour for automatic discovery

### 10. File Structure

```
projects/mia/
├── rpi/
│   ├── api/
│   │   ├── main.py              # Existing API (extend)
│   │   ├── systemd_client.py    # NEW: Systemd integration
│   │   ├── cpp_bridge.py        # NEW: C++ app bridge
│   │   └── websocket_handlers.py # NEW: WebSocket handlers
│   └── web-interface/           # NEW: Frontend application
│       ├── public/
│       ├── src/
│       ├── package.json
│       └── vite.config.js
├── docs/
│   └── development/
│       └── WEB_INTERFACE_PLAN.md # This file
└── scripts/
    └── deploy-web-interface.sh   # NEW: Deployment script
```

### 11. Integration with Existing MIA Components

#### ZeroMQ Integration
- Use existing ZeroMQ router (port 5555) for commands
- Subscribe to existing ZeroMQ PUB socket (port 5557) for telemetry
- Extend message protocol for web interface commands

#### Device Registry
- Use existing `DeviceRegistry` for device status
- Expose device information via API
- Add device management UI

#### Authentication
- Integrate with existing `api.auth` module
- Add web session management
- Implement role-based access control

### 12. Deployment

#### Installation
- Add web interface build step to `deploy-complete-system.sh`
- Serve static files via FastAPI or nginx
- Configure systemd service for web interface
- Set up automatic updates

#### Configuration
- Environment variables for port, host, SSL
- Configuration file for UI settings
- Integration with existing MIA config system

### 13. Testing Strategy

#### Unit Tests
- API endpoint tests
- Systemd client tests
- WebSocket handler tests

#### Integration Tests
- End-to-end service management
- Real-time data streaming
- Configuration updates

#### Manual Testing
- Test on physical Raspberry Pi
- Test on various browsers and devices
- Test network access from other devices

### 14. Documentation

#### User Documentation
- Web interface user guide
- Dashboard explanation
- Configuration guide
- Troubleshooting

#### Developer Documentation
- API documentation (OpenAPI/Swagger)
- Frontend architecture
- Backend extension guide
- Contribution guidelines

## Next Steps

1. **Review and Approve Plan**: Review this plan and provide feedback
2. **Set Up Development Environment**: Create frontend project structure
3. **Implement Phase 1**: Start with foundation and basic dashboard
4. **Iterate**: Build incrementally, test frequently
5. **Deploy**: Integrate into deployment scripts

## References

- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/
- Systemd D-Bus API: https://www.freedesktop.org/wiki/Software/systemd/dbus/
- ZeroMQ Guide: https://zeromq.org/get-started/
- Chart.js: https://www.chartjs.org/
- Vue.js: https://vuejs.org/ (if using Vue)
