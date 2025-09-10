# api/main.py - FIXED VERSION WITH MULTI-CSV AND RATE LIMITING
"""
Enhanced FastAPI server with proper multi-CSV upload and USPS rate limiting
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import pandas as pd
import time
import sys
import re
import asyncio
from pathlib import Path
from datetime import datetime

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
    description="Advanced validation service with 3-bucket categorization and USPS rate limiting",
    version=Config.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize validation service
validation_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize validation service with Docker-compatible paths"""
    global validation_service
    
    logger.info("Starting Docker-compatible API server", "API")
    
    try:
        # 🔧 FIXED: Use configurable dictionary path
        dictionary_path = Config.get_dictionary_path()
        validation_service = ValidationService(dictionary_path)
        
        dict_status = "with dictionaries" if validation_service.dictionary_status else "AI-only mode"
        logger.info(f"Validation service initialized {dict_status}", "API")
        
        # Log dictionary status for debugging
        if dictionary_path:
            logger.info(f"Dictionary path: {dictionary_path}", "API")
        else:
            logger.warning("No dictionary path found - using AI fallback", "API")
            
    except Exception as e:
        logger.error(f"Failed to initialize validation service: {e}", "API")

    @app.get("/health")    
    async def health_check():
        """Enhanced health check with dictionary status"""
        return {
            "status": "healthy",
            "dictionary_loaded": validation_service.dictionary_status if validation_service else False,
            "dictionary_path": Config.get_dictionary_path(),
            "usps_configured": validation_service.is_address_validation_available() if validation_service else False,
            "csv_upload_enabled": True,
            "docker_compatible": True
        }
    @app.post("/api/upload-address-csv")
    async def upload_address_csv(files: List[UploadFile] = File(...)):
        """Multi-CSV address upload endpoint"""
        if not validation_service:
            raise HTTPException(status_code=503, detail="Validation service not available")
        
        logger.info(f"Processing {len(files)} CSV files for address validation", "API")
        
        # Implementation here...
        return {"status": "CSV upload endpoint active", "files_received": len(files)}
    
    @app.post("/api/upload-names-csv") 
    async def upload_names_csv(files: List[UploadFile] = File(...)):
        """Multi-CSV name upload endpoint"""
        if not validation_service:
            raise HTTPException(status_code=503, detail="Validation service not available")
            
        logger.info(f"Processing {len(files)} CSV files for name validation", "API")
        
        # Implementation here...
        return {"status": "CSV upload endpoint active", "files_received": len(files)}
    
