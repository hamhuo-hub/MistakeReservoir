/*
 Navicat Premium Dump SQL

 Source Server         : reservoir_1
 Source Server Type    : SQLite
 Source Server Version : 3045000 (3.45.0)
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3045000 (3.45.0)
 File Encoding         : 65001

 Date: 13/02/2026 00:29:37
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for questions
-- ----------------------------
DROP TABLE IF EXISTS "questions";
CREATE TABLE "questions" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "source_id" INTEGER,
  "material_id" INTEGER,
  "original_num" INTEGER,
  "type" TEXT,
  "content_html" TEXT,
  "options_html" TEXT,
  "answer_html" TEXT,
  "images" TEXT,
  FOREIGN KEY ("source_id") REFERENCES "sources" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION,
  FOREIGN KEY ("material_id") REFERENCES "materials" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
);

-- ----------------------------
-- Auto increment value for questions
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 164 WHERE name = 'questions';

PRAGMA foreign_keys = true;
