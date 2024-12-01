-- Create images table
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    type TEXT CHECK(type IN ('SD', 'Comfy')) NOT NULL,
    details TEXT,
    is_hidden BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create keywords table
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create image_keywords junction table
CREATE TABLE IF NOT EXISTS image_keywords (
    image_id INTEGER,
    keyword_id INTEGER,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE,
    FOREIGN KEY (keyword_id) REFERENCES keywords(id) ON DELETE CASCADE,
    PRIMARY KEY (image_id, keyword_id)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_images_type ON images(type);
CREATE INDEX IF NOT EXISTS idx_images_is_hidden ON images(is_hidden);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keywords(keyword);
