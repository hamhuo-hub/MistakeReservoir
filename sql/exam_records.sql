/*
 Navicat Premium Dump SQL

 Source Server         : reservoir_1
 Source Server Type    : SQLite
 Source Server Version : 3045000 (3.45.0)
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3045000 (3.45.0)
 File Encoding         : 65001

 Date: 13/02/2026 00:30:04
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for exam_records
-- ----------------------------
DROP TABLE IF EXISTS "exam_records";
CREATE TABLE "exam_records" (
  "id" INTEGER PRIMARY KEY AUTOINCREMENT,
  "upload_date" TEXT,
  "filename" TEXT,
  "total_score" REAL,
  "total_accuracy" REAL,
  "module_stats" TEXT
);

-- ----------------------------
-- Auto increment value for exam_records
-- ----------------------------
UPDATE "sqlite_sequence" SET seq = 4 WHERE name = 'exam_records';

PRAGMA foreign_keys = true;
