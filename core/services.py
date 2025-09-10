# core/services.py
"""
Updated validation service with dictionary integration and enhanced address processing
"""

import time
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.validators import NameValidator, AddressValidator
from core.models import NameValidationResult
from utils.logger import logger
from utils.config import Config


class ValidationService:
    """Enhanced validation service with dictionary integration and batch address processing"""
    
    def __init__(self, dictionary_path: Optional[str] = None):
        self.name_validator = NameValidator(dictionary_path)
        self.address_validator = AddressValidator()
        self.dictionary_status = self.name_validator.dictionary_loaded
        
        logger.info(f"Validation service initialized - dictionaries: {self.dictionary_status}", "SERVICE")
        
        # Log validation capabilities
        if self.dictionary_status:
            logger.info("Dictionary validation available with AI fallback", "SERVICE")
        else:
            logger.warning("Dictionary not loaded - using AI-only validation", "SERVICE")
    
    def is_name_validation_available(self) -> bool:
        """Check if name validation is available"""
        return True  # Always available (has AI fallback)
    
    def is_address_validation_available(self) -> bool:
        """Check if address validation is available"""
        return self.address_validator.is_configured()
    
    def get_service_status(self) -> Dict:
        """Get enhanced service status"""
        status = {
            'name_validation_available': self.is_name_validation_available(),
            'address_validation_available': self.is_address_validation_available(),
            'api_version': Config.API_VERSION,
            'timestamp': datetime.now().isoformat(),
            'dictionary_status': self.dictionary_status,
            'validation_mode': 'Dictionary + AI' if self.dictionary_status else 'AI Only'
        }
        
        # Add dictionary statistics if loaded
        if self.dictionary_status:
            dict_stats = self._get_dictionary_statistics()
            status['dictionary_statistics'] = dict_stats
        
        return status
    
    def _get_dictionary_statistics(self) -> Dict:
        """Get statistics about loaded dictionaries"""
        stats = {}
        
        validator = self.name_validator
        
        if hasattr(validator, 'first_names_set'):
            stats['first_names_count'] = len(validator.first_names_set)
        
        if hasattr(validator, 'surnames_set'):
            stats['surnames_count'] = len(validator.surnames_set)
        
        if hasattr(validator, 'name_to_gender'):
            stats['gender_mappings_count'] = len(validator.name_to_gender)
        
        if hasattr(validator, 'nickname_to_standard'):
            stats['nickname_mappings_count'] = len(validator.nickname_to_standard)
        
        if hasattr(validator, 'business_words_set'):
            stats['business_words_count'] = len(validator.business_words_set)
        
        if hasattr(validator, 'company_suffixes_set'):
            stats['company_suffixes_count'] = len(validator.company_suffixes_set)
        
        return stats
    
    def validate_names(self, names_data: Dict) -> Dict:
        """
        Enhanced name validation with dictionary lookup and AI fallback
        """
        start_time = time.time()
        
        names = names_data.get('names', [])
        results = []
        
        # Track validation methods used
        method_stats = {
            'deterministic': 0,
            'hybrid': 0,
            'ai_fallback': 0,
            'error': 0
        }
        
        logger.info(f"Processing {len(names)} name records with enhanced validation", "SERVICE")
        
        for name_record in names:
            try:
                # Validate single name record with enhanced validator
                result = self.name_validator.validate_name_record(name_record)
                results.append(result)
                
                # Track validation method
                validation_method = result.get('validationMethod', 'unknown')
                if validation_method in method_stats:
                    method_stats[validation_method] += 1
                else:
                    method_stats['error'] += 1
                
            except Exception as e:
                # Create error result
                error_result = {
                    'uniqueID': name_record.get('uniqueID', ''),
                    'partyTypeCd': '',
                    'prefix': None,
                    'firstName': None,
                    'firstNameStd': None,
                    'middleName': None,
                    'lastName': None,
                    'suffix': None,
                    'fullName': name_record.get('fullName', ''),
                    'inGenderCd': name_record.get('genderCd', ''),
                    'outGenderCd': '',
                    'prefixLt': None,
                    'firstNameLt': None,
                    'middleNameLt': None,
                    'lastNameLt': None,
                    'suffixLt': None,
                    'parseInd': name_record.get('parseInd', ''),
                    'confidenceScore': '0.0',
                    'parseStatus': 'Error',
                    'errorMessage': f'Processing error: {str(e)}',
                    'validationMethod': 'error'
                }
                results.append(error_result)
                method_stats['error'] += 1
                logger.error(f"Error processing name record {name_record.get('uniqueID')}: {e}", "SERVICE")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Log method statistics
        total_processed = len(results)
        if total_processed > 0:
            det_pct = (method_stats['deterministic'] / total_processed) * 100
            hybrid_pct = (method_stats['hybrid'] / total_processed) * 100
            ai_pct = (method_stats['ai_fallback'] / total_processed) * 100
            
            logger.info(
                f"Validation completed in {processing_time}ms - "
                f"Dictionary: {det_pct:.1f}%, Hybrid: {hybrid_pct:.1f}%, "
                f"AI Fallback: {ai_pct:.1f}%",
                "SERVICE"
            )
        
        return {
            'names': results,
            'processing_stats': {
                'total_processed': total_processed,
                'processing_time_ms': processing_time,
                'validation_methods': method_stats,
                'dictionary_available': self.dictionary_status
            }
        }
    
    def validate_addresses(self, addresses_data: Dict) -> Dict:
        """
        Enhanced batch address validation
        """
        start_time = time.time()
        
        addresses = addresses_data.get('addresses', [])
        
        if not self.is_address_validation_available():
            # Return error results for all addresses
            error_results = []
            for addr in addresses:
                error_result = self.address_validator._create_error_result(addr, 'USPS API not configured')
                error_results.append(error_result)
            
            return {
                'addresses': error_results,
                'processing_stats': {
                    'total_processed': len(addresses),
                    'successful': 0,
                    'failed': len(addresses),
                    'processing_time_ms': int((time.time() - start_time) * 1000),
                    'usps_configured': False
                }
            }
        
        logger.info(f"Processing {len(addresses)} addresses with USPS validation", "SERVICE")
        
        # Validate addresses in batch
        results = self.address_validator.validate_addresses_batch(addresses)
        
        # Calculate success/failure stats
        successful = 0
        failed = 0
        
        for result in results:
            if result.get('errorMsg') is None and result.get('mailabilityScore') == '1':
                successful += 1
            else:
                failed += 1
        
        processing_time = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"Address validation completed in {processing_time}ms - "
            f"Successful: {successful}, Failed: {failed}",
            "SERVICE"
        )
        
        return {
            'addresses': results,
            'processing_stats': {
                'total_processed': len(results),
                'successful': successful,
                'failed': failed,
                'success_rate': (successful / len(results)) if results else 0,
                'processing_time_ms': processing_time,
                'usps_configured': True
            }
        }
    
    def validate_single_address(self, address_data: Dict) -> Dict:
        """Validate a single address using enhanced format"""
        logger.info(f"Validating single address", "SERVICE")
        
        if not self.is_address_validation_available():
            # Create error result in enhanced format
            error_result = {
                'guid': address_data.get('guid', ''),
                'line1': address_data.get('line1'),
                'line2': address_data.get('line2'),
                'line3': address_data.get('line3'),
                'line4': address_data.get('line4'),
                'line5': address_data.get('line5'),
                'deliveryAddressLine1': None,
                'deliveryAddressLine2': None,
                'deliveryAddressLine3': None,
                'deliveryAddressLine4': None,
                'deliveryAddressLine5': None,
                'city': address_data.get('city'),
                'stateCd': address_data.get('stateCd'),
                'zipCd': address_data.get('zipCd'),
                'zipCd4': None,
                'zipCdComplete': address_data.get('zipCd'),
                'countyName': None,
                'countyCd': None,
                'countryName': None,
                'countryCd': address_data.get('countryCd', 'US'),
                'mailabilityScore': '0',
                'mailabilityScoreDesc': None,
                'matchCode': 'E1',
                'matchCodeDesc': None,
                'CASSErrorCode': None,
                'barcode': None,
                'carrierRoute': None,
                'congressionalDistrict': None,
                'deliveryPointCd': None,
                'zipMoveReturnCd': None,
                'CASSERPStatus': None,
                'residentialDeliveryIndicator': None,
                'latitude': None,
                'longitude': None,
                'errorMsg': 'USPS API not configured',
                'completeAddress': None,
                'inLine1': address_data.get('line1'),
                'inLine2': address_data.get('line2'),
                'inLine3': address_data.get('line3'),
                'inLine4': address_data.get('line4'),
                'inLine5': address_data.get('line5'),
                'inLine6': address_data.get('city'),
                'inLine7': address_data.get('stateCd'),
                'inLine8': address_data.get('zipCd'),
                'inCountryCd': address_data.get('countryCd', 'US'),
                'inVerificationInd': address_data.get('verificationInd', 'Y'),
                'inOnlyOneAddrInd': address_data.get('onlyOneAddrInd', 'N'),
                'RecipientLine1': None,
                'RecipientLine2': None,
                'ResidueSuperfluous1': None,
                'ResidueSuperfluous2': None,
                'ResultPercentage': '0.00'
            }
            return error_result
        
        # ✅ This calls the ENHANCED method that returns the correct format
        return self.address_validator.validate_single_address(address_data)
    
    def validate_complete_record(self, first_name: str, last_name: str,
                                street_address: str, city: str, state: str, zip_code: str) -> Dict:
        """Enhanced complete record validation"""
        
        start_time = time.time()
        
        result = {
            'timestamp': datetime.now(),
            'name_result': None,
            'address_result': None,
            'overall_valid': False,
            'overall_confidence': 0.0,
            'processing_time_ms': 0,
            'validation_methods': {
                'name_method': 'unknown',
                'address_method': 'usps_api'
            },
            'errors': [],
            'warnings': []
        }
        
        try:
            # Create name record for enhanced validation
            name_record = {
                'uniqueID': 'temp',
                'fullName': f"{first_name} {last_name}",
                'genderCd': '',
                'partyTypeCd': 'I',
                'parseInd': 'Y'
            }
            
            # Validate name with enhanced validator
            name_result = self.name_validator.validate_name_record(name_record)
            result['name_result'] = name_result
            result['validation_methods']['name_method'] = name_result.get('validationMethod', 'unknown')
            
            # Validate address
            address_data = {
                'street_address': street_address,
                'city': city,
                'state': state,
                'zip_code': zip_code
            }
            address_result = self.address_validator.validate_address(address_data)
            result['address_result'] = address_result
            
            # Calculate overall results
            name_valid = name_result.get('parseStatus') in ['Parsed', 'Not Parsed']
            address_deliverable = address_result.get('deliverable', False)
            
            result['overall_valid'] = name_valid and address_deliverable
            
            # Enhanced confidence calculation
            name_confidence = float(name_result.get('confidenceScore', '0')) / 100
            address_confidence = address_result.get('confidence', 0)
            
            # Weight confidence based on validation method
            name_method = result['validation_methods']['name_method']
            if 'deterministic' in name_method:
                name_weight = 0.6  # Higher weight for deterministic
            else:
                name_weight = 0.4  # Lower weight for AI
            
            address_weight = 1.0 - name_weight
            result['overall_confidence'] = (name_confidence * name_weight) + (address_confidence * address_weight)
            
        except Exception as e:
            error_msg = f"Validation error: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg, "SERVICE")
        
        result['processing_time_ms'] = int((time.time() - start_time) * 1000)
        return result
    
    def process_csv_names(self, df: pd.DataFrame) -> Dict:
        """Enhanced CSV processing with validation method tracking"""
        
        logger.info(f"Processing CSV with {len(df)} rows using enhanced validation", "SERVICE")
        
        # Try to find name column
        name_columns = ['name', 'full_name', 'fullname', 'fullName', 'Name', 'FULL_NAME']
        name_col = None
        
        for col in name_columns:
            if col in df.columns:
                name_col = col
                break
        
        if not name_col:
            return {
                'success': False,
                'error': f'Name column not found. Available columns: {list(df.columns)}'
            }
        
        # Convert DataFrame to names format
        names_data = []
        for idx, row in df.iterrows():
            full_name = str(row[name_col]).strip()
            
            if full_name and full_name != 'nan':
                name_record = {
                    'uniqueID': str(idx + 1),
                    'fullName': full_name,
                    'genderCd': '',
                    'partyTypeCd': '',
                    'parseInd': 'Y'
                }
                names_data.append(name_record)
        
        if not names_data:
            return {
                'success': False,
                'error': 'No valid names found in CSV'
            }
        
        # Process using enhanced validation
        validation_result = self.validate_names({'names': names_data})
        results = validation_result['names']
        processing_stats = validation_result.get('processing_stats', {})
        
        # Convert results for CSV output with enhanced information
        csv_results = []
        successful = 0
        method_counts = {
            'deterministic': 0,
            'hybrid': 0,
            'ai_fallback': 0
        }
        
        for result in results:
            validation_method = result.get('validationMethod', 'unknown')
            
            csv_result = {
                'row_number': result['uniqueID'],
                'original_name': result['fullName'],
                'prefix': result['prefix'] or '',
                'first_name': result['firstName'] or '',
                'first_name_std': result['firstNameStd'] or '',
                'middle_name': result['middleName'] or '',
                'last_name': result['lastName'] or '',
                'suffix': result['suffix'] or '',
                'gender': result['outGenderCd'],
                'party_type': result['partyTypeCd'],
                'confidence_score': result['confidenceScore'],
                'parse_status': result['parseStatus'],
                'error_message': result['errorMessage'],
                'validation_method': validation_method
            }
            csv_results.append(csv_result)
            
            if result['parseStatus'] in ['Parsed', 'Not Parsed']:
                successful += 1
            
            # Count validation methods
            if validation_method in method_counts:
                method_counts[validation_method] += 1
        
        return {
            'success': True,
            'total_records': len(df),
            'processed_records': len(csv_results),
            'successful_validations': successful,
            'success_rate': successful / len(csv_results) if csv_results else 0,
            'validation_method_breakdown': method_counts,
            'dictionary_available': self.dictionary_status,
            'processing_stats': processing_stats,
            'results': csv_results
        }
    
    def process_csv_addresses(self, df: pd.DataFrame) -> Dict:
        """Process addresses from CSV with automatic format standardization"""
        
        logger.info(f"Processing address CSV with {len(df)} rows", "SERVICE")
        
        try:
            # Standardize CSV format to address format
            standardized_addresses = self.address_validator.standardize_csv_to_address_format(df)
            
            if not standardized_addresses:
                return {
                    'success': False,
                    'error': 'No valid addresses found in CSV'
                }
            
            # Validate addresses using batch processing
            validation_result = self.validate_addresses({'addresses': standardized_addresses})
            results = validation_result['addresses']
            processing_stats = validation_result.get('processing_stats', {})
            
            # Convert results for CSV output
            csv_results = []
            successful = 0
            
            for result in results:
                is_valid = result.get('errorMsg') is None and result.get('mailabilityScore') == '1'
                
                csv_result = {
                    'guid': result['guid'],
                    'input_line1': result['inLine1'] or '',
                    'input_city': result['inLine6'] or '',
                    'input_state': result['inLine7'] or '',
                    'input_zip': result['inLine8'] or '',
                    'validated_line1': result['deliveryAddressLine1'] or '',
                    'validated_city': result['city'] or '',
                    'validated_state': result['stateCd'] or '',
                    'validated_zip': result['zipCdComplete'] or '',
                    'county_name': result['countyName'] or '',
                    'carrier_route': result['carrierRoute'] or '',
                    'congressional_district': result['congressionalDistrict'] or '',
                    'mailability_score': result['mailabilityScore'] or '0',
                    'match_code': result['matchCode'] or '',
                    'result_percentage': result['ResultPercentage'] or '0.00',
                    'is_valid': is_valid,
                    'error_message': result['errorMsg'] or ''
                }
                csv_results.append(csv_result)
                
                if is_valid:
                    successful += 1
            
            return {
                'success': True,
                'total_records': len(df),
                'processed_records': len(csv_results),
                'successful_validations': successful,
                'success_rate': successful / len(csv_results) if csv_results else 0,
                'usps_configured': self.is_address_validation_available(),
                'processing_stats': processing_stats,
                'results': csv_results
            }
            
        except Exception as e:
            logger.error(f"Error processing address CSV: {e}", "SERVICE")
            return {
                'success': False,
                'error': f'CSV processing failed: {str(e)}'
            }
    
    def get_example_payload(self) -> Dict:
        """Get enhanced example payload for testing"""
        return {
            "names": [
                {
                    "uniqueID": "1",
                    "fullName": "Bill Smith",
                    "genderCd": "M",
                    "partyTypeCd": "I",
                    "parseInd": "Y"
                },
                {
                    "uniqueID": "2", 
                    "fullName": "Dr. Sarah Johnson-Williams",
                    "genderCd": "",
                    "partyTypeCd": "",
                    "parseInd": "Y"
                },
                {
                    "uniqueID": "3",
                    "fullName": "TechCorp Solutions LLC",
                    "genderCd": "",
                    "partyTypeCd": "O",
                    "parseInd": "N"
                },
                {
                    "uniqueID": "4",
                    "fullName": "Mr. Michael Thompson Jr.",
                    "genderCd": "",
                    "partyTypeCd": "I", 
                    "parseInd": "Y"
                },
                {
                    "uniqueID": "5",
                    "fullName": "Bob Johnson",
                    "genderCd": "",
                    "partyTypeCd": "",
                    "parseInd": "Y"
                }
            ]
        }
    # Add these methods to core/services.py in the ValidationService class

