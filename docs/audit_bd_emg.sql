\set ON_ERROR_STOP on

-- Audit strictement en lecture seule a executer avec psql sur la base bd_emg.
SELECT current_database() AS base,
       current_user AS utilisateur,
       version() AS version_postgresql;

SELECT schemaname AS schema,
       tablename AS table
FROM pg_catalog.pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;

SELECT schemaname AS schema,
       relname AS table,
       n_live_tup AS lignes_estimees,
       pg_size_pretty(pg_total_relation_size(relid)) AS taille_totale
FROM pg_catalog.pg_stat_user_tables
ORDER BY schemaname, relname;

-- Genere et execute uniquement des SELECT count(*) pour les tables utilisateur existantes.
SELECT format(
    'SELECT %L AS table, count(*) AS lignes_exactes FROM %I.%I;',
    schemaname || '.' || tablename,
    schemaname,
    tablename
)
FROM pg_catalog.pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename
\gexec

SELECT tc.table_schema,
       tc.table_name,
       kcu.column_name,
       ccu.table_schema AS foreign_table_schema,
       ccu.table_name AS foreign_table_name,
       ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.constraint_schema = kcu.constraint_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
 AND ccu.constraint_schema = tc.constraint_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_schema, tc.table_name, kcu.column_name;
