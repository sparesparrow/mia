# 🏗️ MIA Universal: Architecture Diagrams

This document contains comprehensive system architecture diagrams for the MIA Universal ecosystem, showing the relationships between components, data flows, and interaction patterns.

## 🎯 **System Overview**

### **High-Level Architecture**
```mermaid
C4Context
    title MIA Universal - System Context Diagram
    
    Person(user, "User", "Person using AI assistant across multiple devices and environments")
    
    System_Boundary(aiServis, "MIA Universal") {
        System(core, "Core Orchestrator", "MCP Host managing all AI modules and user interactions")
        System(modules, "MCP Server Modules", "Specialized AI services for different domains")
        System(transport, "Transport Layer", "Communication infrastructure (MQTT, HTTP, BLE)")
    }
    
    System_Ext(cloud, "Optional Cloud Services", "Weather, Maps, Social Media APIs")
    System_Ext(devices, "Smart Devices", "IoT devices, phones, computers, car systems")
    System_Ext(services, "External Services", "Spotify, WhatsApp, etc.")
    
    Rel(user, core, "Voice commands, touch, gestures")
    Rel(core, modules, "MCP protocol")
    Rel(modules, transport, "Various protocols")
    Rel(transport, devices, "Control & monitoring")
    Rel(modules, services, "APIs")
    Rel(modules, cloud, "Optional augmentation")
```

## 🔄 **MCP Communication Flow**

### **Request-Response Pattern**
```mermaid
sequenceDiagram
    participant User
    participant Core as Core Orchestrator<br/>(MCP Host)
    participant Discovery as Service Discovery
    participant AudioMCP as AI Audio Assistant<br/>(MCP Server)
    participant PlatformMCP as Platform Controller<br/>(MCP Server)
    
    Note over User,PlatformMCP: User says: "Play relaxing music and dim the lights"
    
    User->>Core: Voice input
    Core->>Core: Speech-to-Text<br/>(ElevenLabs/Whisper)
    Core->>Core: Intent Recognition<br/>Extract: music + lighting
    
    par Service Discovery
        Core->>Discovery: Query available services
        Discovery-->>Core: Return: audio, platform, home-automation
    end
    
    par Multi-Module Coordination
        Core->>AudioMCP: MCP Request<br/>{"method": "play_music", "params": {"genre": "relaxing", "zone": "living_room"}}
        AudioMCP->>AudioMCP: Connect to Spotify API
        AudioMCP->>AudioMCP: Start streaming to zone speakers
        AudioMCP-->>Core: MCP Response<br/>{"result": "Now playing: Ambient Sounds playlist"}
    and
        Core->>PlatformMCP: MCP Request<br/>{"method": "control_lighting", "params": {"zone": "living_room", "brightness": 30}}
        PlatformMCP->>PlatformMCP: Execute system command
        PlatformMCP->>PlatformMCP: Communicate with smart bulbs
        PlatformMCP-->>Core: MCP Response<br/>{"result": "Lights dimmed to 30%"}
    end
    
    Core->>Core: Synthesize response
    Core->>User: "Playing relaxing music and dimmed the lights in living room"
```

### **Service Discovery & Registration**
```mermaid
sequenceDiagram
    participant ModuleNew as New MCP Module
    participant Discovery as Service Discovery
    participant MQTT as MQTT Broker
    participant Core as Core Orchestrator
    
    Note over ModuleNew,Core: New module starts up
    
    ModuleNew->>ModuleNew: Initialize MCP server
    ModuleNew->>Discovery: Register service<br/>{name, capabilities, endpoint, health}
    Discovery->>MQTT: Publish service announcement
    
    MQTT->>Core: New service available
    Core->>Discovery: Query service capabilities
    Discovery-->>Core: Return full service spec
    
    Core->>ModuleNew: Health check ping
    ModuleNew-->>Core: Health status OK
    
    Core->>Core: Add to available services
    
    Note over ModuleNew,Core: Module now available for user commands
```

## 🏠 **Home Environment Integration**