def process_csv_addresses_enhanced(self, df: pd.DataFrame, manual_mappings: Dict = None) -> Dict:
    """Enhanced CSV processing with better error handling and format detection"""
    
    logger.info(f"Processing address CSV with {len(df)} rows using enhanced validation", "SERVICE")
    
    try:
        # Validate DataFrame
        if df.empty:
            return {
                'success': False,
                'error': 'CSV file is empty'
            }
        
        # Use manual mappings if provided, otherwise auto-detect
        if manual_mappings:
            logger.info("Using manual column mappings", "SERVICE")
            standardized_addresses = self._apply_manual_mappings(df, manual_mappings)
        else:
            logger.info("Using auto-detection for column mappings", "SERVICE")
            standardized_addresses = self.address_validator.standardize_csv_to_address_format(df)
        
        if not standardized_addresses:
            return {
                'success': False,
                'error': 'No valid addresses found after standardization. Please check column mappings.'
            }
        
        logger.info(f"Standardized {len(standardized_addresses)} addresses", "SERVICE")
        
        # Validate addresses using batch processing
        validation_result = self.validate_addresses({'addresses': standardized_addresses})
        results = validation_result['addresses']
        processing_stats = validation_result.get('processing_stats', {})
        
        # Enhanced result processing
        csv_results = []
        successful = 0
        error_summary = {}
        
        for i, result in enumerate(results):
            is_valid = result.get('errorMsg') is None and result.get('mailabilityScore') == '1'
            
            # Create enhanced CSV result
            csv_result = {
                'row_number': i + 1,
                'guid': result['guid'],
                
                # Input data
                'input_line1': result.get('inLine1', ''),
                'input_line2': result.get('inLine2', ''),
                'input_city': result.get('inLine6', ''),
                'input_state': result.get('inLine7', ''),
                'input_zip': result.get('inLine8', ''),
                
                # USPS validated data
                'validated_line1': result.get('deliveryAddressLine1', ''),
                'validated_line2': result.get('deliveryAddressLine2', ''),
                'validated_city': result.get('city', ''),
                'validated_state': result.get('stateCd', ''),
                'validated_zip': result.get('zipCdComplete', ''),
                'validated_zip_plus4': result.get('zipCd4', ''),
                
                # Geographic and postal info
                'county_name': result.get('countyName', ''),
                'county_code': result.get('countyCd', ''),
                'carrier_route': result.get('carrierRoute', ''),
                'congressional_district': result.get('congressionalDistrict', ''),
                'delivery_point': result.get('deliveryPointCd', ''),
                
                # Validation results
                'mailability_score': result.get('mailabilityScore', '0'),
                'match_code': result.get('matchCode', ''),
                'result_percentage': result.get('ResultPercentage', '0.00'),
                'is_residential': result.get('residentialDeliveryIndicator') == 'Y',
                'is_valid': is_valid,
                'is_deliverable': is_valid,
                
                # Error info
                'error_message': result.get('errorMsg', ''),
                'validation_notes': self._get_validation_notes(result)
            }
            
            csv_results.append(csv_result)
            
            if is_valid:
                successful += 1
            else:
                # Track error types
                error_type = self._categorize_error(result.get('errorMsg', 'Unknown error'))
                error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        # Enhanced statistics
        enhanced_stats = {
            'total_records': len(df),
            'processed_records': len(csv_results),
            'successful_validations': successful,
            'failed_validations': len(csv_results) - successful,
            'success_rate': successful / len(csv_results) if csv_results else 0,
            'usps_configured': self.is_address_validation_available(),
            'processing_stats': processing_stats,
            'error_breakdown': error_summary,
            'data_quality': {
                'complete_addresses': len([r for r in csv_results if r['input_line1'] and r['input_city'] and r['input_state'] and r['input_zip']]),
                'missing_data_count': len([r for r in csv_results if not (r['input_line1'] and r['input_city'] and r['input_state'] and r['input_zip'])]),
                'standardization_improvements': len([r for r in csv_results if r['is_valid'] and (r['input_line1'] != r['validated_line1'] or r['input_city'] != r['validated_city'])])
            }
        }
        
        return {
            'success': True,
            'total_records': enhanced_stats['total_records'],
            'processed_records': enhanced_stats['processed_records'],
            'successful_validations': enhanced_stats['successful_validations'],
            'success_rate': enhanced_stats['success_rate'],
            'usps_configured': enhanced_stats['usps_configured'],
            'processing_stats': enhanced_stats['processing_stats'],
            'enhanced_statistics': enhanced_stats,
            'results': csv_results
        }
        
    except Exception as e:
        logger.error(f"Enhanced CSV processing error: {e}", "SERVICE")
        return {
            'success': False,
            'error': f'CSV processing failed: {str(e)}',
            'details': 'Check CSV format and ensure address columns are present'
        }

