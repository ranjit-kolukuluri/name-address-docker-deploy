# core/models.py
"""
Updated Pydantic models for enhanced address validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# API Request Models
class NameRecord(BaseModel):
    uniqueID: str = Field(..., description="Unique identifier for the record")
    fullName: str = Field(..., description="Full name to validate")
    genderCd: Optional[str] = Field("", description="Gender code (M/F/empty)")
    partyTypeCd: Optional[str] = Field("", description="Party type code (I/O/empty)")
    parseInd: Optional[str] = Field("", description="Parse indicator (Y/N/empty)")


class NameValidationRequest(BaseModel):
    names: List[NameRecord] = Field(..., description="List of name records to validate")


# Enhanced Address Models
class AddressRecord(BaseModel):
    guid: str = Field(..., description="Unique identifier for the address")
    line1: Optional[str] = Field(None, description="Address line 1")
    line2: Optional[str] = Field(None, description="Address line 2") 
    line3: Optional[str] = Field(None, description="Address line 3")
    line4: Optional[str] = Field(None, description="Address line 4")
    line5: Optional[str] = Field(None, description="Address line 5")
    city: str = Field(..., description="City name")
    stateCd: str = Field(..., description="State code")
    zipCd: str = Field(..., description="ZIP code")
    countryCd: Optional[str] = Field("US", description="Country code")
    verificationInd: Optional[str] = Field("Y", description="Verification indicator")
    onlyOneAddrInd: Optional[str] = Field("N", description="Only one address indicator")


class AddressValidationRequest(BaseModel):
    addresses: List[AddressRecord] = Field(..., description="List of addresses to validate")


# Response Models
class NameValidationResult(BaseModel):
    uniqueID: str
    partyTypeCd: str
    prefix: Optional[str] = None
    firstName: Optional[str] = None
    firstNameStd: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    suffix: Optional[str] = None
    fullName: str
    inGenderCd: str
    outGenderCd: str
    prefixLt: Optional[str] = None
    firstNameLt: Optional[str] = None
    middleNameLt: Optional[str] = None
    lastNameLt: Optional[str] = None
    suffixLt: Optional[str] = None
    parseInd: str
    confidenceScore: str
    parseStatus: str
    errorMessage: str


class NameValidationResponse(BaseModel):
    names: List[NameValidationResult]


class AddressValidationResult(BaseModel):
    guid: str
    line1: Optional[str] = None
    line2: Optional[str] = None
    line3: Optional[str] = None
    line4: Optional[str] = None
    line5: Optional[str] = None
    deliveryAddressLine1: Optional[str] = None
    deliveryAddressLine2: Optional[str] = None
    deliveryAddressLine3: Optional[str] = None
    deliveryAddressLine4: Optional[str] = None
    deliveryAddressLine5: Optional[str] = None
    city: Optional[str] = None
    stateCd: Optional[str] = None
    zipCd: Optional[str] = None
    zipCd4: Optional[str] = None
    zipCdComplete: Optional[str] = None
    countyName: Optional[str] = None
    countyCd: Optional[str] = None
    countryName: Optional[str] = None
    countryCd: Optional[str] = None
    mailabilityScore: Optional[str] = None
    mailabilityScoreDesc: Optional[str] = None
    matchCode: Optional[str] = None
    matchCodeDesc: Optional[str] = None
    CASSErrorCode: Optional[str] = None
    barcode: Optional[str] = None
    carrierRoute: Optional[str] = None
    congressionalDistrict: Optional[str] = None
    deliveryPointCd: Optional[str] = None
    zipMoveReturnCd: Optional[str] = None
    CASSERPStatus: Optional[str] = None
    residentialDeliveryIndicator: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    errorMsg: Optional[str] = None
    completeAddress: Optional[str] = None
    inLine1: Optional[str] = None
    inLine2: Optional[str] = None
    inLine3: Optional[str] = None
    inLine4: Optional[str] = None
    inLine5: Optional[str] = None
    inLine6: Optional[str] = None
    inLine7: Optional[str] = None
    inLine8: Optional[str] = None
    inCountryCd: Optional[str] = None
    inVerificationInd: Optional[str] = None
    inOnlyOneAddrInd: Optional[str] = None
    RecipientLine1: Optional[str] = None
    RecipientLine2: Optional[str] = None
    ResidueSuperfluous1: Optional[str] = None
    ResidueSuperfluous2: Optional[str] = None
    ResultPercentage: Optional[str] = None


class AddressValidationResponse(BaseModel):
    addresses: List[AddressValidationResult]


class ServiceStatus(BaseModel):
    name_validation_available: bool
    address_validation_available: bool
    api_version: str
    timestamp: str