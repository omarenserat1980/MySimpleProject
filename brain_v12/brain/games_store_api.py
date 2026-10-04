"""BRAIN Originals game commerce API.

Fail-closed:
- creates real Stripe Checkout Sessions only when STRIPE_SECRET_KEY exists
- verifies Stripe webhook signatures before marking orders paid
- generates a one-time delivery token after verified payment
- never accepts card data
"""
from __future__ import annotations
import hashlib,hmac,json,os,secrets,time
from pathlib import Path
import httpx
from fastapi import APIRouter,HTTPException,Request
from pydantic import BaseModel,Field

ORIGIN=os.getenv("BRAIN_PUBLIC_ORIGIN","https://omarenserat1980.github.io/MySimpleProject").rstrip("/")
ORDERS_PATH=Path(os.getenv("BRAIN_GAMES_ORDERS_DB","brain_v12_games_orders.json"))

GAMES={
 "neon-rift":{"id":"neon-rift","title":"BRAIN: Neon Rift","price_usd":4.99,"platform":"Web/PC","delivery_path":"/games/neon-rift.html"},
 "last-light":{"id":"last-light","title":"BRAIN: Last Light","price_usd":6.99,"platform":"Web/PC","delivery_path":"/games/last-light.html"},
 "drift-circuit":{"id":"drift-circuit","title":"BRAIN: Drift Circuit","price_usd":7.99,"platform":"Web/PC","delivery_path":"/games/drift-circuit.html"},
}

def _read():
    if not ORDERS_PATH.exists(): return {}
    try:return json.loads(ORDERS_PATH.read_text(encoding="utf-8"))
    except Exception:return {}

def _write(data):
    ORDERS_PATH.parent.mkdir(parents=True,exist_ok=True)
    tmp=ORDERS_PATH.with_suffix(".tmp");tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(ORDERS_PATH)

def _new_order(game):
    oid="BG-"+secrets.token_hex(7).upper()
    token=secrets.token_urlsafe(32)
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    order={"order_id":oid,"game_id":game["id"],"game_title":game["title"],"amount_usd":game["price_usd"],
           "currency":"usd","state":"PAYMENT_PENDING","created_at":int(time.time()),
           "token_hash":token_hash,"payment":{"status":"PENDING"},"delivery":{"status":"PENDING"}}
    d=_read();d[oid]=order;_write(d)
    return order,token

class CheckoutIn(BaseModel):
    game_id:str=Field(min_length=3,max_length=80)
    email:str=Field(default="",max_length=320)

def _stripe_configured(): return bool(os.getenv("STRIPE_SECRET_KEY") and os.getenv("STRIPE_WEBHOOK_SECRET"))

def _stripe_headers():
    return {"Authorization":"Bearer "+os.environ["STRIPE_SECRET_KEY"],"Content-Type":"application/x-www-form-urlencoded"}

async def _stripe_get_session(session_id):
    async with httpx.AsyncClient(timeout=25) as client:
        r=await client.get("https://api.stripe.com/v1/checkout/sessions/"+session_id,
                           headers=_stripe_headers())
    if r.status_code>=400: raise HTTPException(502,"PAYMENT_PROVIDER_ERROR")
    return r.json()

async def _stripe_checkout(order,email):
    game=GAMES[order["game_id"]]
    data={
      "mode":"payment",
      "success_url":ORIGIN+"/games-success.html?session_id={CHECKOUT_SESSION_ID}",
      "cancel_url":ORIGIN+"/games-store.html?cancelled=1&order_id="+order["order_id"],
      "line_items[0][quantity]":"1",
      "line_items[0][price_data][currency]":"usd",
      "line_items[0][price_data][unit_amount]":str(int(round(game["price_usd"]*100))),
      "line_items[0][price_data][product_data][name]":game["title"],
      "line_items[0][price_data][product_data][description]":"Original BRAIN game license",
      "metadata[order_id]":order["order_id"],
      "metadata[game_id]":game["id"],
    }
    if email: data["customer_email"]=email
    async with httpx.AsyncClient(timeout=25) as client:
        r=await client.post("https://api.stripe.com/v1/checkout/sessions",headers=_stripe_headers(),data=data)
    if r.status_code>=400: raise HTTPException(502,"PAYMENT_PROVIDER_ERROR")
    return r.json()

def _stripe_sig_ok(raw,header,secret):
    parts={}
    for item in header.split(","):
        if "=" in item:
            k,v=item.split("=",1);parts.setdefault(k,[]).append(v)
    try:t=int(parts["t"][0]);sig=parts["v1"]
    except Exception:return False
    if abs(int(time.time())-t)>300:return False
    expected=hmac.new(secret.encode(),f"{t}.".encode()+raw,hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected,x) for x in sig)

router=APIRouter(prefix="/api/games",tags=["games"])

@router.get("/catalog")
def catalog():
    return {"ok":True,"currency":"USD","payment_configured":_stripe_configured(),
            "games":[{**g,"sellable":True,"checkout_ready":_stripe_configured()} for g in GAMES.values()]}

@router.get("/status")
def status():
    orders=_read()
    return {"ok":True,"payment_configured":_stripe_configured(),
            "orders":len(orders),
            "paid":sum(1 for x in orders.values() if x.get("state")=="PAID"),
            "delivered":sum(1 for x in orders.values() if x.get("state")=="DELIVERED")}