def _apply_manual_mappings(self, df: pd.DataFrame, mappings: Dict) -> List[Dict]:
    """Apply manual column mappings to standardize CSV format"""
    
    standardized_addresses = []
    
    for idx, row in df.iterrows():
        address = {
            'guid': str(idx + 1),
            'line1': str(row.get(mappings.get('line1', ''), '')).strip() or None,
            'line2': str(row.get(mappings.get('line2', ''), '')).strip() or None,
            'line3': None,
            'line4': None,
            'line5': None,
            'city': str(row.get(mappings.get('city', ''), '')).strip(),
            'stateCd': str(row.get(mappings.get('stateCd', ''), '')).strip().upper(),
            'zipCd': str(row.get(mappings.get('zipCd', ''), '')).strip(),
            'countryCd': str(row.get(mappings.get('countryCd', ''), 'US')).strip().upper(),
            'verificationInd': 'Y',
            'onlyOneAddrInd': 'N'
        }
        
        # Clean up empty strings to appropriate values
        for key in ['line1', 'line2', 'city', 'stateCd', 'zipCd']:
            if address[key] == '' or address[key] == 'nan':
                if key in ['city', 'stateCd', 'zipCd']:
                    address[key] = ''  # Required fields should be empty string, not None
                else:
                    address[key] = None
        
        standardized_addresses.append(address)
    
    return standardized_addresses

