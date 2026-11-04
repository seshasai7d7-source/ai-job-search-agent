from typing import Protocol


class JobSource(Protocol):
    def fetch_jobs(self, company: str, identifier: str) -> list[dict]:
        ...
