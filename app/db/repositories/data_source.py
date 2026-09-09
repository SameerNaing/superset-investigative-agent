from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DataSource, Provider


class DataSourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_provider_and_name(
        self,
        provider: Provider,
        name: str,
    ) -> DataSource | None:
        return self._session.scalar(
            select(DataSource).where(
                DataSource.provider == provider,
                DataSource.name == name,
            )
        )

    def list_by_provider(self, provider: Provider) -> list[DataSource]:
        return list(
            self._session.scalars(
                select(DataSource).where(DataSource.provider == provider)
            ).all()
        )

    def get_or_create(
        self,
        *,
        provider: Provider,
        name: str,
    ) -> DataSource:
        existing = self.get_by_provider_and_name(provider, name)
        if existing is not None:
            return existing
        data_source = DataSource(name=name, provider=provider)
        self._session.add(data_source)
        self._session.flush()
        return data_source
