# client_sdk/address_validator_client.py
"""
Professional Python SDK for Address Validator API
Provides easy-to-use client for name and address validation services
"""

import requests
import json
import time
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import csv
import io

@dataclass
class ValidationResult:
    """Standard validation result"""
    success: bool
    data: Dict
    error: Optional[str] = None
    rate_limit_remaining: Optional[int] = None
    processing_time: Optional[float] = None

@dataclass
class AddressRecord:
    """Address record for validation"""
    guid: str
    line1: str
    city: str
    state_cd: str
    zip_cd: str
    line2: Optional[str] = None
    country_cd: str = "US"

@dataclass
class NameRecord:
    """Name record for validation"""
    unique_id: str
    full_name: str
    gender_cd: str = ""
    party_type_cd: str = ""
    parse_ind: str = "Y"

class AddressValidatorClient:
    """
    Professional client for Address Validator API
    
    Usage:
        client = AddressValidatorClient(api_key="your-api-key", base_url="https://your-api.com")
        result = client.validate_address("123 Main St", "New York", "NY", "10001")
    """
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        """
        Initialize the client
        
        Args:
            api_key: Your API key
            base_url: Base URL of the API (e.g., https://your-api.railway.app)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'AddressValidatorClient/2.0.0'
        })
        
        # Track usage
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> ValidationResult:
        """Make authenticated request to API"""
        start_time = time.time()
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.total_requests += 1
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            processing_time = time.time() - start_time
            
            # Extract rate limit info from headers
            rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
            if rate_limit_remaining:
                rate_limit_remaining = int(rate_limit_remaining)
            
            if response.status_code == 200:
                self.successful_requests += 1
                return ValidationResult(
                    success=True,
                    data=response.json(),
                    rate_limit_remaining=rate_limit_remaining,
                    processing_time=processing_time
                )
            elif response.status_code == 401:
                error_msg = "Invalid API key. Please check your credentials."
            elif response.status_code == 403:
                error_msg = "Access forbidden. Feature may not be available in your tier."
            elif response.status_code == 429:
                error_msg = "Rate limit exceeded. Please slow down your requests."
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', {}).get('message', f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
            
            self.failed_requests += 1
            return ValidationResult(
                success=False,
                data={},
                error=error_msg,
                rate_limit_remaining=rate_limit_remaining,
                processing_time=processing_time
            )
            
        except requests.exceptions.Timeout:
            self.failed_requests += 1
            return ValidationResult(
                success=False,
                data={},
                error="Request timeout. Please try again.",
                processing_time=time.time() - start_time
            )
        except requests.exceptions.ConnectionError:
            self.failed_requests += 1
            return ValidationResult(
                success=False,
                data={},
                error="Connection error. Please check your internet connection.",
                processing_time=time.time() - start_time
            )
        except Exception as e:
            self.failed_requests += 1
            return ValidationResult(
                success=False,
                data={},
                error=f"Unexpected error: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def health_check(self) -> ValidationResult:
        """Check API health and availability"""
        return self._make_request('GET', '/health')
    
    def get_api_info(self) -> ValidationResult:
        """Get API information and usage statistics"""
        return self._make_request('GET', '/api-info')
    
    def validate_address(self, 
                        line1: str, 
                        city: str, 
                        state_cd: str, 
                        zip_cd: str,
                        line2: Optional[str] = None,
                        guid: Optional[str] = None) -> ValidationResult:
        """
        Validate a single address
        
        Args:
            line1: Street address
            city: City name
            state_cd: State code (e.g., 'CA') or name (e.g., 'California')
            zip_cd: ZIP code
            line2: Optional second address line
            guid: Optional unique identifier
            
        Returns:
            ValidationResult with address validation data
        """
        address = AddressRecord(
            guid=guid or str(int(time.time())),
            line1=line1,
            line2=line2,
            city=city,
            state_cd=state_cd,
            zip_cd=zip_cd
        )
        
        return self._make_request('POST', '/api/validate-address', json=address.__dict__)
    
    def validate_addresses_batch(self, addresses: List[AddressRecord]) -> ValidationResult:
        """
        Validate multiple addresses (requires premium/enterprise tier)
        
        Args:
            addresses: List of AddressRecord objects
            
        Returns:
            ValidationResult with batch validation data
        """
        address_data = [addr.__dict__ for addr in addresses]
        return self._make_request('POST', '/api/batch-validate-addresses', 
                                json={"addresses": address_data})
    
    def validate_name(self, 
                     full_name: str,
                     unique_id: Optional[str] = None,
                     gender_cd: str = "",
                     party_type_cd: str = "",
                     parse_ind: str = "Y") -> ValidationResult:
        """
        Validate a single name
        
        Args:
            full_name: Full name to validate
            unique_id: Optional unique identifier
            gender_cd: Gender code (M/F) or empty for prediction
            party_type_cd: Party type (I=Individual, O=Organization) or empty for detection
            parse_ind: Parse indicator (Y=parse components, N=don't parse)
            
        Returns:
            ValidationResult with name validation data
        """
        name = NameRecord(
            unique_id=unique_id or str(int(time.time())),
            full_name=full_name,
            gender_cd=gender_cd,
            party_type_cd=party_type_cd,
            parse_ind=parse_ind
        )
        
        return self._make_request('POST', '/api/validate-names', 
                                json={"names": [name.__dict__]})
    
    def validate_names_batch(self, names: List[NameRecord]) -> ValidationResult:
        """
        Validate multiple names
        
        Args:
            names: List of NameRecord objects
            
        Returns:
            ValidationResult with batch name validation data
        """
        names_data = [name.__dict__ for name in names]
        return self._make_request('POST', '/api/validate-names', 
                                json={"names": names_data})
    
    def upload_csv_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """
        Upload and process CSV file (requires premium/enterprise tier)
        
        Args:
            file_path: Path to CSV file containing addresses
            
        Returns:
            ValidationResult with batch processing data
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            return ValidationResult(
                success=False,
                data={},
                error=f"File not found: {file_path}"
            )
        
        if not file_path.suffix.lower() == '.csv':
            return ValidationResult(
                success=False,
                data={},
                error="File must be a CSV file"
            )
        
        files = {'files': (file_path.name, open(file_path, 'rb'), 'text/csv')}
        
        try:
            return self._make_request('POST', '/api/batch-validate-addresses', files=files)
        finally:
            # Ensure file is closed
            if 'files' in locals():
                files['files'][1].close()
    
    def upload_csv_data(self, csv_data: str, filename: str = "data.csv") -> ValidationResult:
        """
        Upload CSV data as string (requires premium/enterprise tier)
        
        Args:
            csv_data: CSV content as string
            filename: Name for the uploaded file
            
        Returns:
            ValidationResult with batch processing data
        """
        files = {'files': (filename, io.StringIO(csv_data), 'text/csv')}
        return self._make_request('POST', '/api/batch-validate-addresses', files=files)
    
    def get_usage_stats(self) -> ValidationResult:
        """Get detailed usage statistics"""
        return self._make_request('GET', '/api/usage-stats')
    
    def get_examples(self) -> ValidationResult:
        """Get API usage examples"""
        return self._make_request('GET', '/api/examples')
    
    def export_results_to_csv(self, results: Dict, output_path: Union[str, Path]) -> bool:
        """
        Export validation results to CSV file
        
        Args:
            results: Results from batch validation
            output_path: Path where to save the CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            
            # Extract results data
            if 'categorized_results' in results:
                all_results = []
                
                # Add USPS validated addresses
                for result in results['categorized_results'].get('usps_validated_addresses', []):
                    all_results.append({
                        'source_file': result.get('source_file', ''),
                        'row_number': result.get('row_number', ''),
                        'category': 'US_USPS_Validated',
                        'input_address': result.get('input_address', ''),
                        'output_address': result.get('standardized_address', ''),
                        'usps_valid': result.get('usps_valid', False),
                        'county': result.get('county', ''),
                        'is_residential': result.get('is_residential', ''),
                        'error_message': result.get('error_message', '')
                    })
                
                # Add international addresses
                for result in results['categorized_results'].get('international_addresses', []):
                    all_results.append({
                        'source_file': result.get('source_file', ''),
                        'row_number': result.get('row_number', ''),
                        'category': 'International',
                        'input_address': result.get('complete_address', ''),
                        'output_address': result.get('complete_address', ''),
                        'usps_valid': False,
                        'county': '',
                        'is_residential': '',
                        'error_message': ''
                    })
                
                # Add invalid addresses
                for result in results['categorized_results'].get('invalid_addresses', []):
                    issues = result.get('issues', [])
                    issues_text = '; '.join(issues) if isinstance(issues, list) else str(issues)
                    
                    all_results.append({
                        'source_file': result.get('source_file', ''),
                        'row_number': result.get('row_number', ''),
                        'category': 'Invalid',
                        'input_address': result.get('complete_address', ''),
                        'output_address': '',
                        'usps_valid': False,
                        'county': '',
                        'is_residential': '',
                        'error_message': issues_text
                    })
                
                # Write to CSV
                if all_results:
                    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
                        fieldnames = all_results[0].keys()
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(all_results)
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error exporting to CSV: {e}")
            return False
    
    def get_client_stats(self) -> Dict:
        """Get client-side usage statistics"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': (self.successful_requests / self.total_requests) if self.total_requests > 0 else 0
        }