### **Smart Home Ecosystem**
```mermaid
graph TB
    subgraph "🏠 Home Environment"
        Kitchen[Kitchen Hub<br/>Voice + Display]
        LivingRoom[Living Room<br/>Smart TV + Speakers]
        Bedroom[Bedroom<br/>Smart Lights + Climate]
        Office[Home Office<br/>Desktop + Automation]
    end
    
    subgraph "🧠 MIA Core"
        CoreHome[Core Orchestrator<br/>Home Instance]
        AudioHome[Audio Assistant]
        HomeAuto[Home Automation]
        Security[Security & ANPR]
    end
    
    subgraph "🔌 Smart Devices"
        Lights[Smart Lights<br/>Philips Hue, LIFX]
        Climate[Climate Control<br/>Nest, Ecobee]
        Cameras[Security Cameras<br/>ONVIF, RTSP]
        Speakers[Multi-Room Audio<br/>Sonos, Chromecast]
        Appliances[Smart Appliances<br/>Fridge, Oven, Washer]
    end
    
    subgraph "🌐 Protocols"
        Matter[Matter/Thread]
        Zigbee[Zigbee Hub]
        WiFi[WiFi Direct]
        BLE[Bluetooth LE]
    end
    
    Kitchen --> CoreHome
    LivingRoom --> CoreHome
    Bedroom --> CoreHome
    Office --> CoreHome
    
    CoreHome --> AudioHome
    CoreHome --> HomeAuto
    CoreHome --> Security
    
    HomeAuto --> Matter
    HomeAuto --> Zigbee
    AudioHome --> WiFi
    Security --> BLE
    
    Matter --> Lights
    Matter --> Climate
    Zigbee --> Appliances
    WiFi --> Speakers
    BLE --> Cameras
    
    classDef homeEnv fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef aiCore fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef devices fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef protocols fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class Kitchen,LivingRoom,Bedroom,Office homeEnv
    class CoreHome,AudioHome,HomeAuto,Security aiCore
    class Lights,Climate,Cameras,Speakers,Appliances devices
    class Matter,Zigbee,WiFi,BLE protocols
```

## 🚗 **Automotive Integration (Existing)**

### **Car System Architecture**
```mermaid
graph TB
    subgraph "🚗 Vehicle Environment"
        Dashboard[Car Dashboard<br/>Android App]
        OBD[OBD-2 Port<br/>Diagnostic Access]
        Cameras[Vehicle Cameras<br/>ANPR + Security]
        Audio[Car Audio System<br/>Speakers + Mic]
    end
    
    subgraph "💻 Processing Units"
        ESP32[ESP32 DevKit<br/>CAN Gateway]
        Android[Android Phone<br/>Main Computing]
        Pi[Raspberry Pi<br/>Optional Gateway]
    end
    
    subgraph "📡 Communication"
        CAN[CAN Bus<br/>Vehicle Network]
        BT[Bluetooth LE<br/>Local Comm]
        WiFi[WiFi Hotspot<br/>Internet Access]
        Cell[Cellular<br/>4G/5G Data]
    end
    
    subgraph "☁️ AI Services"
        CoreCar[Core Orchestrator<br/>Car Instance]
        DiagCar[OBD Diagnostics]
        ANPRCar[License Plate Recognition]
        NavCar[Navigation & Maps]
    end
    
    Dashboard --> Android
    OBD --> ESP32
    Cameras --> Pi
    Audio --> Android
    
    ESP32 --> CAN
    Android --> BT
    Android --> WiFi
    Pi --> WiFi
    
    Android --> CoreCar
    ESP32 --> DiagCar
    Pi --> ANPRCar
    Android --> NavCar
    
    CoreCar --> BT
    DiagCar --> CAN
    ANPRCar --> WiFi
    NavCar --> Cell
    
    classDef vehicle fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef processing fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef communication fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef aiServices fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class Dashboard,OBD,Cameras,Audio vehicle
    class ESP32,Android,Pi processing
    class CAN,BT,WiFi,Cell communication
    class CoreCar,DiagCar,ANPRCar,NavCar aiServices
```

## 💻 **Cross-Platform Architecture**

