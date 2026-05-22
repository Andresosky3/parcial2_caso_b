CREATE TABLE IF NOT EXISTS jugadores (
    id SERIAL PRIMARY KEY,
    nickname VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'jugador',
    estado VARCHAR(30) NOT NULL DEFAULT 'activo',
    token_balance INT NOT NULL DEFAULT 0,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_method VARCHAR(20),
    mfa_secret_hash VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),
    ip_address VARCHAR(45),
    success BOOLEAN NOT NULL DEFAULT FALSE,
    reason VARCHAR(120),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS partidas (
    id SERIAL PRIMARY KEY,
    session_token UUID UNIQUE NOT NULL,
    jugador_id INT NOT NULL REFERENCES jugadores(id),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP,
    usado BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS puntuaciones (
    id SERIAL PRIMARY KEY,
    jugador_id INT NOT NULL REFERENCES jugadores(id),
    partida_id INT REFERENCES partidas(id),
    score INT NOT NULL,
    level_reached INT NOT NULL,
    estado VARCHAR(30) NOT NULL DEFAULT 'valida',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS log_anticheat (
    id SERIAL PRIMARY KEY,
    jugador_id INT REFERENCES jugadores(id),
    ip_address VARCHAR(45),
    datos_enviados JSONB,
    razon_rechazo TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS payment_cards (
    id SERIAL PRIMARY KEY,
    jugador_id INT NOT NULL REFERENCES jugadores(id),
    card_token UUID UNIQUE NOT NULL,
    last4 VARCHAR(4) NOT NULL,
    brand VARCHAR(30) NOT NULL,
    exp_month INT NOT NULL,
    exp_year INT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'activa',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS token_transactions (
    id SERIAL PRIMARY KEY,
    jugador_id INT NOT NULL REFERENCES jugadores(id),
    card_id INT REFERENCES payment_cards(id),
    transaction_type VARCHAR(30) NOT NULL,
    package_name VARCHAR(50),
    item_code VARCHAR(50),
    tokens_amount INT NOT NULL,
    price_cop INT DEFAULT 0,
    result VARCHAR(30) NOT NULL,
    last4 VARCHAR(4),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_items (
    id SERIAL PRIMARY KEY,
    jugador_id INT NOT NULL REFERENCES jugadores(id),
    item_code VARCHAR(50) NOT NULL,
    item_name VARCHAR(100) NOT NULL,
    tokens_spent INT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pdf_audit_logs (
    id SERIAL PRIMARY KEY,
    requested_by INT REFERENCES jugadores(id),
    report_type VARCHAR(50) NOT NULL,
    target_player_id INT,
    ip_address VARCHAR(45),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_puntuaciones_jugador ON puntuaciones(jugador_id);
CREATE INDEX IF NOT EXISTS idx_login_attempts_email_ip ON login_attempts(email, ip_address);
CREATE INDEX IF NOT EXISTS idx_token_transactions_jugador ON token_transactions(jugador_id);