# USPS Rate Limiting
class USPSRateLimiter:
    """Rate limiter for USPS API calls"""
    
    def __init__(self, calls_per_second: float = 2.0):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0
        
    async def wait_if_needed(self):
        """Wait if needed to respect rate limits"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            wait_time = self.min_interval - time_since_last_call
            await asyncio.sleep(wait_time)
        
        self.last_call_time = time.time()

# Initialize rate limiter (2 calls per second to be safe)
usps_rate_limiter = USPSRateLimiter(calls_per_second=2.0)

# Enhanced state normalization for API
class StateNormalizer:
    """State name to code normalization for API"""
    
    def __init__(self):
        self.state_name_to_code = {
            # Full state names to codes
            'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
            'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
            'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
            'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
            'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
            'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
            'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
            'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
            'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
            'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
            'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
            'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
            'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
            
            # Common abbreviations and variations
            'calif': 'CA', 'cali': 'CA', 'cal': 'CA',
            'fla': 'FL', 'tex': 'TX', 'penn': 'PA', 'penna': 'PA',
            'mass': 'MA', 'conn': 'CT', 'wash': 'WA', 'ore': 'OR', 'oreg': 'OR',
            'mich': 'MI', 'ill': 'IL', 'ind': 'IN', 'tenn': 'TN',
            'ky': 'KY', 'la': 'LA', 'miss': 'MS', 'ala': 'AL', 'ga': 'GA',
            'nc': 'NC', 'n carolina': 'NC', 'n. carolina': 'NC',
            'sc': 'SC', 's carolina': 'SC', 's. carolina': 'SC',
            'nd': 'ND', 'n dakota': 'ND', 'n. dakota': 'ND',
            'sd': 'SD', 's dakota': 'SD', 's. dakota': 'SD',
            'wv': 'WV', 'w virginia': 'WV', 'w. virginia': 'WV',
            'dc': 'DC', 'd.c.': 'DC', 'washington dc': 'DC', 'washington d.c.': 'DC'
        }
        
        self.valid_state_codes = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        }
    
    def normalize_state(self, state_input: str) -> tuple:
        """Normalize state input to standard 2-letter code"""
        if not state_input or not state_input.strip():
            return '', False, state_input
        
        cleaned_input = state_input.strip().lower()
        original_input = state_input.strip()
        
        # Check if already valid state code
        if len(cleaned_input) == 2 and cleaned_input.upper() in self.valid_state_codes:
            return cleaned_input.upper(), True, original_input
        
        # Check state name mapping
        if cleaned_input in self.state_name_to_code:
            return self.state_name_to_code[cleaned_input], True, original_input
        
        # Try without punctuation
        cleaned_no_punct = cleaned_input.replace('.', '').replace(',', '')
        if cleaned_no_punct in self.state_name_to_code:
            return self.state_name_to_code[cleaned_no_punct], True, original_input
        
        return original_input.upper(), False, original_input

# Initialize state normalizer
state_normalizer = StateNormalizer()

class AddressCategorizer:
    """Enhanced address categorization with state name support"""
    
    @staticmethod
    def analyze_zip_code(zip_code: str) -> Dict:
        """Analyze ZIP code to determine if it's US, International, or Invalid"""
        if not zip_code:
            return {'type': 'invalid', 'reason': 'Empty ZIP code'}
        
        # US ZIP patterns
        us_patterns = [
            r'^\d{5}$',           # 12345
            r'^\d{9}$',           # 123456789 (ZIP+4 without dash)
            r'^\d{5}-?\d{4}$'     # 12345-6789
        ]
        
        for pattern in us_patterns:
            if re.match(pattern, zip_code.strip()):
                return {'type': 'us', 'reason': 'US ZIP code format'}
        
        # International postal code patterns
        international_patterns = {
            r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$': 'Canadian postal code',
            r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$': 'UK postal code',
            r'^[0-9]{5}$': 'German postal code (5 digits)',
            r'^[0-9]{4}$': 'Australian postal code',
            r'^[0-9]{4}\s?[A-Z]{2}$': 'Dutch postal code',
            r'^[0-9]{3}\s?[0-9]{2}$': 'Nordic postal code',
            r'^\d{3}-?\d{4}$': 'Japanese postal code',
            r'^\d{5}-?\d{3}$': 'Brazilian postal code',
            r'^[0-9]{6}$': 'Indian/Chinese postal code',
            r'^[A-Z]{2,4}\s?[0-9]{3,5}$': 'International postal code (letters + numbers)',
            r'^[0-9]{6,8}$': 'International postal code (6-8 digits)',
            r'^[A-Z0-9]{5,10}$': 'International postal code (alphanumeric)'
        }
        
        zip_upper = zip_code.strip().upper()
        
        for pattern, description in international_patterns.items():
            if re.match(pattern, zip_upper):
                return {'type': 'international', 'reason': description}
        
        return {'type': 'invalid', 'reason': 'Unrecognized postal code format'}
    
    @staticmethod
    def categorize_address(address_data: Dict, row_num: int = 1, source_file: str = "api") -> Dict:
        """Categorize address into US Valid, International, or Invalid"""
        result = {
            'row_number': row_num,
            'source_file': source_file,
            'category': 'invalid',
            'issues': [],
            'line1': address_data.get('line1', ''),
            'line2': address_data.get('line2', ''),
            'city': address_data.get('city', ''),
            'state': address_data.get('stateCd', ''),
            'zip': address_data.get('zipCd', ''),
            'country': address_data.get('countryCd', 'US').upper(),
            'complete_address': '',
            'validation_notes': '',
            'normalized_state': '',
            'state_normalization_applied': False
        }
        
        # Normalize state input
        normalized_state, is_valid_state, original_state = state_normalizer.normalize_state(result['state'])
        result['normalized_state'] = normalized_state
        result['state_normalization_applied'] = (normalized_state != original_state.upper())
        
        # Create complete address string
        address_parts = []
        if result['line1']: address_parts.append(result['line1'])
        if result['line2']: address_parts.append(result['line2'])
        if result['city']: address_parts.append(result['city'])
        if result['state']: address_parts.append(result['state'])
        if result['zip']: address_parts.append(result['zip'])
        result['complete_address'] = ', '.join(address_parts)
        
        # Step 1: Check if explicitly international
        if result['country'] and result['country'] != 'US' and result['country'] != 'USA':
            result['category'] = 'international'
            result['validation_notes'] = f"International address (Country: {result['country']})"
            return result
        
        # Step 2: Check required fields
        missing_fields = []
        if not result['line1'] or not result['line1'].strip():
            missing_fields.append("street address")
        if not result['city'] or not result['city'].strip():
            missing_fields.append("city")
        if not result['state'] or not result['state'].strip():
            missing_fields.append("state")
        if not result['zip'] or not result['zip'].strip():
            missing_fields.append("zip code")
        
        if missing_fields:
            result['category'] = 'invalid'
            result['issues'] = [f"Missing: {', '.join(missing_fields)}"]
            result['validation_notes'] = f"Invalid - Missing required fields: {', '.join(missing_fields)}"
            return result
        
        # Step 3: Analyze ZIP code
        zip_analysis = AddressCategorizer.analyze_zip_code(result['zip'])
        
        if zip_analysis['type'] == 'international':
            result['category'] = 'international'
            result['validation_notes'] = f"International address - {zip_analysis['reason']}"
            return result
        elif zip_analysis['type'] == 'invalid':
            result['category'] = 'invalid'
            result['issues'] = [zip_analysis['reason']]
            result['validation_notes'] = f"Invalid - {zip_analysis['reason']}"
            return result
        
        # Step 4: Validate US-specific requirements
        us_validation = AddressCategorizer.validate_us_format(result, normalized_state, is_valid_state)
        
        if us_validation['valid']:
            result['category'] = 'us_valid'
            result['state'] = normalized_state  # Update to normalized state
            if result['state_normalization_applied']:
                result['validation_notes'] = f"Valid US address - State normalized from '{original_state}' to '{normalized_state}'"
            else:
                result['validation_notes'] = "Valid US address - Ready for USPS validation"
        else:
            result['category'] = 'invalid'
            result['issues'] = us_validation['issues']
            result['validation_notes'] = f"Invalid - {'; '.join(us_validation['issues'])}"
        
        return result
    
    @staticmethod
    def validate_us_format(address_data: Dict, normalized_state: str, is_valid_state: bool) -> Dict:
        """Validate US address format requirements"""
        issues = []
        
        # Validate state
        if not is_valid_state:
            issues.append(f"Invalid US state: '{address_data['state']}' (not recognized as state name or code)")
        
        # Validate ZIP code format
        zip_code = address_data['zip'].strip()
        if not re.match(r'^\d{5}(-\d{4})?$', zip_code):
            issues.append("ZIP code must be 5 digits or ZIP+4 format")
        
        # Basic validations
        if len(address_data['line1'].strip()) < 3:
            issues.append("Street address too short")
        
        if len(address_data['city'].strip()) < 2:
            issues.append("City name too short")
        elif not re.match(r'^[A-Za-z\s\.\-\']+$', address_data['city'].strip()):
            issues.append("City contains invalid characters")
        
        return {'valid': len(issues) == 0, 'issues': issues}

