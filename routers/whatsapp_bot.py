import os
from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Optional
import httpx

from supabase_client import supabase_admin

router = APIRouter(prefix="/whatsapp-bot", tags=["whatsapp-bot"])


# ---------- MODELOS PARA CONFIG ----------

class BotConfigIn(BaseModel):
    business_id: str
    provider: str = "whatsapp_cloud"
    phone_number_id: str
    waba_id: str
    access_token: str
    verify_token: str
    bot_type: str = "orders"  # 'orders' | 'appointments' | 'catalog'

    greeting_message: Optional[str] = None
    ask_order_message: Optional[str] = None
    ask_address_message: Optional[str] = None
    ask_payment_method_message: Optional[str] = None
    closing_message: Optional[str] = None


class BotTextsUpdate(BaseModel):
    greeting_message: Optional[str] = None
    ask_order_message: Optional[str] = None
    ask_address_message: Optional[str] = None
    ask_payment_method_message: Optional[str] = None
    closing_message: Optional[str] = None


# ---------- ENDPOINTS PARA CONFIG (los que ya veías en /docs) ----------

@router.get("/by-business/{business_id}")
def get_bot_config(business_id: str):
    res = (
        supabase_admin.table("whatsapp_bot_configs")
        .select("*")
        .eq("business_id", business_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="No hay bot configurado para este negocio")
    return res.data[0]


@router.post("/", summary="Crear o reemplazar config de bot")
def upsert_bot_config(data: BotConfigIn):
    fields = data.dict()
    res = (
        supabase_admin.table("whatsapp_bot_configs")
        .upsert(fields, on_conflict="business_id")
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo guardar la configuración del bot")
    return res.data[0]


@router.patch("/texts/{business_id}", summary="Actualizar solo textos del bot")
def update_bot_texts(business_id: str, texts: BotTextsUpdate):
    updates = {k: v for k, v in texts.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No se enviaron textos para actualizar")

    res = (
        supabase_admin.table("whatsapp_bot_configs")
        .update(updates)
        .eq("business_id", business_id)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Bot no encontrado para este negocio")

    return res.data[0]


# ---------- HELPER: ENVIAR MENSAJE DE TEXTO A WHATSAPP CLOUD ----------

async def send_whatsapp_text(phone_number_id: str, access_token: str, to_number: str, text: str):
    url = f"https://graph.facebook.com/v22.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code >= 400:
            print("WhatsApp send error:", resp.status_code, resp.text)


# ---------- GET /webhook (VERIFICACIÓN CON META) ----------
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "flowh1-dev-token")


@router.get("/webhook", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """
    Meta llama a este GET cuando configuras el webhook.
    Aquí SOLO comparamos contra un token fijo (env o por defecto).
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN and hub_challenge:
        # devolvemos el challenge tal cual lo manda Meta
        return hub_challenge

    raise HTTPException(status_code=403, detail="Verification failed")

# ---------- POST /webhook (MENSAJES REALES) ----------

@router.post("/webhook")
async def whatsapp_webhook(payload: dict = Body(...)):
    """
    Aquí llegan los mensajes reales de WhatsApp.

    Versión simple:
      - Detecta phone_number_id y número del cliente
      - Busca la config del bot (whatsapp_bot_configs)
      - Crea un pedido pendiente en 'orders'
      - Responde con greeting + ask_order
    """

    entry_list = payload.get("entry", [])
    if not entry_list:
        return {"status": "ignored"}

    changes = entry_list[0].get("changes", [])
    if not changes:
        return {"status": "ignored"}

    value = changes[0].get("value", {})
    messages = value.get("messages", [])
    if not messages:
        return {"status": "no_messages"}

    message = messages[0]
    from_number = message.get("from")
    msg_type = message.get("type")

    if not from_number:
        return {"status": "missing_from"}

    if msg_type == "text":
        text_body = message["text"]["body"].strip()
        print("Mensaje recibido:", text_body)

    phone_number_id = value.get("metadata", {}).get("phone_number_id")
    if not phone_number_id:
        return {"status": "missing_phone_number_id"}

    # vincular phone_number_id -> negocio
    res = (
        supabase_admin.table("whatsapp_bot_configs")
        .select("*")
        .eq("phone_number_id", phone_number_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        print("No bot config for phone_number_id", phone_number_id)
        return {"status": "no_bot_config"}

    bot_conf = res.data[0]
    business_id = bot_conf["business_id"]

    greeting = bot_conf["greeting_message"]
    ask_order = bot_conf["ask_order_message"]
    closing = bot_conf["closing_message"]

    # Crear pedido muy simple en 'orders'
    order_insert = {
        "business_id": business_id,
        "customer_name": f"Cliente WhatsApp {from_number}",
        "customer_phone": from_number,
        "delivery_address": "Por definir por chat",
        "delivery_references": None,
        "amount_total": 0,
        "payment_method": "cash",
        "amount_paid": None,
        "change_amount": None,
        "status": "pending",
    }
    order_res = supabase_admin.table("orders").insert(order_insert).execute()
    order = order_res.data[0]

    reply_text = (
        f"{greeting}\n\n"
        f"{ask_order}\n\n"
        f"(ID interno de tu pedido: {order['id'][:8]}...)"
    )

    await send_whatsapp_text(
        phone_number_id=bot_conf["phone_number_id"],
        access_token=bot_conf["access_token"],
        to_number=from_number,
        text=reply_text,
    )

    return {"status": "ok"}