### **Platform Controller Matrix**
```mermaid
graph LR
    subgraph "🧠 Core Orchestrator"
        Core[MCP Host<br/>Platform Agnostic]
    end
    
    subgraph "🐧 Linux"
        LinuxCtrl[Linux Controller<br/>systemd, apt, bash]
        LinuxAudio[PipeWire/ALSA<br/>Audio Engine]
        LinuxApps[Desktop Apps<br/>D-Bus Integration]
    end
    
    subgraph "🪟 Windows"
        WinCtrl[Windows Controller<br/>PowerShell, WMI]
        WinAudio[WASAPI<br/>Audio Engine]
        WinApps[Windows Apps<br/>COM Integration]
    end
    
    subgraph "🍎 macOS"
        MacCtrl[macOS Controller<br/>AppleScript, defaults]
        MacAudio[Core Audio<br/>Audio Engine]
        MacApps[macOS Apps<br/>NSWorkspace]
    end
    
    subgraph "🤖 Android"
        AndroidCtrl[Android Bridge<br/>ADB, Intents]
        AndroidAudio[AudioManager<br/>Media Control]
        AndroidApps[Package Manager<br/>App Control]
    end
    
    subgraph "📱 iOS"
        iOSCtrl[iOS Bridge<br/>Shortcuts, Automation]
        iOSAudio[AVAudioSession<br/>Limited Control]
        iOSApps[App Store Connect<br/>Limited Access]
    end
    
    Core --> LinuxCtrl
    Core --> WinCtrl
    Core --> MacCtrl
    Core --> AndroidCtrl
    Core --> iOSCtrl
    
    LinuxCtrl --> LinuxAudio
    LinuxCtrl --> LinuxApps
    WinCtrl --> WinAudio
    WinCtrl --> WinApps
    MacCtrl --> MacAudio
    MacCtrl --> MacApps
    AndroidCtrl --> AndroidAudio
    AndroidCtrl --> AndroidApps
    iOSCtrl --> iOSAudio
    iOSCtrl --> iOSApps
    
    classDef core fill:#9c27b0,stroke:#4a148c,stroke-width:3px,color:#fff
    classDef linux fill:#ff9800,stroke:#e65100,stroke-width:2px
    classDef windows fill:#2196f3,stroke:#0d47a1,stroke-width:2px
    classDef macos fill:#607d8b,stroke:#263238,stroke-width:2px
    classDef android fill:#4caf50,stroke:#1b5e20,stroke-width:2px
    classDef ios fill:#9e9e9e,stroke:#212121,stroke-width:2px
    
    class Core core
    class LinuxCtrl,LinuxAudio,LinuxApps linux
    class WinCtrl,WinAudio,WinApps windows
    class MacCtrl,MacAudio,MacApps macos
    class AndroidCtrl,AndroidAudio,AndroidApps android
    class iOSCtrl,iOSAudio,iOSApps ios
```

## 🔐 **Security & Privacy Architecture**

### **Privacy-First Data Flow**
```mermaid
flowchart TD
    subgraph "🎤 Input Layer"
        Voice[Voice Input]
        Touch[Touch/Gesture]
        Sensors[Sensor Data]
    end
    
    subgraph "🛡️ Privacy Layer"
        LocalSTT[Local Speech-to-Text<br/>Whisper/OpenAI]
        Anonymize[Data Anonymization<br/>Remove PII]
        Encrypt[Local Encryption<br/>AES-256]
    end
    
    subgraph "🧠 Processing Layer"
        NLP[Local NLP<br/>Intent Recognition]
        Context[Context Management<br/>No Cloud Storage]
        Decision[Decision Engine<br/>Local Rules]
    end
    
    subgraph "💾 Storage Layer"
        LocalDB[(Local Database<br/>SQLite/PostgreSQL)]
        TempCache[(Temporary Cache<br/>Redis)]
        UserPrefs[(User Preferences<br/>Encrypted)]
    end
    
    subgraph "☁️ Optional Cloud"
        CloudAPIs[External APIs<br/>Weather, Maps]
        CloudBackup[Encrypted Backup<br/>User Controlled]
    end
    
    Voice --> LocalSTT
    Touch --> Anonymize
    Sensors --> Encrypt
    
    LocalSTT --> NLP
    Anonymize --> Context
    Encrypt --> Decision
    
    NLP --> LocalDB
    Context --> TempCache
    Decision --> UserPrefs
    
    Decision -.-> CloudAPIs
    UserPrefs -.-> CloudBackup
    
    classDef input fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef privacy fill:#e8f5e8,stroke:#388e3c,stroke-width:3px
    classDef processing fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef storage fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef cloud fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,stroke-dasharray: 5 5
    
    class Voice,Touch,Sensors input
    class LocalSTT,Anonymize,Encrypt privacy
    class NLP,Context,Decision processing
    class LocalDB,TempCache,UserPrefs storage
    class CloudAPIs,CloudBackup cloud
```

