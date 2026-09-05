from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.buyer_personas.routes import products_router as buyer_personas_products_router
from app.api.v1.buyer_personas.routes import router as buyer_personas_router
from app.api.v1.campaigns.routes import router as campaigns_router
from app.api.v1.companies.routes import router as companies_router
from app.api.v1.contacts.routes import router as contacts_router
from app.api.v1.health.routes import router as health_router
from app.api.v1.icps.routes import products_router as icps_products_router
from app.api.v1.icps.routes import router as icps_router
from app.api.v1.integrations.routes import router as integrations_router
from app.api.v1.missions.routes import router as missions_router
from app.api.v1.products.routes import router as products_router
from app.api.v1.workspace.routes import router as workspace_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(workspace_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(icps_router)
api_v1_router.include_router(icps_products_router)  # GET /products/{id}/default-icp
api_v1_router.include_router(buyer_personas_router)
api_v1_router.include_router(buyer_personas_products_router)  # GET /products/{id}/default-persona
api_v1_router.include_router(missions_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(contacts_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(integrations_router)
