# api/production_main.py
"""
Production-ready FastAPI server with authentication, rate limiting, and monitoring
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
import pandas as pd
import time
import sys
import re
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
current_file = Path(__file__).resolve()
parent_dir = current_file.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.services import ValidationService
from core.models import (
    NameValidationRequest, NameValidationResponse, AddressRecord,
    AddressValidationResult, ServiceStatus
)
from utils.logger import logger
from utils.config import Config

# Initialize FastAPI app
app = FastAPI(
    title="Enhanced Name & Address Validation API",
    description="Professional validation service with authentication and rate limiting",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize validation service
validation_service = None

# =============================================================================
# AUTHENTICATION & RATE LIMITING
# =============================================================================

security = HTTPBearer()

# API Keys - In production, store these in a database or secure vault
API_KEYS = {
    "demo-key-12345": {
        "name": "Demo User",
        "tier": "demo",
        "requests_per_minute": 60,
        "max_addresses_per_request": 100,
        "features": ["name_validation", "address_validation"]
    },
    "premium-key-67890": {
        "name": "Premium User", 
        "tier": "premium",
        "requests_per_minute": 300,
        "max_addresses_per_request": 1000,
        "features": ["name_validation", "address_validation", "batch_processing"]
    },
    "enterprise-key-abc123": {
        "name": "Enterprise User",
        "tier": "enterprise", 
        "requests_per_minute": 1000,
        "max_addresses_per_request": 5000,
        "features": ["name_validation", "address_validation", "batch_processing", "priority_support"]
    }
}

# Rate limiting storage
request_counts = defaultdict(list)
usage_stats = defaultdict(lambda: {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "addresses_processed": 0,
    "names_processed": 0
})

class APIKeyAuth:
    """API Key authentication and rate limiting"""
    
    @staticmethod
    def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
        """Verify API key and check rate limits"""
        api_key = credentials.credentials
        
        if api_key not in API_KEYS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "Invalid API key",
                    "message": "Please provide a valid API key in the Authorization header",
                    "format": "Authorization: Bearer your-api-key-here"
                }
            )
        
        user_info = API_KEYS[api_key]
        
        # Check rate limiting
        now = time.time()
        user_requests = request_counts[api_key]
        
        # Remove requests older than 1 minute
        user_requests[:] = [req_time for req_time in user_requests if now - req_time < 60]
        
        # Check if under limit
        rate_limit = user_info["requests_per_minute"]
        if len(user_requests) >= rate_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {rate_limit} requests per minute for {user_info['tier']} tier",
                    "retry_after": 60,
                    "current_usage": len(user_requests),
                    "limit": rate_limit
                }
            )
        
        # Record this request
        user_requests.append(now)
        usage_stats[api_key]["total_requests"] += 1
        
        return {
            "api_key": api_key,
            "user_info": user_info,
            "current_usage": len(user_requests),
            "rate_limit": rate_limit
        }

# =============================================================================
# STARTUP AND HEALTH CHECKS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize validation service on startup"""
    global validation_service
    
    logger.info("Starting Production Name & Address Validation API", "API")
    
    try:
        validation_service = ValidationService()
        dict_status = "with dictionaries" if validation_service.dictionary_status else "AI-only mode"
        logger.info(f"Validation service initialized {dict_status}", "API")
        logger.info("Authentication and rate limiting enabled", "API")
    except Exception as e:
        logger.error(f"Failed to initialize validation service: {e}", "API")

