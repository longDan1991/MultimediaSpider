from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "users" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(50) NOT NULL,
    "logtoId" VARCHAR(50) NOT NULL
);
CREATE TABLE IF NOT EXISTS "cookies" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "value" TEXT NOT NULL,
    "platform" VARCHAR(50) NOT NULL,
    "platform_account" JSON,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "sessions" (
    "id" VARCHAR(64) NOT NULL  PRIMARY KEY,
    "data" JSON NOT NULL,
    "expiry" TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS "keywords" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "value" VARCHAR(255) NOT NULL,
    "platform_info" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "xhs_notes" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "notes_id" VARCHAR(255) NOT NULL UNIQUE,
    "model_type" VARCHAR(50) NOT NULL,
    "xsec_token" VARCHAR(255) NOT NULL,
    "type" VARCHAR(50) NOT NULL,
    "display_title" VARCHAR(255),
    "user_id" VARCHAR(255) NOT NULL,
    "nickname" VARCHAR(255) NOT NULL,
    "avatar" VARCHAR(1024) NOT NULL,
    "liked" INT NOT NULL,
    "liked_count" VARCHAR(50) NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "keyword_notes" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "keyword_id" INT NOT NULL REFERENCES "keywords" ("id") ON DELETE CASCADE,
    "note_id" INT NOT NULL REFERENCES "xhs_notes" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_keyword_not_keyword_a36b99" UNIQUE ("keyword_id", "note_id")
);
CREATE TABLE IF NOT EXISTS "user_keyword" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "is_monitored" INT NOT NULL  DEFAULT 1,
    "created_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "platforms" JSON NOT NULL,
    "keyword_id" INT NOT NULL REFERENCES "keywords" ("id") ON DELETE CASCADE,
    "user_id" INT NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    CONSTRAINT "uid_user_keywor_user_id_0e3ef4" UNIQUE ("user_id", "keyword_id")
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
