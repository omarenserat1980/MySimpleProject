import json
import math
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat()

class MemoryStore:
    def __init__(self, path="brain_v12.db"):
        self.path=Path(path)

    def connect(self):
        con=sqlite3.connect(self.path)
        con.row_factory=sqlite3.Row
        return con

    def init(self):
        with self.connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS memories(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              key TEXT UNIQUE NOT NULL,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_metadata(
              memory_key TEXT PRIMARY KEY REFERENCES memories(key) ON DELETE CASCADE,
              source TEXT NOT NULL DEFAULT 'LEGACY_UNKNOWN',
              confidence REAL NOT NULL DEFAULT 0.5,
              expires_at TEXT,
              status TEXT NOT NULL DEFAULT 'ACTIVE',
              tags TEXT NOT NULL DEFAULT '[]',
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS memory_conflicts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              memory_key TEXT NOT NULL,
              conflicting_key TEXT NOT NULL,
              reason TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'OPEN',
              created_at TEXT NOT NULL,
              resolution_evidence TEXT NOT NULL DEFAULT '',
              resolved_by TEXT NOT NULL DEFAULT '',
              resolved_at TEXT,
              UNIQUE(memory_key,conflicting_key)
            );
            CREATE TABLE IF NOT EXISTS goals(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              text TEXT NOT NULL,
              priority REAL NOT NULL DEFAULT 0.5,
              status TEXT NOT NULL DEFAULT 'PENDING',
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              role TEXT NOT NULL,
              content TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              kind TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS state(
              id INTEGER PRIMARY KEY CHECK(id=1),
              data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS income_opportunities(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              opportunity_id TEXT UNIQUE NOT NULL,
              category TEXT NOT NULL,
              title TEXT NOT NULL,
              source_url TEXT,
              evidence TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'DISCOVERY',
              score REAL NOT NULL DEFAULT 0,
              expected_value_jod REAL,
              verified_amount_jod REAL NOT NULL DEFAULT 0,
              verification_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
              owner_role TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS incidents(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              fingerprint TEXT UNIQUE NOT NULL,
              severity TEXT NOT NULL,
              status TEXT NOT NULL,
              message TEXT NOT NULL,
              service_id TEXT,
              first_seen TEXT NOT NULL,
              last_seen TEXT NOT NULL,
              occurrences INTEGER NOT NULL DEFAULT 1,
              data TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS device_tasks(
              task_id TEXT PRIMARY KEY,
              task TEXT NOT NULL,
              params TEXT NOT NULL,
              status TEXT NOT NULL,
              agent_id TEXT,
              created_at TEXT NOT NULL,
              claimed_at TEXT,
              completed_at TEXT,
              result TEXT NOT NULL DEFAULT '{}',
              error TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS device_agents(
              agent_id TEXT PRIMARY KEY,
              last_seen REAL NOT NULL
            );
            INSERT OR IGNORE INTO state(id,data) VALUES(1,'{"status":"READY"}');
            """)

    def state(self):
        with self.connect() as con:
            row=con.execute("SELECT data FROM state WHERE id=1").fetchone()
            return json.loads(row["data"])

    def set_state(self,data):
        with self.connect() as con:
            con.execute("UPDATE state SET data=? WHERE id=1",(json.dumps(data,ensure_ascii=False),))
            con.commit()

    def event(self,kind,payload):
        with self.connect() as con:
            con.execute("INSERT INTO events(kind,payload,created_at) VALUES(?,?,?)",
                        (kind,json.dumps(payload,ensure_ascii=False),now()))
            con.commit()

    def messages(self):
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT role,content,created_at FROM messages ORDER BY id").fetchall()]

    def add_message(self,role,content):
        with self.connect() as con:
            con.execute("INSERT INTO messages(role,content,created_at) VALUES(?,?,?)",(role,content,now()))
            con.commit()

    def memories(self):
        with self.connect() as con:
            rows = con.execute("""
                SELECT m.key,m.value,m.updated_at,
                       COALESCE(mm.source,'LEGACY_UNKNOWN') AS source,
                       COALESCE(mm.confidence,0.5) AS confidence,
                       mm.expires_at,
                       COALESCE(mm.status,'ACTIVE') AS status,
                       COALESCE(mm.tags,'[]') AS tags
                FROM memories AS m
                LEFT JOIN memory_metadata AS mm ON mm.memory_key=m.key
                ORDER BY m.id DESC
            """).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["tags"] = json.loads(item.get("tags") or "[]")
            except (TypeError, ValueError):
                item["tags"] = []
            out.append(item)
        return out

    @staticmethod
    def _memory_is_recallable(memory, at=None):
        """Exclude inactive, disputed, or expired memories from decision recall."""
        status = str(memory.get("status") or "ACTIVE").strip().upper()
        if status != "ACTIVE":
            return False
        expires_at = memory.get("expires_at")
        if not expires_at:
            return True
        try:
            expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            current = at or datetime.now(timezone.utc)
            if current.tzinfo is None:
                current = current.replace(tzinfo=timezone.utc)
            return expiry > current
        except (TypeError, ValueError, OverflowError):
            # A malformed expiry must not silently turn stale data into live evidence.
            return False

    def set_memory_metadata(self, key, *, source=None, confidence=None, expires_at=None,
                            status=None, tags=None):
        """Set provenance/lifecycle metadata without rewriting the memory value."""
        allowed_statuses = {"ACTIVE", "UNVERIFIED", "CONFLICTED", "SUPERSEDED", "RETRACTED", "ARCHIVED"}
        if confidence is not None:
            try:
                confidence = float(confidence)
            except (TypeError, ValueError, OverflowError):
                raise ValueError("confidence must be a finite number from 0 to 1")
            if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
                raise ValueError("confidence must be a finite number from 0 to 1")
        if status is not None:
            status = str(status).strip().upper()
            if status not in allowed_statuses:
                raise ValueError("unsupported memory status")
        if source is not None:
            source = str(source).strip()[:500] or "UNKNOWN"
        if expires_at is not None:
            try:
                expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            except (TypeError, ValueError, OverflowError):
                raise ValueError("expires_at must be an ISO-8601 datetime")
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            expires_at = expiry.astimezone(timezone.utc).isoformat()
        if tags is not None:
            if not isinstance(tags, (list, tuple, set)):
                raise ValueError("tags must be a list, tuple, or set")
            tags = sorted({str(tag).strip()[:80] for tag in tags if str(tag).strip()})[:50]
        with self.connect() as con:
            exists = con.execute("SELECT 1 FROM memories WHERE key=?", (key,)).fetchone()
            if not exists:
                raise KeyError(key)
            current = con.execute("SELECT * FROM memory_metadata WHERE memory_key=?", (key,)).fetchone()
            current = dict(current) if current else {
                "source": "LEGACY_UNKNOWN", "confidence": 0.5, "expires_at": None,
                "status": "ACTIVE", "tags": "[]", "updated_at": now()
            }
            merged = {
                "source": current["source"] if source is None else source,
                "confidence": current["confidence"] if confidence is None else confidence,
                "expires_at": current["expires_at"] if expires_at is None else expires_at,
                "status": current["status"] if status is None else status,
                "tags": current["tags"] if tags is None else json.dumps(tags, ensure_ascii=False),
                "updated_at": now(),
            }
            con.execute("""
                INSERT INTO memory_metadata(memory_key,source,confidence,expires_at,status,tags,updated_at)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(memory_key) DO UPDATE SET
                    source=excluded.source, confidence=excluded.confidence,
                    expires_at=excluded.expires_at, status=excluded.status,
                    tags=excluded.tags, updated_at=excluded.updated_at
            """, (key, merged["source"], merged["confidence"], merged["expires_at"],
                  merged["status"], merged["tags"], merged["updated_at"]))
            con.commit()
        self.event("MEMORY_METADATA_UPDATED", {"key": key, "status": merged["status"]})
        return {**merged, "memory_key": key, "tags": json.loads(merged["tags"])}


    @staticmethod
    def _memory_terms(text):
        """Normalize Arabic/English text into simple searchable terms; no external NLP dependency."""
        text = unicodedata.normalize("NFKC", str(text or "")).lower()
        text = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text)
        text = text.translate(str.maketrans({"أ":"ا","إ":"ا","آ":"ا","ى":"ي","ؤ":"و","ئ":"ي","ة":"ه"}))
        terms = re.findall(r"[a-z0-9_]+|[\u0621-\u064A]+", text)
        stop = {
            "the","and","for","with","from","this","that","have","has","was","were","are","is","to","of","in","on",
            "a","an","it","my","our","brain","goal","run","الذي","التي","هذا","هذه","ذلك","تلك","من","في","على",
            "الى","إلى","عن","مع","هو","هي","كان","كانت","تم","قد","ما","ماذا","كيف","اريد","أريد","عند","بعد",
            "قبل","بين","كل","ثم","او","أو","و","ف","ب","ل"
        }
        normalized = set()
        for term in terms:
            if term in stop:
                continue
            # Strip Arabic definite article so الخبر/خبر and الدليل/دليل match.
            if term.startswith("ال") and len(term) > 4:
                term = term[2:]
            if len(term) > 1 and term not in stop:
                normalized.add(term)
        return normalized

    def recall_memories(self, query="", limit=12, candidates=None, fallback_recent=True):
        """Recall goal-relevant memories first; fall back to recent records only when no match exists."""
        limit = max(1, min(int(limit), 100))
        rows = list(candidates) if candidates is not None else self.memories()
        rows = [memory for memory in rows if self._memory_is_recallable(memory)]
        query_terms = self._memory_terms(query)
        if not query_terms:
            return rows[:limit] if fallback_recent else []

        prepared = []
        document_frequency = {term: 0 for term in query_terms}
        for memory in rows:
            key_terms = self._memory_terms(memory.get("key", ""))
            value_terms = self._memory_terms(memory.get("value", ""))
            document_terms = key_terms | value_terms
            for term in query_terms & document_terms:
                document_frequency[term] += 1
            prepared.append((memory, key_terms, value_terms))

        # Rare goal terms carry more information than generic words repeated
        # across many memories. This is a small corpus-local IDF weighting.
        corpus_size = max(1, len(prepared))
        term_weights = {
            term: math.log((corpus_size + 1) / (document_frequency[term] + 1)) + 1.0
            for term in query_terms
        }
        ranked = []
        for position, (memory, key_terms, value_terms) in enumerate(prepared):
            key_score = sum(term_weights[term] for term in query_terms & key_terms)
            value_score = sum(term_weights[term] for term in query_terms & value_terms)
            score = (key_score * 3) + (value_score * 2)
            try:
                confidence = float(memory.get("confidence", 0.5))
            except (TypeError, ValueError, OverflowError):
                confidence = 0.5
            if not math.isfinite(confidence):
                confidence = 0.5
            confidence = min(1.0, max(0.0, confidence))
            # Confidence adjusts relevance without erasing the lexical match.
            score *= 0.5 + confidence
            if score:
                ranked.append((score, position, memory))
        if not ranked:
            return rows[:limit] if fallback_recent else []

        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [memory for _, _, memory in ranked[:limit]]

    def record_memory_conflict(self, key, conflicting_key, reason):
        """Record an explicit conflict and quarantine both memories from active recall."""
        key = str(key or "").strip()
        conflicting_key = str(conflicting_key or "").strip()
        reason = str(reason or "").strip()[:2000]
        if not key or not conflicting_key or key == conflicting_key:
            raise ValueError("two distinct memory keys are required")
        if not reason:
            raise ValueError("a conflict reason is required")
        first, second = sorted((key, conflicting_key))
        created_at = now()
        with self.connect() as con:
            existing = con.execute(
                "SELECT key FROM memories WHERE key IN (?,?)", (first, second)
            ).fetchall()
            if len(existing) != 2:
                raise KeyError(key if not any(row["key"] == key for row in existing) else conflicting_key)
            con.execute("""
                INSERT INTO memory_conflicts(memory_key,conflicting_key,reason,status,created_at)
                VALUES(?,?,?,'OPEN',?)
                ON CONFLICT(memory_key,conflicting_key) DO UPDATE SET
                    reason=excluded.reason,status='OPEN',created_at=excluded.created_at
            """, (first, second, reason, created_at))
            for memory_key in (first, second):
                con.execute("""
                    INSERT INTO memory_metadata(memory_key,source,confidence,expires_at,status,tags,updated_at)
                    VALUES(?,'LEGACY_UNKNOWN',0.5,NULL,'CONFLICTED','[]',?)
                    ON CONFLICT(memory_key) DO UPDATE SET
                        status='CONFLICTED',updated_at=excluded.updated_at
                """, (memory_key, created_at))
            con.commit()
        self.event("MEMORY_CONFLICT_RECORDED", {
            "memory_key": first, "conflicting_key": second, "reason": reason
        })
        return {
            "memory_key": first, "conflicting_key": second, "reason": reason,
            "status": "OPEN", "created_at": created_at
        }

    def resolve_memory_conflict(self, key, conflicting_key, accepted_key, evidence, verifier):
        """Resolve a recorded conflict by activating one evidence-backed fact and superseding the other."""
        key = str(key or "").strip()
        conflicting_key = str(conflicting_key or "").strip()
        accepted_key = str(accepted_key or "").strip()
        evidence = str(evidence or "").strip()[:2000]
        verifier = str(verifier or "").strip()[:500]
        if not key or not conflicting_key or key == conflicting_key:
            raise ValueError("two distinct memory keys are required")
        if accepted_key not in {key, conflicting_key}:
            raise ValueError("accepted_key must identify one side of the conflict")
        if not evidence or not verifier:
            raise ValueError("resolution evidence and verifier identity are required")
        first, second = sorted((key, conflicting_key))
        resolved_at = now()
        rejected_key = conflicting_key if accepted_key == key else key
        with self.connect() as con:
            conflict = con.execute(
                "SELECT status FROM memory_conflicts WHERE memory_key=? AND conflicting_key=?",
                (first, second)
            ).fetchone()
            if not conflict:
                raise KeyError(f"{first} <> {second}")
            if conflict["status"] != "OPEN":
                raise ValueError("only an OPEN memory conflict can be resolved")
            for memory_key, status in ((accepted_key, "ACTIVE"), (rejected_key, "SUPERSEDED")):
                current = con.execute(
                    "SELECT source,confidence,expires_at,tags FROM memory_metadata WHERE memory_key=?",
                    (memory_key,)
                ).fetchone()
                if current:
                    source = f"conflict_resolution:{verifier}"
                    con.execute("""
                        UPDATE memory_metadata SET source=?,status=?,updated_at=?
                        WHERE memory_key=?
                    """, (source, status, resolved_at, memory_key))
                else:
                    con.execute("""
                        INSERT INTO memory_metadata(
                            memory_key,source,confidence,expires_at,status,tags,updated_at
                        ) VALUES(?,?,0.5,NULL,?,'[]',?)
                    """, (memory_key, f"conflict_resolution:{verifier}", status, resolved_at))
            con.execute("""
                UPDATE memory_conflicts
                SET status='RESOLVED',resolution_evidence=?,resolved_by=?,resolved_at=?
                WHERE memory_key=? AND conflicting_key=?
            """, (evidence, verifier, resolved_at, first, second))
            con.commit()
        self.event("MEMORY_CONFLICT_RESOLVED", {
            "memory_key": first, "conflicting_key": second,
            "accepted_key": accepted_key, "rejected_key": rejected_key,
            "verifier": verifier, "evidence": evidence
        })
        return {
            "memory_key": first, "conflicting_key": second,
            "accepted_key": accepted_key, "rejected_key": rejected_key,
            "status": "RESOLVED", "evidence": evidence, "verifier": verifier,
            "resolved_at": resolved_at
        }

    def memory_conflicts(self, limit=100):
        with self.connect() as con:
            rows = con.execute(
                "SELECT memory_key,conflicting_key,reason,status,created_at "
                "FROM memory_conflicts ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 500)),)
            ).fetchall()
        return [dict(row) for row in rows]

    def save_memory(self,key,value):
        with self.connect() as con:
            con.execute("""INSERT INTO memories(key,value,updated_at) VALUES(?,?,?)
                           ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",(key,value,now()))
            con.execute("""
                INSERT OR IGNORE INTO memory_metadata(memory_key,source,confidence,expires_at,status,tags,updated_at)
                VALUES(?,?,?,?,?,?,?)
            """, (key, "LEGACY_UNKNOWN", 0.5, None, "ACTIVE", "[]", now()))
            con.commit()
        self.event("MEMORY_UPDATED",{"key":key})

    def goals(self):
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT * FROM goals ORDER BY priority DESC,id DESC").fetchall()]

    def add_goal(self,text,priority=0.5):
        with self.connect() as con:
            cur=con.execute("INSERT INTO goals(text,priority,created_at) VALUES(?,?,?)",(text,priority,now()))
            con.commit()
            gid=cur.lastrowid
        self.event("GOAL_CREATED",{"id":gid,"text":text})
        return gid

    def active_goal(self):
        with self.connect() as con:
            return con.execute("SELECT * FROM goals WHERE status IN ('PENDING','IN_PROGRESS') ORDER BY priority DESC,id LIMIT 1").fetchone()

    def set_goal_status(self,gid,status):
        with self.connect() as con:
            con.execute("UPDATE goals SET status=? WHERE id=?",(status,gid))
            con.commit()

    def upsert_income_opportunity(self, opportunity):
        import json
        from datetime import datetime, timezone
        now_iso=datetime.now(timezone.utc).isoformat()
        data=dict(opportunity)
        oid=data["opportunity_id"]
        with self.connect() as con:
            row=con.execute("SELECT id FROM income_opportunities WHERE opportunity_id=?",(oid,)).fetchone()
            if row:
                con.execute("""UPDATE income_opportunities
                               SET category=?,title=?,source_url=?,evidence=?,status=?,score=?,
                                   expected_value_jod=?,verified_amount_jod=?,verification_status=?,
                                   owner_role=?,updated_at=?,data=? WHERE opportunity_id=?""",
                            (data.get("category",""),data.get("title",""),data.get("source_url"),
                             data.get("evidence",""),data.get("status","DISCOVERY"),float(data.get("score",0)),
                             data.get("expected_value_jod"),float(data.get("verified_amount_jod",0)),
                             data.get("verification_status","UNVERIFIED"),data.get("owner_role"),
                             now_iso,json.dumps(data,ensure_ascii=False),oid))
            else:
                con.execute("""INSERT INTO income_opportunities
                               (opportunity_id,category,title,source_url,evidence,status,score,
                                expected_value_jod,verified_amount_jod,verification_status,owner_role,
                                created_at,updated_at,data)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (oid,data.get("category",""),data.get("title",""),data.get("source_url"),
                             data.get("evidence",""),data.get("status","DISCOVERY"),float(data.get("score",0)),
                             data.get("expected_value_jod"),float(data.get("verified_amount_jod",0)),
                             data.get("verification_status","UNVERIFIED"),data.get("owner_role"),
                             now_iso,now_iso,json.dumps(data,ensure_ascii=False)))
            con.commit()

    def purge_non_live_income_opportunities(self):
        """Remove legacy channel-only records; live records must carry source_kind=LIVE_OPPORTUNITY."""
        with self.connect() as con:
            rows=con.execute("SELECT opportunity_id,data FROM income_opportunities").fetchall()
            removed=0
            for row in rows:
                try: data=json.loads(row["data"])
                except Exception: data={}
                if data.get("source_kind") != "LIVE_OPPORTUNITY":
                    con.execute("DELETE FROM income_opportunities WHERE opportunity_id=?",(row["opportunity_id"],)); removed += 1
            con.commit()
        if removed: self.event("INCOME_LEGACY_CHANNELS_PURGED", {"removed":removed})
        return removed

    def income_opportunities(self, limit=100):
        with self.connect() as con:
            rows=con.execute("SELECT * FROM income_opportunities ORDER BY score DESC,id DESC LIMIT ?",
                             (max(1,min(int(limit),500)),)).fetchall()
        out=[]
        for row in rows:
            item=dict(row)
            try: item["data"]=json.loads(item["data"])
            except Exception: pass
            out.append(item)
        return out

    def income_summary(self):
        with self.connect() as con:
            row=con.execute("""SELECT COUNT(*) total,
                                      COALESCE(SUM(verified_amount_jod),0) verified,
                                      COALESCE(SUM(CASE WHEN status IN ('READY','IN_PROGRESS') THEN 1 ELSE 0 END),0) active,
                                      COALESCE(SUM(CASE WHEN verification_status='VERIFIED' THEN 1 ELSE 0 END),0) verified_count
                               FROM income_opportunities""").fetchone()
        return dict(row)

    def events_for_run(self,run_id,limit=100):
        with self.connect() as con:
            rows=con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(max(limit,1000),)).fetchall()
        out=[]
        for row in rows:
            try: payload=json.loads(row["payload"])
            except Exception: payload={}
            if payload.get("run_id")==run_id: out.append(dict(row))
            if len(out)>=limit: break
        return out

    def monitor_state(self):
        for item in self.memories():
            if item.get("key")=="render.monitor.state":
                try:
                    return json.loads(item.get("value") or "{}")
                except Exception:
                    return {}
        return {}

    def set_monitor_state(self,data):
        self.save_memory("render.monitor.state",json.dumps(data,ensure_ascii=False))

    def upsert_incident(self,incident):
        with self.connect() as con:
            row=con.execute("SELECT * FROM incidents WHERE fingerprint=?",(incident["fingerprint"],)).fetchone()
            if row:
                con.execute("""UPDATE incidents
                               SET severity=?,status=?,message=?,service_id=?,last_seen=?,occurrences=occurrences+1,data=?
                               WHERE fingerprint=?""",
                            (incident["severity"],incident.get("status","OPEN"),incident["message"],
                             incident.get("service_id"),incident["timestamp"],
                             json.dumps(incident,ensure_ascii=False),incident["fingerprint"]))
                con.commit()
                updated=con.execute("SELECT * FROM incidents WHERE fingerprint=?",(incident["fingerprint"],)).fetchone()
                return {**dict(updated),"new":False}
            con.execute("""INSERT INTO incidents
                           (fingerprint,severity,status,message,service_id,first_seen,last_seen,occurrences,data)
                           VALUES(?,?,?,?,?,?,?,?,?)""",
                        (incident["fingerprint"],incident["severity"],incident.get("status","OPEN"),
                         incident["message"],incident.get("service_id"),incident["timestamp"],incident["timestamp"],
                         1,json.dumps(incident,ensure_ascii=False)))
            con.commit()
            created=con.execute("SELECT * FROM incidents WHERE fingerprint=?",(incident["fingerprint"],)).fetchone()
            return {**dict(created),"new":True}

    def incidents(self,limit=50):
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT * FROM incidents ORDER BY last_seen DESC,id DESC LIMIT ?",(limit,)).fetchall()]

    def events(self,limit=50):
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]

    def device_agent_touch(self, agent_id, seen_at=None):
        import time
        with self.connect() as con:
            con.execute(
                "INSERT INTO device_agents(agent_id,last_seen) VALUES(?,?) "
                "ON CONFLICT(agent_id) DO UPDATE SET last_seen=excluded.last_seen",
                (agent_id, float(seen_at if seen_at is not None else time.time()))
            )
            con.commit()

    def device_agents(self):
        with self.connect() as con:
            return [dict(x) for x in con.execute(
                "SELECT agent_id,last_seen FROM device_agents ORDER BY last_seen DESC"
            ).fetchall()]

    def device_task_create(self, task_id, task, params, created_at):
        with self.connect() as con:
            con.execute("INSERT INTO device_tasks(task_id,task,params,status,created_at) VALUES(?,?,?,?,?)",
                        (task_id,task,json.dumps(params or {},ensure_ascii=False),"QUEUED",str(created_at)))
            con.commit()

    def device_task_claim(self, agent_id):
        # Serialize claimers so two polling requests cannot claim the same task.
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row=con.execute("SELECT * FROM device_tasks WHERE status='QUEUED' ORDER BY created_at,task_id LIMIT 1").fetchone()
            if not row:
                con.commit()
                return None
            t=dict(row); claimed=now()
            updated=con.execute(
                "UPDATE device_tasks SET status='CLAIMED',agent_id=?,claimed_at=? WHERE task_id=? AND status='QUEUED'",
                (agent_id,claimed,t["task_id"])
            ).rowcount
            if updated != 1:
                con.rollback()
                return None
            con.commit()
        t["status"]="CLAIMED"; t["agent_id"]=agent_id; t["claimed_at"]=claimed
        try: t["params"]=json.loads(t["params"])
        except Exception: t["params"]={}
        return t

    def device_task_requeue_stale(self, max_age_seconds=120):
        """Return stale CLAIMED tasks to QUEUED so a lost agent cannot deadlock the queue."""
        import time
        age_limit=max(5, float(max_age_seconds))
        cutoff=time.time() - age_limit
        with self.connect() as con:
            rows=con.execute("SELECT task_id,claimed_at FROM device_tasks WHERE status='CLAIMED'").fetchall()
            stale=[]
            for row in rows:
                try:
                    age=time.time() - float(row["claimed_at"])
                except (TypeError,ValueError):
                    continue
                if age > age_limit:
                    changed=con.execute("UPDATE device_tasks SET status='QUEUED',agent_id=NULL,claimed_at=NULL WHERE task_id=? AND status='CLAIMED'",(row["task_id"],)).rowcount
                    if changed: stale.append(row["task_id"])
            con.commit()
        return stale

    def device_task_report(self, task_id, agent_id, ok, result, error):
        with self.connect() as con:
            row=con.execute("SELECT agent_id FROM device_tasks WHERE task_id=?",(task_id,)).fetchone()
            if not row: return None
            if row["agent_id"] != agent_id: return "AGENT_MISMATCH"
            status="COMPLETED" if ok else "FAILED"
            con.execute("UPDATE device_tasks SET status=?,completed_at=?,result=?,error=? WHERE task_id=?",
                        (status,now(),json.dumps(result or {},ensure_ascii=False),(error or "")[:1000],task_id))
            con.commit()
            return status

    def device_task_get(self, task_id):
        with self.connect() as con:
            row=con.execute("SELECT * FROM device_tasks WHERE task_id=?",(task_id,)).fetchone()
        if not row: return None
        t=dict(row)
        try: t["params"]=json.loads(t["params"])
        except Exception: t["params"]={}
        try: t["result"]=json.loads(t["result"])
        except Exception: t["result"]={}
        return t

    def device_task_counts(self):
        with self.connect() as con:
            rows=con.execute("SELECT status,COUNT(*) n FROM device_tasks GROUP BY status").fetchall()
        return {r["status"]:r["n"] for r in rows}
