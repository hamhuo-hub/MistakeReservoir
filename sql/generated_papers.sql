/*
 Navicat Premium Dump SQL

 Source Server         : reservoir_1
 Source Server Type    : SQLite
 Source Server Version : 3045000 (3.45.0)
 Source Schema         : main

 Target Server Type    : SQLite
 Target Server Version : 3045000 (3.45.0)
 File Encoding         : 65001

 Date: 13/02/2026 00:29:53
*/

PRAGMA foreign_keys = false;

-- ----------------------------
-- Table structure for generated_papers
-- ----------------------------
DROP TABLE IF EXISTS "generated_papers";
CREATE TABLE "generated_papers" (
  "uuid" TEXT,
  "created_at" TEXT,
  "question_ids" TEXT,
  PRIMARY KEY ("uuid")
);

PRAGMA foreign_keys = true;