@router.post("/checkout")
async def checkout(body:CheckoutIn):
    if not _stripe_configured(): raise HTTPException(503,"PAYMENT_PROVIDER_NOT_CONFIGURED")
    game=GAMES.get(body.game_id)
    if not game: raise HTTPException(404,"GAME_NOT_FOUND")
    order,token=_new_order(game)
    session=await _stripe_checkout(order,body.email.strip())
    d=_read();d[order["order_id"]]["payment"].update({"provider":"stripe","session_id":session.get("id")});_write(d)
    return {"ok":True,"order_id":order["order_id"],"checkout_url":session.get("url"),"delivery_token":token}

@router.get("/checkout-result")
async def checkout_result(session_id:str):
    if not _stripe_configured(): raise HTTPException(503,"PAYMENT_PROVIDER_NOT_CONFIGURED")
    if not session_id or len(session_id)>200: raise HTTPException(400,"INVALID_SESSION_ID")
    session=await _stripe_get_session(session_id)
    if session.get("payment_status")!="paid": raise HTTPException(409,"PAYMENT_NOT_VERIFIED")
    oid=(session.get("metadata") or {}).get("order_id","")
    d=_read();o=d.get(oid)
    if not o: raise HTTPException(404,"ORDER_NOT_FOUND")
    if (o.get("payment") or {}).get("session_id")!=session_id: raise HTTPException(409,"SESSION_MISMATCH")
    expected=int(round(o["amount_usd"]*100))
    if int(session.get("amount_total") or 0)!=expected or (session.get("currency") or "").lower()!="usd":
        raise HTTPException(409,"PAYMENT_AMOUNT_MISMATCH")
    if o.get("state") not in {"PAID","DELIVERED"}: raise HTTPException(409,"PAYMENT_NOT_RECORDED")
    if o.get("state")=="DELIVERED":
        return {"ok":True,"order_id":oid,"game_id":o["game_id"],"game_title":o["game_title"],
                "license":o.get("license",""),"download_url":ORIGIN+GAMES[o["game_id"]]["delivery_path"],
                "already_delivered":True}
    token=secrets.token_urlsafe(32)
    o["token_hash"]=hashlib.sha256(token.encode()).hexdigest()
    o["delivery"]={"status":"READY","url":ORIGIN+GAMES[o["game_id"]]["delivery_path"]}
    d[oid]=o;_write(d)
    license_token="BRAIN-"+secrets.token_hex(10).upper()
    o["license"]=license_token
    d[oid]=o;_write(d)
    return {"ok":True,"order_id":oid,"game_id":o["game_id"],"game_title":o["game_title"],
            "license":license_token,"download_url":ORIGIN+GAMES[o["game_id"]]["delivery_path"],
            "delivery_url":ORIGIN+"/api/games/orders/"+oid+"/delivery?token="+token}

@router.post("/webhook")
async def webhook(request:Request):
    secret=os.getenv("STRIPE_WEBHOOK_SECRET","")
    raw=await request.body();sig=request.headers.get("Stripe-Signature","")
    if not secret or not _stripe_sig_ok(raw,sig,secret): raise HTTPException(401,"INVALID_STRIPE_SIGNATURE")
    try:event=json.loads(raw)
    except Exception:raise HTTPException(400,"INVALID_JSON")
    if event.get("type")!="checkout.session.completed": return {"ok":True,"ignored":True}
    session=event.get("data",{}).get("object",{})
    if session.get("payment_status")!="paid": return {"ok":True,"ignored":True}
    oid=(session.get("metadata") or {}).get("order_id","");d=_read();order=d.get(oid)
    if not order: raise HTTPException(404,"ORDER_NOT_FOUND")
    if order.get("state")!="PAYMENT_PENDING": return {"ok":True,"already_processed":True}
    paid=int(session.get("amount_total") or 0)
    expected=int(round(order["amount_usd"]*100))
    if paid!=expected or (session.get("currency") or "").lower()!="usd": raise HTTPException(409,"PAYMENT_AMOUNT_MISMATCH")
    order["state"]="PAID";order["payment"]={"status":"VERIFIED","provider":"stripe","session_id":session.get("id"),"verified_at":int(time.time())}
    order["delivery"]={"status":"READY","url":ORIGIN+GAMES[order["game_id"]]["delivery_path"]}
    d[oid]=order;_write(d)
    return {"ok":True,"verified":True,"order_id":oid,"state":"PAID"}

@router.get("/orders/{order_id}/delivery")
def delivery(order_id:str,token:str=""):
    d=_read();o=d.get(order_id)
    if not o: raise HTTPException(404,"ORDER_NOT_FOUND")
    if o.get("state")!="PAID": raise HTTPException(409,"PAYMENT_NOT_VERIFIED")
    if not token or not hmac.compare_digest(hashlib.sha256(token.encode()).hexdigest(),o.get("token_hash","")): raise HTTPException(403,"INVALID_DELIVERY_TOKEN")
    o["state"]="DELIVERED";o["delivery"]["status"]="DELIVERED";o["delivery"]["delivered_at"]=int(time.time());d[order_id]=o;_write(d)
    return {"ok":True,"order_id":order_id,"game_id":o["game_id"],"game_title":o["game_title"],"license":o.get("license",""),"download_url":o["delivery"]["url"]}
