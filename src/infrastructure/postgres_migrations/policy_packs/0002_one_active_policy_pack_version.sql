DROP INDEX IF EXISTS ux_policy_pack_catalog_active_version;

CREATE UNIQUE INDEX IF NOT EXISTS ux_policy_pack_catalog_one_active_version
    ON policy_pack_catalog_versions (policy_pack_id)
    WHERE activation_state = 'ACTIVE';
