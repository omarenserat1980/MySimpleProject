import json
import sqlite3
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
            return [dict(x) for x in con.execute("SELECT key,value,updated_at FROM memories ORDER BY id DESC").fetchall()]

    def save_memory(self,key,value):
        with self.connect() as con:
            con.execute("""INSERT INTO memories(key,value,updated_at) VALUES(?,?,?)
                           ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",(key,value,now()))
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
                                      SUM(CASE WHEN status IN ('READY','IN_PROGRESS') THEN 1 ELSE 0 END) active,
                                      SUM(CASE WHEN verification_status='VERIFIED' THEN 1 ELSE 0 END) verified_count
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