## 🚀 **Deployment Architecture**

### **Container Orchestration**
```mermaid
graph TB
    subgraph "🐳 Docker Compose Stack"
        subgraph "Core Services"
            CoreContainer[mia-core<br/>Orchestrator]
            DiscoveryContainer[ai-servis-discovery<br/>Service Registry]
            MQTTContainer[eclipse-mosquitto<br/>Message Broker]
        end
        
        subgraph "AI Modules"
            AudioContainer[ai-servis-audio<br/>Audio Assistant]
            PlatformContainer[ai-servis-platform<br/>Platform Controller]
            HomeContainer[ai-servis-home<br/>Home Automation]
            SecurityContainer[ai-servis-security<br/>Security & ANPR]
        end
        
        subgraph "Support Services"
            MonitorContainer[prometheus<br/>Monitoring]
            LogsContainer[grafana<br/>Visualization]
            StorageContainer[postgresql<br/>Persistent Storage]
        end
    end
    
    subgraph "🌐 Network Layer"
        Frontend[Frontend Network<br/>User Interfaces]
        Backend[Backend Network<br/>Service Communication]
        External[External Network<br/>Internet Access]
    end
    
    subgraph "💾 Persistent Volumes"
        ConfigVol[Configuration<br/>Volume]
        DataVol[Data<br/>Volume]
        LogsVol[Logs<br/>Volume]
    end
    
    CoreContainer --> DiscoveryContainer
    CoreContainer --> MQTTContainer
    CoreContainer --> AudioContainer
    CoreContainer --> PlatformContainer
    CoreContainer --> HomeContainer
    CoreContainer --> SecurityContainer
    
    MonitorContainer --> LogsContainer
    StorageContainer --> DataVol
    
    Frontend --> CoreContainer
    Backend --> MQTTContainer
    External --> CoreContainer
    
    CoreContainer --> ConfigVol
    AudioContainer --> DataVol
    LogsContainer --> LogsVol
    
    classDef core fill:#9c27b0,stroke:#4a148c,stroke-width:3px,color:#fff
    classDef modules fill:#2196f3,stroke:#0d47a1,stroke-width:2px
    classDef support fill:#ff9800,stroke:#e65100,stroke-width:2px
    classDef network fill:#4caf50,stroke:#1b5e20,stroke-width:2px
    classDef storage fill:#607d8b,stroke:#263238,stroke-width:2px
    
    class CoreContainer,DiscoveryContainer,MQTTContainer core
    class AudioContainer,PlatformContainer,HomeContainer,SecurityContainer modules
    class MonitorContainer,LogsContainer,StorageContainer support
    class Frontend,Backend,External network
    class ConfigVol,DataVol,LogsVol storage
```

### **Multi-Environment Deployment**
```mermaid
flowchart LR
    subgraph "Development"
        Dev[Local Docker<br/>Hot Reload<br/>Debug Mode]
    end
    
    subgraph "Testing"
        Test[Pi Simulation<br/>Integration Tests<br/>CI/CD Pipeline]
    end
    
    subgraph "Production"
        subgraph "Home Desktop"
            HomeAMD[AMD64 Desktop<br/>Full Features]
            HomeARM[ARM64 Pi<br/>Limited Resources]
        end
        
        subgraph "Automotive"
            CarAndroid[Android Phone<br/>Mobile App]
            CarESP[ESP32<br/>Hardware Bridge]
            CarPi[Raspberry Pi<br/>Edge Gateway]
        end
        
        subgraph "Enterprise"
            EntServer[Dedicated Server<br/>Multi-Tenant]
            EntK8s[Kubernetes<br/>Scalable Deployment]
        end
    end
    
    Dev --> Test
    Test --> HomeAMD
    Test --> HomeARM
    Test --> CarAndroid
    Test --> CarESP
    Test --> CarPi
    Test --> EntServer
    Test --> EntK8s
    
    classDef dev fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef test fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef prod fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef enterprise fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class Dev dev
    class Test test
    class HomeAMD,HomeARM,CarAndroid,CarESP,CarPi prod
    class EntServer,EntK8s enterprise
```

