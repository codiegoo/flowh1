# backend/routers/auth_business.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from supabase_client import supabase_admin

router = APIRouter(prefix="/auth-business", tags=["auth"])

DEFAULT_PASSWORD = "cambiaesto123"


@router.get("/ping")
def ping():
    return {"message": "pong"}


class RegisterBusinessIn(BaseModel):
    email: EmailStr
    password: str | None = None
    name: str
    type: str  # 'orders' | 'appointments' | 'catalog'
    phone: str | None = None
    whatsapp_number: str | None = None
    address: str | None = None
    address_references: str | None = None


@router.post("/register")
def register_business(data: RegisterBusinessIn):
    password = data.password or DEFAULT_PASSWORD

    # 1) crear usuario en Supabase Auth
    try:
        user_res = supabase_admin.auth.admin.create_user(
            {
                "email": data.email,
                "password": password,
                "email_confirm": True,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creando usuario: {e}")

    user = user_res.user
    if not user:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario")

    # 2) crear negocio
    business_insert = {
        "owner_user_id": user.id,
        "name": data.name,
        "type": data.type,
        "phone": data.phone,
        "whatsapp_number": data.whatsapp_number,
        "address": data.address,
        "address_references": data.address_references,
    }

    res = supabase_admin.table("businesses").insert(business_insert).execute()
    business = res.data[0]

    return {
        "user_id": user.id,
        "business": business,
        "default_password_used": data.password is None,
    }


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login_business(data: LoginIn):
    try:
        res = supabase_admin.auth.sign_in_with_password(
            {"email": data.email, "password": data.password}
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login incorrecto: {e}")

    if not res.session:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    return {
        "access_token": res.session.access_token,
        "refresh_token": res.session.refresh_token,
        "user": {
            "id": res.user.id,
            "email": res.user.email,
        },
    }



@router.get("/business-by-owner/{user_id}")
def get_business_by_owner(user_id: str):
    res = (
        supabase_admin.table("businesses")
        .select("*")
        .eq("owner_user_id", user_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=404, detail="Business not found")

    # por ahora asumimos 1 negocio por usuario
    return res.data[0]
