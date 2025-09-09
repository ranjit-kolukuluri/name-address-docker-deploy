# ui/app.py
"""
Complete Professional Streamlit UI for name and address validation with enhanced state name/code support
"""

import streamlit as st
import pandas as pd
import json
import time
import re  # Added for enhanced address categorization
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path
current_file = Path(__file__).resolve()
parent_dir = current_file.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.services import ValidationService
from utils.logger import logger


class ValidatorApp:
    """Complete Professional Streamlit application with enhanced state name/code support"""
    
    def __init__(self):
        self.service = ValidationService()
        
        # Initialize session state
        if 'validation_results' not in st.session_state:
            st.session_state.validation_results = []
        
        if 'processing_stats' not in st.session_state:
            st.session_state.processing_stats = {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'deterministic': 0,
                'hybrid': 0,
                'ai_fallback': 0
            }
        
        if 'address_stats' not in st.session_state:
            st.session_state.address_stats = {
                'total_validated': 0,
                'successful': 0,
                'failed': 0
            }
        
        # Enhanced State name to code mapping
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
            'fla': 'FL', 'florida': 'FL',
            'tex': 'TX', 'texas': 'TX',
            'penn': 'PA', 'penna': 'PA',
            'mass': 'MA', 'massachusetts': 'MA',
            'conn': 'CT', 'connecticut': 'CT',
            'wash': 'WA', 'washington': 'WA',
            'ore': 'OR', 'oreg': 'OR',
            'mich': 'MI', 'michigan': 'MI',
            'ill': 'IL', 'illinois': 'IL',
            'ind': 'IN', 'indiana': 'IN',
            'tenn': 'TN', 'tennessee': 'TN',
            'ky': 'KY', 'kentucky': 'KY',
            'la': 'LA', 'louisiana': 'LA',
            'miss': 'MS', 'mississippi': 'MS',
            'ala': 'AL', 'alabama': 'AL',
            'ga': 'GA', 'georgia': 'GA',
            'nc': 'NC', 'n carolina': 'NC', 'n. carolina': 'NC',
            'sc': 'SC', 's carolina': 'SC', 's. carolina': 'SC',
            'nd': 'ND', 'n dakota': 'ND', 'n. dakota': 'ND',
            'sd': 'SD', 's dakota': 'SD', 's. dakota': 'SD',
            'wv': 'WV', 'w virginia': 'WV', 'w. virginia': 'WV',
            'dc': 'DC', 'd.c.': 'DC', 'washington dc': 'DC', 'washington d.c.': 'DC'
        }
        
        # Valid state codes for quick lookup
        self.valid_state_codes = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
        }
    
    def _normalize_state_input(self, state_input):
        """
        Normalize state input to standard 2-letter state code
        Accepts both state names and codes
        Returns: (normalized_code, is_valid, original_input)
        """
        if not state_input or not state_input.strip():
            return '', False, state_input
        
        # Clean the input
        cleaned_input = state_input.strip().lower()
        original_input = state_input.strip()
        
        # Check if it's already a valid state code
        if len(cleaned_input) == 2 and cleaned_input.upper() in self.valid_state_codes:
            return cleaned_input.upper(), True, original_input
        
        # Check if it's a state name or abbreviation
        if cleaned_input in self.state_name_to_code:
            return self.state_name_to_code[cleaned_input], True, original_input
        
        # Try without punctuation
        cleaned_no_punct = cleaned_input.replace('.', '').replace(',', '')
        if cleaned_no_punct in self.state_name_to_code:
            return self.state_name_to_code[cleaned_no_punct], True, original_input
        
        # Not found
        return original_input.upper(), False, original_input
    
    def apply_styling(self):
        """Apply enhanced professional CSS styling"""
        st.markdown("""
        <style>
        /* Main application styling */
        .main {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }
        
        /* Professional header */
        .header {
            background: linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%);
            padding: 3rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            text-align: center;
            color: white;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Ccircle cx='30' cy='30' r='3'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.3;
        }
        
        .title {
            font-size: 3rem;
            font-weight: 800;
            margin-bottom: 1rem;
            letter-spacing: -0.025em;
            position: relative;
            z-index: 1;
        }
        
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
            font-weight: 400;
            position: relative;
            z-index: 1;
        }
        
        /* Professional status indicators */
        .status-success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            display: inline-flex;
            align-items: center;
            margin: 0.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        
        .status-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        .status-warning {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            display: inline-flex;
            align-items: center;
            margin: 0.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
        }
        
        .status-warning:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        
        /* Professional method badges */
        .method-deterministic {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 0.4rem 0.8rem;
            border-radius: 15px;
            font-size: 0.85rem;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .method-hybrid {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: white;
            padding: 0.4rem 0.8rem;
            border-radius: 15px;
            font-size: 0.85rem;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        .method-ai {
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: white;
            padding: 0.4rem 0.8rem;
            border-radius: 15px;
            font-size: 0.85rem;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        
        /* Professional result cards */
        .result-card {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 2rem;
            margin: 1.5rem 0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
        }
        
        .result-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }
        
        /* Professional confidence indicators */
        .confidence-high {
            color: #059669;
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        .confidence-medium {
            color: #d97706;
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        .confidence-low {
            color: #dc2626;
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        /* Professional dictionary status */
        .dict-status {
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border: 1px solid #0ea5e9;
            border-radius: 12px;
            padding: 1.5rem;
            margin: 1.5rem 0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        /* Professional form styling */
        .stTextInput > div > div > input {
            border-radius: 8px;
            border: 2px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        .stSelectbox > div > div > div {
            border-radius: 8px;
            border: 2px solid #e2e8f0;
        }
        
        /* Professional button styling */
        .stButton > button {
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.3s ease;
            border: none;
        }
        
        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        /* Professional metrics */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        
        [data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        /* Professional tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        
        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 0.5rem 1rem;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            color: white;
        }
        
        /* Professional file uploader */
        .stFileUploader > div {
            border-radius: 12px;
            border: 2px dashed #cbd5e1;
            transition: all 0.3s ease;
        }
        
        .stFileUploader > div:hover {
            border-color: #3b82f6;
            background: #f8fafc;
        }
        
        /* Professional dataframe styling */
        .stDataFrame {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        /* Professional expander */
        .streamlit-expanderHeader {
            border-radius: 8px;
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            font-weight: 600;
        }
        
        /* Professional progress bar */
        .stProgress > div > div > div {
            background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
            border-radius: 4px;
        }
        
        /* Professional alerts */
        .stAlert {
            border-radius: 12px;
            border: none;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
    
    def render_header(self):
        """Render enhanced professional application header"""
        name_available = self.service.is_name_validation_available()
        address_available = self.service.is_address_validation_available()
        dict_status = self.service.dictionary_status
        
        st.markdown('''
        <div class="header">
            <div class="title">🚀 Name & Address Validator</div>
            <div class="subtitle">Enterprise-Grade Validation • Dictionary Intelligence • USPS Integration • State Name Support</div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Professional status indicators
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            status_html = ""
            if name_available:
                if dict_status:
                    status_html += '<span class="status-success">🎯 Enhanced Name Validation Active</span>'
                else:
                    status_html += '<span class="status-warning">⚡ AI-Only Name Validation</span>'
            
            if address_available:
                status_html += '<span class="status-success">📮 USPS Address Validation Ready</span>'
            else:
                status_html += '<span class="status-warning">📮 USPS API Configuration Required</span>'
            
            st.markdown(f'<div style="text-align: center;">{status_html}</div>', unsafe_allow_html=True)
        
        # Professional dictionary status panel
        if dict_status:
            stats = self.service._get_dictionary_statistics()
            st.markdown(f'''
            <div class="dict-status">
                <div style="display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 2rem;">
                    <div><strong>📚 Dictionary Engine:</strong> <span style="color: #059669;">Active</span></div>
                    <div><strong>👥 Names:</strong> {stats.get('first_names_count', 0):,}</div>
                    <div><strong>👤 Surnames:</strong> {stats.get('surnames_count', 0):,}</div>
                    <div><strong>⚧ Gender Maps:</strong> {stats.get('gender_mappings_count', 0):,}</div>
                    <div><strong>🏢 Business Terms:</strong> {stats.get('business_words_count', 0):,}</div>
                    <div><strong>🗺️ State Support:</strong> <span style="color: #059669;">Names + Codes</span></div>
                </div>
            </div>
            ''', unsafe_allow_html=True)
    
    def render_name_validation(self):
        """Render enhanced name validation interface"""
        st.markdown("## 👤 Name Validation")
        
        # Single name validation
        with st.expander("Single Name Validation", expanded=True):
            with st.form("single_name_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    full_name = st.text_input("Full Name", placeholder="Enter full name (e.g., Dr. William Smith Jr.)")
                
                with col2:
                    col2a, col2b, col2c = st.columns(3)
                    
                    with col2a:
                        gender_cd = st.selectbox("Gender", ["", "M", "F"], help="Leave empty for AI prediction")
                    
                    with col2b:
                        party_type_cd = st.selectbox("Party Type", ["", "I", "O"], help="I=Individual, O=Organization, empty=AI detection")
                    
                    with col2c:
                        parse_ind = st.selectbox("Parse", ["Y", "N"], help="Y=Parse name components")
                
                submitted = st.form_submit_button("🔍 Validate Name", type="primary")
                
                if submitted and full_name:
                    with st.spinner("Processing with enhanced validation..."):
                        # Create name record
                        name_record = {
                            'uniqueID': '1',
                            'fullName': full_name,
                            'genderCd': gender_cd,
                            'partyTypeCd': party_type_cd,
                            'parseInd': parse_ind
                        }
                        
                        # Validate using enhanced format
                        result = self.service.validate_names({'names': [name_record]})
                        
                        if result['names']:
                            self._display_enhanced_name_result(result['names'][0])
        
        # Enhanced API Testing
       
        # with st.expander("Enhanced API Testing"):
        #     st.markdown("### Test Enhanced API Format")
            
        #     # Get example payload
        #     default_payload = self.service.get_example_payload()
            
        #     json_input = st.text_area(
        #         "JSON Payload (Enhanced Format):",
        #         value=json.dumps(default_payload, indent=2),
        #         height=300
        #     )
            
        #     if st.button("🚀 Test Enhanced API", type="primary"):
        #         try:
        #             payload = json.loads(json_input)
                    
        #             with st.spinner("Processing with dictionary lookup + AI fallback..."):
        #                 result = self.service.validate_names(payload)
                        
        #                 st.success("✅ API request processed successfully")
                        
        #                 # Display results with method information
        #                 for name_result in result['names']:
        #                     self._display_enhanced_name_result(name_result)
                        
        #                 # Show processing statistics
        #                 if 'processing_stats' in result:
        #                     stats = result['processing_stats']
        #                     with st.expander("📈 Processing Statistics"):
        #                         col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                                
        #                         with col_stat1:
        #                             st.metric("Total Processed", stats['total_processed'])
                                
        #                         with col_stat2:
        #                             methods = stats.get('validation_methods', {})
        #                             st.metric("Dictionary", methods.get('deterministic', 0))
                                
        #                         with col_stat3:
        #                             st.metric("Hybrid", methods.get('hybrid', 0))
                                
        #                         with col_stat4:
        #                             st.metric("AI Fallback", methods.get('ai_fallback', 0))
                        
        #                 # Show raw JSON for developers
        #                 with st.expander("Raw JSON Response"):
        #                     st.json(result)
                        
        #         except json.JSONDecodeError:
        #             st.error("❌ Invalid JSON format")
        #         except Exception as e:
        #             st.error(f"❌ Error: {str(e)}") 
        
        # Enhanced CSV Upload
        with st.expander("Enhanced CSV Upload"):
            uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])
            
            if uploaded_file is not None:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.success(f"✅ File uploaded: {len(df)} rows")
                    
                    # Show preview
                    st.write("Preview:")
                    st.dataframe(df.head())
                    
                    if st.button("🔄 Process with Enhanced Validation", type="primary"):
                        with st.spinner("Processing CSV with dictionary lookup + AI fallback..."):
                            result = self.service.process_csv_names(df)
                            
                            if result['success']:
                                st.success(f"✅ Processed {result['processed_records']} names")
                                st.write(f"Success rate: {result['success_rate']:.1%}")
                                
                                # Show method breakdown
                                if 'validation_method_breakdown' in result:
                                    method_breakdown = result['validation_method_breakdown']
                                    col_method1, col_method2, col_method3 = st.columns(3)
                                    
                                    with col_method1:
                                        st.metric("Dictionary Validated", method_breakdown.get('deterministic', 0))
                                    
                                    with col_method2:
                                        st.metric("Hybrid Validation", method_breakdown.get('hybrid', 0))
                                    
                                    with col_method3:
                                        st.metric("AI Fallback", method_breakdown.get('ai_fallback', 0))
                                
                                if result['results']:
                                    # Create enhanced results DataFrame
                                    results_df = pd.DataFrame(result['results'])
                                    st.dataframe(results_df, use_container_width=True)
                                    
                                    # Download button
                                    csv = results_df.to_csv(index=False)
                                    st.download_button(
                                        label="📥 Download Results",
                                        data=csv,
                                        file_name=f"validated_names_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                            else:
                                st.error(f"❌ {result['error']}")
                                
                except Exception as e:
                    st.error(f"❌ Error reading file: {str(e)}")
    
    def render_address_validation(self):
        """Render professional address validation interface with enhanced state name/code support"""
        st.markdown("## 🏠 Address Validation")
        
        # Professional status bar
        self._render_address_status_bar()
        
        # Create tabs for different validation types
        single_tab, csv_tab = st.tabs(["📍 Single Address", "📊 Enhanced Batch Processing"])
        
        # =========================================================================
        # TAB 1: SINGLE ADDRESS VALIDATION WITH STATE NAME SUPPORT
        # =========================================================================
        
        with single_tab:
            self._render_single_address_validation()
        
        # =========================================================================
        # TAB 2: ENHANCED 3-BUCKET BATCH CSV PROCESSING WITH STATE NORMALIZATION
        # =========================================================================
        
        with csv_tab:
            self._render_professional_csv_processing()
    
    def _render_address_status_bar(self):
        """Render professional status bar"""
        if not self.service.is_address_validation_available():
            st.error("🚫 **USPS API Not Configured** - Address validation unavailable", icon="⚠️")
            with st.expander("📖 Setup Instructions"):
                st.code("""
# Set environment variables:
export USPS_CLIENT_ID="your_client_id"
export USPS_CLIENT_SECRET="your_client_secret"

# Or create .env file:
echo 'USPS_CLIENT_ID=your_id' > .env
echo 'USPS_CLIENT_SECRET=your_secret' >> .env
                """)
            return False
        else:
            st.success("✅ **USPS API Connected** - Ready for address validation", icon="🔗")
            return True
    
    def _render_single_address_validation(self):
        """Render professional single address validation with state name support"""
        st.markdown("### 🎯 Single Address Validation")
        
        # Enhanced info about state support
        st.info("💡 **Enhanced State Support**: Enter state as code (CA, NY) or full name (California, New York)")
        
        # Professional form layout
        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); 
                        padding: 2rem; border-radius: 12px; margin: 1rem 0;">
            """, unsafe_allow_html=True)
            
            with st.form("single_address_form", clear_on_submit=False):
                # Address input grid
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    line1 = st.text_input(
                        "🏠 Street Address*", 
                        placeholder="123 Main Street",
                        help="Primary street address (required)"
                    )
                    line2 = st.text_input(
                        "🏢 Unit/Apartment", 
                        placeholder="Apt 4B, Suite 200, etc.",
                        help="Secondary address line (optional)"
                    )
                
                with col2:
                    city = st.text_input(
                        "🏙️ City*", 
                        placeholder="New York",
                        help="City name (required)"
                    )
                    
                    col2a, col2b = st.columns(2)
                    with col2a:
                        state_cd = st.text_input(
                            "🗺️ State*", 
                            placeholder="NY or New York",
                            help="State code (NY) or name (New York)"
                        )
                    with col2b:
                        zip_cd = st.text_input(
                            "📮 ZIP Code*", 
                            placeholder="10001",
                            help="ZIP or ZIP+4 code"
                        )
                
                # Professional submit button
                col_submit1, col_submit2, col_submit3 = st.columns([1, 2, 1])
                with col_submit2:
                    submitted = st.form_submit_button(
                        "🔍 Validate with USPS", 
                        type="primary",
                        use_container_width=True
                    )
                
                if submitted:
                    self._process_single_address(line1, line2, city, state_cd, zip_cd)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def _render_professional_csv_processing(self):
        """Render professional CSV processing with enhanced 3-bucket categorization and state normalization"""
        st.markdown("### 📊 Enhanced 3-Bucket Processing")
        
        # Professional info panel
        with st.container():
            st.markdown("""
            <div style="background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%); 
                        padding: 1.5rem; border-radius: 12px; border-left: 4px solid #3b82f6;">
                <h4 style="margin: 0; color: #1e40af;">🚀 Intelligent 3-Bucket Processing Pipeline</h4>
                <p style="margin: 0.5rem 0 0 0; color: #1e40af;">
                    🇺🇸 US Addresses → USPS Validation  •  🌍 International → Identified & Categorized  •  ❌ Invalid → Error Analysis<br>
                    🔄 <strong>State Names Supported:</strong> "California" or "CA", "New York" or "NY", etc.
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        # File upload section
        st.markdown("#### 📁 Upload CSV Files")
        uploaded_files = st.file_uploader(
            "Select multiple CSV files with address data",
            type=['csv'],
            accept_multiple_files=True,
            key="enhanced_csv_upload",
            help="Supports any CSV format - state names and codes both accepted"
        )
        
        if uploaded_files:
            st.success(f"📄 **{len(uploaded_files)} file(s) uploaded** - Ready for intelligent categorization")
            
            # Process files for enhanced categorization
            with st.spinner("🔍 Analyzing and categorizing addresses..."):
                file_analysis = self._analyze_uploaded_files(uploaded_files)
            
            if file_analysis['valid_files']:
                # Enhanced categorization display
                st.markdown("#### 🎯 Address Categorization Results")
                
                # Toggle buttons for viewing different categories
                col_toggle1, col_toggle2, col_toggle3, col_toggle4 = st.columns([1, 1, 1, 1])
                
                with col_toggle1:
                    show_us_valid = st.toggle("🇺🇸 US Valid", value=True, key="show_us_valid")
                
                with col_toggle2:
                    show_international = st.toggle("🌍 International", value=True, key="show_international")
                
                with col_toggle3:
                    show_invalid = st.toggle("❌ Invalid", value=True, key="show_invalid")
                
                with col_toggle4:
                    overall_quality = (file_analysis['us_valid_count'] / file_analysis['total_records']) if file_analysis['total_records'] > 0 else 0
                    st.metric("🎯 US Valid Rate", f"{overall_quality:.1%}")
                
                # Display categorized results
                self._display_categorized_results(file_analysis, show_us_valid, show_international, show_invalid)
                
                # USPS Processing section
                if file_analysis['us_valid_count'] > 0:
                    st.markdown("#### 🚀 USPS Address Validation")
                    
                    # Enhanced info box about USPS processing
                    st.markdown("""
                    <div style="background: #f0f9ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981; margin: 1rem 0;">
                        <strong>🎯 Ready for USPS Processing:</strong> {us_count} US addresses will be validated with USPS API<br>
                        <strong>🌍 International Addresses:</strong> {intl_count} identified and categorized (no USPS processing needed)<br>
                        <strong>❌ Invalid Addresses:</strong> {invalid_count} require manual review<br>
                        <strong>🔄 State Normalization:</strong> State names automatically converted to codes for USPS
                    </div>
                    """.format(
                        us_count=file_analysis['us_valid_count'],
                        intl_count=file_analysis['international_count'],
                        invalid_count=file_analysis['invalid_count']
                    ), unsafe_allow_html=True)
                    
                    col_process1, col_process2, col_process3 = st.columns([1, 2, 1])
                    with col_process2:
                        if st.button(
                            f"🔥 Validate {file_analysis['us_valid_count']} US Addresses with USPS",
                            type="primary",
                            use_container_width=True,
                            key="enhanced_usps_process"
                        ):
                            self._process_us_addresses_with_usps(file_analysis)
                
                else:
                    st.info("ℹ️ No US valid addresses found for USPS processing. Check international and invalid categories above.")
            
            else:
                st.error("❌ No valid CSV files found for processing")

    # =========================================================================
    # ENHANCED 3-BUCKET CATEGORIZATION METHODS WITH STATE NAME SUPPORT
    # =========================================================================

    def _analyze_uploaded_files(self, uploaded_files):
        """Analyze uploaded files and categorize addresses with state name normalization"""
        analysis = {
            'valid_files': [],
            'total_records': 0,
            'us_valid_addresses': [],        # Valid US addresses for USPS
            'international_addresses': [],   # International addresses
            'invalid_addresses': [],         # Invalid addresses with errors
            'us_valid_count': 0,
            'international_count': 0,
            'invalid_count': 0,
            'quality_breakdown': {
                'us_valid_percentage': 0.0,
                'international_percentage': 0.0,
                'invalid_percentage': 0.0
            },
            'file_details': []
        }
        
        for file in uploaded_files:
            try:
                file.seek(0)
                df = pd.read_csv(file)
                
                if df.empty:
                    continue
                
                # Auto-detect address columns
                standardized_addresses = self.service.address_validator.standardize_csv_to_address_format(df)
                
                if not standardized_addresses:
                    analysis['file_details'].append({
                        'filename': file.name,
                        'status': 'failed',
                        'reason': 'No address columns detected'
                    })
                    continue
                
                # Categorize each address with state normalization
                file_us_valid = []
                file_international = []
                file_invalid = []
                
                for i, addr in enumerate(standardized_addresses):
                    categorization_result = self._categorize_address(addr, i + 1, file.name)
                    
                    if categorization_result['category'] == 'us_valid':
                        file_us_valid.append(categorization_result)
                    elif categorization_result['category'] == 'international':
                        file_international.append(categorization_result)
                    else:
                        file_invalid.append(categorization_result)
                
                # Update analysis
                analysis['us_valid_addresses'].extend(file_us_valid)
                analysis['international_addresses'].extend(file_international)
                analysis['invalid_addresses'].extend(file_invalid)
                analysis['total_records'] += len(standardized_addresses)
                analysis['us_valid_count'] += len(file_us_valid)
                analysis['international_count'] += len(file_international)
                analysis['invalid_count'] += len(file_invalid)
                
                analysis['file_details'].append({
                    'filename': file.name,
                    'status': 'analyzed',
                    'total_rows': len(df),
                    'detected_addresses': len(standardized_addresses),
                    'us_valid_addresses': len(file_us_valid),
                    'international_addresses': len(file_international),
                    'invalid_addresses': len(file_invalid),
                    'us_valid_percentage': len(file_us_valid) / len(standardized_addresses) if standardized_addresses else 0
                })
                
                analysis['valid_files'].append(file.name)
                
            except Exception as e:
                analysis['file_details'].append({
                    'filename': file.name,
                    'status': 'error',
                    'reason': str(e)
                })
        
        # Calculate overall percentages
        if analysis['total_records'] > 0:
            analysis['quality_breakdown'] = {
                'us_valid_percentage': analysis['us_valid_count'] / analysis['total_records'],
                'international_percentage': analysis['international_count'] / analysis['total_records'],
                'invalid_percentage': analysis['invalid_count'] / analysis['total_records']
            }
        
        return analysis

    def _categorize_address(self, address_data, row_num, filename):
        """Enhanced categorize address with state name/code normalization"""
        result = {
            'row_number': row_num,
            'source_file': filename,
            'category': 'invalid',  # Default to invalid
            'issues': [],
            'line1': address_data.get('line1', ''),
            'line2': address_data.get('line2', ''),
            'city': address_data.get('city', ''),
            'state': address_data.get('stateCd', ''),
            'zip': address_data.get('zipCd', ''),
            'country': address_data.get('countryCd', 'US').upper(),
            'complete_address': '',
            'validation_notes': '',
            'normalized_state': '',  # Add this field
            'state_normalization_applied': False
        }
        
        # Normalize state input
        normalized_state, is_valid_state, original_state = self._normalize_state_input(result['state'])
        result['normalized_state'] = normalized_state
        result['state_normalization_applied'] = (normalized_state != original_state.upper())
        
        # Create complete address string
        address_parts = []
        if result['line1']:
            address_parts.append(result['line1'])
        if result['line2']:
            address_parts.append(result['line2'])
        if result['city']:
            address_parts.append(result['city'])
        if result['state']:
            # Show original state in address display
            address_parts.append(result['state'])
        if result['zip']:
            address_parts.append(result['zip'])
        result['complete_address'] = ', '.join(address_parts)
        
        # Step 1: Check if explicitly marked as international
        if result['country'] and result['country'] != 'US' and result['country'] != 'USA':
            result['category'] = 'international'
            result['validation_notes'] = f"International address (Country: {result['country']})"
            return result
        
        # Step 2: Check for required fields
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
        
        # Step 3: Analyze ZIP code to determine if US or International
        zip_analysis = self._analyze_zip_code(result['zip'])
        
        if zip_analysis['type'] == 'international':
            result['category'] = 'international'
            result['validation_notes'] = f"International address - {zip_analysis['reason']}"
            return result
        elif zip_analysis['type'] == 'invalid':
            result['category'] = 'invalid'
            result['issues'] = [zip_analysis['reason']]
            result['validation_notes'] = f"Invalid - {zip_analysis['reason']}"
            return result
        
        # Step 4: Validate US-specific requirements with enhanced state validation
        us_validation = self._validate_us_address_format_enhanced(result, normalized_state, is_valid_state)
        
        if us_validation['valid']:
            result['category'] = 'us_valid'
            # Update state to normalized version for USPS processing
            result['state'] = normalized_state
            if result['state_normalization_applied']:
                result['validation_notes'] = f"Valid US address - State normalized from '{original_state}' to '{normalized_state}'"
            else:
                result['validation_notes'] = "Valid US address - Ready for USPS validation"
        else:
            result['category'] = 'invalid'
            result['issues'] = us_validation['issues']
            result['validation_notes'] = f"Invalid - {'; '.join(us_validation['issues'])}"
        
        return result

    def _validate_us_address_format_enhanced(self, address_data, normalized_state, is_valid_state):
        """Enhanced US address format validation with state name/code support"""
        issues = []
        
        # Validate normalized state
        if not is_valid_state:
            issues.append(f"Invalid US state: '{address_data['state']}' (not recognized as state name or code)")
        
        # Validate ZIP code format
        zip_code = address_data['zip'].strip()
        if not re.match(r'^\d{5}(-\d{4})?$', zip_code):
            issues.append("ZIP code must be 5 digits or ZIP+4 format")
        
        # Basic street address validation
        line1 = address_data['line1'].strip()
        if len(line1) < 3:
            issues.append("Street address too short")
        
        # City validation (basic)
        city = address_data['city'].strip()
        if len(city) < 2:
            issues.append("City name too short")
        elif not re.match(r'^[A-Za-z\s\.\-\']+$', city):
            issues.append("City contains invalid characters")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def _analyze_zip_code(self, zip_code):
        """Analyze ZIP code to determine if it's US, International, or Invalid"""
        if not zip_code:
            return {'type': 'invalid', 'reason': 'Empty ZIP code'}
        
        zip_clean = zip_code.strip().replace(' ', '').replace('-', '')
        
        # US ZIP patterns
        us_patterns = [
            r'^\d{5}$',           # 12345
            r'^\d{9}$',           # 123456789 (ZIP+4 without dash)
            r'^\d{5}-?\d{4}$'     # 12345-6789 or 123456789
        ]
        
        for pattern in us_patterns:
            if re.match(pattern, zip_code.strip()):
                return {'type': 'us', 'reason': 'US ZIP code format'}
        
        # International postal code patterns
        international_patterns = {
            # Canada: A1A 1A1 or A1A1A1
            r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$': 'Canadian postal code',
            
            # UK: Various formats like SW1A 1AA, M1 1AA, B33 8TH
            r'^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$': 'UK postal code',
            
            # Germany: 5 digits
            r'^[0-9]{5}$': 'German postal code (5 digits)',
            
            # Australia: 4 digits
            r'^[0-9]{4}$': 'Australian postal code',
            
            # Netherlands: 4 digits + 2 letters
            r'^[0-9]{4}\s?[A-Z]{2}$': 'Dutch postal code',
            
            # Sweden/Norway/Denmark: 5 digits with optional space
            r'^[0-9]{3}\s?[0-9]{2}$': 'Nordic postal code',
            
            # Japan: 7 digits with dash
            r'^\d{3}-?\d{4}$': 'Japanese postal code',
            
            # Brazil: 8 digits with dash
            r'^\d{5}-?\d{3}$': 'Brazilian postal code',
            
            # India: 6 digits
            r'^[0-9]{6}$': 'Indian postal code',
            
            # China: 6 digits
            r'^[0-9]{6}$': 'Chinese postal code',
            
            # Generic international patterns
            r'^[A-Z]{2,4}\s?[0-9]{3,5}$': 'International postal code (letters + numbers)',
            r'^[0-9]{6,8}$': 'International postal code (6-8 digits)',
            r'^[A-Z0-9]{5,10}$': 'International postal code (alphanumeric)'
        }
        
        zip_upper = zip_code.strip().upper()
        
        for pattern, description in international_patterns.items():
            if re.match(pattern, zip_upper):
                return {'type': 'international', 'reason': description}
        
        # If it doesn't match any known pattern, it's likely invalid
        return {'type': 'invalid', 'reason': 'Unrecognized postal code format'}

    def _display_categorized_results(self, analysis, show_us_valid, show_international, show_invalid):
        """Enhanced display with state normalization indicators"""
        
        # Enhanced summary metrics
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        
        with col_metric1:
            st.metric("📊 Total Addresses", analysis['total_records'])
        
        with col_metric2:
            us_pct = analysis['quality_breakdown']['us_valid_percentage']
            st.metric("🇺🇸 US Valid", analysis['us_valid_count'], delta=f"{us_pct:.1%}")
        
        with col_metric3:
            intl_pct = analysis['quality_breakdown']['international_percentage']
            st.metric("🌍 International", analysis['international_count'], delta=f"{intl_pct:.1%}")
        
        with col_metric4:
            invalid_pct = analysis['quality_breakdown']['invalid_percentage']
            st.metric("❌ Invalid", analysis['invalid_count'], delta=f"{invalid_pct:.1%}")
        
        # Check for state normalizations
        state_normalizations = len([addr for addr in analysis['us_valid_addresses'] 
                                  if addr.get('state_normalization_applied', False)])
        
        if state_normalizations > 0:
            st.info(f"🔄 **State Normalization**: {state_normalizations} addresses had state names converted to standard codes (e.g., 'California' → 'CA')")
        
        # File-by-file breakdown
        with st.expander("📋 File Analysis Breakdown"):
            for detail in analysis['file_details']:
                if detail['status'] == 'analyzed':
                    st.write(
                        f"📄 **{detail['filename']}**: "
                        f"🇺🇸 {detail['us_valid_addresses']} US | "
                        f"🌍 {detail['international_addresses']} Intl | "
                        f"❌ {detail['invalid_addresses']} Invalid "
                        f"({detail['us_valid_percentage']:.1%} US valid)"
                    )
                else:
                    st.write(f"❌ **{detail['filename']}**: {detail.get('reason', 'Failed')}")
        
        # Categorized displays with enhanced state info
        if show_us_valid and analysis['us_valid_addresses']:
            st.markdown("### 🇺🇸 US Valid Addresses (Ready for USPS)")
            us_valid_df = pd.DataFrame(analysis['us_valid_addresses'])
            
            st.markdown("""
            <div style="background: #f0f9ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #10b981;">
            """, unsafe_allow_html=True)
            
            # Enhanced display columns including state normalization info
            display_columns = ['source_file', 'row_number', 'complete_address', 'normalized_state', 'validation_notes']
            
            # Add state normalization indicator
            if 'state_normalization_applied' in us_valid_df.columns:
                us_valid_df['state_normalized'] = us_valid_df['state_normalization_applied'].apply(
                    lambda x: '🔄 Yes' if x else 'No'
                )
                display_columns = ['source_file', 'row_number', 'complete_address', 'normalized_state', 'state_normalized', 'validation_notes']
            
            st.dataframe(
                us_valid_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'source_file': st.column_config.TextColumn('File', width='small'),
                    'row_number': st.column_config.NumberColumn('Row', width='small'),
                    'complete_address': st.column_config.TextColumn('Address', width='large'),
                    'normalized_state': st.column_config.TextColumn('State Code', width='small'),
                    'state_normalized': st.column_config.TextColumn('Normalized', width='small'),
                    'validation_notes': st.column_config.TextColumn('Status', width='medium')
                }
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        if show_international and analysis['international_addresses']:
            st.markdown("### 🌍 International Addresses")
            intl_df = pd.DataFrame(analysis['international_addresses'])
            
            st.markdown("""
            <div style="background: #fffbeb; padding: 1rem; border-radius: 8px; border-left: 4px solid #f59e0b;">
            """, unsafe_allow_html=True)
            
            display_columns = ['source_file', 'row_number', 'complete_address', 'validation_notes']
            st.dataframe(
                intl_df[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'source_file': st.column_config.TextColumn('File', width='small'),
                    'row_number': st.column_config.NumberColumn('Row', width='small'),
                    'complete_address': st.column_config.TextColumn('Address', width='large'),
                    'validation_notes': st.column_config.TextColumn('Type', width='medium')
                }
            )
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        if show_invalid and analysis['invalid_addresses']:
            st.markdown("### ❌ Invalid Addresses (Need Review)")
            invalid_df = pd.DataFrame(analysis['invalid_addresses'])
            
            st.markdown("""
            <div style="background: #fef2f2; padding: 1rem; border-radius: 8px; border-left: 4px solid #ef4444;">
            """, unsafe_allow_html=True)
            
            # Add issues column for display
            invalid_display = invalid_df.copy()
            invalid_display['issues_text'] = invalid_display['issues'].apply(lambda x: '; '.join(x) if isinstance(x, list) else str(x))
            
            display_columns = ['source_file', 'row_number', 'complete_address', 'issues_text']
            st.dataframe(
                invalid_display[display_columns],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'source_file': st.column_config.TextColumn('File', width='small'),
                    'row_number': st.column_config.NumberColumn('Row', width='small'),
                    'complete_address': st.column_config.TextColumn('Address', width='large'),
                    'issues_text': st.column_config.TextColumn('Issues', width='medium')
                }
            )
            
            st.markdown("</div>", unsafe_allow_html=True)

    def _process_us_addresses_with_usps(self, analysis):
        """Enhanced USPS processing with state normalization tracking"""
        
        if not analysis['us_valid_addresses']:
            st.warning("⚠️ No US valid addresses to process with USPS")
            return
        
        # Professional progress tracking
        progress_container = st.container()
        
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        try:
            status_text.info("🚀 **Processing US addresses with USPS API...**")
            progress_bar.progress(10)
            
            # Process only US valid addresses
            usps_results = []
            successful = 0
            failed = 0
            state_normalizations = 0
            
            us_addresses = analysis['us_valid_addresses']
            total_us = len(us_addresses)
            
            for i, us_addr in enumerate(us_addresses):
                status_text.info(f"🔄 **Processing {i+1}/{total_us}**: {us_addr['source_file']}")
                progress_bar.progress(10 + int(80 * (i+1) / total_us))
                
                # Track state normalizations
                if us_addr.get('state_normalization_applied', False):
                    state_normalizations += 1
                
                # Convert to USPS format and validate
                address_record = {
                    'guid': f"{us_addr['source_file']}_{us_addr['row_number']}",
                    'line1': us_addr['line1'],
                    'line2': us_addr['line2'] or None,
                    'city': us_addr['city'],
                    'stateCd': us_addr['normalized_state'],  # Use normalized state
                    'zipCd': us_addr['zip'],
                    'countryCd': 'US'
                }
                
                try:
                    usps_result = self.service.validate_single_address(address_record)
                    
                    # Enhanced result with categorization info
                    enhanced_result = {
                        'source_file': us_addr['source_file'],
                        'row_number': us_addr['row_number'],
                        'category': 'us_validated',
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
                    
                    if enhanced_result['usps_valid']:
                        successful += 1
                    else:
                        failed += 1
                        
                except Exception as e:
                    # Handle individual address errors
                    error_result = {
                        'source_file': us_addr['source_file'],
                        'row_number': us_addr['row_number'],
                        'category': 'us_error',
                        'input_address': us_addr['complete_address'],
                        'normalized_state': us_addr['normalized_state'],
                        'state_normalization_applied': us_addr.get('state_normalization_applied', False),
                        'usps_valid': False,
                        'error_message': str(e),
                        'standardized_address': 'Processing Error'
                    }
                    usps_results.append(error_result)
                    failed += 1
            
            progress_bar.progress(100)
            status_text.success("✅ **USPS validation completed!**")
            
            # Show state normalization statistics
            if state_normalizations > 0:
                st.info(f"🔄 **State Normalization Applied**: {state_normalizations} addresses had their state names/abbreviations normalized to standard codes")
            
            # Combine all results for comprehensive output
            comprehensive_results = self._create_comprehensive_results(analysis, usps_results)
            
            # Display enhanced results
            self._display_comprehensive_results(comprehensive_results, analysis, successful, failed, total_us)
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ **USPS processing failed**: {str(e)}")

    def _create_comprehensive_results(self, analysis, usps_results):
        """Create comprehensive results combining all categories"""
        
        comprehensive = {
            'us_usps_validated': usps_results,
            'international_addresses': analysis['international_addresses'],
            'invalid_addresses': analysis['invalid_addresses'],
            'summary': {
                'total_addresses': analysis['total_records'],
                'us_processed': len(usps_results),
                'us_valid_count': len([r for r in usps_results if r.get('usps_valid', False)]),
                'us_invalid_count': len([r for r in usps_results if not r.get('usps_valid', False)]),
                'international_count': analysis['international_count'],
                'invalid_count': analysis['invalid_count']
            }
        }
        
        return comprehensive

    def _display_comprehensive_results(self, results, analysis, successful, failed, total_us):
        """Display comprehensive results with all categories"""
        
        st.markdown("## 🎉 Comprehensive Address Validation Results")
        
        # Enhanced metrics display
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("📊 Total Addresses", results['summary']['total_addresses'])
        
        with col2:
            st.metric("🇺🇸 USPS Processed", total_us)
        
        with col3:
            st.metric("✅ USPS Valid", successful, delta=f"{successful/total_us:.1%}" if total_us > 0 else "0%")
        
        with col4:
            st.metric("🌍 International", results['summary']['international_count'])
        
        with col5:
            st.metric("❌ Invalid/Error", results['summary']['invalid_count'] + failed)
        
        # Tabbed results display
        usps_tab, intl_tab, invalid_tab = st.tabs(["🇺🇸 USPS Results", "🌍 International", "❌ Invalid/Errors"])
        
        with usps_tab:
            if results['us_usps_validated']:
                usps_df = pd.DataFrame(results['us_usps_validated'])
                
                # Separate valid and invalid USPS results
                valid_usps = usps_df[usps_df['usps_valid'] == True]
                invalid_usps = usps_df[usps_df['usps_valid'] == False]
                
                if not valid_usps.empty:
                    st.markdown("### ✅ USPS Validated Addresses")
                    
                    # Enhanced display columns including state normalization info
                    display_columns = ['source_file', 'row_number', 'input_address', 'standardized_address', 'normalized_state', 'county', 'is_residential']
                    
                    # Add state normalization indicator
                    if 'state_normalization_applied' in valid_usps.columns:
                        valid_usps_display = valid_usps.copy()
                        valid_usps_display['state_normalized'] = valid_usps_display['state_normalization_applied'].apply(
                            lambda x: '🔄' if x else ''
                        )
                        display_columns = ['source_file', 'row_number', 'input_address', 'standardized_address', 'normalized_state', 'state_normalized', 'county', 'is_residential']
                        
                        st.dataframe(
                            valid_usps_display[display_columns],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                'is_residential': st.column_config.CheckboxColumn('Residential'),
                                'state_normalized': st.column_config.TextColumn('State Norm.', width='small'),
                                'normalized_state': st.column_config.TextColumn('State Code', width='small'),
                                'source_file': st.column_config.TextColumn('File', width='small'),
                                'row_number': st.column_config.NumberColumn('Row', width='small')
                            }
                        )
                    else:
                        st.dataframe(
                            valid_usps[display_columns],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                'is_residential': st.column_config.CheckboxColumn('Residential'),
                                'source_file': st.column_config.TextColumn('File', width='small'),
                                'row_number': st.column_config.NumberColumn('Row', width='small')
                            }
                        )
                
                if not invalid_usps.empty:
                    st.markdown("### ❌ USPS Validation Failed")
                    display_columns = ['source_file', 'row_number', 'input_address', 'error_message']
                    st.dataframe(
                        invalid_usps[display_columns],
                        use_container_width=True,
                        hide_index=True
                    )
        
        with intl_tab:
            if results['international_addresses']:
                intl_df = pd.DataFrame(results['international_addresses'])
                st.dataframe(
                    intl_df[['source_file', 'row_number', 'complete_address', 'validation_notes']],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No international addresses found in the uploaded data.")
        
        with invalid_tab:
            if results['invalid_addresses']:
                invalid_df = pd.DataFrame(results['invalid_addresses'])
                invalid_display = invalid_df.copy()
                invalid_display['issues_text'] = invalid_display['issues'].apply(
                    lambda x: '; '.join(x) if isinstance(x, list) else str(x)
                )
                st.dataframe(
                    invalid_display[['source_file', 'row_number', 'complete_address', 'issues_text']],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        'issues_text': st.column_config.TextColumn('Issues', width='medium')
                    }
                )
            else:
                st.info("No invalid addresses found in the uploaded data.")
        
        # Enhanced download options
        st.markdown("### 📥 Download Results")
        self._create_enhanced_download_buttons(results)

    def _create_enhanced_download_buttons(self, results):
        """Create enhanced download buttons for all result categories"""
        
        col_download1, col_download2, col_download3, col_download4 = st.columns(4)
        
        # Combined results download
        with col_download1:
            if results['us_usps_validated'] or results['international_addresses'] or results['invalid_addresses']:
                combined_data = []
                
                # Add USPS validated results
                for result in results['us_usps_validated']:
                    combined_data.append({
                        'source_file': result['source_file'],
                        'row_number': result['row_number'],
                        'category': 'US_USPS_Validated',
                        'input_address': result['input_address'],
                        'output_address': result.get('standardized_address', ''),
                        'normalized_state': result.get('normalized_state', ''),
                        'state_normalized': 'Yes' if result.get('state_normalization_applied', False) else 'No',
                        'usps_valid': result.get('usps_valid', False),
                        'county': result.get('county', ''),
                        'is_residential': result.get('is_residential', ''),
                        'error_message': result.get('error_message', ''),
                        'notes': 'USPS Validated'
                    })
                
                # Add international results
                for result in results['international_addresses']:
                    combined_data.append({
                        'source_file': result['source_file'],
                        'row_number': result['row_number'],
                        'category': 'International',
                        'input_address': result['complete_address'],
                        'output_address': result['complete_address'],
                        'normalized_state': '',
                        'state_normalized': 'N/A',
                        'usps_valid': False,
                        'county': '',
                        'is_residential': '',
                        'error_message': '',
                        'notes': result['validation_notes']
                    })
                
                # Add invalid results
                for result in results['invalid_addresses']:
                    issues_text = '; '.join(result['issues']) if isinstance(result['issues'], list) else str(result.get('issues', ''))
                    combined_data.append({
                        'source_file': result['source_file'],
                        'row_number': result['row_number'],
                        'category': 'Invalid',
                        'input_address': result['complete_address'],
                        'output_address': '',
                        'normalized_state': result.get('normalized_state', ''),
                        'state_normalized': 'Yes' if result.get('state_normalization_applied', False) else 'No',
                        'usps_valid': False,
                        'county': '',
                        'is_residential': '',
                        'error_message': issues_text,
                        'notes': result['validation_notes']
                    })
                
                if combined_data:
                    combined_df = pd.DataFrame(combined_data)
                    combined_csv = combined_df.to_csv(index=False)
                    st.download_button(
                        "📄 All Results",
                        combined_csv,
                        f"complete_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        "text/csv",
                        use_container_width=True
                    )
        
        # US USPS results only
        with col_download2:
            if results['us_usps_validated']:
                usps_df = pd.DataFrame(results['us_usps_validated'])
                usps_csv = usps_df.to_csv(index=False)
                st.download_button(
                    "🇺🇸 USPS Results",
                    usps_csv,
                    f"usps_validated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
        
        # International addresses only
        with col_download3:
            if results['international_addresses']:
                intl_df = pd.DataFrame(results['international_addresses'])
                intl_csv = intl_df.to_csv(index=False)
                st.download_button(
                    "🌍 International",
                    intl_csv,
                    f"international_addresses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )
        
        # Invalid addresses only
        with col_download4:
            if results['invalid_addresses']:
                invalid_df = pd.DataFrame(results['invalid_addresses'])
                # Add issues as text for CSV
                invalid_df_export = invalid_df.copy()
                invalid_df_export['issues_text'] = invalid_df_export['issues'].apply(
                    lambda x: '; '.join(x) if isinstance(x, list) else str(x)
                )
                invalid_csv = invalid_df_export.to_csv(index=False)
                st.download_button(
                    "❌ Invalid",
                    invalid_csv,
                    f"invalid_addresses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    use_container_width=True
                )

    # =========================================================================
    # EXISTING METHODS (Keep all the existing methods from the original app.py)
    # =========================================================================

    def _process_single_address(self, line1, line2, city, state_cd, zip_cd):
        """Process single address validation with state name support"""
        if not all([line1, city, state_cd, zip_cd]):
            st.error("❌ Please fill in all required fields (marked with *)")
            return
        
        # Normalize state input
        normalized_state, is_valid_state, original_state = self._normalize_state_input(state_cd)
        
        if not is_valid_state:
            st.error(f"❌ Invalid state: '{state_cd}' is not recognized as a US state name or code")
            return
        
        # Show state normalization if applied
        if normalized_state != original_state.upper():
            st.info(f"🔄 State normalized: '{original_state}' → '{normalized_state}'")
        
        with st.spinner("🔄 Validating with USPS..."):
            address_record = {
                'guid': '1',
                'line1': line1,
                'line2': line2 if line2 else None,
                'city': city,
                'stateCd': normalized_state,  # Use normalized state
                'zipCd': zip_cd,
                'countryCd': 'US'
            }
            
            result = self.service.validate_single_address(address_record)
            self._display_single_address_result(result)
    
    def render_monitoring(self):
        """Render enhanced monitoring dashboard"""
        st.markdown("## 📊 System Monitoring & Analytics")
        
        # Service status
        status = self.service.get_service_status()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            name_status = "✅ Enhanced Ready" if status['name_validation_available'] else "❌ Unavailable"
            st.metric("Name Service", name_status)
        
        with col2:
            addr_status = "✅ USPS Ready" if status['address_validation_available'] else "❌ Unavailable"
            st.metric("Address Service", addr_status)
        
        with col3:
            dict_status = "✅ Loaded" if status['dictionary_status'] else "❌ Not Available"
            st.metric("Dictionaries", dict_status)
        
        with col4:
            st.metric("API Version", f"v{status['api_version']}")
        
        # Enhanced processing stats
        name_stats = st.session_state.processing_stats
        address_stats = self._get_address_stats()
        
        # Name validation stats
        st.markdown("### Name Validation Statistics")
        col5, col6, col7, col8, col9 = st.columns(5)
        
        with col5:
            st.metric("Names Processed", name_stats['total_processed'])
        
        with col6:
            st.metric("Successful", name_stats['successful'])
        
        with col7:
            st.metric("Dictionary", name_stats['deterministic'])
        
        with col8:
            st.metric("Hybrid", name_stats['hybrid'])
        
        with col9:
            st.metric("AI Fallback", name_stats['ai_fallback'])
        
        # Address validation stats
        st.markdown("### Address Validation Statistics")
        col10, col11, col12 = st.columns(3)
        
        with col10:
            st.metric("Addresses Validated", address_stats['total_validated'])
        
        with col11:
            st.metric("Valid/Deliverable", address_stats['successful'])
        
        with col12:
            st.metric("Failed/Invalid", address_stats['failed'])
        
        # Dictionary information
        if status['dictionary_status'] and 'dictionary_statistics' in status:
            st.markdown("### Dictionary Information")
            dict_stats = status['dictionary_statistics']
            
            col13, col14, col15 = st.columns(3)
            
            with col13:
                st.metric("First Names", f"{dict_stats.get('first_names_count', 0):,}")
                st.metric("Surnames", f"{dict_stats.get('surnames_count', 0):,}")
            
            with col14:
                st.metric("Gender Mappings", f"{dict_stats.get('gender_mappings_count', 0):,}")
                st.metric("Nickname Mappings", f"{dict_stats.get('nickname_mappings_count', 0):,}")
            
            with col15:
                st.metric("Business Words", f"{dict_stats.get('business_words_count', 0):,}")
                st.metric("Company Suffixes", f"{dict_stats.get('company_suffixes_count', 0):,}")
        
        # Recent logs
        recent_logs = logger.get_recent_logs(10)
        
        if recent_logs:
            st.markdown("### Recent Activity")
            
            log_data = []
            for log in recent_logs:
                log_data.append({
                    'Time': log['timestamp'].strftime('%H:%M:%S'),
                    'Level': log['level'],
                    'Category': log['category'],
                    'Message': log['message'][:100] + ('...' if len(log['message']) > 100 else '')
                })
            
            logs_df = pd.DataFrame(log_data)
            st.dataframe(logs_df, use_container_width=True)
        
        # Clear stats button
        if st.button("🗑️ Clear Statistics"):
            st.session_state.processing_stats = {
                'total_processed': 0,
                'successful': 0,
                'failed': 0,
                'deterministic': 0,
                'hybrid': 0,
                'ai_fallback': 0
            }
            st.session_state.address_stats = {
                'total_validated': 0,
                'successful': 0,
                'failed': 0
            }
            st.session_state.validation_results = []
            logger.clear()
            st.success("Statistics cleared!")
            st.rerun()
    
    def _display_enhanced_name_result(self, result: dict):
        """Display enhanced name validation result with method information"""
        
        # Determine confidence level for styling
        confidence = float(result.get('confidenceScore', '0'))
        validation_method = result.get('validationMethod', 'unknown')
        
        if confidence >= 90:
            confidence_class = "confidence-high"
            confidence_icon = "🟢"
        elif confidence >= 70:
            confidence_class = "confidence-medium"
            confidence_icon = "🟡"
        else:
            confidence_class = "confidence-low"
            confidence_icon = "🔴"
        
        # Method styling
        if 'deterministic' in validation_method:
            method_class = "method-deterministic"
            method_label = "Dictionary"
        elif 'hybrid' in validation_method:
            method_class = "method-hybrid"
            method_label = "Hybrid"
        else:
            method_class = "method-ai"
            method_label = "AI Fallback"
        
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        
        # Header with confidence and method
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"### {result['fullName']}")
        
        with col2:
            st.markdown(f"**Party Type:** {result['partyTypeCd']}")
        
        with col3:
            st.markdown(f"**Status:** {result['parseStatus']}")
        
        # Confidence and method information
        st.markdown(f"""
        {confidence_icon} **Confidence:** <span class="{confidence_class}">{confidence:.2f}%</span>  
        **Method:** <span class="{method_class}">{method_label}</span>  
        **Message:** {result['errorMessage']}
        """, unsafe_allow_html=True)
        
        # Parsed components (if individual)
        if result['partyTypeCd'] == 'I' and result['parseInd'] == 'Y':
            st.markdown("#### 🔍 Parsed Components")
            
            comp_col1, comp_col2, comp_col3 = st.columns(3)
            
            with comp_col1:
                if result['prefix']:
                    st.write(f"**Prefix:** {result['prefix']}")
                st.write(f"**First Name:** {result['firstName'] or 'N/A'}")
                if result['firstNameStd'] and result['firstNameStd'] != result['firstName']:
                    st.write(f"**Standardized:** {result['firstNameStd']}")
            
            with comp_col2:
                if result['middleName']:
                    st.write(f"**Middle Name:** {result['middleName']}")
                st.write(f"**Last Name:** {result['lastName'] or 'N/A'}")
            
            with comp_col3:
                if result['suffix']:
                    st.write(f"**Suffix:** {result['suffix']}")
                
                # Gender prediction
                gender_display = result['outGenderCd'] if result['outGenderCd'] else 'Unknown'
                if result['outGenderCd'] and not result['inGenderCd']:
                    gender_display += " (Predicted)"
                st.write(f"**Gender:** {gender_display}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Update stats
        st.session_state.processing_stats['total_processed'] += 1
        if result['parseStatus'] in ['Parsed', 'Not Parsed']:
            st.session_state.processing_stats['successful'] += 1
        else:
            st.session_state.processing_stats['failed'] += 1
        
        # Update method stats
        if 'deterministic' in validation_method:
            st.session_state.processing_stats['deterministic'] += 1
        elif 'hybrid' in validation_method:
            st.session_state.processing_stats['hybrid'] += 1
        else:
            st.session_state.processing_stats['ai_fallback'] += 1
    
    def _display_single_address_result(self, result: dict):
        """Display single address validation result"""
        
        is_valid = result.get('errorMsg') is None and result.get('mailabilityScore') == '1'
        
        if is_valid:
            st.success("✅ Address is valid and deliverable!")
            
            # Display validated address
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**📮 Input Address:**")
                st.write(f"{result.get('inLine1', '')}")
                if result.get('inLine2'):
                    st.write(f"{result.get('inLine2', '')}")
                st.write(f"{result.get('inLine6', '')}, {result.get('inLine7', '')} {result.get('inLine8', '')}")
            
            with col2:
                st.markdown("**✅ USPS Standardized:**")
                st.write(f"{result.get('deliveryAddressLine1', '')}")
                if result.get('deliveryAddressLine2'):
                    st.write(f"{result.get('deliveryAddressLine2', '')}")
                st.write(f"{result.get('city', '')}, {result.get('stateCd', '')} {result.get('zipCdComplete', '')}")
            
            # Additional details
            with st.expander("📊 Additional Details"):
                detail_col1, detail_col2 = st.columns(2)
                
                with detail_col1:
                    if result.get('countyName'):
                        st.write(f"**County:** {result['countyName']}")
                    if result.get('carrierRoute'):
                        st.write(f"**Carrier Route:** {result['carrierRoute']}")
                    if result.get('congressionalDistrict'):
                        st.write(f"**Congressional District:** {result['congressionalDistrict']}")
                
                with detail_col2:
                    if result.get('zipCd4'):
                        st.write(f"**ZIP+4:** {result['zipCd4']}")
                    is_residential = result.get('residentialDeliveryIndicator') == 'Y'
                    st.write(f"**Address Type:** {'Residential' if is_residential else 'Business'}")
                    st.write(f"**Result Percentage:** {result.get('ResultPercentage', '0')}%")
        
        else:
            # Address validation failed
            st.error("❌ Address validation failed")
            
            if result.get('errorMsg'):
                st.write(f"**Error:** {result['errorMsg']}")
            
            # Show what was attempted
            with st.expander("📋 Input Details"):
                st.write(f"**Address:** {result.get('inLine1', '')}")
                if result.get('inLine2'):
                    st.write(f"**Line 2:** {result.get('inLine2', '')}")
                st.write(f"**City:** {result.get('inLine6', '')}")
                st.write(f"**State:** {result.get('inLine7', '')}")
                st.write(f"**ZIP:** {result.get('inLine8', '')}")
                
                st.info("💡 **Tips for better results:**\n- Check spelling of street name and city\n- Ensure state code is correct (2 letters)\n- Verify ZIP code is valid for the area")
        
        # Update session stats
        self._update_address_stats(is_valid)
    
    def _update_address_stats(self, is_valid: bool):
        """Update address validation statistics"""
        if 'address_stats' not in st.session_state:
            st.session_state.address_stats = {
                'total_validated': 0,
                'successful': 0,
                'failed': 0
            }
        
        st.session_state.address_stats['total_validated'] += 1
        if is_valid:
            st.session_state.address_stats['successful'] += 1
        else:
            st.session_state.address_stats['failed'] += 1
    
    def _get_address_stats(self):
        """Get address validation statistics"""
        if 'address_stats' not in st.session_state:
            return {'total_validated': 0, 'successful': 0, 'failed': 0}
        return st.session_state.address_stats
    
    def run(self):
        """Main application entry point"""
        # Configure page
        st.set_page_config(
            page_title="Enhanced Name & Address Validator",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Apply styling
        self.apply_styling()
        
        # Render header
        self.render_header()
        
        # Main tabs
        name_tab, address_tab, monitoring_tab = st.tabs([
            "🤖 Name Validation",
            "🏠 Address Validation", 
            "📊 Monitoring"
        ])
        
        with name_tab:
            self.render_name_validation()
        
        with address_tab:
            self.render_address_validation()
        
        with monitoring_tab:
            self.render_monitoring()

def run_without_page_config(self):
    """Run app without calling set_page_config (for Docker entry point)"""
    # Apply styling
    self.apply_styling()
    
    # Render header
    self.render_header()
    
    # Main tabs
    name_tab, address_tab, monitoring_tab = st.tabs([
        "🤖 Name Validation",
        "🏠 Address Validation", 
        "📊 Monitoring"
    ])
    
    with name_tab:
        self.render_name_validation()
    
    with address_tab:
        self.render_address_validation()
    
    with monitoring_tab:
        self.render_monitoring()

def main():
    """Application entry point"""
    try:
        app = ValidatorApp()
        app.run()
    except Exception as e:
        st.error(f"❌ Application error: {str(e)}")
        logger.error(f"Application error: {e}", "APP")


if __name__ == "__main__":
    main()