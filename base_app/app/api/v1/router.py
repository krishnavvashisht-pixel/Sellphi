from fastapi import APIRouter

from app.api.v1.admin.routes import router as admin_router
from app.api.v1.auth.routes import router as auth_router
from app.api.v1.campaigns.routes import router as campaigns_router
from app.api.v1.companies.routes import router as companies_router
from app.api.v1.contacts.routes import router as contacts_router
from app.api.v1.health.routes import router as health_router
from app.api.v1.integrations.routes import router as integrations_router
from app.api.v1.missions.routes import router as missions_router
from app.api.v1.opportunities.routes import router as opportunities_router
from app.api.v1.products.routes import router as products_router
from app.api.v1.signals.routes import router as signals_router
from app.api.v1.workspace.routes import router as workspace_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(workspace_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(missions_router)
api_v1_router.include_router(signals_router)
api_v1_router.include_router(opportunities_router)
api_v1_router.include_router(companies_router)
api_v1_router.include_router(contacts_router)
api_v1_router.include_router(campaigns_router)
api_v1_router.include_router(integrations_router)

