"""
Tax calculation and management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from decimal import Decimal
import logging

from src.db.base import get_db
from src.db.models import Customer, Currency
from src.models.schemas import (
    TaxCalculationRequest, TaxCalculationResponse,
    TaxRateResponse, TaxSettingsUpdate
)
from src.core.auth import get_current_user, require_admin
from src.services.tax_service import TaxService
from src.services.cache_service import CacheService

router = APIRouter()
logger = logging.getLogger(__name__)
tax_service = TaxService()
cache_service = CacheService()


@router.post("/calculate", response_model=TaxCalculationResponse)
async def calculate_tax(
    calculation_request: TaxCalculationRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Calculate tax for a transaction"""
    # Get customer
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Use customer's billing address if not provided
    if not calculation_request.billing_address:
        if not customer.billing_country:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billing address required for tax calculation"
            )
        
        billing_address = {
            "line1": customer.billing_address_line1,
            "line2": customer.billing_address_line2,
            "city": customer.billing_city,
            "state": customer.billing_state,
            "country": customer.billing_country,
            "postal_code": customer.billing_postal_code
        }
    else:
        billing_address = calculation_request.billing_address
    
    # Calculate tax
    try:
        tax_result = await tax_service.calculate_tax(
            amount=calculation_request.amount,
            currency=calculation_request.currency or customer.currency or Currency.USD,
            billing_address=billing_address,
            tax_code=calculation_request.tax_code,
            customer_tax_exempt=customer.tax_exempt,
            customer_tax_ids=customer.tax_ids
        )
        
        return TaxCalculationResponse(
            subtotal=calculation_request.amount,
            tax_amount=tax_result["tax_amount"],
            total=calculation_request.amount + tax_result["tax_amount"],
            tax_rate=tax_result["tax_rate"],
            tax_breakdown=tax_result["breakdown"],
            currency=calculation_request.currency or customer.currency or Currency.USD
        )
        
    except Exception as e:
        logger.error(f"Tax calculation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tax calculation failed"
        )


@router.get("/rates", response_model=List[TaxRateResponse])
async def get_tax_rates(
    country: Optional[str] = None,
    state: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get applicable tax rates"""
    # Check cache
    cache_key = f"tax:rates:{country}:{state}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    
    try:
        # Get tax rates from service
        rates = await tax_service.get_tax_rates(
            country=country,
            state=state
        )
        
        # Convert to response format
        tax_rates = [
            TaxRateResponse(
                id=rate["id"],
                country=rate["country"],
                state=rate.get("state"),
                rate=rate["rate"],
                name=rate["name"],
                inclusive=rate.get("inclusive", False),
                active=rate.get("active", True)
            )
            for rate in rates
        ]
        
        # Cache for 1 hour
        await cache_service.set(cache_key, tax_rates, expire=3600)
        
        return tax_rates
        
    except Exception as e:
        logger.error(f"Failed to get tax rates: {e}")
        return []


@router.post("/validate-tax-id")
async def validate_tax_id(
    tax_id: str,
    country: str,
    current_user=Depends(get_current_user)
):
    """Validate a tax ID (VAT number, etc.)"""
    try:
        is_valid = await tax_service.validate_tax_id(
            tax_id=tax_id,
            country=country
        )
        
        return {
            "valid": is_valid,
            "tax_id": tax_id,
            "country": country
        }
        
    except Exception as e:
        logger.error(f"Tax ID validation failed: {e}")
        return {
            "valid": False,
            "tax_id": tax_id,
            "country": country,
            "error": str(e)
        }


@router.get("/exemptions")
async def get_tax_exemptions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get customer's tax exemptions"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        return {
            "tax_exempt": False,
            "tax_ids": [],
            "exemption_certificates": []
        }
    
    return {
        "tax_exempt": customer.tax_exempt,
        "tax_ids": customer.tax_ids,
        "exemption_certificates": customer.metadata.get("tax_exemption_certificates", [])
    }


@router.post("/exemptions")
async def add_tax_exemption(
    tax_id: str,
    tax_id_type: str,
    country: str,
    certificate_url: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Add a tax exemption"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Validate tax ID
    is_valid = await tax_service.validate_tax_id(tax_id, country)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tax ID"
        )
    
    # Add tax ID
    if not customer.tax_ids:
        customer.tax_ids = []
    
    tax_id_entry = {
        "id": tax_id,
        "type": tax_id_type,
        "country": country,
        "validated": True,
        "added_at": datetime.utcnow().isoformat()
    }
    
    customer.tax_ids.append(tax_id_entry)
    
    # Add certificate if provided
    if certificate_url:
        if "tax_exemption_certificates" not in customer.metadata:
            customer.metadata["tax_exemption_certificates"] = []
        
        customer.metadata["tax_exemption_certificates"].append({
            "url": certificate_url,
            "tax_id": tax_id,
            "uploaded_at": datetime.utcnow().isoformat()
        })
    
    # Update tax exempt status
    customer.tax_exempt = True
    
    await db.commit()
    
    logger.info(f"Tax exemption added for customer {customer.id}")
    
    return {
        "message": "Tax exemption added successfully",
        "tax_id": tax_id
    }


@router.delete("/exemptions/{tax_id}")
async def remove_tax_exemption(
    tax_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Remove a tax exemption"""
    customer = await db.execute(
        select(Customer).where(Customer.organization_id == current_user.organization_id)
    )
    customer = customer.scalar()
    
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )
    
    # Remove tax ID
    if customer.tax_ids:
        customer.tax_ids = [
            tid for tid in customer.tax_ids
            if tid.get("id") != tax_id
        ]
    
    # Remove associated certificates
    if "tax_exemption_certificates" in customer.metadata:
        customer.metadata["tax_exemption_certificates"] = [
            cert for cert in customer.metadata["tax_exemption_certificates"]
            if cert.get("tax_id") != tax_id
        ]
    
    # Update tax exempt status if no more exemptions
    if not customer.tax_ids:
        customer.tax_exempt = False
    
    await db.commit()
    
    return {"message": "Tax exemption removed"}


