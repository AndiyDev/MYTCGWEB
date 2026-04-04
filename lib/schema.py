from sqlalchemy import text


SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id CHAR(36) PRIMARY KEY,
        username VARCHAR(64) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        display_name VARCHAR(128),
        avatar_url TEXT,
        reputation_level INT DEFAULT 1,
        role VARCHAR(16) DEFAULT 'USER',
        failed_login_attempts INT DEFAULT 0,
        locked_until TIMESTAMP NULL,
        last_login_at TIMESTAMP NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS tcg_sets (
        id CHAR(36) PRIMARY KEY,
        game VARCHAR(32) NOT NULL,
        series VARCHAR(128),
        set_name VARCHAR(128) NOT NULL,
        set_code VARCHAR(32),
        total_cards INT DEFAULT 0,
        logo_path TEXT,
        symbol_path TEXT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS tcg_cards (
        id CHAR(36) PRIMARY KEY,
        set_id CHAR(36) NOT NULL,
        card_number VARCHAR(16),
        name VARCHAR(128) NOT NULL,
        rarity VARCHAR(64),
        image_url TEXT,
        has_normal TINYINT(1) DEFAULT 1,
        has_holofoil TINYINT(1) DEFAULT 0,
        has_reverse_holo TINYINT(1) DEFAULT 0,
        FOREIGN KEY (set_id) REFERENCES tcg_sets(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS card_instances (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        card_id CHAR(36) NOT NULL,
        variant VARCHAR(32) DEFAULT 'Normal',
        condition_label VARCHAR(32) DEFAULT 'Near Mint',
        state_label VARCHAR(32) DEFAULT 'PLACEHOLDER',
        is_public TINYINT(1) DEFAULT 0,
        locked_by_listing_id CHAR(36),
        locked_by_post_id CHAR(36),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (card_id) REFERENCES tcg_cards(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS listings (
        id CHAR(36) PRIMARY KEY,
        item_id CHAR(36) NOT NULL,
        seller_id CHAR(36) NOT NULL,
        price DECIMAL(12,2),
        currency VARCHAR(8) DEFAULT 'SEK',
        notes TEXT,
        status VARCHAR(16) DEFAULT 'DRAFT',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES card_instances(id) ON DELETE CASCADE,
        FOREIGN KEY (seller_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS groups (
        id CHAR(36) PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS group_members (
        id CHAR(36) PRIMARY KEY,
        group_id CHAR(36) NOT NULL,
        user_id CHAR(36) NOT NULL,
        role VARCHAR(16) DEFAULT 'MEMBER',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_group_user (group_id, user_id),
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS group_posts (
        id CHAR(36) PRIMARY KEY,
        group_id CHAR(36) NOT NULL,
        author_id CHAR(36) NOT NULL,
        category VARCHAR(16) DEFAULT 'POST',
        trade_type VARCHAR(16),
        offered_item_id CHAR(36),
        requested_card_id CHAR(36),
        content TEXT,
        status VARCHAR(16) DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
        FOREIGN KEY (author_id) REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS room_items (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        item_id CHAR(36) NOT NULL,
        slot_type VARCHAR(32),
        x_pos FLOAT,
        y_pos FLOAT,
        rotation FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES card_instances(id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id CHAR(36) PRIMARY KEY,
        user_id CHAR(36),
        action VARCHAR(64) NOT NULL,
        meta_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_audit_user (user_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
]


ALTER_SQL = [
    "ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'USER'",
    "ALTER TABLE users ADD COLUMN failed_login_attempts INT DEFAULT 0",
    "ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL",
    "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL",
]


def init_schema(engine):
    with engine.begin() as conn:
        for statement in SCHEMA_SQL:
            conn.execute(text(statement))
        for statement in ALTER_SQL:
            try:
                conn.execute(text(statement))
            except Exception:
                pass
