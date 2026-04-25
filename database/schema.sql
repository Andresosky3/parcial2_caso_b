-- Esquema PixelForge Studio
CREATE DATABASE pixelforge_db;
\c pixelforge_db;

CREATE TABLE jugadores (
    id            SERIAL PRIMARY KEY,
    nickname      VARCHAR(20) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) DEFAULT 'JUGADOR',
    estado        VARCHAR(20) DEFAULT 'activo',
    created_at    TIMESTAMP DEFAULT NOW(),
    last_login    TIMESTAMP
);

CREATE TABLE partidas (
    id            SERIAL PRIMARY KEY,
    session_token UUID UNIQUE NOT NULL,
    jugador_id    INT REFERENCES jugadores(id),
    started_at    TIMESTAMP DEFAULT NOW(),
    ended_at      TIMESTAMP,
    usado         BOOLEAN DEFAULT FALSE
);

CREATE TABLE puntuaciones (
    id              SERIAL PRIMARY KEY,
    jugador_id      INT REFERENCES jugadores(id),
    partida_id      INT REFERENCES partidas(id),
    score           INT NOT NULL,
    level_reached   INT NOT NULL,
    coins_collected INT DEFAULT 0,
    time_remaining  INT DEFAULT 0,
    estado          VARCHAR(20) DEFAULT 'valida',
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE log_anticheat (
    id              SERIAL PRIMARY KEY,
    jugador_id      INT REFERENCES jugadores(id),
    ip_address      VARCHAR(45),
    datos_enviados  JSONB,
    razon_rechazo   VARCHAR(255),
    timestamp       TIMESTAMP DEFAULT NOW()
);

CREATE USER game_app WITH PASSWORD 'CHANGE_ME';
GRANT CONNECT ON DATABASE pixelforge_db TO game_app;
GRANT USAGE ON SCHEMA public TO game_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO game_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO game_app;
