# backend/routers/orders.py
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

from supabase_client import supabase_admin

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderItemIn(BaseModel):
    product_id: str
    quantity: int
    price: float


class CreateOrderIn(BaseModel):
    business_id: str

    customer_name: str
    customer_phone: str
    delivery_address: str
    delivery_references: Optional[str] = None

    amount_total: float          # "cuánto es"
    payment_method: str          # 'cash' | 'transfer'
    amount_paid: Optional[float] = None   # "con cuánto paga"
    change_amount: Optional[float] = None

    items: List[OrderItemIn]


@router.post("/", summary="Crear pedido con items")
def create_order(data: CreateOrderIn):
    if data.payment_method not in ("cash", "transfer"):
        raise HTTPException(status_code=400, detail="payment_method inválido")

    # calcular cambio si es efectivo
    change = data.change_amount
    if data.payment_method == "cash" and data.amount_paid is not None:
        change = data.amount_paid - data.amount_total

    status = "pending"
    if data.payment_method == "transfer":
        status = "waiting_payment"

    order_insert = {
        "business_id": data.business_id,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "delivery_address": data.delivery_address,
        "delivery_references": data.delivery_references,
        "amount_total": data.amount_total,
        "payment_method": data.payment_method,
        "amount_paid": data.amount_paid,
        "change_amount": change,
        "status": status,
    }

    res_order = supabase_admin.table("orders").insert(order_insert).execute()
    if not res_order.data:
        raise HTTPException(status_code=400, detail="No se pudo crear el pedido")

    order = res_order.data[0]
    order_id = order["id"]

    # items
    items_insert = [
        {
            "order_id": order_id,
            "product_id": it.product_id,
            "quantity": it.quantity,
            "price": it.price,
        }
        for it in data.items
    ]
    supabase_admin.table("order_items").insert(items_insert).execute()

    return {"order": order}


@router.get("/by-business/{business_id}", summary="Listar pedidos por negocio")
def list_orders(business_id: str, status: Optional[str] = None):
    query = (
        supabase_admin.table("orders")
        .select("*")
        .eq("business_id", business_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)

    res = query.execute()
    return res.data


@router.post("/{order_id}/receipt", summary="Subir captura de transferencia")
async def upload_transfer_receipt(order_id: str, file: UploadFile = File(...)):
    ext = file.filename.split(".")[-1]
    filename = f"{order_id}/{uuid.uuid4()}.{ext}"

    file_bytes = await file.read()
    storage = supabase_admin.storage

    try:
        storage.from_("transfer_receipts").upload(filename, file_bytes)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error subiendo archivo: {e}")

    public_url = storage.from_("transfer_receipts").get_public_url(filename)

    supabase_admin.table("orders").update(
        {
            "transfer_receipt_url": public_url,
            "status": "payment_confirmed",
            "payment_confirmed_at": datetime.astimezone(),
        }
    ).eq("id", order_id).execute()

    return {"order_id": order_id, "transfer_receipt_url": public_url}
