"""
Enhanced validation logic for names and addresses with dictionary integration and batch processing
"""

import requests
import re
import time
import sys
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.config import Config, load_usps_credentials
from utils.logger import logger


class NameValidator:
    """Enhanced name validator with dictionary integration and AI fallback"""
    
    def __init__(self, dictionary_path: Optional[str] = None):
        # 🔧 FIXED: Make dictionary path configurable for Docker
        if dictionary_path is None:
            # Try multiple possible dictionary locations
            possible_paths = [
                os.getenv('DICTIONARY_PATH'),  # Environment variable
                '/app/dictionaries',            # Docker standard location
                '/app/data/dictionaries',       # Alternative Docker location
                './dictionaries',              # Local relative path
                './data/dictionaries',         # Alternative local path
                '/Users/t93uyz8/Documents/name_dictionaries'  # Original local path (fallback)
            ]
            
            self.dictionary_path = None
            for path in possible_paths:
                if path and os.path.exists(path):
                    self.dictionary_path = path
                    logger.info(f"Found dictionary path: {path}", "VALIDATOR")
                    break
            
            if not self.dictionary_path:
                logger.warning("No dictionary path found - using AI-only validation", "VALIDATOR")
        else:
            self.dictionary_path = dictionary_path
        
        self.dictionary_loaded = False
        
        # Dictionary lookup structures
        self.first_names_set = set()
        self.surnames_set = set()
        self.business_words_set = set()
        self.company_suffixes_set = set()
        self.name_prefixes_set = set()
        self.name_to_gender = {}
        self.nickname_to_standard = {}
        
        # Load dictionaries if available
        self._load_dictionaries()
        
        # AI fallback patterns
        self._initialize_ai_patterns()
        
        logger.info(f"Name validator initialized - dictionaries loaded: {self.dictionary_loaded}", "VALIDATOR")
    
    
    def _load_dictionaries(self):
        """Load dictionaries from CSV files with enhanced error handling"""
        if not self.dictionary_path:
            logger.warning("No dictionary path available", "VALIDATOR")
            return
            
        try:
            logger.info(f"Attempting to load dictionaries from: {self.dictionary_path}", "VALIDATOR")
            
            if not os.path.exists(self.dictionary_path):
                logger.warning(f"Dictionary path not found: {self.dictionary_path}", "VALIDATOR")
                return
            
            # List available files for debugging
            try:
                files = os.listdir(self.dictionary_path)
                logger.info(f"Available files in dictionary path: {files}", "VALIDATOR")
            except Exception as e:
                logger.error(f"Cannot list dictionary directory: {e}", "VALIDATOR")
                return
            
            loaded_count = 0
            
            # 🔧 FIXED: More flexible file loading with multiple encodings
            dictionary_files = {
                'first_names': ['usa_firstnames_infa.csv', 'firstnames.csv', 'first_names.csv'],
                'surnames': ['usa_surnames_infa.csv', 'surnames.csv', 'last_names.csv'],
                'gender': ['usa_gender_infa.csv', 'gender.csv', 'gender_mappings.csv'],
                'nicknames': ['usa_nicknames_infa.csv', 'nicknames.csv', 'nickname_mappings.csv'],
                'business': ['usa_business_word_infa.csv', 'business_words.csv', 'business.csv'],
                'suffixes': ['usa_company_sufx_abrv_infa.csv', 'company_suffixes.csv', 'suffixes.csv'],
                'prefixes': ['usa_name_prefix_NYL.csv', 'name_prefixes.csv', 'prefixes.csv']
            }
            
            encodings_to_try = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'iso-8859-1']
            
            for dict_type, possible_filenames in dictionary_files.items():
                loaded = False
                for filename in possible_filenames:
                    filepath = os.path.join(self.dictionary_path, filename)
                    if os.path.exists(filepath):
                        for encoding in encodings_to_try:
                            try:
                                df = pd.read_csv(filepath, encoding=encoding)
                                if len(df.columns) > 0 and len(df) > 0:
                                    self._process_dictionary_file(dict_type, df)
                                    loaded_count += 1
                                    loaded = True
                                    logger.info(f"Loaded {dict_type}: {len(df)} records from {filename} (encoding: {encoding})", "VALIDATOR")
                                    break
                            except Exception as e:
                                logger.warning(f"Failed to load {filename} with {encoding}: {e}", "VALIDATOR")
                        if loaded:
                            break
                
                if not loaded:
                    logger.warning(f"Could not load {dict_type} dictionary", "VALIDATOR")
            
            self.dictionary_loaded = loaded_count > 0
            logger.info(f"Dictionary loading complete: {loaded_count} files loaded", "VALIDATOR")
            
        except Exception as e:
            logger.error(f"Error loading dictionaries: {e}", "VALIDATOR")
            self.dictionary_loaded = False
    
    def _initialize_ai_patterns(self):
        """Initialize AI fallback patterns"""
        # Name standardization mappings (fallback)
        self.ai_name_standardizations = {
            'bill': 'william', 'bob': 'robert', 'dick': 'richard', 'jim': 'james',
            'joe': 'joseph', 'mike': 'michael', 'steve': 'steven', 'dave': 'david',
            'tom': 'thomas', 'tony': 'anthony', 'chris': 'christopher', 'matt': 'matthew',
            'dan': 'daniel', 'sam': 'samuel', 'alex': 'alexander', 'ben': 'benjamin',
            'nick': 'nicholas', 'rick': 'richard', 'will': 'william', 'tim': 'timothy',
            'pat': 'patricia', 'sue': 'susan', 'liz': 'elizabeth', 'kate': 'katherine',
            'beth': 'elizabeth', 'anne': 'ann', 'maggie': 'margaret', 'peg': 'margaret',
            'jen': 'jennifer', 'jenn': 'jennifer', 'amy': 'amelia', 'becky': 'rebecca'
        }
        
        # Common prefixes and suffixes (fallback)
        self.ai_prefixes = {
            'mr', 'mrs', 'ms', 'miss', 'dr','drs', 'prof', 'professor', 'rev', 'reverend',
            'father', 'mother', 'sister', 'brother', 'sir', 'lady', 'lord', 'dame',
            'capt', 'captain', 'col', 'colonel', 'maj', 'major', 'lt', 'lieutenant',
            'sgt', 'sergeant', 'gen', 'general', 'admiral', 'judge', 'justice'
        }
        
        self.ai_suffixes = {
            'jr', 'sr', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x',
            'md', 'phd', 'edd', 'jd', 'cpa', 'dds', 'dvm', 'rn', 'lpn', 'pa',
            'esq', 'esquire', 'pe', 'cpe', 'cfa', 'mba', 'ms', 'ma', 'bs', 'ba'
        }
        
        # Organization indicators (fallback)
        self.ai_org_indicators = {
            'llc', 'inc', 'corp', 'corporation', 'company', 'ltd', 'limited', 'co.',
            'hospital', 'medical', 'clinic', 'center', 'centre', 'services', 'solutions',
            'group', 'partners', 'associates', 'firm', 'office', 'bank', 'trust',
            'foundation', 'institute', 'university', 'college', 'school', 'academy','jtly','jointly'
        }

        def _process_dictionary_file(self, dict_type: str, df: pd.DataFrame):
            """Process different types of dictionary files"""
            try:
                if dict_type == 'first_names':
                    name_col = df.columns[0]
                    self.first_names_set = set(df[name_col].str.lower().dropna())
                
                elif dict_type == 'surnames':
                    name_col = df.columns[0]
                    self.surnames_set = set(df[name_col].str.lower().dropna())
                
                elif dict_type == 'gender' and len(df.columns) >= 2:
                    name_col, gender_col = df.columns[0], df.columns[1]
                    for _, row in df.iterrows():
                        if pd.notna(row[name_col]) and pd.notna(row[gender_col]):
                            self.name_to_gender[row[name_col].lower()] = row[gender_col].upper()
                
                elif dict_type == 'nicknames' and len(df.columns) >= 2:
                    nickname_col, standard_col = df.columns[0], df.columns[1]
                    for _, row in df.iterrows():
                        if pd.notna(row[nickname_col]) and pd.notna(row[standard_col]):
                            self.nickname_to_standard[row[nickname_col].lower()] = row[standard_col].title()
                
                elif dict_type == 'business':
                    word_col = df.columns[0]
                    self.business_words_set = set(df[word_col].str.lower().dropna())
                
                elif dict_type == 'suffixes':
                    suffix_col = df.columns[0]
                    self.company_suffixes_set = set(df[suffix_col].str.lower().dropna())
                
                elif dict_type == 'prefixes':
                    prefix_col = df.columns[0]
                    self.name_prefixes_set = set(df[prefix_col].str.lower().dropna())
                    
            except Exception as e:
                logger.error(f"Error processing {dict_type} dictionary: {e}", "VALIDATOR")
    
    def validate(self, first_name: str, last_name: str) -> Dict:
        """Enhanced validation with dictionary lookup and AI fallback"""
        start_time = time.time()
        
        result = {
            'valid': False,
            'confidence': 0.0,
            'errors': [],
            'warnings': [],
            'suggestions': {},
            'normalized': {
                'first_name': first_name.strip().title() if first_name else '',
                'last_name': last_name.strip().title() if last_name else ''
            },
            'analysis': {
                'first_name': {
                    'found_in_dictionary': False,
                    'confidence': 0.0,
                    'method': 'unknown'
                },
                'last_name': {
                    'found_in_dictionary': False,
                    'confidence': 0.0,
                    'method': 'unknown'
                }
            },
            'validation_method': 'ai_fallback'
        }
        
        # Basic validation
        if not first_name or not first_name.strip():
            result['errors'].append("First name required")
        if not last_name or not last_name.strip():
            result['errors'].append("Last name required")
        
        if result['errors']:
            result['processing_time_ms'] = int((time.time() - start_time) * 1000)
            return result
        
        # Dictionary lookup if available
        if self.dictionary_loaded:
            first_in_dict = first_name.strip().lower() in self.first_names_set
            last_in_dict = last_name.strip().lower() in self.surnames_set
            
            # First name analysis
            if first_in_dict:
                result['analysis']['first_name']['found_in_dictionary'] = True
                result['analysis']['first_name']['confidence'] = 0.95
                result['analysis']['first_name']['method'] = 'dictionary_lookup'
            else:
                # AI fallback for first name
                result['analysis']['first_name']['method'] = 'ai_pattern_matching'
                result['analysis']['first_name']['confidence'] = self._ai_name_confidence(first_name)
            
            # Last name analysis
            if last_in_dict:
                result['analysis']['last_name']['found_in_dictionary'] = True
                result['analysis']['last_name']['confidence'] = 0.95
                result['analysis']['last_name']['method'] = 'dictionary_lookup'
            else:
                # AI fallback for last name
                result['analysis']['last_name']['method'] = 'ai_pattern_matching'
                result['analysis']['last_name']['confidence'] = self._ai_name_confidence(last_name)
            
            # Determine overall validation method
            if first_in_dict and last_in_dict:
                result['validation_method'] = 'deterministic'
            elif first_in_dict or last_in_dict:
                result['validation_method'] = 'hybrid'
            else:
                result['validation_method'] = 'ai_fallback'
        
        else:
            # Pure AI fallback
            result['analysis']['first_name']['confidence'] = self._ai_name_confidence(first_name)
            result['analysis']['first_name']['method'] = 'ai_pattern_matching'
            result['analysis']['last_name']['confidence'] = self._ai_name_confidence(last_name)
            result['analysis']['last_name']['method'] = 'ai_pattern_matching'
            result['validation_method'] = 'ai_fallback'
        
        # Additional validation
        if first_name and len(first_name.strip()) < 2:
            result['warnings'].append("First name seems short")
        if last_name and len(last_name.strip()) < 2:
            result['warnings'].append("Last name seems short")
        
        # Set validity and confidence
        result['valid'] = len(result['errors']) == 0
        
        if result['valid']:
            # Calculate overall confidence
            first_conf = result['analysis']['first_name']['confidence']
            last_conf = result['analysis']['last_name']['confidence']
            result['confidence'] = (first_conf + last_conf) / 2
        else:
            result['confidence'] = 0.0
        
        result['processing_time_ms'] = int((time.time() - start_time) * 1000)
        return result
    
    def _ai_name_confidence(self, name: str) -> float:
        """Calculate confidence for AI pattern matching"""
        if not name:
            return 0.0
        
        confidence = 0.5  # Base confidence for AI
        
        # Length-based confidence
        if 2 <= len(name) <= 15:
            confidence += 0.2
        
        # Character pattern confidence
        if re.match(r'^[A-Za-z\-\']+$', name):
            confidence += 0.1
        
        # Common pattern recognition
        if name.lower() in ['john', 'jane', 'smith', 'johnson', 'williams', 'brown', 'jones']:
            confidence += 0.2
        
        return min(confidence, 0.8)  # Cap AI confidence at 80%
    
    def validate_name_record(self, record: Dict) -> Dict:
        """Enhanced name record validation with new format"""
        start_time = time.time()
        
        unique_id = record.get('uniqueID', '')
        full_name = record.get('fullName', '').strip()
        gender_cd = record.get('genderCd', '').strip().upper()
        party_type_cd = record.get('partyTypeCd', '').strip().upper()
        parse_ind = record.get('parseInd', '').strip().upper()
        
        # Initialize result structure
        result = {
            'uniqueID': unique_id,
            'partyTypeCd': '',
            'prefix': None,
            'firstName': None,
            'firstNameStd': None,
            'middleName': None,
            'lastName': None,
            'suffix': None,
            'fullName': full_name,
            'inGenderCd': gender_cd,
            'outGenderCd': '',
            'prefixLt': None,
            'firstNameLt': None,
            'middleNameLt': None,
            'lastNameLt': None,
            'suffixLt': None,
            'parseInd': parse_ind if parse_ind else 'Y',
            'confidenceScore': '0.0',
            'parseStatus': 'Error',
            'errorMessage': 'Processing error',
            'validationMethod': 'unknown'
        }
        
        try:
            # Step 1: Determine if organization or individual
            is_org, org_confidence, org_method = self._determine_organization(full_name, party_type_cd)
            
            if is_org:
                result['partyTypeCd'] = 'O'
                result['outGenderCd'] = ''
                result['parseStatus'] = 'Organization'
                result['errorMessage'] = 'Valid Organization'
                result['confidenceScore'] = f"{org_confidence:.4f}"
                result['validationMethod'] = org_method
                return result
            else:
                result['partyTypeCd'] = 'I'
            
            # Step 2: Parse the name if indicated
            if result['parseInd'] == 'Y':
                parsed = self._enhanced_parse_name(full_name)
                
                result['prefix'] = parsed['prefix']
                result['firstName'] = parsed['first_name']
                result['middleName'] = parsed['middle_name']
                result['lastName'] = parsed['last_name']
                result['suffix'] = parsed['suffix']
                
                # Create literal (uppercase) versions
                result['prefixLt'] = parsed['prefix'].upper() if parsed['prefix'] else None
                result['firstNameLt'] = parsed['first_name'].upper() if parsed['first_name'] else None
                result['middleNameLt'] = parsed['middle_name'].upper() if parsed['middle_name'] else None
                result['lastNameLt'] = parsed['last_name'].upper() if parsed['last_name'] else None
                result['suffixLt'] = parsed['suffix'].upper() if parsed['suffix'] else None
                
                # Step 3: Standardize first name
                if parsed['first_name']:
                    result['firstNameStd'] = self._standardize_name(parsed['first_name'])
                
                # Step 4: Predict gender if not provided
                if not gender_cd and parsed['first_name']:
                    predicted_gender = self._predict_gender(parsed['first_name'])
                    result['outGenderCd'] = predicted_gender
                else:
                    result['outGenderCd'] = gender_cd
                
                # Step 5: Calculate confidence and determine method
                confidence, validation_method = self._calculate_confidence(parsed, result['outGenderCd'])
                result['confidenceScore'] = f"{confidence:.4f}"
                result['validationMethod'] = validation_method
                
                if confidence >= 90:
                    result['parseStatus'] = 'Parsed'
                    result['errorMessage'] = 'Dictionary Validated' if 'deterministic' in validation_method else 'Probably Valid'
                elif confidence >= 70:
                    result['parseStatus'] = 'Parsed'
                    result['errorMessage'] = 'Possibly Valid'
                else:
                    result['parseStatus'] = 'Warning'
                    result['errorMessage'] = 'Low Confidence'
                    
            else:
                # No parsing requested
                result['parseStatus'] = 'Not Parsed'
                result['errorMessage'] = 'Parsing not requested'
                result['confidenceScore'] = '80.0'
                result['outGenderCd'] = gender_cd
                result['validationMethod'] = 'no_parse'
            
        except Exception as e:
            logger.error(f"Error validating name record: {e}", "VALIDATOR")
            result['parseStatus'] = 'Error'
            result['errorMessage'] = f'Processing error: {str(e)}'
            result['confidenceScore'] = '0.0'
            result['validationMethod'] = 'error'
        
        processing_time = int((time.time() - start_time) * 1000)
        logger.info(f"Name validation completed in {processing_time}ms - method: {result.get('validationMethod')}", "VALIDATOR")
        
        return result
    
    def _determine_organization(self, full_name: str, party_type_hint: str = '') -> Tuple[bool, float, str]:
        """Determine if name is organization with dictionary lookup + AI fallback"""
        if not full_name:
            return False, 0.0, 'empty_name'
        
        # If explicitly marked
        if party_type_hint == 'O':
            return True, 99.0, 'explicit_org'
        elif party_type_hint == 'I':
            return False, 99.0, 'explicit_individual'
        
        name_lower = full_name.lower()
        
        # Dictionary lookup first
        if self.dictionary_loaded:
            # Check company suffixes
            if self.company_suffixes_set:
                for suffix in self.company_suffixes_set:
                    if suffix in name_lower:
                        return True, 95.0, 'deterministic_suffix'
            
            # Check business words
            if self.business_words_set:
                name_words = set(name_lower.split())
                if name_words.intersection(self.business_words_set):
                    return True, 92.0, 'deterministic_business_word'
            
            # Check against individual name patterns
            name_parts = name_lower.split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = name_parts[-1]
                
                if (first_name in self.first_names_set and last_name in self.surnames_set):
                    return False, 94.0, 'deterministic_individual'
        
        # AI fallback
        return self._ai_organization_detection(name_lower)
    
    def _ai_organization_detection(self, name_lower: str) -> Tuple[bool, float, str]:
        """AI fallback for organization detection"""
        org_score = 0
        
        # Pattern matching
        for indicator in self.ai_org_indicators:
            if indicator in name_lower:
                org_score += 10
        
        if re.search(r'\b(llc|inc|corp|ltd)\b', name_lower):
            org_score += 15
        
        # Length-based scoring
        if len(name_lower.split()) > 3:
            org_score += 5
        
        # Personal name patterns (negative scoring)
        personal_patterns = [
            r'\b(mr|mrs|ms|dr)\s+[a-z]+\s+[a-z]+\b',
            r'\b[a-z]+\s+(jr|sr|ii|iii)\b'
        ]
        
        for pattern in personal_patterns:
            if re.search(pattern, name_lower):
                org_score -= 8
        
        is_org = org_score > 10
        confidence = min(80.0, 50.0 + abs(org_score) * 2)  # AI confidence capped at 80%
        
        return is_org, confidence, 'ai_pattern_matching'
    
    def _enhanced_parse_name(self, full_name: str) -> Dict[str, str]:
        """Enhanced name parsing with dictionary lookup for prefixes/suffixes"""
        if not full_name or not full_name.strip():
            return {
                'prefix': '', 'first_name': '', 'middle_name': '',
                'last_name': '', 'suffix': ''
            }
        
        # Clean and normalize
        name = re.sub(r'[^\w\s\.]', ' ', full_name)
        name = ' '.join(name.split())
        
        parts = name.split()
        
        prefix = ''
        suffix = ''
        name_parts = parts[:]
        
        # Extract prefix (dictionary lookup first)
        if parts:
            first_part = parts[0].lower().rstrip('.')
            
            if self.dictionary_loaded and self.name_prefixes_set:
                if first_part in self.name_prefixes_set:
                    prefix = parts[0].rstrip('.')
                    name_parts = parts[1:]
            elif first_part in self.ai_prefixes:
                prefix = parts[0].rstrip('.')
                name_parts = parts[1:]
        
        # Extract suffix (dictionary/AI fallback)
        if name_parts:
            last_part = name_parts[-1].lower().rstrip('.')
            
            # Use AI suffixes as fallback
            if last_part in self.ai_suffixes:
                suffix = name_parts[-1].rstrip('.')
                name_parts = name_parts[:-1]
        
        # Parse remaining name parts
        if len(name_parts) == 0:
            return {'prefix': prefix, 'first_name': '', 'middle_name': '', 
                   'last_name': '', 'suffix': suffix}
        elif len(name_parts) == 1:
            return {'prefix': prefix, 'first_name': name_parts[0], 'middle_name': '', 
                   'last_name': '', 'suffix': suffix}
        elif len(name_parts) == 2:
            return {'prefix': prefix, 'first_name': name_parts[0], 'middle_name': '', 
                   'last_name': name_parts[1], 'suffix': suffix}
        else:
            return {
                'prefix': prefix,
                'first_name': name_parts[0],
                'middle_name': ' '.join(name_parts[1:-1]),
                'last_name': name_parts[-1],
                'suffix': suffix
            }
    
    def _standardize_name(self, name: str) -> str:
        """Standardize name with dictionary lookup + AI fallback"""
        if not name:
            return ''
        
        name_lower = name.lower()
        
        # Dictionary lookup first
        if self.dictionary_loaded and self.nickname_to_standard:
            if name_lower in self.nickname_to_standard:
                return self.nickname_to_standard[name_lower]
        
        # AI fallback
        if name_lower in self.ai_name_standardizations:
            return self.ai_name_standardizations[name_lower].title()
        
        return name.title()
    
    def _predict_gender(self, first_name: str) -> str:
        """Predict gender with dictionary lookup + AI fallback"""
        if not first_name:
            return ''
        
        name_lower = first_name.lower()
        
        # Dictionary lookup first
        if self.dictionary_loaded and self.name_to_gender:
            if name_lower in self.name_to_gender:
                return self.name_to_gender[name_lower]
        
        # AI fallback
        return self._ai_gender_prediction(name_lower)
    
    def _ai_gender_prediction(self, name_lower: str) -> str:
        """AI fallback for gender prediction"""
        gender_score = 0
        
        # Female patterns
        if name_lower.endswith(('a', 'ia', 'ana', 'ella', 'ina', 'lyn', 'lynn', 'elle', 'ette')):
            gender_score -= 3
        
        if name_lower.endswith(('y', 'ie', 'ey')):
            gender_score -= 1
        
        # Male patterns
        if name_lower.endswith(('er', 'on', 'an', 'en', 'son', 'ton', 'man')):
            gender_score += 2
        
        if name_lower.endswith(('ck', 'x', 'z')):
            gender_score += 1
        
        # Common names (basic fallback)
        common_female = {
            'mary', 'jennifer', 'patricia', 'linda', 'barbara', 'susan', 'jessica',
            'sarah', 'karen', 'nancy', 'lisa', 'betty', 'helen', 'sandra', 'donna'
        }
        
        common_male = {
            'james', 'john', 'robert', 'michael', 'william', 'david', 'richard',
            'charles', 'joseph', 'thomas', 'christopher', 'daniel', 'paul', 'mark'
        }
        
        if name_lower in common_female:
            return 'F'
        elif name_lower in common_male:
            return 'M'
        
        # Pattern-based prediction
        if gender_score <= -2:
            return 'F'
        elif gender_score >= 2:
            return 'M'
        
        return ''
    
    def _calculate_confidence(self, parsed: Dict, predicted_gender: str) -> Tuple[float, str]:
        """Calculate confidence and determine validation method"""
        
        method_scores = {'deterministic': 0, 'hybrid': 0, 'ai': 0}
        confidence = 50.0  # Base confidence
        
        # Check first name
        if parsed['first_name']:
            if self.dictionary_loaded and parsed['first_name'].lower() in self.first_names_set:
                method_scores['deterministic'] += 1
                confidence += 20
            else:
                method_scores['ai'] += 1
                confidence += 10
        
        # Check last name
        if parsed['last_name']:
            if self.dictionary_loaded and parsed['last_name'].lower() in self.surnames_set:
                method_scores['deterministic'] += 1
                confidence += 20
            else:
                method_scores['ai'] += 1
                confidence += 10
        
        # Check gender prediction
        if predicted_gender:
            if (self.dictionary_loaded and parsed['first_name'] and 
                parsed['first_name'].lower() in self.name_to_gender):
                method_scores['deterministic'] += 1
                confidence += 10
            else:
                method_scores['ai'] += 1
                confidence += 5
        
        # Determine overall method
        if method_scores['deterministic'] > method_scores['ai']:
            overall_method = 'deterministic'
            confidence = min(confidence, 99.0)
        elif method_scores['deterministic'] == method_scores['ai'] and method_scores['deterministic'] > 0:
            overall_method = 'hybrid'
            confidence = min(confidence, 90.0)
        else:
            overall_method = 'ai_fallback'
            confidence = min(confidence, 80.0)
        
        return confidence, overall_method
    
    def parse_full_name(self, full_name: str) -> Dict[str, str]:
        """Parse full name into components (legacy compatibility)"""
        parsed = self._enhanced_parse_name(full_name)
        return {
            'first_name': parsed['first_name'],
            'last_name': parsed['last_name'],
            'middle_name': parsed['middle_name']
        }
    
    def is_organization(self, name: str) -> bool:
        """Check if name appears to be an organization (legacy compatibility)"""
        is_org, _, _ = self._determine_organization(name)
        return is_org
    
    def predict_gender(self, first_name: str) -> str:
        """Simple gender prediction (legacy compatibility)"""
        return self._predict_gender(first_name)