# =============================================================================
# USAGE EXAMPLES
# =============================================================================

def example_single_address():
    """Example: Validate a single address"""
    client = AddressValidatorClient(
        api_key="your-api-key-here",
        base_url="https://your-api-domain.com"
    )
    
    # Validate single address
    result = client.validate_address(
        line1="1600 Pennsylvania Avenue NW",
        city="Washington",
        state_cd="DC",  # Can also use "District of Columbia"
        zip_cd="20500"
    )
    
    if result.success:
        print("✅ Address validation successful!")
        print(f"Category: {result.data['categorization']['category']}")
        
        if result.data.get('usps_result'):
            usps_data = result.data['usps_result']
            print(f"USPS Valid: {usps_data.get('mailabilityScore') == '1'}")
            print(f"Standardized: {usps_data.get('deliveryAddressLine1')}")
            print(f"County: {usps_data.get('countyName')}")
    else:
        print(f"❌ Validation failed: {result.error}")

def example_batch_addresses():
    """Example: Validate multiple addresses"""
    client = AddressValidatorClient(
        api_key="premium-key-67890",  # Requires premium/enterprise
        base_url="https://your-api-domain.com"
    )
    
    addresses = [
        AddressRecord("1", "123 Main St", "New York", "NY", "10001"),
        AddressRecord("2", "456 Oak Ave", "Los Angeles", "California", "90210"),
        AddressRecord("3", "789 Pine St", "Chicago", "IL", "60601")
    ]
    
    result = client.validate_addresses_batch(addresses)
    
    if result.success:
        print("✅ Batch validation successful!")
        summary = result.data['processing_summary']
        print(f"Total records: {summary['total_records']}")
        print(f"US valid: {summary['categorization_results']['us_valid_count']}")
        print(f"International: {summary['categorization_results']['international_count']}")
        print(f"Invalid: {summary['categorization_results']['invalid_count']}")
    else:
        print(f"❌ Batch validation failed: {result.error}")

