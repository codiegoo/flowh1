from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth_business, orders, appointments, catalog, whatsapp_bot

app = FastAPI(title="Flow1H API")

# ⚠️ DEV: permitir todo para no pelear con CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # <--- aquí lo abrimos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_business.router)
app.include_router(orders.router)
app.include_router(appointments.router)
app.include_router(catalog.router)
app.include_router(whatsapp_bot.router)


@app.get("/")
def root():
    return {"status": "ok", "message": "Flow1H backend live"}
