"""SQLite store for local tracker runs when Supabase is not configured."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from jobintel.collectors.normalize import job_content_hash
from jobintel.models import (
    CollectedJob,
    Job,
    JobRead,
    JobStatus,
    Post,
    PostStatus,
    ProgressEntityType,
    ProgressEvent,
    Prospect,
    ProspectStatus,
    dump_progress_with_labels,
)
from jobintel.text import clean_description


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value.isoformat()


class SqliteStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            create table if not exists companies (
              id text primary key,
              name text not null unique
            );
            create table if not exists jobs (
              id text primary key,
              company_id text,
              company_name text,
              title text not null,
              location text,
              country text,
              remote_type text not null default 'unknown',
              source text not null default 'manual',
              source_job_id text,
              url text unique,
              apply_url text,
              description text not null,
              posted_at text,
              deadline_at text,
              discovered_at text not null,
              salary_text text,
              employment_type text,
              department text,
              seniority text,
              tags text not null default '[]',
              metadata_json text not null default '{}',
              status text not null default 'new',
              content_hash text unique,
              created_at text not null,
              updated_at text not null
            );
            create table if not exists applications (
              id text primary key,
              job_id text not null,
              status text not null,
              notes text,
              applied_at text,
              created_at text not null,
              updated_at text not null
            );
            create table if not exists prospects (
              id text primary key,
              name text not null,
              company text,
              country text,
              role text,
              source text,
              potential_problem text,
              date_contacted text,
              channel text,
              proposal_sent integer not null default 0,
              response text,
              status text not null default 'new',
              package text not null default 'unknown',
              follow_up_date text,
              next_action text,
              value_estimate_usd real,
              notes text,
              created_at text not null,
              updated_at text not null
            );
            create table if not exists progress_events (
              id text primary key,
              entity_type text not null,
              entity_id text not null,
              status text not null,
              note text,
              created_at text not null
            );
            create table if not exists dismissed_jobs (
              id text primary key,
              url text unique,
              content_hash text unique,
              created_at text not null
            );
            create table if not exists posts (
              id text primary key,
              title text not null,
              summary text,
              body text,
              tags text not null default '[]',
              cover_url text,
              canonical_url text,
              notes text,
              metadata_json text not null default '{}',
              media_json text not null default '[]',
              channels text not null default '[]',
              web_url text,
              linkedin_url text,
              scheduled_at text,
              published_at text,
              status text not null default 'idea',
              created_at text not null,
              updated_at text not null
            );
            """
        )
        self._conn.commit()
        self._ensure_job_columns()
        self._ensure_posts_table()
        self._purge_not_related_jobs()

    def _ensure_job_columns(self) -> None:
        existing = {
            row["name"]
            for row in self._rows("pragma table_info(jobs)")
        }
        additions = {
            "apply_url": "text",
            "deadline_at": "text",
            "salary_text": "text",
            "employment_type": "text",
            "department": "text",
            "seniority": "text",
            "tags": "text not null default '[]'",
            "metadata_json": "text not null default '{}'",
        }
        for name, ddl in additions.items():
            if name not in existing:
                self._conn.execute(f"alter table jobs add column {name} {ddl}")
        self._conn.commit()

    def _ensure_posts_table(self) -> None:
        existing = {row["name"] for row in self._rows("pragma table_info(posts)")}
        if not existing:
            return
        additions = {
            "summary": "text",
            "body": "text",
            "tags": "text not null default '[]'",
            "cover_url": "text",
            "canonical_url": "text",
            "notes": "text",
            "metadata_json": "text not null default '{}'",
            "media_json": "text not null default '[]'",
            "channels": "text not null default '[]'",
            "web_url": "text",
            "linkedin_url": "text",
            "scheduled_at": "text",
            "published_at": "text",
            "status": "text not null default 'idea'",
        }
        for name, ddl in additions.items():
            if name not in existing:
                self._conn.execute(f"alter table posts add column {name} {ddl}")
        self._conn.commit()

    def _row(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self._conn.execute(query, params).fetchone()

    def _rows(self, query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self._conn.execute(query, params).fetchall()

    def ensure_company(self, name: str) -> UUID | None:
        cleaned = name.strip()
        if not cleaned:
            return None
        existing = self._row("select id from companies where name = ?", (cleaned,))
        if existing:
            return UUID(str(existing["id"]))
        company_id = uuid4()
        self._conn.execute(
            "insert into companies (id, name) values (?, ?)", (str(company_id), cleaned)
        )
        self._conn.commit()
        return company_id

    def _job_from_row(self, row: sqlite3.Row) -> JobRead:
        data = dict(row)
        tags = data.get("tags")
        if isinstance(tags, str):
            try:
                data["tags"] = json.loads(tags or "[]")
            except json.JSONDecodeError:
                data["tags"] = []
        elif tags is None:
            data["tags"] = []
        meta = data.get("metadata_json")
        if isinstance(meta, str):
            try:
                data["metadata_json"] = json.loads(meta or "{}")
            except json.JSONDecodeError:
                data["metadata_json"] = {}
        elif meta is None:
            data["metadata_json"] = {}
        if isinstance(data.get("description"), str):
            data["description"] = clean_description(data["description"])
        return JobRead.model_validate(data)

    def list_jobs(
        self,
        *,
        status: str | None = None,
        source: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JobRead]:
        self._purge_not_related_jobs()
        clauses = ["1=1"]
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if q:
            clauses.append("(title like ? or description like ?)")
            like = f"%{q}%"
            params.extend([like, like])
        params.extend([limit, offset])
        rows = self._rows(
            f"""
            select * from jobs
            where {" and ".join(clauses)}
            order by discovered_at desc
            limit ? offset ?
            """,
            tuple(params),
        )
        return [self._job_from_row(row) for row in rows]

    def get_job(self, job_id: UUID) -> JobRead | None:
        row = self._row("select * from jobs where id = ?", (str(job_id),))
        return self._job_from_row(row) if row else None

    def create_job(self, job: Job, company_name: str | None = None) -> JobRead:
        now = _now()
        job_id = job.id or uuid4()
        company_id = job.company_id
        if company_name and not company_id:
            company_id = self.ensure_company(company_name)
        digest = job.content_hash or job_content_hash(
            title=job.title, company=company_name or "", description=job.description
        )
        description = clean_description(job.description)
        self._conn.execute(
            """
            insert into jobs (
              id, company_id, company_name, title, location, country, remote_type,
              source, source_job_id, url, apply_url, description, posted_at, deadline_at,
              discovered_at, salary_text, employment_type, department, seniority,
              tags, metadata_json, status, content_hash, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(job_id),
                str(company_id) if company_id else None,
                company_name,
                job.title,
                job.location,
                job.country,
                job.remote_type.value,
                job.source,
                job.source_job_id,
                job.url or None,
                job.apply_url,
                description,
                _iso(job.posted_at),
                _iso(job.deadline_at),
                _iso(now),
                job.salary_text,
                job.employment_type,
                job.department,
                job.seniority,
                json.dumps(job.tags or []),
                json.dumps(job.metadata_json or {}),
                job.status.value,
                digest,
                _iso(now),
                _iso(now),
            ),
        )
        self._conn.commit()
        created = self.get_job(job_id)
        assert created is not None
        return created

    def update_job(self, job_id: UUID, fields: dict[str, Any]) -> JobRead:
        if not self.get_job(job_id):
            raise KeyError(f"job not found: {job_id}")
        if not fields:
            found = self.get_job(job_id)
            assert found is not None
            return found
        columns = []
        values: list[Any] = []
        for key, value in fields.items():
            if key in {"tags", "metadata_json"} and not isinstance(value, str):
                value = json.dumps(value)
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif hasattr(value, "value"):
                value = value.value
            columns.append(f"{key} = ?")
            values.append(value)
        columns.append("updated_at = ?")
        values.append(_iso(_now()))
        values.append(str(job_id))
        self._conn.execute(
            f"update jobs set {', '.join(columns)} where id = ?",
            tuple(values),
        )
        self._conn.commit()
        updated = self.get_job(job_id)
        assert updated is not None
        return updated

    def delete_job(self, job_id: UUID) -> None:
        if not self.get_job(job_id):
            raise KeyError(f"job not found: {job_id}")
        job_key = str(job_id)
        self._conn.execute("delete from applications where job_id = ?", (job_key,))
        self._conn.execute(
            "delete from progress_events where entity_type = 'job' and entity_id = ?",
            (job_key,),
        )
        self._conn.execute("delete from jobs where id = ?", (job_key,))
        self._conn.commit()

    def dismiss_job(self, job_id: UUID) -> None:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"job not found: {job_id}")
        if job.url or job.content_hash:
            self._conn.execute(
                """
                insert or ignore into dismissed_jobs (id, url, content_hash, created_at)
                values (?, ?, ?, ?)
                """,
                (str(uuid4()), job.url or None, job.content_hash or None, _iso(_now())),
            )
            self._conn.commit()
        self.delete_job(job_id)

    def _purge_not_related_jobs(self) -> None:
        rows = self._rows("select id from jobs where status = 'not_related'")
        for row in rows:
            try:
                self.dismiss_job(UUID(str(row["id"])))
            except KeyError:
                continue

    def existing_job_keys(self) -> tuple[set[str], set[str]]:
        urls = {str(row["url"]) for row in self._rows("select url from jobs where url is not null")}
        hashes = {
            str(row["content_hash"])
            for row in self._rows("select content_hash from jobs where content_hash is not null")
        }
        urls.update(
            str(row["url"])
            for row in self._rows("select url from dismissed_jobs where url is not null")
        )
        hashes.update(
            str(row["content_hash"])
            for row in self._rows(
                "select content_hash from dismissed_jobs where content_hash is not null"
            )
        )
        return urls, hashes

    def insert_collected_jobs(self, collected: list[CollectedJob]) -> dict[str, int]:
        urls, hashes = self.existing_job_keys()
        inserted = 0
        skipped = 0
        for item in collected:
            digest = job_content_hash(
                title=item.title,
                company=item.company_name,
                description=item.description,
            )
            if item.url in urls or digest in hashes:
                skipped += 1
                continue
            try:
                self.create_job(
                    Job(
                        title=item.title,
                        description=item.description,
                        url=item.url,
                        apply_url=item.apply_url,
                        location=item.location,
                        country=item.country,
                        remote_type=item.remote_type,
                        source=item.source,
                        source_job_id=item.source_job_id,
                        posted_at=item.posted_at,
                        deadline_at=item.deadline_at,
                        salary_text=item.salary_text,
                        employment_type=item.employment_type,
                        department=item.department,
                        seniority=item.seniority,
                        tags=item.tags,
                        metadata_json=item.metadata_json,
                        status=JobStatus.NEW,
                        content_hash=digest,
                    ),
                    company_name=item.company_name,
                )
            except sqlite3.IntegrityError:
                skipped += 1
                continue
            urls.add(item.url)
            hashes.add(digest)
            inserted += 1
        return {"inserted": inserted, "skipped": skipped, "seen": len(collected)}

    def submit_job_progress(
        self, job_id: UUID, status: JobStatus, note: str | None = None
    ) -> ProgressEvent:
        if not self.get_job(job_id):
            raise KeyError(f"job not found: {job_id}")
        now = _iso(_now())
        self._conn.execute(
            "update jobs set status = ?, updated_at = ? where id = ?",
            (status.value, now, str(job_id)),
        )
        existing = self._row("select id from applications where job_id = ?", (str(job_id),))
        applied_at = now if status == JobStatus.APPLIED else None
        if existing:
            self._conn.execute(
                """
                update applications set status = ?, notes = ?, applied_at = coalesce(?, applied_at),
                  updated_at = ? where id = ?
                """,
                (status.value, note, applied_at, now, existing["id"]),
            )
        else:
            self._conn.execute(
                """
                insert into applications
                  (id, job_id, status, notes, applied_at, created_at, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (str(uuid4()), str(job_id), status.value, note, applied_at, now, now),
            )
        self._conn.commit()
        return self._insert_progress(ProgressEntityType.JOB, job_id, status.value, note)

    def list_prospects(
        self,
        *,
        status: str | None = None,
        package: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Prospect]:
        clauses = ["1=1"]
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if package:
            clauses.append("package = ?")
            params.append(package)
        if q:
            clauses.append("(name like ? or ifnull(company,'') like ? or ifnull(notes,'') like ?)")
            like = f"%{q}%"
            params.extend([like, like, like])
        params.extend([limit, offset])
        rows = self._rows(
            f"""
            select * from prospects
            where {" and ".join(clauses)}
            order by updated_at desc
            limit ? offset ?
            """,
            tuple(params),
        )
        return [self._prospect_from_row(row) for row in rows]

    def _prospect_from_row(self, row: sqlite3.Row) -> Prospect:
        data = dict(row)
        data["proposal_sent"] = bool(data.get("proposal_sent"))
        return Prospect.model_validate(data)

    def get_prospect(self, prospect_id: UUID) -> Prospect | None:
        row = self._row("select * from prospects where id = ?", (str(prospect_id),))
        return self._prospect_from_row(row) if row else None

    def create_prospect(self, prospect: Prospect) -> Prospect:
        now = _iso(_now())
        prospect_id = prospect.id or uuid4()
        payload = prospect.model_dump(mode="json")
        self._conn.execute(
            """
            insert into prospects (
              id, name, company, country, role, source, potential_problem, date_contacted,
              channel, proposal_sent, response, status, package, follow_up_date, next_action,
              value_estimate_usd, notes, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(prospect_id),
                payload["name"],
                payload.get("company"),
                payload.get("country"),
                payload.get("role"),
                payload.get("source"),
                payload.get("potential_problem"),
                payload.get("date_contacted"),
                payload.get("channel"),
                1 if payload.get("proposal_sent") else 0,
                payload.get("response"),
                payload["status"],
                payload["package"],
                payload.get("follow_up_date"),
                payload.get("next_action"),
                payload.get("value_estimate_usd"),
                payload.get("notes"),
                now,
                now,
            ),
        )
        self._conn.commit()
        created = self.get_prospect(prospect_id)
        assert created is not None
        self._insert_progress(
            ProgressEntityType.PROSPECT,
            prospect_id,
            created.status.value,
            prospect.notes,
        )
        return created

    def update_prospect(self, prospect_id: UUID, fields: dict[str, Any]) -> Prospect:
        if not self.get_prospect(prospect_id):
            raise KeyError(f"prospect not found: {prospect_id}")
        if not fields:
            found = self.get_prospect(prospect_id)
            assert found is not None
            return found
        columns = []
        values: list[Any] = []
        for key, value in fields.items():
            if key == "proposal_sent":
                value = 1 if value else 0
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()
            columns.append(f"{key} = ?")
            values.append(value)
        columns.append("updated_at = ?")
        values.append(_iso(_now()))
        values.append(str(prospect_id))
        self._conn.execute(
            f"update prospects set {', '.join(columns)} where id = ?",
            tuple(values),
        )
        self._conn.commit()
        updated = self.get_prospect(prospect_id)
        assert updated is not None
        return updated

    def submit_prospect_progress(
        self, prospect_id: UUID, status: ProspectStatus, note: str | None = None
    ) -> ProgressEvent:
        if not self.get_prospect(prospect_id):
            raise KeyError(f"prospect not found: {prospect_id}")
        fields: dict[str, Any] = {"status": status.value}
        if note:
            fields["notes"] = note
        if status == ProspectStatus.CONTACTED:
            fields["date_contacted"] = datetime.now(UTC).date().isoformat()
        if status == ProspectStatus.PROPOSAL:
            fields["proposal_sent"] = True
        self.update_prospect(prospect_id, fields)
        return self._insert_progress(
            ProgressEntityType.PROSPECT, prospect_id, status.value, note
        )

    def list_posts(
        self,
        *,
        status: str | None = None,
        channel: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Post]:
        clauses = ["1=1"]
        params: list[Any] = []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if channel:
            clauses.append("channels like ?")
            params.append(f'%"{channel}"%')
        if q:
            clauses.append(
                "(title like ? or ifnull(summary,'') like ? or ifnull(body,'') like ?)"
            )
            like = f"%{q}%"
            params.extend([like, like, like])
        params.extend([limit, offset])
        rows = self._rows(
            f"""
            select * from posts
            where {" and ".join(clauses)}
            order by updated_at desc
            limit ? offset ?
            """,
            tuple(params),
        )
        return [self._post_from_row(row) for row in rows]

    def _post_from_row(self, row: sqlite3.Row) -> Post:
        data = dict(row)
        json_defaults: tuple[tuple[str, list[Any] | dict[str, Any]], ...] = (
            ("tags", []),
            ("channels", []),
            ("media_json", []),
            ("metadata_json", {}),
        )
        for key, empty in json_defaults:
            value = data.get(key)
            if isinstance(value, str):
                try:
                    data[key] = json.loads(value or json.dumps(empty))
                except json.JSONDecodeError:
                    data[key] = empty
            elif value is None:
                data[key] = empty
        return Post.model_validate(data)

    def get_post(self, post_id: UUID) -> Post | None:
        row = self._row("select * from posts where id = ?", (str(post_id),))
        return self._post_from_row(row) if row else None

    def create_post(self, post: Post) -> Post:
        now = _iso(_now())
        post_id = post.id or uuid4()
        payload = post.model_dump(mode="json")
        self._conn.execute(
            """
            insert into posts (
              id, title, summary, body, tags, cover_url, canonical_url, notes,
              metadata_json, media_json, channels, web_url, linkedin_url,
              scheduled_at, published_at, status, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(post_id),
                payload["title"],
                payload.get("summary"),
                payload.get("body"),
                json.dumps(payload.get("tags") or []),
                payload.get("cover_url"),
                payload.get("canonical_url"),
                payload.get("notes"),
                json.dumps(payload.get("metadata_json") or {}),
                json.dumps(payload.get("media_json") or []),
                json.dumps(payload.get("channels") or []),
                payload.get("web_url"),
                payload.get("linkedin_url"),
                payload.get("scheduled_at"),
                payload.get("published_at"),
                payload["status"],
                now,
                now,
            ),
        )
        self._conn.commit()
        created = self.get_post(post_id)
        assert created is not None
        self._insert_progress(
            ProgressEntityType.POST,
            post_id,
            created.status.value,
            post.notes,
        )
        return created

    def update_post(self, post_id: UUID, fields: dict[str, Any]) -> Post:
        if not self.get_post(post_id):
            raise KeyError(f"post not found: {post_id}")
        if not fields:
            found = self.get_post(post_id)
            assert found is not None
            return found
        columns = []
        values: list[Any] = []
        json_keys = {"tags", "channels", "media_json", "metadata_json"}
        for key, value in fields.items():
            if key in json_keys and not isinstance(value, str):
                value = json.dumps(value)
            elif isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif hasattr(value, "value"):
                value = value.value
            columns.append(f"{key} = ?")
            values.append(value)
        columns.append("updated_at = ?")
        values.append(_iso(_now()))
        values.append(str(post_id))
        self._conn.execute(
            f"update posts set {', '.join(columns)} where id = ?",
            tuple(values),
        )
        self._conn.commit()
        updated = self.get_post(post_id)
        assert updated is not None
        return updated

    def submit_post_progress(
        self, post_id: UUID, status: PostStatus, note: str | None = None
    ) -> ProgressEvent:
        current = self.get_post(post_id)
        if current is None:
            raise KeyError(f"post not found: {post_id}")
        fields: dict[str, Any] = {"status": status.value}
        if note:
            fields["notes"] = note
        if status == PostStatus.PUBLISHED and not current.published_at:
            fields["published_at"] = _iso(_now())
        self.update_post(post_id, fields)
        return self._insert_progress(ProgressEntityType.POST, post_id, status.value, note)

    def list_progress(
        self,
        *,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        since: str | None = None,
        limit: int = 50,
    ) -> list[ProgressEvent]:
        clauses = ["1=1"]
        params: list[Any] = []
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type)
        if entity_id:
            clauses.append("entity_id = ?")
            params.append(str(entity_id))
        if since:
            clauses.append("created_at >= ?")
            params.append(since)
        params.append(limit)
        rows = self._rows(
            f"""
            select * from progress_events
            where {" and ".join(clauses)}
            order by created_at desc
            limit ?
            """,
            tuple(params),
        )
        return [ProgressEvent.model_validate(dict(row)) for row in rows]

    def dashboard(self) -> dict[str, Any]:
        jobs = self._rows("select status from jobs")
        prospects = self._rows("select status from prospects")
        posts = self._rows("select status from posts")
        job_counts: dict[str, int] = {}
        prospect_counts: dict[str, int] = {}
        post_counts: dict[str, int] = {}
        for row in jobs:
            key = str(row["status"] or "unknown")
            job_counts[key] = job_counts.get(key, 0) + 1
        for row in prospects:
            key = str(row["status"] or "unknown")
            prospect_counts[key] = prospect_counts.get(key, 0) + 1
        for row in posts:
            key = str(row["status"] or "unknown")
            post_counts[key] = post_counts.get(key, 0) + 1
        recent = self.list_progress(limit=20)
        return {
            "jobs_total": len(jobs),
            "prospects_total": len(prospects),
            "posts_total": len(posts),
            "jobs_by_status": job_counts,
            "prospects_by_status": prospect_counts,
            "posts_by_status": post_counts,
            "recent_progress": dump_progress_with_labels(recent, self._progress_labels(recent)),
        }

    def _progress_labels(
        self, events: list[ProgressEvent]
    ) -> dict[str, tuple[str | None, str | None]]:
        job_ids = [
            str(event.entity_id)
            for event in events
            if event.entity_type == ProgressEntityType.JOB
        ]
        prospect_ids = [
            str(event.entity_id)
            for event in events
            if event.entity_type == ProgressEntityType.PROSPECT
        ]
        post_ids = [
            str(event.entity_id)
            for event in events
            if event.entity_type == ProgressEntityType.POST
        ]
        labels: dict[str, tuple[str | None, str | None]] = {}
        if job_ids:
            placeholders = ",".join("?" * len(job_ids))
            for row in self._rows(
                f"select id, title, company_name from jobs where id in ({placeholders})",
                tuple(job_ids),
            ):
                labels[str(row["id"])] = (row["title"], row["company_name"])
        if prospect_ids:
            placeholders = ",".join("?" * len(prospect_ids))
            for row in self._rows(
                f"select id, name, company from prospects where id in ({placeholders})",
                tuple(prospect_ids),
            ):
                labels[str(row["id"])] = (row["name"], row["company"])
        if post_ids:
            placeholders = ",".join("?" * len(post_ids))
            for row in self._rows(
                f"select id, title, channels from posts where id in ({placeholders})",
                tuple(post_ids),
            ):
                channels = row["channels"]
                if isinstance(channels, str):
                    try:
                        channels = json.loads(channels or "[]")
                    except json.JSONDecodeError:
                        channels = []
                subtitle = " · ".join(channels) if channels else None
                labels[str(row["id"])] = (row["title"], subtitle)
        return labels

    def _insert_progress(
        self,
        entity_type: ProgressEntityType,
        entity_id: UUID,
        status: str,
        note: str | None,
    ) -> ProgressEvent:
        event_id = uuid4()
        created_at = _iso(_now())
        self._conn.execute(
            """
            insert into progress_events (id, entity_type, entity_id, status, note, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (str(event_id), entity_type.value, str(entity_id), status, note, created_at),
        )
        self._conn.commit()
        return ProgressEvent.model_validate(
            {
                "id": event_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "status": status,
                "note": note,
                "created_at": created_at,
            }
        )
