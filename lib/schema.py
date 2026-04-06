from sqlalchemy import text


TABLE_OPTIONS = "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"


BASE_TABLES = [
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
    ) """ + TABLE_OPTIONS + """;
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
    ) """ + TABLE_OPTIONS + """;
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
    ) """ + TABLE_OPTIONS + """;
    """,
]


DEPENDENT_TABLES = [
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
    ) """ + TABLE_OPTIONS + """;
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
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS groups (
        id CHAR(36) PRIMARY KEY,
        name VARCHAR(128) NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
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
    ) """ + TABLE_OPTIONS + """;
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
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS room_items (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        item_id CHAR(36) NOT NULL,
        slot_type VARCHAR(32),
        furniture_id CHAR(36),
        x_pos FLOAT,
        y_pos FLOAT,
        rotation FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES card_instances(id) ON DELETE CASCADE
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS room_furniture (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        type VARCHAR(32) NOT NULL,
        x_pos FLOAT,
        y_pos FLOAT,
        rotation FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS sealed_products (
        id VARCHAR(64) PRIMARY KEY,
        game VARCHAR(32) NOT NULL,
        type VARCHAR(32) NOT NULL,
        set_id CHAR(36),
        name VARCHAR(255) NOT NULL,
        image_url TEXT,
        cards_per_pack INT DEFAULT 10,
        msrp DECIMAL(12,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS sealed_instances (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        sealed_product_id VARCHAR(64) NOT NULL,
        purchase_price DECIMAL(12,2) DEFAULT 0,
        purchase_date DATE NULL,
        state VARCHAR(16) DEFAULT 'SEALED',
        opened_at TIMESTAMP NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS booster_openings (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        sealed_instance_id CHAR(36) NOT NULL,
        set_id CHAR(36),
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_spent DECIMAL(12,2) DEFAULT 0,
        estimated_value DECIMAL(12,2) DEFAULT 0,
        platform_fee_pct DECIMAL(5,2) DEFAULT 10,
        net_value DECIMAL(12,2) DEFAULT 0,
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    ) """ + TABLE_OPTIONS + """;
    """,
    """
    CREATE TABLE IF NOT EXISTS booster_opening_cards (
        id CHAR(36) PRIMARY KEY,
        opening_id CHAR(36) NOT NULL,
        card_id CHAR(36) NOT NULL,
        variant VARCHAR(32) DEFAULT 'Normal',
        market_value_snapshot DECIMAL(12,2) DEFAULT 0
    ) """ + TABLE_OPTIONS + """;
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
    ) """ + TABLE_OPTIONS + """;
    """,
]