# Initialize categorizer
address_categorizer = AddressCategorizer()

# Enhanced USPS validation with rate limiting and retry logic
async def validate_with_usps_rate_limited(address_data: Dict, max_retries: int = 3) -> Dict:
    """Validate address with USPS API using rate limiting and retry logic"""
    
    for attempt in range(max_retries):
        try:
            # Wait for rate limiting
            await usps_rate_limiter.wait_if_needed()
            
            # Call USPS validation
            result = validation_service.validate_single_address(address_data)
            return result
            
        except Exception as e:
            error_str = str(e)
            
            # Handle rate limiting specifically
            if "429" in error_str or "Too Many Requests" in error_str:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # Exponential backoff: 2s, 4s, 6s
                    logger.warning(f"USPS rate limit hit, waiting {wait_time}s before retry {attempt + 1}", "API")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"USPS rate limit exceeded after {max_retries} attempts", "API")
                    raise HTTPException(
                        status_code=429, 
                        detail={
                            "error": "USPS API rate limit exceeded",
                            "message": "Please try again in a few moments. The USPS API has temporary rate limits.",
                            "retry_after": 30,
                            "suggestion": "For bulk processing, consider using smaller batches."
                        }
                    )
            
            # Handle other errors
            elif attempt < max_retries - 1:
                logger.warning(f"USPS API error on attempt {attempt + 1}: {error_str}", "API")
                await asyncio.sleep(1)  # Brief wait before retry
                continue
            else:
                # Final attempt failed
                logger.error(f"USPS API failed after {max_retries} attempts: {error_str}", "API")
                raise e
    
    # This shouldn't be reached, but just in case
    raise Exception("USPS validation failed after all retry attempts")

