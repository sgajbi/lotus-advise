-- Durable tenant on the policy evaluation record (#624).
--
-- The reads over this table cannot be tenant-scoped because the table records no
-- tenant: the only scoping anchor present is portfolio_id, and the portfolio-to-tenant
-- mapping belongs to lotus-core, not here. Deriving the tenant at read time would make
-- the scope only as stable as the deriving code, so it is captured at write time from
-- the admitted principal and stored.
--
-- Nullable, deliberately. Rows written before this column existed do not record what
-- the caller presented, and that is unknowable rather than absent -- the two must stay
-- distinguishable, because an absent tenant can be replayed faithfully and an
-- unrecorded one cannot be replayed at all. Backfilling would substitute a guess for a
-- fact and make every historical row indistinguishable from a genuine submission.
--
-- The reads decide what to do with a NULL. This migration only stops the loss.

-- TEXT, like every other column in this table. The first version of this migration
-- used VARCHAR(128), carried over from a sibling repository where that is the
-- convention -- which would have made a >128-character `X-Tenant-Id` succeed against
-- the in-memory profile and fail in production with `value too long for type
-- character varying(128)`. The header carries no length limit at the boundary, so the
-- limit would have been one this migration invented and nothing else enforced.
ALTER TABLE policy_evaluation_records
    ADD COLUMN IF NOT EXISTS tenant_id TEXT;
