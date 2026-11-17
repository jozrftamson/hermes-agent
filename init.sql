-- Initialize Prompts Database
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    version VARCHAR(20),
    system_prompt TEXT,
    description TEXT,
    tags TEXT[],
    model VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    checksum VARCHAR(32)
);

CREATE TABLE IF NOT EXISTS deployments (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(20),
    response JSONB,
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompts(prompt_id)
);

CREATE TABLE IF NOT EXISTS executions (
    id SERIAL PRIMARY KEY,
    prompt_id VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    input_text TEXT,
    output_text TEXT,
    latency_ms INTEGER,
    status VARCHAR(20),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prompt_id) REFERENCES prompts(prompt_id)
);

CREATE TABLE IF NOT EXISTS platform_health (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(50) NOT NULL,
    healthy BOOLEAN DEFAULT TRUE,
    latency_ms INTEGER,
    last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE INDEX idx_prompts_category ON prompts(category);
CREATE INDEX idx_deployments_platform ON deployments(platform);
CREATE INDEX idx_executions_prompt_id ON executions(prompt_id);
CREATE INDEX idx_executions_executed_at ON executions(executed_at DESC);