def _get_validation_notes(self, result: Dict) -> str:
    """Generate human-readable validation notes"""
    notes = []
    
    # Mailability scoring
    mailability = result.get('mailabilityScore', '0')
    if mailability == '1':
        notes.append("USPS Deliverable")
    elif mailability == '0':
        notes.append("Not Deliverable")
    
    # Match code interpretation
    match_code = result.get('matchCode', '')
    if match_code == 'A1':
        notes.append("Exact Match")
    elif match_code == 'B1':
        notes.append("Default Match")
    elif match_code.startswith('C'):
        notes.append("Partial Match")
    elif match_code.startswith('E'):
        notes.append("Error")
    
    # Address type
    if result.get('residentialDeliveryIndicator') == 'Y':
        notes.append("Residential")
    elif result.get('residentialDeliveryIndicator') == 'N':
        notes.append("Business")
    
    # Result percentage
    result_pct = float(result.get('ResultPercentage', '0'))
    if result_pct >= 90:
        notes.append("High Confidence")
    elif result_pct >= 70:
        notes.append("Medium Confidence")
    elif result_pct > 0:
        notes.append("Low Confidence")
    
    return "; ".join(notes) if notes else "No additional notes"

def _categorize_error(self, error_msg: str) -> str:
    """Categorize error messages for summary"""
    if not error_msg:
        return "No Error"
    
    error_lower = error_msg.lower()
    
    if 'not found' in error_lower or '404' in error_lower:
        return "Address Not Found"
    elif 'invalid' in error_lower or '400' in error_lower:
        return "Invalid Format"
    elif 'missing' in error_lower or 'required' in error_lower:
        return "Missing Data"
    elif 'api' in error_lower or 'service' in error_lower:
        return "Service Error"
    elif 'timeout' in error_lower:
        return "Timeout"
    else:
        return "Other Error"

