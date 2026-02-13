/*
 Navicat Premium Dump SQL

 Source Server         : reservoir_1
 Source Server Type    : SQLite
 Source Server Version : 3045000 (3.45.0)
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3045000 (3.45.0)
 File Encoding         : 65001

 Date: 13/02/2026 00:29:07
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for review_stats_copy1
-- ----------------------------
DROP TABLE IF EXISTS "review_stats_copy1";
CREATE TABLE "review_stats_copy1" (
  "question_id" INTEGER,
  "status" TEXT DEFAULT 'pool',
  "mistake_count" INTEGER DEFAULT 2,
  PRIMARY KEY ("question_id"),
  FOREIGN KEY ("question_id") REFERENCES "questions" ("id") ON DELETE CASCADE ON UPDATE NO ACTION
);

-- ----------------------------
-- Triggers structure for table review_stats_copy1
-- ----------------------------
CREATE TRIGGER "auto_delete_mastered_copy1"
AFTER UPDATE OF "mistake_count"
ON "review_stats_copy1"
WHEN NEW.mistake_count <= 0
BEGIN
                    DELETE FROM questions WHERE id = NEW.question_id;
                END;

PRAGMA foreign_keys = true;
