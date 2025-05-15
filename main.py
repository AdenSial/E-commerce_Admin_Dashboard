from fastapi import FastAPI, Depends, HTTPException, status 
from typing import Annotated, List
from pydantic import BaseModel
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import func
from models import Product, Sale, Inventory 
app = FastAPI()
#demo data
def init_demo_data():
    db_session = SessionLocal()
    
    
    if db_session.query(models.Product).first():
        db_session.close()
        print("Demo data already exists. Skipping insertion.")
        return
    products = [
        models.Product(name="Laptop", description="High-end gaming laptop", price=1200.00, stock_quantity=50, category="Electronics"),
        models.Product(name="Smartphone", description="Latest model smartphone", price=800.00, stock_quantity=100, category="Electronics"),
        models.Product(name="Headphones", description="Noise-cancelling headphones", price=150.00, stock_quantity=200, category="Accessories"),
        models.Product(name="T-Shirt", description="Cotton T-shirt", price=20.00, stock_quantity=500, category="Clothing"),
        models.Product(name="Coffee Maker", description="Automatic coffee maker", price=100.00, stock_quantity=30, category="Home Appliances"),
    ]
    db_session.add_all(products)
    db_session.commit()

    # Get product IDs
    product_ids = [product.id for product in db_session.query(models.Product).all()]

    # Add sales
    sales = [
        models.Sale(product_id=product_ids[0], quantity_sold=10, sale_date=datetime.now(), total_revenue=12000.00),
        models.Sale(product_id=product_ids[1], quantity_sold=15, sale_date=datetime.now(), total_revenue=12000.00),
        models.Sale(product_id=product_ids[2], quantity_sold=50, sale_date=datetime.now(), total_revenue=7500.00),
        models.Sale(product_id=product_ids[3], quantity_sold=100, sale_date=datetime.now(), total_revenue=2000.00),
        models.Sale(product_id=product_ids[4], quantity_sold=5, sale_date=datetime.now(), total_revenue=500.00),
    ]
    db_session.add_all(sales)

    # Add inventory
    inventory = [
        models.Inventory(product_id=product_ids[0], quantity=40, last_updated=datetime.now()),
        models.Inventory(product_id=product_ids[1], quantity=85, last_updated=datetime.now()),
        models.Inventory(product_id=product_ids[2], quantity=150, last_updated=datetime.now()),
        models.Inventory(product_id=product_ids[3], quantity=400, last_updated=datetime.now()),
        models.Inventory(product_id=product_ids[4], quantity=25, last_updated=datetime.now()),
    ]
    db_session.add_all(inventory)
    db_session.commit()
    db_session.close()
    print("Demo data inserted.")
models.Base.metadata.create_all(bind=engine)
init_demo_data()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

#pydantic models for request and response bodies
class Product(BaseModel):
    id: int
    name: str
    description: str
    price: float
    stock_quantity: int

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock_quantity: int

class Sale(BaseModel):
    id: int
    product_id: int
    quantity_sold: int
    sale_date: datetime
    total_revenue: float

class RevenueAnalysis(BaseModel):
    period: str
    revenue: float

class RevenueComparison(BaseModel):
    period: str
    revenue: float
    category: str

class Inventory(BaseModel):
    id: int
    product_id: int
    quantity: int
    last_updated: datetime


# Sales Endpoints
@app.get("/sales/period", response_model=List[Sale])
def get_sales_by_period(start_date: datetime, end_date: datetime, db: Session = Depends(get_db)):
    sales = db.query(models.Sale).filter(models.Sale.sale_date >= start_date, models.Sale.sale_date <= end_date).all()
    if not sales:
        raise HTTPException(status_code=404, detail="No sales data for the given date range")
    return sales
