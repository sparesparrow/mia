-- AI-SERVIS Universal Database Initialization

-- Core tables
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    capabilities TEXT[],
    health_status VARCHAR(50) DEFAULT 'unknown',
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS commands_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    command_text TEXT NOT NULL,
    intent VARCHAR(255),
    confidence FLOAT,
    parameters JSONB,
    response TEXT,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audio_zones (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    devices TEXT[],
    volume INTEGER DEFAULT 50,
    is_active BOOLEAN DEFAULT FALSE,
    user_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_commands_log_user_id ON commands_log(user_id);
CREATE INDEX IF NOT EXISTS idx_commands_log_created_at ON commands_log(created_at);
CREATE INDEX IF NOT EXISTS idx_services_health_status ON services(health_status);
CREATE INDEX IF NOT EXISTS idx_audio_zones_is_active ON audio_zones(is_active);

-- Insert default data
INSERT INTO users (username, email) VALUES ('admin', 'admin@ai-servis.local') ON CONFLICT DO NOTHING;
