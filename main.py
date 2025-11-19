import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import LicenseProduct, LicenseOrder, OrderItem

app = FastAPI(title="NWTech Services API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "NWTech Services Backend Running"}


# -----------------------------
# License Catalog Endpoints
# -----------------------------

@app.get("/api/licenses", response_model=List[LicenseProduct])
def list_licenses(q: Optional[str] = None, vendor: Optional[str] = None):
    """List/search license products from the catalog"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    query = {}
    if q:
        # simple text search across name/description
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"sku": {"$regex": q, "$options": "i"}},
        ]
    if vendor:
        query["vendor"] = vendor

    docs = get_documents("licenseproduct", query)
    items = []
    for d in docs:
        d.pop("_id", None)
        items.append(LicenseProduct(**d))
    return items


class CreateLicenseProduct(LicenseProduct):
    pass


@app.post("/api/licenses", status_code=201)
def create_license(product: CreateLicenseProduct):
    """Admin: add a new license product to catalog"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Ensure SKU unique
    exists = db["licenseproduct"].find_one({"sku": product.sku})
    if exists:
        raise HTTPException(status_code=400, detail="SKU already exists")

    _id = create_document("licenseproduct", product)
    return {"id": _id}


@app.post("/api/licenses/seed")
def seed_licenses():
    """Seed catalog with a few Saad license plans if empty"""
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    count = db["licenseproduct"].count_documents({})
    if count > 0:
        return {"status": "ok", "message": "Catalog already has items", "count": count}

    samples: List[LicenseProduct] = [
        LicenseProduct(
            name="Saad Basic",
            sku="SAAD-BASIC-1Y",
            vendor="Saad",
            description="Entry plan ideal for small teams",
            price=99.0,
            duration_months=12,
            tier="Basic",
            features=["Up to 10 users", "Email support", "Core features"],
            terms_url="https://saad.example.com/terms"
        ),
        LicenseProduct(
            name="Saad Pro",
            sku="SAAD-PRO-1Y",
            vendor="Saad",
            description="Professional plan for growing companies",
            price=249.0,
            duration_months=12,
            tier="Pro",
            features=["Up to 50 users", "Priority support", "Advanced analytics"],
            terms_url="https://saad.example.com/terms"
        ),
        LicenseProduct(
            name="Saad Enterprise",
            sku="SAAD-ENT-1Y",
            vendor="Saad",
            description="Enterprise-grade with SSO and dedicated support",
            price=599.0,
            duration_months=12,
            tier="Enterprise",
            features=["Unlimited users", "SSO/SAML", "Dedicated CSM"],
            terms_url="https://saad.example.com/terms"
        ),
    ]

    inserted = 0
    for s in samples:
        create_document("licenseproduct", s)
        inserted += 1

    return {"status": "ok", "inserted": inserted}


# -----------------------------
# Ordering Endpoints
# -----------------------------

class CreateOrder(BaseModel):
    company: Optional[str] = None
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    items: List[OrderItem]
    notes: Optional[str] = None


@app.post("/api/orders", status_code=201)
def place_order(order: CreateOrder):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Calculate totals and validate items against catalog
    total = 0.0
    validated_items: List[OrderItem] = []
    for item in order.items:
        prod = db["licenseproduct"].find_one({"sku": item.sku})
        if not prod:
            raise HTTPException(status_code=404, detail=f"SKU not found: {item.sku}")
        unit_price = float(prod.get("price", 0))
        name = prod.get("name")
        subtotal = unit_price * item.quantity
        total += subtotal
        validated_items.append(
            OrderItem(sku=item.sku, name=name, quantity=item.quantity, unit_price=unit_price, subtotal=subtotal)
        )

    order_doc = LicenseOrder(
        company=order.company,
        contact_name=order.contact_name,
        contact_email=order.contact_email,
        contact_phone=order.contact_phone,
        items=validated_items,
        total_amount=round(total, 2),
        status="pending",
        notes=order.notes,
    )

    order_id = create_document("licenseorder", order_doc)
    return {"order_id": order_id, "total": order_doc.total_amount, "status": order_doc.status}


@app.get("/api/orders")
def list_orders(email: Optional[str] = None):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    query = {"vendor": "Saad"}
    if email:
        query["contact_email"] = email
    orders = get_documents("licenseorder", query)
    for o in orders:
        o["id"] = str(o.pop("_id"))
    return orders


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db as _db

        if _db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = _db.name if hasattr(_db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = _db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