@app.get("/sales/comparison", response_model=List[RevenueComparison])
def compare_revenue(start_date: datetime, end_date: datetime, category: str = None, db: Session = Depends(get_db)):
    sales_data = db.query(
        models.Product.category,
        func.sum(models.Sale.total_revenue).label("revenue")
    ).join(models.Product).filter(
        models.Sale.sale_date >= start_date,
        models.Sale.sale_date <= end_date
    )

    if category:
        sales_data = sales_data.filter(models.Product.category == category)

    sales_comparison = sales_data.group_by(models.Product.category).all()

    return [
        {
            "period": f"{start_date.date()} to {end_date.date()}",
            "category": cat,
            "revenue": revenue
        }
        for cat, revenue in sales_comparison
    ]

@app.get("/sales/{product_id}", response_model=List[Sale])
def get_sales_by_product(product_id: int, db: Session = Depends(get_db)):
    sales = db.query(models.Sale).filter(models.Sale.product_id == product_id).all()
    if not sales:
        raise HTTPException(status_code=404, detail="Sales data not found")
    return sales


@app.get("/sales/revenue/daily", response_model=List[RevenueAnalysis])
def get_daily_revenue(db: Session = Depends(get_db)):
    daily_revenue = db.query(func.date(models.Sale.sale_date), func.sum(models.Sale.total_revenue).label("revenue")) \
        .group_by(func.date(models.Sale.sale_date)).all()
    return [{"period": str(date), "revenue": revenue} for date, revenue in daily_revenue]

@app.get("/sales/revenue/weekly", response_model=List[RevenueAnalysis])
def get_weekly_revenue(db: Session = Depends(get_db)):
    weekly_revenue = db.query(func.week(models.Sale.sale_date), func.sum(models.Sale.total_revenue).label("revenue")) \
        .group_by(func.week(models.Sale.sale_date)).all()
    return [{"period": str(week), "revenue": revenue} for week, revenue in weekly_revenue]

@app.get("/sales/revenue/monthly", response_model=List[RevenueAnalysis])
def get_monthly_revenue(db: Session = Depends(get_db)):
    monthly_revenue = db.query(func.month(models.Sale.sale_date), func.sum(models.Sale.total_revenue).label("revenue")) \
        .group_by(func.month(models.Sale.sale_date)).all()
    return [{"period": str(month), "revenue": revenue} for month, revenue in monthly_revenue]

@app.get("/sales/revenue/annual", response_model=List[RevenueAnalysis])
def get_annual_revenue(db: Session = Depends(get_db)):
    annual_revenue = db.query(func.year(models.Sale.sale_date), func.sum(models.Sale.total_revenue).label("revenue")) \
        .group_by(func.year(models.Sale.sale_date)).all()
    return [{"period": str(year), "revenue": revenue} for year, revenue in annual_revenue]

# Inventory Management Endpoints
@app.get("/inventory/status", response_model=List[Inventory])
def get_inventory_status(db: Session = Depends(get_db)):
    inventory = db.query(models.Inventory).all()
    return inventory
@app.get("/inventory/low-stock", response_model=List[Inventory])
def get_low_stock_alerts(db: Session = Depends(get_db)):
    low_stock_inventory = db.query(models.Inventory).filter(models.Inventory.quantity < 10).all()  # Assuming 10 as low stock threshold
    return low_stock_inventory

@app.get("/inventory/{product_id}", response_model=Inventory)
def get_inventory_by_product(product_id: int, db: Session = Depends(get_db)):
    inventory = db.query(models.Inventory).filter(models.Inventory.product_id == product_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory



@app.post("/inventory/{product_id}/update", response_model=Inventory)
def update_inventory(product_id: int, quantity: int, db: Session = Depends(get_db)):
    inventory = db.query(models.Inventory).filter(models.Inventory.product_id == product_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Product not found")
    inventory.quantity = quantity
    db.commit()
    db.refresh(inventory)
    return inventory


# Product Endpoints

@app.get("/products", response_model=List[Product])
def get_all_products(db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return products

@app.post("/products", response_model=Product)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = models.Product(name=product.name, description=product.description, price=product.price, stock_quantity=product.stock_quantity)
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product