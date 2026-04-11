-- StarLoom: Content IR columns (run once on MySQL)
-- articles.body_ir, daily_guides.content_ir, reports.content_ir

ALTER TABLE articles ADD COLUMN body_ir JSON NULL COMMENT 'Content IR v1 JSON' AFTER body;
ALTER TABLE daily_guides ADD COLUMN content_ir JSON NULL COMMENT 'Content IR v1 JSON' AFTER content;
ALTER TABLE reports ADD COLUMN content_ir JSON NULL COMMENT 'Content IR v1 JSON' AFTER content;
