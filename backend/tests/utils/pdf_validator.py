"""
PDF validation utilities for detecting corruption and format issues.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from io import BytesIO
import re
import struct


logger = logging.getLogger(__name__)


class PDFValidationResult:
    """Result of PDF validation."""
    
    def __init__(self):
        self.is_valid = True
        self.errors = []
        self.warnings = []
        self.info = {}
    
    def add_error(self, message: str):
        """Add validation error."""
        self.errors.append(message)
        self.is_valid = False
        logger.error(f"PDF Validation Error: {message}")
    
    def add_warning(self, message: str):
        """Add validation warning."""
        self.warnings.append(message)
        logger.warning(f"PDF Validation Warning: {message}")
    
    def add_info(self, key: str, value: Any):
        """Add validation info."""
        self.info[key] = value
        logger.info(f"PDF Validation Info: {key} = {value}")
    
    def __str__(self):
        """String representation of validation result."""
        result = f"PDF Validation Result: {'VALID' if self.is_valid else 'INVALID'}\n"
        if self.errors:
            result += f"Errors ({len(self.errors)}):\n"
            for error in self.errors:
                result += f"  - {error}\n"
        if self.warnings:
            result += f"Warnings ({len(self.warnings)}):\n"
            for warning in self.warnings:
                result += f"  - {warning}\n"
        if self.info:
            result += f"Info:\n"
            for key, value in self.info.items():
                result += f"  - {key}: {value}\n"
        return result


class PDFValidator:
    """Comprehensive PDF validation utility."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_pdf_bytes(self, pdf_bytes: bytes) -> PDFValidationResult:
        """
        Validate PDF bytes for corruption and format issues.
        
        Args:
            pdf_bytes: PDF content as bytes
            
        Returns:
            PDFValidationResult: Validation result
        """
        result = PDFValidationResult()
        
        try:
            # Basic validation
            self._validate_basic_structure(pdf_bytes, result)
            
            # Header validation
            self._validate_pdf_header(pdf_bytes, result)
            
            # Object validation
            self._validate_pdf_objects(pdf_bytes, result)
            
            # Cross-reference validation
            self._validate_xref_table(pdf_bytes, result)
            
            # Trailer validation
            self._validate_trailer(pdf_bytes, result)
            
            # Content validation
            self._validate_content_structure(pdf_bytes, result)
            
            # Size validation
            self._validate_file_size(pdf_bytes, result)
            
            # ReportLab specific validation
            self._validate_reportlab_structure(pdf_bytes, result)
            
        except Exception as e:
            result.add_error(f"Validation failed with exception: {str(e)}")
        
        return result
    
    def _validate_basic_structure(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate basic PDF structure."""
        if not pdf_bytes:
            result.add_error("PDF bytes are empty")
            return
        
        result.add_info("file_size", len(pdf_bytes))
        
        if len(pdf_bytes) < 100:
            result.add_error("PDF file is too small to be valid")
            return
        
        # Check for null bytes at the start (corruption indicator)
        if pdf_bytes[:10] == b'\x00' * 10:
            result.add_error("PDF starts with null bytes (corrupted)")
    
    def _validate_pdf_header(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate PDF header."""
        try:
            # Convert to string for header checking
            header_str = pdf_bytes[:100].decode('latin-1', errors='ignore')
            
            # Check for PDF header
            if not header_str.startswith('%PDF-'):
                # Check if it's a ReportLab PDF (starts with objects)
                if '1 0 obj' in header_str[:50]:
                    result.add_info("pdf_type", "ReportLab PDF (no explicit header)")
                    result.add_info("pdf_version", "Unknown (ReportLab)")
                else:
                    result.add_error("PDF does not start with %PDF- header")
                    return
            else:
                # Extract version
                version_match = re.search(r'%PDF-(\d+\.\d+)', header_str)
                if version_match:
                    version = version_match.group(1)
                    result.add_info("pdf_version", version)
                else:
                    result.add_warning("Could not extract PDF version")
                
                result.add_info("pdf_type", "Standard PDF")
        
        except Exception as e:
            result.add_error(f"Header validation failed: {str(e)}")
    
    def _validate_pdf_objects(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate PDF objects."""
        try:
            content = pdf_bytes.decode('latin-1', errors='ignore')
            
            # Count objects
            obj_pattern = r'(\d+) (\d+) obj'
            obj_matches = re.findall(obj_pattern, content)
            
            if not obj_matches:
                result.add_error("No PDF objects found")
                return
            
            result.add_info("object_count", len(obj_matches))
            
            # Check for endobj markers
            endobj_count = content.count('endobj')
            if endobj_count != len(obj_matches):
                result.add_error(f"Object count mismatch: {len(obj_matches)} objects, {endobj_count} endobj markers")
            
            # Check for stream objects
            stream_count = content.count('stream')
            endstream_count = content.count('endstream')
            
            if stream_count != endstream_count:
                result.add_warning(f"Stream count mismatch: {stream_count} stream, {endstream_count} endstream")
            
            result.add_info("stream_count", stream_count)
            
        except Exception as e:
            result.add_error(f"Object validation failed: {str(e)}")
    
    def _validate_xref_table(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate cross-reference table."""
        try:
            content = pdf_bytes.decode('latin-1', errors='ignore')
            
            # Check for xref table
            if 'xref' not in content:
                result.add_warning("No xref table found (might be compressed)")
                return
            
            # Count xref entries
            xref_matches = re.findall(r'xref', content)
            result.add_info("xref_table_count", len(xref_matches))
            
            # Check for trailer after xref
            if 'trailer' not in content:
                result.add_warning("No trailer found after xref table")
            
        except Exception as e:
            result.add_error(f"Xref validation failed: {str(e)}")
    
    def _validate_trailer(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate PDF trailer."""
        try:
            content = pdf_bytes.decode('latin-1', errors='ignore')
            
            # Check for trailer
            if 'trailer' not in content:
                result.add_warning("No trailer found")
                return
            
            # Check for startxref
            if 'startxref' not in content:
                result.add_warning("No startxref found")
            
            # Check for EOF
            if not content.rstrip().endswith('%%EOF'):
                result.add_warning("PDF does not end with %%EOF")
            
        except Exception as e:
            result.add_error(f"Trailer validation failed: {str(e)}")
    
    def _validate_content_structure(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate PDF content structure."""
        try:
            content = pdf_bytes.decode('latin-1', errors='ignore')
            
            # Check for catalog
            if '/Type/Catalog' in content or '/Type /Catalog' in content:
                result.add_info("has_catalog", True)
            else:
                result.add_warning("No catalog found")
            
            # Check for pages
            if '/Type/Pages' in content or '/Type /Pages' in content:
                result.add_info("has_pages", True)
            else:
                result.add_warning("No pages object found")
            
            # Check for page objects
            page_matches = re.findall(r'/Type\s*/Page[^s]', content)
            result.add_info("page_count", len(page_matches))
            
            # Check for fonts
            font_matches = re.findall(r'/Type\s*/Font', content)
            result.add_info("font_count", len(font_matches))
            
            # Check for content streams
            if '/Length' in content:
                result.add_info("has_content_streams", True)
            
        except Exception as e:
            result.add_error(f"Content structure validation failed: {str(e)}")
    
    def _validate_file_size(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate file size characteristics."""
        size = len(pdf_bytes)
        
        # Size bounds checking
        if size < 1000:
            result.add_warning("PDF file is very small (< 1KB)")
        elif size > 50 * 1024 * 1024:  # 50MB
            result.add_warning("PDF file is very large (> 50MB)")
        
        # Check for excessive null bytes (corruption indicator)
        null_count = pdf_bytes.count(b'\x00')
        null_percentage = (null_count / size) * 100
        
        if null_percentage > 50:
            result.add_error(f"PDF contains {null_percentage:.1f}% null bytes (likely corrupted)")
        elif null_percentage > 10:
            result.add_warning(f"PDF contains {null_percentage:.1f}% null bytes")
        
        result.add_info("null_byte_percentage", null_percentage)
    
    def _validate_reportlab_structure(self, pdf_bytes: bytes, result: PDFValidationResult):
        """Validate ReportLab-specific PDF structure."""
        try:
            content = pdf_bytes.decode('latin-1', errors='ignore')
            
            # Check for ReportLab markers
            if 'ReportLab' in content:
                result.add_info("generated_by", "ReportLab")
            
            # Check for common ReportLab structures
            if '/Producer' in content and 'ReportLab' in content:
                result.add_info("reportlab_producer", True)
            
            # Check for ReportLab font handling
            if '/FontName' in content or '/BaseFont' in content:
                result.add_info("has_font_definitions", True)
            
            # Check for ReportLab page structure
            if '/Contents' in content and '/Length' in content:
                result.add_info("has_page_contents", True)
            
        except Exception as e:
            result.add_error(f"ReportLab validation failed: {str(e)}")
    
    def validate_pdf_file(self, file_path: str) -> PDFValidationResult:
        """
        Validate PDF file from disk.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            PDFValidationResult: Validation result
        """
        try:
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            result = self.validate_pdf_bytes(pdf_bytes)
            result.add_info("file_path", file_path)
            
            return result
        
        except Exception as e:
            result = PDFValidationResult()
            result.add_error(f"Could not read file {file_path}: {str(e)}")
            return result
    
    def diagnose_corruption(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Diagnose specific corruption issues.
        
        Args:
            pdf_bytes: PDF content as bytes
            
        Returns:
            Dict with corruption diagnosis
        """
        diagnosis = {
            "corruption_detected": False,
            "corruption_type": None,
            "corruption_details": [],
            "repair_suggestions": []
        }
        
        try:
            # Check for truncated file
            if len(pdf_bytes) < 100:
                diagnosis["corruption_detected"] = True
                diagnosis["corruption_type"] = "truncated"
                diagnosis["corruption_details"].append("File is too small to be valid PDF")
                diagnosis["repair_suggestions"].append("Re-generate the PDF")
            
            # Check for null byte corruption
            if pdf_bytes[:10] == b'\x00' * 10:
                diagnosis["corruption_detected"] = True
                diagnosis["corruption_type"] = "null_bytes"
                diagnosis["corruption_details"].append("File starts with null bytes")
                diagnosis["repair_suggestions"].append("Check PDF generation process")
            
            # Check for text/binary mismatch
            try:
                content = pdf_bytes.decode('utf-8')
                if 'PCAP ANALYSIS REPORT' in content and '%PDF-' not in content:
                    diagnosis["corruption_detected"] = True
                    diagnosis["corruption_type"] = "text_instead_of_pdf"
                    diagnosis["corruption_details"].append("File contains text instead of PDF")
                    diagnosis["repair_suggestions"].append("Check PDF service - might be using text fallback")
            except UnicodeDecodeError:
                pass  # Binary content is expected
            
            # Check for incomplete PDF
            content = pdf_bytes.decode('latin-1', errors='ignore')
            if '1 0 obj' in content and 'endobj' not in content:
                diagnosis["corruption_detected"] = True
                diagnosis["corruption_type"] = "incomplete_objects"
                diagnosis["corruption_details"].append("PDF objects are incomplete")
                diagnosis["repair_suggestions"].append("Check PDF generation for early termination")
            
            # Check for missing EOF
            if not content.rstrip().endswith('%%EOF'):
                diagnosis["corruption_detected"] = True
                diagnosis["corruption_type"] = "missing_eof"
                diagnosis["corruption_details"].append("PDF does not end with %%EOF")
                diagnosis["repair_suggestions"].append("PDF generation may have been interrupted")
            
        except Exception as e:
            diagnosis["corruption_details"].append(f"Diagnosis failed: {str(e)}")
        
        return diagnosis


def validate_pdf_content(pdf_bytes: bytes) -> Tuple[bool, List[str]]:
    """
    Simple PDF content validation.
    
    Args:
        pdf_bytes: PDF content as bytes
        
    Returns:
        Tuple of (is_valid, error_messages)
    """
    validator = PDFValidator()
    result = validator.validate_pdf_bytes(pdf_bytes)
    
    return result.is_valid, result.errors


def diagnose_pdf_corruption(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Diagnose PDF corruption issues.
    
    Args:
        pdf_bytes: PDF content as bytes
        
    Returns:
        Dict with corruption diagnosis
    """
    validator = PDFValidator()
    return validator.diagnose_corruption(pdf_bytes)


def create_test_pdf_bytes() -> bytes:
    """
    Create minimal test PDF bytes for testing.
    
    Returns:
        bytes: Minimal valid PDF
    """
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000208 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
304
%%EOF"""


if __name__ == "__main__":
    # Test the validator
    validator = PDFValidator()
    
    # Test with minimal PDF
    test_pdf = create_test_pdf_bytes()
    result = validator.validate_pdf_bytes(test_pdf)
    print(result)
    
    # Test corruption diagnosis
    diagnosis = validator.diagnose_corruption(test_pdf)
    print(f"\nCorruption diagnosis: {diagnosis}")