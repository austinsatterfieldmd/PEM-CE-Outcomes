-- =============================================================================
-- CE Outcomes Dashboard — Post-Migration Fixes
-- Migration 004: Reset sequences + backfill activity_id FKs
--
-- Run AFTER data migration (migrate_to_supabase.py) completes.
-- =============================================================================

-- ============================================================
-- 1. Reset SERIAL sequences to max(id) + 1
--    (Needed because IDs were explicitly inserted during migration)
-- ============================================================

-- Tables where IDs were preserved from SQLite
SELECT setval('questions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM questions));
SELECT setval('activities_id_seq', (SELECT COALESCE(MAX(id), 1) FROM activities));
SELECT setval('novel_entities_id_seq', (SELECT COALESCE(MAX(id), 1) FROM novel_entities));
SELECT setval('tag_proposals_id_seq', (SELECT COALESCE(MAX(id), 1) FROM tag_proposals));

-- Tables where IDs were auto-assigned (reset just in case)
-- NOTE: tags has no id column (PK is question_id, no sequence)
SELECT setval('performance_id_seq', (SELECT COALESCE(MAX(id), 1) FROM performance));
SELECT setval('question_activities_id_seq', (SELECT COALESCE(MAX(id), 1) FROM question_activities));
SELECT setval('demographic_performance_id_seq', (SELECT COALESCE(MAX(id), 1) FROM demographic_performance));
SELECT setval('novel_entity_occurrences_id_seq', (SELECT COALESCE(MAX(id), 1) FROM novel_entity_occurrences));
SELECT setval('user_defined_values_id_seq', (SELECT COALESCE(MAX(id), 1) FROM user_defined_values));
SELECT setval('data_error_questions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM data_error_questions));
SELECT setval('duplicate_clusters_cluster_id_seq', (SELECT COALESCE(MAX(cluster_id), 1) FROM duplicate_clusters));
SELECT setval('cluster_members_id_seq', (SELECT COALESCE(MAX(id), 1) FROM cluster_members));
SELECT setval('duplicate_decisions_id_seq', (SELECT COALESCE(MAX(id), 1) FROM duplicate_decisions));
SELECT setval('tag_proposal_candidates_id_seq', (SELECT COALESCE(MAX(id), 1) FROM tag_proposal_candidates));
SELECT setval('user_roles_id_seq', (SELECT COALESCE(MAX(id), 1) FROM user_roles));

-- ============================================================
-- 2. Backfill activity_id FK in question_activities
--    (activity_id was skipped during migration due to SQLite/PG ID mismatch)
-- ============================================================

UPDATE question_activities qa
SET activity_id = a.id
FROM activities a
WHERE qa.activity_name = a.activity_name
  AND qa.activity_id IS NULL;

-- ============================================================
-- 3. Backfill activity_id FK in demographic_performance
-- ============================================================

-- demographic_performance doesn't have activity_name directly,
-- but it links through question_activities. Skip if no direct mapping exists.
-- (activity_id was skipped during migration — leave NULL if no join path)

-- Verify results
SELECT 'question_activities' AS table_name,
       COUNT(*) AS total,
       COUNT(activity_id) AS with_activity_id,
       COUNT(*) - COUNT(activity_id) AS missing_activity_id
FROM question_activities
UNION ALL
SELECT 'demographic_performance',
       COUNT(*),
       COUNT(activity_id),
       COUNT(*) - COUNT(activity_id)
FROM demographic_performance;
