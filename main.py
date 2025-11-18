from fastapi import FastAPI
from routers import invoice

app = FastAPI(title="Invoice Status API")

# Include the router for all invoice-related endpoints
app.include_router(invoice.router)