@app.get("/health")
async def health_check():
    """Enhanced health check with authentication info"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "features": {
            "authentication": True,
            "rate_limiting": True,
            "name_validation": validation_service.is_name_validation_available() if validation_service else False,
            "address_validation": validation_service.is_address_validation_available() if validation_service else False,
            "dictionary_engine": validation_service.dictionary_status if validation_service else False
        },
        "api_tiers": {
            "demo": "60 req/min, 100 addresses/request",
            "premium": "300 req/min, 1000 addresses/request", 
            "enterprise": "1000 req/min, 5000 addresses/request"
        }
    }

@app.get("/api-info")
async def api_info(auth_data = Depends(APIKeyAuth.verify_api_key)):
    """Get API information for authenticated user"""
    user_info = auth_data["user_info"]
    api_key = auth_data["api_key"]
    stats = usage_stats[api_key]
    
    return {
        "user": user_info["name"],
        "tier": user_info["tier"],
        "rate_limit": f"{user_info['requests_per_minute']} requests/minute",
        "current_usage": f"{auth_data['current_usage']}/{auth_data['rate_limit']}",
        "max_batch_size": user_info["max_addresses_per_request"],
        "features": user_info["features"],
        "usage_statistics": {
            "total_requests": stats["total_requests"],
            "successful_requests": stats["successful_requests"],
            "failed_requests": stats["failed_requests"],
            "addresses_processed": stats["addresses_processed"],
            "names_processed": stats["names_processed"]
        }
    }

# =============================================================================
# NAME VALIDATION ENDPOINTS
# =============================================================================

@app.post("/api/validate-names", response_model=NameValidationResponse)
async def validate_names(
    request: NameValidationRequest,
    auth_data = Depends(APIKeyAuth.verify_api_key)
):
    """Enhanced name validation with authentication"""
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    user_info = auth_data["user_info"]
    api_key = auth_data["api_key"]
    
    # Check if name validation is allowed for this tier
    if "name_validation" not in user_info["features"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Feature not available",
                "message": f"Name validation not included in {user_info['tier']} tier"
            }
        )
    
    try:
        names_data = {"names": [name.dict() for name in request.names]}
        result = validation_service.validate_names(names_data)
        
        # Update usage statistics
        usage_stats[api_key]["names_processed"] += len(request.names)
        usage_stats[api_key]["successful_requests"] += 1
        
        # Log successful request
        logger.info(f"Name validation: {len(request.names)} names for {user_info['name']}", "API")
        
        response_data = {"names": result['names']}
        return NameValidationResponse(**response_data)
        
    except Exception as e:
        usage_stats[api_key]["failed_requests"] += 1
        logger.error(f"Name validation error: {e}", "API")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "Name validation failed",
                "message": str(e)
            }
        )

# =============================================================================
# ADDRESS VALIDATION ENDPOINTS
# =============================================================================

@app.post("/api/validate-address")
async def validate_single_address(
    address: AddressRecord,
    auth_data = Depends(APIKeyAuth.verify_api_key)
):
    """Enhanced single address validation with authentication"""
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    user_info = auth_data["user_info"]
    api_key = auth_data["api_key"]
    
    # Check if address validation is allowed for this tier
    if "address_validation" not in user_info["features"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Feature not available",
                "message": f"Address validation not included in {user_info['tier']} tier"
            }
        )
    
    try:
        # Use the enhanced categorization from the main API
        from api.main import AddressCategorizer, state_normalizer
        
        categorizer = AddressCategorizer()
        categorization = categorizer.categorize_address(address.dict())
        
        result = {
            "categorization": categorization,
            "usps_result": None,
            "processing_info": {
                "timestamp": datetime.now().isoformat(),
                "category": categorization['category'],
                "state_normalization_applied": categorization.get('state_normalization_applied', False),
                "validation_notes": categorization['validation_notes'],
                "user_tier": user_info['tier']
            }
        }
        
        # Process with USPS if US valid
        if categorization['category'] == 'us_valid' and validation_service.is_address_validation_available():
            try:
                usps_address = address.dict()
                usps_address['stateCd'] = categorization['normalized_state']
                
                usps_result = validation_service.validate_single_address(usps_address)
                result["usps_result"] = usps_result
                result["processing_info"]["usps_processed"] = True
                result["processing_info"]["usps_valid"] = usps_result.get('mailabilityScore') == '1'
                
            except Exception as e:
                result["processing_info"]["usps_error"] = str(e)
                result["processing_info"]["usps_processed"] = False
        
        # Update usage statistics
        usage_stats[api_key]["addresses_processed"] += 1
        usage_stats[api_key]["successful_requests"] += 1
        
        logger.info(f"Address validation: {categorization['category']} for {user_info['name']}", "API")
        
        return result
        
    except Exception as e:
        usage_stats[api_key]["failed_requests"] += 1
        logger.error(f"Address validation error: {e}", "API")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Address validation failed",
                "message": str(e)
            }
        )

# =============================================================================
# BATCH PROCESSING ENDPOINTS
# =============================================================================

@app.post("/api/batch-validate-addresses")
async def batch_validate_addresses(
    files: List[UploadFile] = File(...),
    auth_data = Depends(APIKeyAuth.verify_api_key)
):
    """Enhanced batch address validation with tier-based limits"""
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    user_info = auth_data["user_info"]
    api_key = auth_data["api_key"]
    
    # Check if batch processing is allowed for this tier
    if "batch_processing" not in user_info["features"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Feature not available",
                "message": f"Batch processing not included in {user_info['tier']} tier. Please upgrade to premium or enterprise."
            }
        )
    
    # Validate file count and size
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per request")
    
    total_records = 0
    
    # Pre-validate files and count records
    for file in files:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be CSV format")
        
        try:
            file.file.seek(0)
            df = pd.read_csv(file.file)
            total_records += len(df)
            file.file.seek(0)  # Reset for processing
        except Exception:
            raise HTTPException(status_code=400, detail=f"Cannot read CSV file: {file.filename}")
    
    # Check tier limits
    max_addresses = user_info["max_addresses_per_request"]
    if total_records > max_addresses:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Batch size limit exceeded",
                "message": f"Total records ({total_records}) exceeds {user_info['tier']} tier limit of {max_addresses}",
                "suggestion": "Split into smaller batches or upgrade your tier"
            }
        )
    
    try:
        # Use the enhanced batch processing from main API
        from api.main import address_categorizer
        
        start_time = time.time()
        
        # Process files with enhanced categorization
        all_us_valid = []
        all_international = []
        all_invalid = []
        usps_results = []
        
        file_summaries = []
        state_normalizations = 0
        
        logger.info(f"Processing {len(files)} CSV files with {total_records} addresses for {user_info['name']}", "API")
        
        for file_index, file in enumerate(files):
            try:
                df = pd.read_csv(file.file)
                
                if df.empty:
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "skipped",
                        "reason": "Empty file",
                        "records": 0
                    })
                    continue
                
                # Standardize CSV format
                standardized_addresses = validation_service.address_validator.standardize_csv_to_address_format(df)
                
                if not standardized_addresses:
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "failed",
                        "reason": "No address columns detected"
                    })
                    continue
                
                # Categorize addresses
                file_us_valid = []
                file_international = []
                file_invalid = []
                
                for i, addr in enumerate(standardized_addresses):
                    categorization = address_categorizer.categorize_address(addr, i + 1, file.filename)
                    
                    if categorization.get('state_normalization_applied', False):
                        state_normalizations += 1
                    
                    if categorization['category'] == 'us_valid':
                        file_us_valid.append(categorization)
                    elif categorization['category'] == 'international':
                        file_international.append(categorization)
                    else:
                        file_invalid.append(categorization)
                
                all_us_valid.extend(file_us_valid)
                all_international.extend(file_international)
                all_invalid.extend(file_invalid)
                
                file_summaries.append({
                    "filename": file.filename,
                    "status": "processed",
                    "total_records": len(standardized_addresses),
                    "us_valid": len(file_us_valid),
                    "international": len(file_international),
                    "invalid": len(file_invalid)
                })
                
            except Exception as file_error:
                file_summaries.append({
                    "filename": file.filename,
                    "status": "error",
                    "reason": str(file_error)
                })
        
        # Process US valid addresses with USPS
        usps_processed = 0
        usps_successful = 0
        
        if all_us_valid and validation_service.is_address_validation_available():
            for us_addr in all_us_valid:
                try:
                    usps_address = {
                        'guid': f"{us_addr['source_file']}_{us_addr['row_number']}",
                        'line1': us_addr['line1'],
                        'line2': us_addr['line2'] or None,
                        'city': us_addr['city'],
                        'stateCd': us_addr['normalized_state'],
                        'zipCd': us_addr['zip'],
                        'countryCd': 'US'
                    }
                    
                    usps_result = validation_service.validate_single_address(usps_address)
                    
                    enhanced_result = {
                        'source_file': us_addr['source_file'],
                        'row_number': us_addr['row_number'],
                        'category': 'us_usps_validated',
                        'input_address': us_addr['complete_address'],
                        'normalized_state': us_addr['normalized_state'],
                        'state_normalization_applied': us_addr.get('state_normalization_applied', False),
                        'usps_valid': usps_result.get('mailabilityScore') == '1',
                        'standardized_address': f"{usps_result.get('deliveryAddressLine1', '')} | {usps_result.get('city', '')}, {usps_result.get('stateCd', '')} {usps_result.get('zipCdComplete', '')}",
                        'county': usps_result.get('countyName', ''),
                        'is_residential': usps_result.get('residentialDeliveryIndicator') == 'Y',
                        'full_usps_result': usps_result
                    }
                    
                    usps_results.append(enhanced_result)
                    usps_processed += 1
                    
                    if enhanced_result['usps_valid']:
                        usps_successful += 1
                        
                except Exception:
                    # Skip failed individual validations in batch mode
                    pass
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Update usage statistics
        usage_stats[api_key]["addresses_processed"] += total_records
        usage_stats[api_key]["successful_requests"] += 1
        
        logger.info(f"Batch processing completed: {total_records} addresses in {processing_time}ms for {user_info['name']}", "API")
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "user_info": {
                "name": user_info["name"],
                "tier": user_info["tier"],
                "addresses_processed": total_records
            },
            "processing_summary": {
                "total_files": len(files),
                "total_records": total_records,
                "processing_time_ms": processing_time,
                "categorization_results": {
                    "us_valid_count": len(all_us_valid),
                    "international_count": len(all_international),
                    "invalid_count": len(all_invalid),
                    "us_valid_percentage": len(all_us_valid) / total_records if total_records > 0 else 0
                },
                "usps_processing": {
                    "total_processed": usps_processed,
                    "successful_validations": usps_successful,
                    "success_rate": usps_successful / usps_processed if usps_processed > 0 else 0
                },
                "state_normalization": {
                    "total_normalized": state_normalizations,
                    "normalization_applied": state_normalizations > 0
                }
            },
            "file_summaries": file_summaries,
            "categorized_results": {
                "us_valid_addresses": all_us_valid,
                "international_addresses": all_international,
                "invalid_addresses": all_invalid,
                "usps_validated_addresses": usps_results
            }
        }
        
    except Exception as e:
        usage_stats[api_key]["failed_requests"] += 1
        logger.error(f"Batch processing error: {e}", "API")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Batch processing failed",
                "message": str(e)
            }
        )

# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.get("/api/usage-stats")
async def get_usage_stats(auth_data = Depends(APIKeyAuth.verify_api_key)):
    """Get detailed usage statistics for authenticated user"""
    api_key = auth_data["api_key"]
    user_info = auth_data["user_info"]
    stats = usage_stats[api_key]
    
    return {
        "user": user_info["name"],
        "tier": user_info["tier"],
        "current_period": {
            "requests_this_minute": auth_data["current_usage"],
            "rate_limit": auth_data["rate_limit"],
            "percentage_used": (auth_data["current_usage"] / auth_data["rate_limit"]) * 100
        },
        "lifetime_statistics": stats,
        "tier_limits": {
            "requests_per_minute": user_info["requests_per_minute"],
            "max_addresses_per_request": user_info["max_addresses_per_request"],
            "features": user_info["features"]
        }
    }

@app.get("/api/examples")
async def get_api_examples():
    """Get API usage examples (no authentication required)"""
    return {
        "authentication": {
            "description": "All API endpoints require authentication",
            "header_format": "Authorization: Bearer your-api-key-here",
            "example": "Authorization: Bearer demo-key-12345"
        },
        "single_address_validation": {
            "endpoint": "POST /api/validate-address",
            "example_request": {
                "guid": "1",
                "line1": "1600 Pennsylvania Avenue NW",
                "city": "Washington",
                "stateCd": "DC",
                "zipCd": "20500",
                "countryCd": "US"
            }
        },
        "name_validation": {
            "endpoint": "POST /api/validate-names",
            "example_request": {
                "names": [
                    {
                        "uniqueID": "1",
                        "fullName": "Dr. William Smith Jr.",
                        "genderCd": "",
                        "partyTypeCd": "I",
                        "parseInd": "Y"
                    }
                ]
            }
        },
        "batch_processing": {
            "endpoint": "POST /api/batch-validate-addresses",
            "description": "Upload CSV files for batch processing",
            "note": "Available for premium and enterprise tiers only"
        }
    }

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "message": "The requested endpoint does not exist",
            "available_endpoints": [
                "GET /health",
                "GET /docs",
                "GET /api-info",
                "POST /api/validate-address",
                "POST /api/validate-names",
                "POST /api/batch-validate-addresses"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "support": "Please contact support if this persists"
        }
    )

# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Production API starting on port {port}")
    print(f"📚 Documentation: http://localhost:{port}/docs")
    print(f"🔐 Authentication: Required for all endpoints")
    print(f"⚡ Rate limiting: Enabled based on API tier")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)