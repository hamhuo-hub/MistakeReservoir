/*
 Navicat Premium Dump SQL

 Source Server         : reservoir_1
 Source Server Type    : SQLite
 Source Server Version : 3045000 (3.45.0)
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3045000 (3.45.0)
 File Encoding         : 65001

 Date: 13/02/2026 00:29:46
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for materials
-- ----------------------------
DROP TABLE IF EXISTS "materials";
CREATE TABLE "materials" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "source_id" INTEGER,
  "content_html" TEXT,
  "images" TEXT,
  "type" TEXT
);

-- ----------------------------
-- Auto increment value for materials
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 12 WHERE name = 'materials';

PRAGMA foreign_keys = true;