def get_csv_format_examples(self) -> Dict:
    """Get examples of supported CSV formats"""
    return {
        "standard_format": {
            "description": "Standard address validation format",
            "columns": ["id", "line1", "city", "stateCd", "zipCd"],
            "example_data": [
                {"id": "1", "line1": "123 Main St", "city": "New York", "stateCd": "NY", "zipCd": "10001"},
                {"id": "2", "line1": "456 Oak Ave", "city": "Los Angeles", "stateCd": "CA", "zipCd": "90210"}
            ]
        },
        "common_format": {
            "description": "Common CSV export format",
            "columns": ["address", "city", "state", "zip"],
            "example_data": [
                {"address": "789 Pine St", "city": "Chicago", "state": "IL", "zip": "60601"},
                {"address": "321 Elm Dr", "city": "Houston", "state": "TX", "zip": "77001"}
            ]
        },
        "extended_format": {
            "description": "Extended format with apartment/suite info",
            "columns": ["street_address", "apartment", "city", "state_code", "zip_code"],
            "example_data": [
                {"street_address": "555 Maple Ave", "apartment": "Apt 4B", "city": "Miami", "state_code": "FL", "zip_code": "33101"},
                {"street_address": "777 Cedar Ln", "apartment": "", "city": "Seattle", "state_code": "WA", "zip_code": "98101"}
            ]
        },
        "auto_mapping_supported": {
            "line1_variations": ["line1", "address_line_1", "address1", "street_address", "street", "addr1", "address"],
            "line2_variations": ["line2", "address_line_2", "address2", "apartment", "apt", "suite", "unit", "addr2"],
            "city_variations": ["city", "town", "municipality"],
            "state_variations": ["state_cd", "state", "state_code", "st", "province"],
            "zip_variations": ["zip_cd", "zip", "zip_code", "postal_code", "zipcode", "postcode"]
        }
    }
    def get_example_address_payload(self) -> Dict:
        """Get example address payload for testing"""
        return {
            "addresses": [
                {
                    "guid": "1",
                    "line1": "1394 N SAINT LOUIS",
                    "line2": None,
                    "line3": None,
                    "line4": None,
                    "line5": None,
                    "city": "BATESVILLE",
                    "stateCd": "AR",
                    "zipCd": "72501",
                    "countryCd": "US",
                    "verificationInd": "Y",
                    "onlyOneAddrInd": "N"
                },
                {
                    "guid": "2",
                    "line1": "123 Main Street",
                    "line2": "Apt 4B",
                    "line3": None,
                    "line4": None,
                    "line5": None,
                    "city": "New York",
                    "stateCd": "NY",
                    "zipCd": "10001",
                    "countryCd": "US",
                    "verificationInd": "Y",
                    "onlyOneAddrInd": "N"
                }
            ]
        }