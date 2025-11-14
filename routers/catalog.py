# backend/routers/catalog.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from supabase_client import supabase_admin

router = APIRouter(prefix="/catalog", tags=["catalog"])


class CatalogItemIn(BaseModel):
    business_id: str
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    stock: int = 0


class CatalogOrderItemIn(BaseModel):
    catalog_item_id: str
    quantity: int
    price: float


class CatalogOrderIn(BaseModel):
    business_id: str
    customer_name: str
    customer_phone: str
    items: List[CatalogOrderItemIn]
    total: float


@router.post("/items", summary="Crear producto de catálogo")
def create_catalog_item(data: CatalogItemIn):
    res = supabase_admin.table("catalog_items").insert(data.dict()).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo crear el item")
    return res.data[0]


@router.get("/items/{business_id}", summary="Listar catálogo por negocio")
def list_catalog_items(business_id: str):
    res = (
        supabase_admin.table("catalog_items")
        .select("*")
        .eq("business_id", business_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


@router.post("/orders", summary="Crear pedido de catálogo")
def create_catalog_order(data: CatalogOrderIn):
    # 1) crear orden
    order_insert = {
        "business_id": data.business_id,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "status": "pending",
        "total": data.total,
    }
    res_order = supabase_admin.table("catalog_orders").insert(order_insert).execute()
    if not res_order.data:
        raise HTTPException(status_code=400, detail="No se pudo crear la orden")

    order = res_order.data[0]
    order_id = order["id"]

    # 2) (opcional) podrías crear tabla catalog_order_items;
    # por ahora solo regresamos la orden
    return {"order": order}


@router.get("/orders/{business_id}", summary="Listar órdenes de catálogo")
def list_catalog_orders(business_id: str, status: Optional[str] = None):
    query = (
        supabase_admin.table("catalog_orders")
        .select("*")
        .eq("business_id", business_id)
        .order("created_at", desc=True)
    )
    if status:
        query = query.eq("status", status)
    res = query.execute()
    return res.data
