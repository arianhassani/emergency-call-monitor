DROP TABLE IF EXISTS emergency_calls;

CREATE TABLE emergency_calls (
    call_id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    caller_id VARCHAR(32) NOT NULL,
    tower_id VARCHAR(32) NOT NULL,
    latency_ms INTEGER NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('SUCCESS', 'FAILED')),
    failure_reason TEXT
);

CREATE INDEX idx_emergency_calls_timestamp ON emergency_calls(timestamp);
CREATE INDEX idx_emergency_calls_status ON emergency_calls(status);
CREATE INDEX idx_emergency_calls_tower ON emergency_calls(tower_id);