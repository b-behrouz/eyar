from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Optional
import sqlite3
import secrets
import os

app = FastAPI(title="Eyar API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "zarrin1234")

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(credentials.username.encode(), ADMIN_USERNAME.encode())
    ok_pass = secrets.compare_digest(credentials.password.encode(), ADMIN_PASSWORD.encode())
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="اطلاعات ورود اشتباه است",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

DB_PATH = "zarrinmap.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            phone      TEXT    NOT NULL,
            address    TEXT    NOT NULL,
            type       TEXT    NOT NULL DEFAULT 'gold',
            lat        REAL,
            lng        REAL,
            active     INTEGER NOT NULL DEFAULT 1,
            created_at TEXT    DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()

init_db()

class ShopCreate(BaseModel):
    name:    str
    phone:   str
    address: str
    type:    str = "gold"
    lat:     Optional[float] = None
    lng:     Optional[float] = None

class ShopUpdate(BaseModel):
    name:    Optional[str]   = None
    phone:   Optional[str]   = None
    address: Optional[str]   = None
    type:    Optional[str]   = None
    lat:     Optional[float] = None
    lng:     Optional[float] = None
    active:  Optional[int]   = None

@app.get("/api/shops")
def list_shops():
    conn = get_db()
    rows = conn.execute("SELECT * FROM shops WHERE active=1 ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/shops/{shop_id}")
def get_shop(shop_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM shops WHERE id=?", (shop_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "طلافروشی یافت نشد")
    return dict(row)

@app.get("/api/admin/shops")
def admin_list_shops(username: str = Depends(verify_admin)):
    conn = get_db()
    rows = conn.execute("SELECT * FROM shops ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/admin/shops", status_code=201)
def admin_create_shop(shop: ShopCreate, username: str = Depends(verify_admin)):
    if not shop.name.strip() or not shop.phone.strip() or not shop.address.strip():
        raise HTTPException(400, "همه فیلدها اجباری هستند")
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO shops (name, phone, address, type, lat, lng) VALUES (?,?,?,?,?,?)",
        (shop.name.strip(), shop.phone.strip(), shop.address.strip(), shop.type, shop.lat, shop.lng)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM shops WHERE id=?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)

@app.put("/api/admin/shops/{shop_id}")
def admin_update_shop(shop_id: int, shop: ShopUpdate, username: str = Depends(verify_admin)):
    conn = get_db()
    existing = conn.execute("SELECT * FROM shops WHERE id=?", (shop_id,)).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(404, "طلافروشی یافت نشد")
    fields = {k: v for k, v in shop.dict().items() if v is not None}
    if fields:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE shops SET {set_clause} WHERE id=?", list(fields.values()) + [shop_id])
        conn.commit()
    row = conn.execute("SELECT * FROM shops WHERE id=?", (shop_id,)).fetchone()
    conn.close()
    return dict(row)

@app.delete("/api/admin/shops/{shop_id}")
def admin_delete_shop(shop_id: int, username: str = Depends(verify_admin)):
    conn = get_db()
    if not conn.execute("SELECT id FROM shops WHERE id=?", (shop_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "طلافروشی یافت نشد")
    conn.execute("DELETE FROM shops WHERE id=?", (shop_id,))
    conn.commit()
    conn.close()
    return {"detail": "حذف شد", "id": shop_id}

@app.get("/api/admin/verify")
def admin_verify(username: str = Depends(verify_admin)):
    return {"ok": True, "username": username}