class AddressValidator:
    """Enhanced USPS Address Validator with batch processing and CSV standardization"""
    
    def __init__(self):
        
        self.client_id, self.client_secret = load_usps_credentials()
        self._access_token = None
        self._token_expires_at = 0
        
        # Add US States for validation - ADD THIS
        self.US_STATES = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        }
        
        logger.info(f"Address validator initialized - configured: {self.is_configured()}", "VALIDATOR")

    
    def is_configured(self) -> bool:
        """Check if USPS credentials are available"""
        return bool(self.client_id and self.client_secret)
    
    def get_access_token(self) -> Optional[str]:
        """Get USPS access token"""
        if not self.is_configured():
            return None
        
        # Check cached token
        if (self._access_token and time.time() < (self._token_expires_at - 300)):
            return self._access_token
        
        # Get new token
        try:
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            }
            
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'addresses'
            }
            
            response = requests.post(Config.USPS_AUTH_URL, headers=headers, data=data, timeout=15)
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data.get('access_token')
                expires_in = token_data.get('expires_in', 3600)
                self._token_expires_at = time.time() + expires_in
                logger.info("USPS token obtained", "USPS")
                return self._access_token
            else:
                logger.error(f"USPS auth failed: {response.status_code}", "USPS")
                return None
                
        except Exception as e:
            logger.error(f"USPS auth error: {e}", "USPS")
            return None
    
    def standardize_csv_to_address_format(self, df: pd.DataFrame) -> List[Dict]:
        """Standardize heterogeneous CSV formats to standard address format"""
        logger.info(f"Standardizing CSV with {len(df)} rows to address format", "VALIDATOR")
        
        # Define possible column mappings for different CSV formats
        column_mappings = {
            'guid': ['guid', 'id', 'unique_id', 'record_id', 'address_id', 'idx', 'index'],
            'line1': ['line1', 'address_line_1', 'address1', 'street_address', 'street', 'addr1', 'address'],
            'line2': ['line2', 'address_line_2', 'address2', 'apartment', 'apt', 'suite', 'unit', 'addr2'],
            'city': ['city', 'town', 'municipality'],
            'stateCd': ['state_cd', 'state', 'state_code', 'st', 'province'],
            'zipCd': ['zip_cd', 'zip', 'zip_code', 'postal_code', 'zipcode', 'postcode'],
            'countryCd': ['country_cd', 'country', 'country_code']
        }
        
        # Find matching columns
        field_mappings = {}
        available_columns = [col.lower().replace(' ', '_') for col in df.columns]
        
        for target_field, possible_names in column_mappings.items():
            for possible_name in possible_names:
                if possible_name in available_columns:
                    original_col = df.columns[available_columns.index(possible_name)]
                    field_mappings[target_field] = original_col
                    break
        
        logger.info(f"Column mappings found: {field_mappings}", "VALIDATOR")
        
        # Convert to standard format
        standardized_addresses = []
        
        for idx, row in df.iterrows():
            address = {
                'guid': str(row.get(field_mappings.get('guid', ''), idx + 1)),
                'line1': str(row.get(field_mappings.get('line1', ''), '')).strip() or None,
                'line2': str(row.get(field_mappings.get('line2', ''), '')).strip() or None,
                'line3': None,
                'line4': None,
                'line5': None,
                'city': str(row.get(field_mappings.get('city', ''), '')).strip(),
                'stateCd': str(row.get(field_mappings.get('stateCd', ''), '')).strip().upper(),
                'zipCd': str(row.get(field_mappings.get('zipCd', ''), '')).strip(),
                'countryCd': str(row.get(field_mappings.get('countryCd', ''), 'US')).strip().upper(),
                'verificationInd': 'Y',
                'onlyOneAddrInd': 'N'
            }
            
            # Clean up empty strings to None
            for key in ['line1', 'line2', 'city', 'stateCd', 'zipCd']:
                if address[key] == '' or address[key] == 'nan':
                    if key in ['city', 'stateCd', 'zipCd']:
                        address[key] = ''  # Required fields should be empty string, not None
                    else:
                        address[key] = None
            
            standardized_addresses.append(address)
        
        logger.info(f"Standardized {len(standardized_addresses)} addresses", "VALIDATOR")
        return standardized_addresses
    
    def validate_addresses_batch(self, addresses: List[Dict]) -> List[Dict]:
        """Validate multiple addresses"""
        logger.info(f"Batch validating {len(addresses)} addresses", "VALIDATOR")
        
        results = []
        
        for address in addresses:
            try:
                result = self.validate_single_address(address)
                results.append(result)
            except Exception as e:
                logger.error(f"Error validating address {address.get('guid', 'unknown')}: {e}", "VALIDATOR")
                # Create error result
                error_result = self._create_error_result(address, str(e))
                results.append(error_result)
        
        logger.info(f"Batch validation completed: {len(results)} results", "VALIDATOR")
        return results
    
    def validate_single_address(self, address_data: Dict) -> Dict:
        """Validate a single address using USPS API and return enhanced format"""
        
        if not self.is_configured():
            return self._create_error_result(address_data, 'USPS API not configured')
        
        access_token = self.get_access_token()
        if not access_token:
            return self._create_error_result(address_data, 'Failed to get access token')
        
        # Extract and validate required fields
        line1 = address_data.get('line1', '').strip()
        city = address_data.get('city', '').strip()
        state_cd = address_data.get('stateCd', '').strip().upper()
        zip_cd = str(address_data.get('zipCd', '')).strip()
        
        if not all([line1, city, state_cd, zip_cd]):
            missing = []
            if not line1: missing.append('line1')
            if not city: missing.append('city')
            if not state_cd: missing.append('stateCd')
            if not zip_cd: missing.append('zipCd')
            
            return self._create_error_result(address_data, f"Missing required fields: {', '.join(missing)}")
        
        # Parse street address for apartment/unit
        street_parts = self._parse_street_address(line1)
        
        # Build query parameters for USPS API
        params = {
            'streetAddress': street_parts['street'].upper(),
            'city': city.upper(),
            'state': state_cd.upper(),
            'ZIPCode': zip_cd[:5]
        }
        
        if street_parts['unit']:
            params['secondaryAddress'] = street_parts['unit'].upper()
        
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(Config.USPS_VALIDATE_URL, headers=headers, params=params, timeout=15)
            
            if response.status_code == 200:
                return self._parse_usps_success_response(response.json(), address_data)
            elif response.status_code == 400:
                return self._create_error_result(address_data, 'Invalid address format')
            elif response.status_code == 404:
                return self._create_error_result(address_data, 'Address not found')
            else:
                return self._create_error_result(address_data, f'API error: HTTP {response.status_code}')
                
        except Exception as e:
            logger.error(f"USPS validation error: {e}", "USPS")
            return self._create_error_result(address_data, 'Validation request failed')
    
    def _parse_street_address(self, address: str) -> Dict[str, str]:
        """Parse street address into main and unit components"""
        if not address:
            return {'street': '', 'unit': ''}
        
        # Normalize whitespace
        address = ' '.join(address.split())
        
        # Common unit patterns
        unit_patterns = [
            r'\s+(apartment|apt|suite|ste|unit|#)\s*\.?\s*([a-z0-9\-]+)$',
            r'\s+([0-9]+[a-z]{1,2})$',  # Like "4B", "12A"
            r'\s+#([a-z0-9\-]+)$'       # "#123"
        ]
        
        for pattern in unit_patterns:
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                unit_start = match.start()
                street_part = address[:unit_start].strip()
                unit_part = match.group(0).strip()
                return {'street': street_part, 'unit': unit_part}
        
        return {'street': address, 'unit': ''}
    
    def _parse_usps_success_response(self, response_data: Dict, original_address: Dict) -> Dict:
        """Parse successful USPS response into enhanced format"""
        
        if not response_data.get('address'):
            return self._create_error_result(original_address, 'No address data in response')
        
        address = response_data.get('address', {})
        additional_info = response_data.get('additionalInfo', {})
        
        # Build enhanced result
        result = {
            'guid': original_address.get('guid', ''),
            'line1': original_address.get('line1'),
            'line2': original_address.get('line2'),
            'line3': original_address.get('line3'),
            'line4': original_address.get('line4'),
            'line5': original_address.get('line5'),
            
            # Delivery address (standardized by USPS)
            'deliveryAddressLine1': address.get('streetAddress', ''),
            'deliveryAddressLine2': address.get('secondaryAddress'),
            'deliveryAddressLine3': None,
            'deliveryAddressLine4': None,
            'deliveryAddressLine5': None,
            
            # Location information
            'city': address.get('city', ''),
            'stateCd': address.get('state', ''),
            'zipCd': address.get('ZIPCode', ''),
            'zipCd4': address.get('ZIPPlus4'),
            'zipCdComplete': f"{address.get('ZIPCode', '')}-{address.get('ZIPPlus4', '')}" if address.get('ZIPPlus4') else address.get('ZIPCode', ''),
            
            # Enhanced address information
            'countyName': additional_info.get('county', '').upper() if additional_info.get('county') else None,
            'countyCd': additional_info.get('countyFIPS'),
            'countryName': 'UNITED STATES',
            'countryCd': 'US',
            
            # Validation scores and codes
            'mailabilityScore': '1' if additional_info.get('DPVConfirmation') in ['Y', 'D'] else '0',
            'mailabilityScoreDesc': None,
            'matchCode': self._determine_match_code(additional_info),
            'matchCodeDesc': None,
            'CASSErrorCode': None,
            
            # Additional USPS data
            'barcode': additional_info.get('barcode'),
            'carrierRoute': additional_info.get('carrierRoute'),
            'congressionalDistrict': additional_info.get('congressionalDistrict'),
            'deliveryPointCd': additional_info.get('deliveryPoint'),
            'zipMoveReturnCd': None,
            'CASSERPStatus': None,
            'residentialDeliveryIndicator': 'Y' if additional_info.get('business', 'N') == 'N' else 'N',
            
            # Coordinates (if available)
            'latitude': None,
            'longitude': None,
            
            # Status
            'errorMsg': None,
            'completeAddress': f"{address.get('streetAddress', '')} {address.get('secondaryAddress', '')}".strip(),
            
            # Input echo
            'inLine1': original_address.get('line1'),
            'inLine2': original_address.get('line2'),
            'inLine3': original_address.get('line3'),
            'inLine4': original_address.get('line4'),
            'inLine5': original_address.get('line5'),
            'inLine6': original_address.get('city'),
            'inLine7': original_address.get('stateCd'),
            'inLine8': original_address.get('zipCd'),
            'inCountryCd': original_address.get('countryCd'),
            'inVerificationInd': original_address.get('verificationInd'),
            'inOnlyOneAddrInd': original_address.get('onlyOneAddrInd'),
            
            # Additional fields
            'RecipientLine1': None,
            'RecipientLine2': None,
            'ResidueSuperfluous1': None,
            'ResidueSuperfluous2': None,
            'ResultPercentage': '100.00' if additional_info.get('DPVConfirmation') in ['Y', 'D'] else '50.00'
        }
        
        return result
    
    def _determine_match_code(self, additional_info: Dict) -> str:
        """Determine match code based on USPS response"""
        dpv_confirmation = additional_info.get('DPVConfirmation', '')
        
        if dpv_confirmation == 'Y':
            return 'A1'  # Exact match
        elif dpv_confirmation == 'D':
            return 'B1'  # Default match
        elif dpv_confirmation == 'N':
            return 'C3'  # No match
        else:
            return 'C3'  # Default to no match
    
    def _create_error_result(self, original_address: Dict, error_message: str) -> Dict:
        """Create error result in enhanced format"""
        return {
            'guid': original_address.get('guid', ''),
            'line1': original_address.get('line1'),
            'line2': original_address.get('line2'),
            'line3': original_address.get('line3'),
            'line4': original_address.get('line4'),
            'line5': original_address.get('line5'),
            'deliveryAddressLine1': None,
            'deliveryAddressLine2': None,
            'deliveryAddressLine3': None,
            'deliveryAddressLine4': None,
            'deliveryAddressLine5': None,
            'city': original_address.get('city'),
            'stateCd': original_address.get('stateCd'),
            'zipCd': original_address.get('zipCd'),
            'zipCd4': None,
            'zipCdComplete': original_address.get('zipCd'),
            'countyName': None,
            'countyCd': None,
            'countryName': None,
            'countryCd': original_address.get('countryCd'),
            'mailabilityScore': '0',
            'mailabilityScoreDesc': None,
            'matchCode': 'E1',  # Error code
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
            'errorMsg': error_message,
            'completeAddress': None,
            'inLine1': original_address.get('line1'),
            'inLine2': original_address.get('line2'),
            'inLine3': original_address.get('line3'),
            'inLine4': original_address.get('line4'),
            'inLine5': original_address.get('line5'),
            'inLine6': original_address.get('city'),
            'inLine7': original_address.get('stateCd'),
            'inLine8': original_address.get('zipCd'),
            'inCountryCd': original_address.get('countryCd'),
            'inVerificationInd': original_address.get('verificationInd'),
            'inOnlyOneAddrInd': original_address.get('onlyOneAddrInd'),
            'RecipientLine1': None,
            'RecipientLine2': None,
            'ResidueSuperfluous1': None,
            'ResidueSuperfluous2': None,
            'ResultPercentage': '0.00'
        }
    
    # Legacy method for backward compatibility
    def validate_address(self, address_data: Dict) -> Dict:
        """Legacy address validation method"""
        # Convert legacy format to new format
        new_format = {
            'guid': '1',
            'line1': address_data.get('street_address', ''),
            'line2': None,
            'line3': None,
            'line4': None,
            'line5': None,
            'city': address_data.get('city', ''),
            'stateCd': address_data.get('state', ''),
            'zipCd': str(address_data.get('zip_code', '')),
            'countryCd': 'US',
            'verificationInd': 'Y',
            'onlyOneAddrInd': 'N'
        }
        
        result = self.validate_single_address(new_format)
        
        # Convert back to legacy format
        is_deliverable = result.get('mailabilityScore') == '1'
        
        return {
            'success': result.get('errorMsg') is None,
            'valid': is_deliverable,
            'deliverable': is_deliverable,
            'standardized': {
                'street_address': result.get('deliveryAddressLine1', ''),
                'city': result.get('city', ''),
                'state': result.get('stateCd', ''),
                'zip_code': result.get('zipCdComplete', '')
            },
            'metadata': {
                'business': result.get('residentialDeliveryIndicator') == 'N',
                'vacant': False,  # Not provided by enhanced format
                'centralized': False,  # Not provided by enhanced format
                'carrier_route': result.get('carrierRoute', ''),
                'delivery_point': result.get('deliveryPointCd', ''),
                'dpv_confirmation': 'Y' if is_deliverable else 'N'
            },
            'confidence': 0.95 if is_deliverable else 0.3,
            'validation_method': 'usps_api_v3',
            'error': result.get('errorMsg')
        }