## 📊 **Performance & Scaling**

### **Performance Monitoring Dashboard**
```mermaid
graph TB
    subgraph "📊 Metrics Collection"
        AppMetrics[Application Metrics<br/>Response Times, Errors]
        SystemMetrics[System Metrics<br/>CPU, Memory, Network]
        BusinessMetrics[Business Metrics<br/>Voice Commands, User Actions]
    end
    
    subgraph "📈 Monitoring Stack"
        Prometheus[Prometheus<br/>Time Series DB]
        Grafana[Grafana<br/>Visualization]
        AlertManager[Alert Manager<br/>Notifications]
    end
    
    subgraph "🔍 Observability"
        Traces[Distributed Tracing<br/>Jaeger]
        Logs[Log Aggregation<br/>ELK Stack]
        APM[Application Performance<br/>Monitoring]
    end
    
    subgraph "⚡ Performance Targets"
        VoiceLatency[Voice Command<br/>< 500ms]
        ModuleStartup[Module Startup<br/>< 10s]
        MemoryUsage[Memory Usage<br/>< 2GB total]
        CPUUsage[CPU Usage<br/>< 20% idle]
    end
    
    AppMetrics --> Prometheus
    SystemMetrics --> Prometheus
    BusinessMetrics --> Prometheus
    
    Prometheus --> Grafana
    Prometheus --> AlertManager
    
    Grafana --> Traces
    Grafana --> Logs
    Grafana --> APM
    
    APM --> VoiceLatency
    APM --> ModuleStartup
    APM --> MemoryUsage
    APM --> CPUUsage
    
    classDef metrics fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef monitoring fill:#e8f5e8,stroke:#388e3c,stroke-width:2px
    classDef observability fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef performance fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    
    class AppMetrics,SystemMetrics,BusinessMetrics metrics
    class Prometheus,Grafana,AlertManager monitoring
    class Traces,Logs,APM observability
    class VoiceLatency,ModuleStartup,MemoryUsage,CPUUsage performance
```

---

## 🎯 **Usage Examples**

### **Cooking Assistant Flow**
```mermaid
journey
    title Cooking Assistant User Journey
    section Preparation
      Start cooking: 5: User
      "AI, play cooking music": 5: User
      Music starts playing: 5: AI Audio Assistant
      Switch to bluetooth headphones: 4: User
      Audio switches seamlessly: 5: AI Audio Assistant
    section Active Cooking
      Set 15min pasta timer: 4: User
      Timer set via system: 5: Platform Controller
      Check recipe step: 3: User
      Read recipe aloud: 4: AI Audio Assistant
    section Interruptions
      Phone rings: 3: External
      Lower music volume: 5: AI Audio Assistant
      Take call on speaker: 4: Communications Module
      Resume cooking music: 5: AI Audio Assistant
    section Completion
      Timer notification: 5: Platform Controller
      Turn off stove reminder: 4: Security Module
      Clean-up playlist: 4: AI Audio Assistant
```

### **Work-from-Home Productivity**
```mermaid
journey
    title Work-from-Home Productivity Journey
    section Morning Setup
      "AI, start work mode": 5: User
      Close social media apps: 5: Platform Controller
      Start focus music: 4: AI Audio Assistant
      Set status to busy: 4: Communications Module
    section Meeting Preparation
      "Join 2 PM meeting": 4: User
      Open calendar app: 5: Platform Controller
      Join Zoom automatically: 5: Platform Controller
      Mute microphone: 4: AI Audio Assistant
    section Interruptions
      Message from team: 3: Communications Module
      "Tell team I'm in meeting": 4: User
      Send auto-response: 5: Communications Module
      Continue meeting: 5: User
    section End of Day
      "AI, end work mode": 5: User
      Save work documents: 5: Platform Controller
      Close work applications: 4: Platform Controller
      Switch to relaxation playlist: 5: AI Audio Assistant
```

These diagrams provide a comprehensive view of the MIA Universal architecture, from high-level system context to detailed component interactions and user journeys. They serve as both documentation and implementation guides for the development team.