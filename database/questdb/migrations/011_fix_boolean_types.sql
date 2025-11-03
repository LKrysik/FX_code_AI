-- ============================================================================
-- Data Migration: Fix Existing is_deleted Values
-- ============================================================================
-- Purpose: Convert any non-BOOLEAN values to proper BOOLEAN type
-- Run this ONCE to fix existing data after deploying code changes
-- ============================================================================

-- Check current values (for verification)
-- SELECT id, name, is_deleted, typeof(is_deleted) as type FROM indicator_variants;

-- Fix: Update all is_deleted values to proper BOOLEAN
-- This handles NULL, STRING 'false'/'true', INT 0/1, etc.
UPDATE indicator_variants
SET is_deleted = CAST(
    CASE
        WHEN is_deleted IS NULL THEN false
        WHEN is_deleted IN (0, '0', 'false', 'False', 'FALSE') THEN false
        ELSE true
    END AS BOOLEAN
);

-- Verify (all should be proper BOOLEAN now)
-- SELECT id, name, is_deleted, typeof(is_deleted) as type FROM indicator_variants;

-- Expected result: All rows should have is_deleted as BOOLEAN type (false or true)
