"""
Product Info API - SKU ile ürün bilgisi ve fotoğraflar
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from database.connection import get_db
from database.models import Product

router = APIRouter(prefix="/products", tags=["products"])


class ProductImageResponse(BaseModel):
    """Ürün bilgisi response"""
    sku: str
    name: Optional[str]
    brand: Optional[str]
    barcode: Optional[str]
    image: Optional[str]  # Primary image (backward compatibility)
    images: List[str]  # All images
    purchase_price_with_vat: float
    
    class Config:
        from_attributes = True


@router.get("/{sku}", response_model=ProductImageResponse)
async def get_product_by_sku(
    sku: str,
    db: Session = Depends(get_db)
):
    """
    SKU ile ürün bilgisini ve fotoğraflarını getir
    
    **Kullanım:**
    - Satış verilerinde ürün fotoğraflarını göstermek için
    - SKU ile eşleşen ürünün tüm resimlerini almak için
    
    **Response:**
    - `image`: İlk resim (backward compatibility)
    - `images`: Tüm resimler (array)
    """
    product = db.query(Product).filter(Product.sku == sku).first()
    
    if not product:
        raise HTTPException(status_code=404, detail=f"Product not found: {sku}")
    
    return ProductImageResponse(
        sku=product.sku,
        name=product.name,
        brand=product.brand,
        barcode=product.barcode,
        image=product.get_primary_image(),
        images=product.get_images(),
        purchase_price_with_vat=product.purchase_price_with_vat
    )


@router.post("/batch", response_model=List[ProductImageResponse])
async def get_products_batch(
    skus: List[str],
    db: Session = Depends(get_db)
):
    """
    Birden fazla SKU için ürün bilgilerini toplu olarak getir
    
    **Body:**
    ```json
    ["SKU1", "SKU2", "SKU3"]
    ```
    
    **Use Case:**
    - Satış listesindeki tüm ürünlerin fotoğraflarını tek seferde almak
    - N+1 query problemini önlemek
    """
    products = db.query(Product).filter(Product.sku.in_(skus)).all()
    
    # SKU mapping
    product_map = {p.sku: p for p in products}
    
    # Sıraya göre döndür (bulunamayanlar için None)
    results = []
    for sku in skus:
        if sku in product_map:
            p = product_map[sku]
            results.append(ProductImageResponse(
                sku=p.sku,
                name=p.name,
                brand=p.brand,
                barcode=p.barcode,
                image=p.get_primary_image(),
                images=p.get_images(),
                purchase_price_with_vat=p.purchase_price_with_vat
            ))
    
    return results
