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

    def events(self,limit=50):
        with self.connect() as con:
            return [dict(x) for x in con.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?",(limit,)).fetchall()]
