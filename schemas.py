"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List

# Example schemas (you can keep or extend these):

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    address: Optional[str] = Field(None, description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Generic products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# ------------------------------------------------------------------
# License management schemas for NWTech Services
# ------------------------------------------------------------------

class LicenseProduct(BaseModel):
    """Represents a licensable SaaS/SaaD product/plan"""
    name: str = Field(..., description="License name as displayed to customers")
    sku: str = Field(..., description="Unique SKU/code for the license plan")
    vendor: str = Field("Saad", description="Software vendor name")
    description: Optional[str] = Field(None, description="Short description of the plan")
    price: float = Field(..., ge=0, description="Unit price in USD")
    duration_months: int = Field(12, ge=1, le=60, description="License term in months")
    tier: Optional[str] = Field(None, description="Plan tier or edition (Basic/Pro/Enterprise)")
    features: List[str] = Field(default_factory=list, description="Key features list")
    terms_url: Optional[str] = Field(None, description="Link to licensing terms")

class OrderItem(BaseModel):
    sku: str
    name: str
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)
    subtotal: float = Field(ge=0)

class LicenseOrder(BaseModel):
    """Represents a customer order for licenses"""
    company: Optional[str] = None
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None
    items: List[OrderItem]
    total_amount: float = Field(ge=0)
    vendor: str = Field("Saad")
    status: str = Field("pending", description="pending, reviewing, approved, fulfilled, cancelled")
    notes: Optional[str] = None

# Note: The Flames database viewer will automatically:
# 1. Read these schemas from GET /schema endpoint
# 2. Use them for document validation when creating/editing
# 3. Handle all database operations (CRUD) directly
# 4. You don't need to create any database endpoints!
