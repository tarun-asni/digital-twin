-- Create the devicestatus enum type if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'devicestatus') THEN
        CREATE TYPE devicestatus AS ENUM ('CREATED', 'ACTIVE', 'INACTIVE', 'REGISTERED', 'STREAMING', 'FAIL_TO_STREAM');
    END IF;
END$$;

-- Create the devices table if it doesn't exist
CREATE TABLE IF NOT EXISTS devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    status devicestatus DEFAULT 'CREATED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    heartbeat_time TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    configured_heartbeat_interval INTEGER
);

-- Create the certificates table if it doesn't exist
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    cert_data TEXT NOT NULL,
    key_data TEXT NOT NULL,
    aes_key VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the keys table if it doesn't exist
CREATE TABLE IF NOT EXISTS keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_id UUID NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    public_key TEXT NOT NULL,
    private_key TEXT NOT NULL,
    aes_key VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);

-- Create the inventories table if it doesn't exist
CREATE TABLE IF NOT EXISTS inventories (
    id SERIAL PRIMARY KEY,
    device_id UUID REFERENCES devices(id) ON DELETE CASCADE,
    hw_data JSONB,
    sw_data JSONB,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'utc')
);