@router.get("/settings")
async def get_tax_settings(
    current_user=Depends(require_admin)
):
    """Get global tax settings (admin only)"""
    settings = await tax_service.get_settings()
    
    return {
        "tax_calculation_enabled": settings.get("enabled", True),
        "tax_inclusive_pricing": settings.get("inclusive_pricing", False),
        "default_tax_code": settings.get("default_tax_code", "P0000000"),
        "nexus_addresses": settings.get("nexus_addresses", []),
        "provider": settings.get("provider", "internal")
    }


@router.put("/settings")
async def update_tax_settings(
    settings_update: TaxSettingsUpdate,
    current_user=Depends(require_admin)
):
    """Update global tax settings (admin only)"""
    try:
        await tax_service.update_settings(
            enabled=settings_update.tax_calculation_enabled,
            inclusive_pricing=settings_update.tax_inclusive_pricing,
            default_tax_code=settings_update.default_tax_code,
            nexus_addresses=settings_update.nexus_addresses
        )
        
        # Clear tax rate cache
        await cache_service.delete_pattern("tax:*")
        
        return {"message": "Tax settings updated successfully"}
        
    except Exception as e:
        logger.error(f"Failed to update tax settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tax settings"
        )


@router.get("/report")
async def get_tax_report(
    start_date: date,
    end_date: date,
    country: Optional[str] = None,
    current_user=Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Generate tax report for a period (admin only)"""
    try:
        report = await tax_service.generate_tax_report(
            start_date=start_date,
            end_date=end_date,
            country=country
        )
        
        return {
            "period": {
                "start": start_date,
                "end": end_date
            },
            "total_sales": report["total_sales"],
            "total_tax_collected": report["total_tax"],
            "by_jurisdiction": report["by_jurisdiction"],
            "by_tax_code": report["by_tax_code"],
            "exempt_sales": report["exempt_sales"]
        }
        
    except Exception as e:
        logger.error(f"Failed to generate tax report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tax report"
        )


from datetime import datetime, date
from sqlalchemy import select