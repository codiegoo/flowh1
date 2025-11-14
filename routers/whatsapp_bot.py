from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from supabase_client import supabase_admin

router = APIRouter(prefix="/whatsapp-bot", tags=["whatsapp-bot"])


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
    # upsert por business_id
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