def example_csv_upload():
    """Example: Upload and process CSV file"""
    client = AddressValidatorClient(
        api_key="enterprise-key-abc123",  # Requires premium/enterprise
        base_url="https://your-api-domain.com"
    )
    
    # Upload CSV file
    result = client.upload_csv_file("addresses.csv")
    
    if result.success:
        print("✅ CSV processing successful!")
        
        # Export results to new CSV
        if client.export_results_to_csv(result.data, "validated_addresses.csv"):
            print("📄 Results exported to validated_addresses.csv")
        
        # Show statistics
        stats = client.get_client_stats()
        print(f"Client stats: {stats}")
    else:
        print(f"❌ CSV processing failed: {result.error}")

def example_name_validation():
    """Example: Validate names"""
    client = AddressValidatorClient(
        api_key="your-api-key-here",
        base_url="https://your-api-domain.com"
    )
    
    result = client.validate_name(
        full_name="Dr. William Smith Jr.",
        parse_ind="Y"
    )
    
    if result.success:
        name_data = result.data['names'][0]
        print("✅ Name validation successful!")
        print(f"Parsed name: {name_data['firstName']} {name_data['lastName']}")
        print(f"Gender: {name_data['outGenderCd']}")
        print(f"Confidence: {name_data['confidenceScore']}%")
        print(f"Method: {name_data.get('validationMethod', 'Unknown')}")
    else:
        print(f"❌ Name validation failed: {result.error}")

if __name__ == "__main__":
    # Run examples
    print("🚀 Address Validator Client Examples\n")
    
    print("1. Single Address Validation:")
    example_single_address()
    print("\n" + "="*50 + "\n")
    
    print("2. Name Validation:")
    example_name_validation()
    print("\n" + "="*50 + "\n")
    
    print("3. Batch Address Validation:")
    example_batch_addresses()
    print("\n" + "="*50 + "\n")
    
    print("4. CSV Upload and Processing:")
    example_csv_upload()