FALLBACK_TABLES = {
    "card_instances": """
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "group_members": """
    CREATE TABLE IF NOT EXISTS group_members (
        id CHAR(36) PRIMARY KEY,
        group_id CHAR(36) NOT NULL,
        user_id CHAR(36) NOT NULL,
        role VARCHAR(16) DEFAULT 'MEMBER',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_group_user (group_id, user_id)
    ) """ + TABLE_OPTIONS + """;
    """,
    "group_posts": """
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "listings": """
    CREATE TABLE IF NOT EXISTS listings (
        id CHAR(36) PRIMARY KEY,
        item_id CHAR(36) NOT NULL,
        seller_id CHAR(36) NOT NULL,
        price DECIMAL(12,2),
        currency VARCHAR(8) DEFAULT 'SEK',
        notes TEXT,
        status VARCHAR(16) DEFAULT 'DRAFT',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "room_items": """
    CREATE TABLE IF NOT EXISTS room_items (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        item_id CHAR(36) NOT NULL,
        slot_type VARCHAR(32),
        furniture_id CHAR(36),
        x_pos FLOAT,
        y_pos FLOAT,
        rotation FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "room_furniture": """
    CREATE TABLE IF NOT EXISTS room_furniture (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        type VARCHAR(32) NOT NULL,
        x_pos FLOAT,
        y_pos FLOAT,
        rotation FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "sealed_products": """
    CREATE TABLE IF NOT EXISTS sealed_products (
        id VARCHAR(64) PRIMARY KEY,
        game VARCHAR(32) NOT NULL,
        type VARCHAR(32) NOT NULL,
        set_id CHAR(36),
        name VARCHAR(255) NOT NULL,
        image_url TEXT,
        cards_per_pack INT DEFAULT 10,
        msrp DECIMAL(12,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "sealed_instances": """
    CREATE TABLE IF NOT EXISTS sealed_instances (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        sealed_product_id VARCHAR(64) NOT NULL,
        purchase_price DECIMAL(12,2) DEFAULT 0,
        purchase_date DATE NULL,
        state VARCHAR(16) DEFAULT 'SEALED',
        opened_at TIMESTAMP NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) """ + TABLE_OPTIONS + """;
    """,
    "booster_openings": """
    CREATE TABLE IF NOT EXISTS booster_openings (
        id CHAR(36) PRIMARY KEY,
        owner_id CHAR(36) NOT NULL,
        sealed_instance_id CHAR(36) NOT NULL,
        set_id CHAR(36),
        opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_spent DECIMAL(12,2) DEFAULT 0,
        estimated_value DECIMAL(12,2) DEFAULT 0,
        platform_fee_pct DECIMAL(5,2) DEFAULT 10,
        net_value DECIMAL(12,2) DEFAULT 0
    ) """ + TABLE_OPTIONS + """;
    """,
    "booster_opening_cards": """
    CREATE TABLE IF NOT EXISTS booster_opening_cards (
        id CHAR(36) PRIMARY KEY,
        opening_id CHAR(36) NOT NULL,
        card_id CHAR(36) NOT NULL,
        variant VARCHAR(32) DEFAULT 'Normal',
        market_value_snapshot DECIMAL(12,2) DEFAULT 0
    ) """ + TABLE_OPTIONS + """;
    """,
    "audit_logs": """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id CHAR(36) PRIMARY KEY,
        user_id CHAR(36),
        action VARCHAR(64) NOT NULL,
        meta_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_audit_user (user_id)
    ) """ + TABLE_OPTIONS + """;
    """,
}


ALTER_SQL = [
    "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)",
    "ALTER TABLE users ADD COLUMN display_name VARCHAR(128)",
    "ALTER TABLE users ADD COLUMN avatar_url TEXT",
    "ALTER TABLE users ADD COLUMN reputation_level INT DEFAULT 1",
    "ALTER TABLE users ENGINE=InnoDB",
    "ALTER TABLE tcg_sets ENGINE=InnoDB",
    "ALTER TABLE tcg_cards ENGINE=InnoDB",
    "ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    "ALTER TABLE tcg_sets CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    "ALTER TABLE tcg_cards CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    "ALTER TABLE users MODIFY id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    "ALTER TABLE tcg_cards MODIFY id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    "ALTER TABLE tcg_cards MODIFY set_id CHAR(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci",
    "ALTER TABLE users ADD COLUMN role VARCHAR(16) DEFAULT 'USER'",
    "ALTER TABLE users ADD COLUMN failed_login_attempts INT DEFAULT 0",
    "ALTER TABLE users ADD COLUMN locked_until TIMESTAMP NULL",
    "ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP NULL",
    "ALTER TABLE card_instances ADD COLUMN purchase_price DECIMAL(12,2) DEFAULT 0",
    "ALTER TABLE card_instances ADD COLUMN purchase_date DATE NULL",
    "ALTER TABLE room_items ADD COLUMN furniture_id CHAR(36)",
    "ALTER TABLE sealed_instances ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
]


def init_schema(engine):
    with engine.begin() as conn:
        for idx, statement in enumerate(BASE_TABLES, start=1):
            conn.execute(text(statement))
        for statement in ALTER_SQL:
            try:
                conn.execute(text(statement))
            except Exception:
                pass
        for statement in DEPENDENT_TABLES:
            try:
                conn.execute(text(statement))
            except Exception:
                fallback_done = False
                for table_name, fallback_sql in FALLBACK_TABLES.items():
                    if table_name in statement:
                        conn.execute(text(fallback_sql))
                        fallback_done = True
                        break
                if not fallback_done:
                    raise