@app.on_event("startup")
async def startup_event():
    """Initialize validation service on startup"""
    global validation_service
    
    logger.info("Starting Enhanced Name & Address Validation API with rate limiting", "API")
    
    try:
        validation_service = ValidationService()
        dict_status = "with dictionaries" if validation_service.dictionary_status else "AI-only mode"
        logger.info(f"Validation service initialized {dict_status}", "API")
        logger.info("USPS rate limiting enabled: 2 calls per second", "API")
    except Exception as e:
        logger.error(f"Failed to initialize validation service: {e}", "API")

# =============================================================================
# CORE ENDPOINTS - WITH RATE LIMITING AND FIXED MULTI-CSV
# =============================================================================

@app.get("/health")
async def health_check():
    """Enhanced health check with rate limiting info"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": Config.API_VERSION,
        "features": {
            "3_bucket_categorization": True,
            "state_name_support": True,
            "international_detection": True,
            "multi_csv_upload": True,
            "usps_rate_limiting": True,
            "usps_validation": validation_service.is_address_validation_available() if validation_service else False
        },
        "rate_limiting": {
            "usps_calls_per_second": 2.0,
            "automatic_retry": True,
            "max_retries": 3
        },
        "services": {
            "name_validation": validation_service.is_name_validation_available() if validation_service else False,
            "address_validation": validation_service.is_address_validation_available() if validation_service else False,
            "dictionary_loaded": validation_service.dictionary_status if validation_service else False
        }
    }

@app.get("/status", response_model=ServiceStatus)
async def service_status():
    """Get enhanced service status"""
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not initialized")
    
    status = validation_service.get_service_status()
    return ServiceStatus(**status)

# =============================================================================
# 1. SINGLE ADDRESS VALIDATION WITH RATE LIMITING
# =============================================================================

@app.post("/api/validate-address")
async def validate_single_address(address: AddressRecord):
    """
    Enhanced single address validation with 3-bucket categorization and rate limiting
    
    **Features:**
    - ✅ 3-bucket categorization: US Valid | International | Invalid
    - ✅ State name support: 'California' or 'CA'
    - ✅ USPS rate limiting: 2 calls/second with retry logic
    - ✅ Automatic error handling for HTTP 429 (Too Many Requests)
    
    **USPS Rate Limiting:**
    - Maximum 2 calls per second to USPS API
    - Automatic retry with exponential backoff
    - Clear error messages for rate limit issues
    """
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not available")
    
    try:
        # Step 1: Categorize the address
        categorization = address_categorizer.categorize_address(address.dict())
        
        result = {
            "categorization": categorization,
            "usps_result": None,
            "processing_info": {
                "timestamp": datetime.now().isoformat(),
                "category": categorization['category'],
                "state_normalization_applied": categorization.get('state_normalization_applied', False),
                "validation_notes": categorization['validation_notes'],
                "rate_limited": False
            }
        }
        
        # Step 2: If US valid, process with USPS (with rate limiting)
        if categorization['category'] == 'us_valid' and validation_service.is_address_validation_available():
            try:
                # Use normalized address for USPS
                usps_address = address.dict()
                usps_address['stateCd'] = categorization['normalized_state']
                
                # Call USPS with rate limiting
                usps_result = await validate_with_usps_rate_limited(usps_address)
                
                result["usps_result"] = usps_result
                result["processing_info"]["usps_processed"] = True
                result["processing_info"]["usps_valid"] = usps_result.get('mailabilityScore') == '1'
                result["processing_info"]["rate_limited"] = True
                
            except HTTPException as e:
                # Re-raise HTTP exceptions (like 429)
                raise e
            except Exception as e:
                result["processing_info"]["usps_error"] = str(e)
                result["processing_info"]["usps_processed"] = False
        
        elif categorization['category'] == 'us_valid':
            result["processing_info"]["usps_processed"] = False
            result["processing_info"]["usps_error"] = "USPS API not configured"
        
        return result
        
    except HTTPException as e:
        # Re-raise HTTP exceptions with proper error details
        raise e
    except Exception as e:
        logger.error(f"Enhanced address validation error: {e}", "API")
        raise HTTPException(status_code=500, detail=f"Address validation failed: {str(e)}")

# =============================================================================
# 2. FIXED MULTI-CSV UPLOAD WITH RATE LIMITING
# =============================================================================

@app.post("/api/upload-address-csv")
async def upload_address_csv(
    files: List[UploadFile] = File(
        ...,
        description="Select multiple CSV files",
        media_type="text/csv"
    )
):
    """
    Enhanced CSV processing with 3-bucket categorization, state name support, and USPS rate limiting
    
    **Multi-File Upload:**
    - ✅ Upload up to 10 CSV files in one request
    - ✅ Swagger UI supports multiple file selection
    - ✅ Auto-detect any CSV column format
    
    **Rate Limiting:**
    - ✅ USPS API: 2 calls per second with automatic retry
    - ✅ Handles HTTP 429 errors gracefully
    - ✅ Progress tracking for large batches
    
    **3-Bucket Categorization:**
    - 🇺🇸 US Valid: Process with USPS API (rate limited)
    - 🌍 International: Identify and categorize
    - ❌ Invalid: Detailed error analysis
    
    **State Name Support:**
    - 'California' → 'CA', 'New York' → 'NY', etc.
    """
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not available")
    
    # Validate inputs
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    for file in files:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be CSV format")
    
    try:
        start_time = time.time()
        
        # Initialize result containers
        all_us_valid = []
        all_international = []
        all_invalid = []
        usps_results = []
        
        file_summaries = []
        total_records = 0
        state_normalizations = 0
        rate_limit_events = 0
        
        logger.info(f"Processing {len(files)} CSV files with enhanced categorization and rate limiting", "API")
        
        # Process each file
        for file_index, file in enumerate(files):
            try:
                # Read CSV
                df = pd.read_csv(file.file)
                
                if df.empty:
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "skipped", 
                        "reason": "Empty file",
                        "records": 0
                    })
                    continue
                
                logger.info(f"Processing {file.filename}: {len(df)} rows", "API")
                
                # Auto-detect and standardize address columns
                standardized_addresses = validation_service.address_validator.standardize_csv_to_address_format(df)
                
                if not standardized_addresses:
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "failed",
                        "reason": "No address columns detected"
                    })
                    continue
                
                # Categorize each address
                file_us_valid = []
                file_international = []
                file_invalid = []
                
                for i, addr in enumerate(standardized_addresses):
                    categorization = address_categorizer.categorize_address(addr, i + 1, file.filename)
                    
                    # Track state normalizations
                    if categorization.get('state_normalization_applied', False):
                        state_normalizations += 1
                    
                    if categorization['category'] == 'us_valid':
                        file_us_valid.append(categorization)
                    elif categorization['category'] == 'international':
                        file_international.append(categorization)
                    else:
                        file_invalid.append(categorization)
                
                # Update totals
                all_us_valid.extend(file_us_valid)
                all_international.extend(file_international)
                all_invalid.extend(file_invalid)
                total_records += len(standardized_addresses)
                
                # File summary
                file_summaries.append({
                    "filename": file.filename,
                    "status": "processed",
                    "total_records": len(standardized_addresses),
                    "us_valid": len(file_us_valid),
                    "international": len(file_international),
                    "invalid": len(file_invalid),
                    "us_valid_percentage": len(file_us_valid) / len(standardized_addresses) if standardized_addresses else 0
                })
                
            except Exception as file_error:
                logger.error(f"Error processing {file.filename}: {file_error}", "API")
                file_summaries.append({
                    "filename": file.filename,
                    "status": "error",
                    "reason": str(file_error)
                })
        
        # Process US valid addresses with USPS (with rate limiting)
        usps_processed = 0
        usps_successful = 0
        usps_failed = 0
        
        if all_us_valid and validation_service.is_address_validation_available():
            logger.info(f"Processing {len(all_us_valid)} US addresses with USPS (rate limited)", "API")
            
            for i, us_addr in enumerate(all_us_valid):
                try:
                    # Prepare address for USPS
                    usps_address = {
                        'guid': f"{us_addr['source_file']}_{us_addr['row_number']}",
                        'line1': us_addr['line1'],
                        'line2': us_addr['line2'] or None,
                        'city': us_addr['city'],
                        'stateCd': us_addr['normalized_state'],
                        'zipCd': us_addr['zip'],
                        'countryCd': 'US'
                    }
                    
                    # Call USPS with rate limiting
                    usps_result = await validate_with_usps_rate_limited(usps_address)
                    
                    # Enhanced result
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
                        'carrier_route': usps_result.get('carrierRoute', ''),
                        'congressional_district': usps_result.get('congressionalDistrict', ''),
                        'is_residential': usps_result.get('residentialDeliveryIndicator') == 'Y',
                        'result_percentage': usps_result.get('ResultPercentage', '0'),
                        'error_message': usps_result.get('errorMsg', ''),
                        'full_usps_result': usps_result
                    }
                    
                    usps_results.append(enhanced_result)
                    usps_processed += 1
                    
                    if enhanced_result['usps_valid']:
                        usps_successful += 1
                    else:
                        usps_failed += 1
                    
                    # Log progress for large batches
                    if (i + 1) % 10 == 0:
                        logger.info(f"USPS processing progress: {i + 1}/{len(all_us_valid)}", "API")
                        
                except HTTPException as e:
                    # Handle rate limiting at batch level
                    if e.status_code == 429:
                        rate_limit_events += 1
                        logger.warning(f"Rate limit hit during batch processing at address {i + 1}", "API")
                        
                        # Create rate limit error result
                        error_result = {
                            'source_file': us_addr['source_file'],
                            'row_number': us_addr['row_number'],
                            'category': 'us_rate_limited',
                            'input_address': us_addr['complete_address'],
                            'normalized_state': us_addr['normalized_state'],
                            'state_normalization_applied': us_addr.get('state_normalization_applied', False),
                            'usps_valid': False,
                            'error_message': 'USPS API rate limit exceeded',
                            'standardized_address': 'Rate Limit Error'
                        }
                        usps_results.append(error_result)
                        usps_processed += 1
                        usps_failed += 1
                        
                        # Continue with remaining addresses after a pause
                        await asyncio.sleep(5)
                        continue
                    else:
                        raise e
                        
                except Exception as e:
                    # Handle other USPS errors
                    error_result = {
                        'source_file': us_addr['source_file'],
                        'row_number': us_addr['row_number'],
                        'category': 'us_usps_error',
                        'input_address': us_addr['complete_address'],
                        'normalized_state': us_addr['normalized_state'],
                        'state_normalization_applied': us_addr.get('state_normalization_applied', False),
                        'usps_valid': False,
                        'error_message': str(e),
                        'standardized_address': 'USPS Processing Error'
                    }
                    usps_results.append(error_result)
                    usps_processed += 1
                    usps_failed += 1
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Comprehensive response
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "processing_summary": {
                "total_files": len(files),
                "total_records": total_records,
                "processing_time_ms": processing_time,
                "categorization_results": {
                    "us_valid_count": len(all_us_valid),
                    "international_count": len(all_international),
                    "invalid_count": len(all_invalid),
                    "us_valid_percentage": len(all_us_valid) / total_records if total_records > 0 else 0,
                    "international_percentage": len(all_international) / total_records if total_records > 0 else 0,
                    "invalid_percentage": len(all_invalid) / total_records if total_records > 0 else 0
                },
                "usps_processing": {
                    "total_processed": usps_processed,
                    "successful_validations": usps_successful,
                    "failed_validations": usps_failed,
                    "success_rate": usps_successful / usps_processed if usps_processed > 0 else 0,
                    "usps_api_available": validation_service.is_address_validation_available(),
                    "rate_limit_events": rate_limit_events,
                    "rate_limited": True
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
            },
            "enhanced_features": {
                "3_bucket_categorization": True,
                "state_name_normalization": True,
                "international_detection": True,
                "multi_file_processing": True,
                "usps_rate_limiting": True,
                "comprehensive_error_analysis": True
            }
        }
        
    except Exception as e:
        logger.error(f"Enhanced CSV processing error: {e}", "API")
        raise HTTPException(status_code=500, detail=f"CSV processing failed: {str(e)}")

# =============================================================================
# 3. NAME VALIDATION WITH FIXED MULTI-CSV
# =============================================================================

@app.post("/api/upload-names-csv")
async def upload_names_csv(
    files: List[UploadFile] = File(
        ...,
        description="Select multiple CSV files with name data",
        media_type="text/csv"
    )
):
    """
    Enhanced name validation with dictionary lookup and AI fallback
    
    **Multi-File Upload:**
    - ✅ Upload up to 10 CSV files in one request
    - ✅ Swagger UI supports multiple file selection
    - ✅ Auto-detect name column formats
    
    **Features:**
    - ✅ Dictionary validation + AI fallback
    - ✅ Gender prediction and organization detection
    - ✅ Comprehensive validation statistics
    """
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not available")
    
    # Validate inputs
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    for file in files:
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail=f"File {file.filename} must be CSV format")
    
    try:
        start_time = time.time()
        combined_results = []
        file_summaries = []
        total_records = 0
        total_successful = 0
        method_stats = {'deterministic': 0, 'hybrid': 0, 'ai_fallback': 0}
        
        logger.info(f"Processing {len(files)} name CSV files", "API")
        
        for file_index, file in enumerate(files):
            try:
                # Read CSV
                df = pd.read_csv(file.file)
                
                if df.empty:
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "skipped", 
                        "reason": "Empty file",
                        "records": 0
                    })
                    continue
                
                logger.info(f"Processing {file.filename}: {len(df)} rows", "API")
                
                # Process with enhanced name validation
                result = validation_service.process_csv_names(df)
                
                if result['success']:
                    # Add file tracking to each result
                    for i, name_result in enumerate(result['results']):
                        name_result.update({
                            'source_file': file.filename,
                            'file_row_number': i + 1,
                            'global_row_number': len(combined_results) + 1
                        })
                    
                    combined_results.extend(result['results'])
                    total_records += result['total_records']
                    total_successful += result['successful_validations']
                    
                    # Aggregate method stats
                    if 'validation_method_breakdown' in result:
                        breakdown = result['validation_method_breakdown']
                        method_stats['deterministic'] += breakdown.get('deterministic', 0)
                        method_stats['hybrid'] += breakdown.get('hybrid', 0)
                        method_stats['ai_fallback'] += breakdown.get('ai_fallback', 0)
                    
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "completed",
                        "total_records": result['total_records'],
                        "successful_validations": result['successful_validations'],
                        "success_rate": f"{result['success_rate']:.1%}",
                        "dictionary_available": result.get('dictionary_available', False)
                    })
                    
                else:
                    file_summaries.append({
                        "filename": file.filename,
                        "status": "failed",
                        "reason": result.get('error', 'Processing failed'),
                        "records": len(df)
                    })
                    
            except Exception as file_error:
                logger.error(f"Error processing {file.filename}: {file_error}", "API")
                file_summaries.append({
                    "filename": file.filename,
                    "status": "error",
                    "reason": str(file_error),
                    "records": 0
                })
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Return comprehensive results
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "processing_summary": {
                "total_files": len(files),
                "total_records": total_records,
                "successful_validations": total_successful,
                "success_rate": total_successful / total_records if total_records > 0 else 0,
                "processing_time_ms": processing_time,
                "validation_methods": method_stats,
                "dictionary_available": validation_service.dictionary_status
            },
            "file_summaries": file_summaries,
            "results": combined_results,
            "validation_info": {
                "dictionary_validation": "Enhanced accuracy with dictionary lookup",
                "ai_fallback": "Pattern matching for names not in dictionaries",
                "multi_file_processing": True,
                "supported_formats": [
                    "name, first_name, last_name columns",
                    "full_name, fullName, Name columns",
                    "Plus automatic gender and organization detection"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Name CSV processing error: {e}", "API")
        raise HTTPException(status_code=500, detail=f"Name CSV processing failed: {str(e)}")

@app.post("/api/validate-names", response_model=NameValidationResponse)
async def validate_names(request: NameValidationRequest):
    """
    Enhanced name validation with dictionary lookup and AI fallback
    
    **Features:**
    - ✅ Dictionary validation for maximum accuracy
    - ✅ AI fallback for names not in dictionaries
    - ✅ Automatic gender prediction
    - ✅ Organization detection
    - ✅ Name parsing and standardization
    """
    
    if not validation_service:
        raise HTTPException(status_code=503, detail="Validation service not available")
    
    try:
        names_data = {"names": [name.dict() for name in request.names]}
        result = validation_service.validate_names(names_data)
        
        if 'processing_stats' in result:
            stats = result['processing_stats']
            methods = stats.get('validation_methods', {})
            det_count = methods.get('deterministic', 0)
            hybrid_count = methods.get('hybrid', 0)
            ai_count = methods.get('ai_fallback', 0)
            
            logger.info(
                f"Name validation processed {len(request.names)} records - "
                f"Dictionary: {det_count}, Hybrid: {hybrid_count}, AI: {ai_count}",
                "API"
            )
        
        response_data = {"names": result['names']}
        return NameValidationResponse(**response_data)
        
    except Exception as e:
        logger.error(f"Name validation error: {e}", "API")
        raise HTTPException(status_code=500, detail=f"Name validation failed: {str(e)}")

# =============================================================================
# UTILITY AND EXAMPLE ENDPOINTS
# =============================================================================

@app.get("/api/example-address")
async def get_example_address():
    """Get example addresses for testing enhanced validation"""
    return {
        "examples": [
            {
                "description": "US Address with state name",
                "request": {
                    "guid": "test1",
                    "line1": "1394 N SAINT LOUIS",
                    "line2": None,
                    "city": "BATESVILLE",
                    "stateCd": "Arkansas",  # State name instead of code
                    "zipCd": "72501",
                    "countryCd": "US"
                },
                "expected_category": "us_valid"
            },
            {
                "description": "International Address (Canadian)",
                "request": {
                    "guid": "test2",
                    "line1": "123 Main Street",
                    "line2": None,
                    "city": "Toronto",
                    "stateCd": "ON",
                    "zipCd": "M5V 3A8",
                    "countryCd": "CA"
                },
                "expected_category": "international"
            },
            {
                "description": "Invalid Address (missing city)",
                "request": {
                    "guid": "test3",
                    "line1": "456 Oak Avenue",
                    "line2": None,
                    "city": "",
                    "stateCd": "CA",
                    "zipCd": "90210",
                    "countryCd": "US"
                },
                "expected_category": "invalid"
            }
        ],
        "usage": "POST /api/validate-address",
        "rate_limiting_note": "USPS API is rate limited to 2 calls per second with automatic retry"
    }

@app.get("/api/example-names")
async def get_example_names():
    """Get example names for testing name validation"""
    return {
        "example_request": {
            "names": [
                {
                    "uniqueID": "1",
                    "fullName": "Dr. William Smith Jr.",
                    "genderCd": "",
                    "partyTypeCd": "I",
                    "parseInd": "Y"
                },
                {
                    "uniqueID": "2",
                    "fullName": "TechCorp Solutions LLC",
                    "genderCd": "",
                    "partyTypeCd": "O",
                    "parseInd": "N"
                }
            ]
        },
        "usage": "POST /api/validate-names"
    }

@app.get("/api/sample-csv")
async def get_sample_csv():
    """Get sample CSV data for testing enhanced validation"""
    
    sample_data = [
        {"id": "1", "address": "1394 N SAINT LOUIS", "city": "BATESVILLE", "state": "Arkansas", "zip": "72501"},
        {"id": "2", "street_address": "123 Main Street", "apartment": "Apt 4B", "city": "New York", "state_code": "New York", "zip_code": "10001"},
        {"id": "3", "line1": "456 Oak Avenue", "city": "Los Angeles", "stateCd": "California", "zipCd": "90210"},
        {"id": "4", "address_line_1": "789 Pine Street", "municipality": "Toronto", "province": "ON", "postal_code": "M5V 3A8"},  # Canadian
        {"id": "5", "street": "321 Elm Drive", "city": "London", "state": "Greater London", "zip": "SW1A 1AA"}  # UK
    ]
    
    # Convert to CSV string
    import io
    import csv
    
    output = io.StringIO()
    if sample_data:
        fieldnames = sample_data[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)
        csv_content = output.getvalue()
    else:
        csv_content = ""
    
    return {
        "description": "Sample CSV with mixed address formats and state names for testing enhanced validation",
        "csv_content": csv_content,
        "expected_results": {
            "us_valid": 3,  # First 3 addresses
            "international": 2,  # Canadian and UK addresses
            "invalid": 0
        },
        "features_demonstrated": [
            "State name normalization (Arkansas → AR, New York → NY, California → CA)",
            "International address detection (Canadian postal code, UK postcode)",
            "Mixed CSV column format handling",
            "Multi-file upload support in Swagger UI",
            "USPS rate limiting with retry logic"
        ],
        "usage": "Upload multiple CSV files to /api/upload-address-csv (max 10 files)",
        "rate_limiting_info": {
            "usps_calls_per_second": 2,
            "automatic_retry": True,
            "max_retries": 3,
            "note": "Large batches will be automatically rate limited to prevent API errors"
        }
    }

# =============================================================================
# SERVER STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    import socket
    
    def is_port_in_use(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('localhost', port))
                return False
            except socket.error:
                return True
    
    def find_available_port(start_port=8000):
        port = start_port
        while is_port_in_use(port):
            port += 1
            if port > 8100:
                raise Exception("No available ports found")
        return port
    
    try:
        port = 8000
        if is_port_in_use(port):
            port = find_available_port(8001)
            print(f"⚠️  Port 8000 in use, using port {port}")
        
        print(f"🌐 Enhanced API starting on port {port}")
        print(f"📚 Documentation: http://localhost:{port}/docs")
        print(f"🔍 Health check: http://localhost:{port}/health")
        print(f"📋 Fixed endpoints:")
        print(f"   • POST /api/validate-address - Single address with rate limiting")
        print(f"   • POST /api/upload-address-csv - Multi-CSV upload (fixed)")
        print(f"   • POST /api/upload-names-csv - Multi-name CSV processing (fixed)")
        print(f"   • POST /api/validate-names - Enhanced name validation")
        print(f"✨ Features: Multi-CSV upload, USPS rate limiting, 3-bucket categorization")
        print(f"🛡️  Rate limiting: 2 USPS calls/second with automatic retry")
        
        uvicorn.run(app, host="0.0.0.0", port=port)
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")