class PostgresProposalRepository:
    def __init__(self, *, dsn: str) -> None:
        if not dsn:
            raise RuntimeError("PROPOSAL_POSTGRES_DSN_REQUIRED")
        raise RuntimeError("PROPOSAL_POSTGRES_NOT_IMPLEMENTED")
