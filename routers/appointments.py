# backend/routers/appointments.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from supabase_client import supabase_admin

router = APIRouter(prefix="/appointments", tags=["appointments"])


class CreateAppointmentIn(BaseModel):
    business_id: str
    customer_name: str
    customer_phone: str
    service_id: str
    employee_id: Optional[str] = None
    datetime: datetime


class UpdateAppointmentStatusIn(BaseModel):
    status: str  # 'pending' | 'confirmed' | 'cancelled' | 'completed'


@router.post("/", summary="Crear cita")
def create_appointment(data: CreateAppointmentIn):
    appointment_insert = {
        "business_id": data.business_id,
        "customer_name": data.customer_name,
        "customer_phone": data.customer_phone,
        "service_id": data.service_id,
        "employee_id": data.employee_id,
        "datetime": data.datetime.isoformat(),
        "status": "pending",
    }

    res = supabase_admin.table("appointments").insert(appointment_insert).execute()
    if not res.data:
        raise HTTPException(status_code=400, detail="No se pudo crear la cita")

    return res.data[0]


@router.get("/by-business/{business_id}", summary="Listar citas por negocio")
def list_appointments(
    business_id: str,
    status: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
):
    query = (
        supabase_admin.table("appointments")
        .select("*")
        .eq("business_id", business_id)
        .order("datetime", desc=False)
    )

    if status:
        query = query.eq("status", status)
    if from_date:
        query = query.gte("datetime", from_date.isoformat())
    if to_date:
        query = query.lte("datetime", to_date.isoformat())

    res = query.execute()
    return res.data


@router.patch("/{appointment_id}/status", summary="Cambiar estado de cita")
def update_appointment_status(
    appointment_id: str, data: UpdateAppointmentStatusIn
):
    if data.status not in ("pending", "confirmed", "cancelled", "completed"):
        raise HTTPException(status_code=400, detail="status inválido")

    res = (
        supabase_admin.table("appointments")
        .update({"status": data.status})
        .eq("id", appointment_id)
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    return res.data[0]
