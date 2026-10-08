from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def aplicar_rls_por_empresa(conn: AsyncConnection, tabla: str) -> None:
    """Habilita y fuerza Row-Level Security por company_id en una tabla."""
    sentencias = [
        f"ALTER TABLE {tabla} ENABLE ROW LEVEL SECURITY",
        f"ALTER TABLE {tabla} FORCE ROW LEVEL SECURITY",
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies WHERE tablename = '{tabla}' AND policyname = 'por_empresa'
            ) THEN
                CREATE POLICY por_empresa ON {tabla}
                    USING (
                        company_id = NULLIF(current_setting('app.company_id', true), '')::uuid
                    )
                    WITH CHECK (
                        company_id = NULLIF(current_setting('app.company_id', true), '')::uuid
                    );
            END IF;
        END $$;
        """,
    ]
    for sql in sentencias:
        await conn.execute(text(sql))
