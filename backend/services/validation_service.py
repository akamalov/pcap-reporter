"""
Validation service for PCAP files and analysis job parameters.
"""
import os
import struct
from typing import Dict, List, Optional, Tuple
from fastapi import UploadFile
import logging

from core.config import get_settings

logger = logging.getLogger(__name__)


class PCAPValidationError(Exception):
    """Exception raised for PCAP validation errors."""
    pass


class ValidationService:
    """Service for validating PCAP files and analysis parameters."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # PCAP magic numbers
        self.PCAP_MAGIC_NUMBERS = {
            b'\xd4\xc3\xb2\xa1': 'pcap',      # Standard PCAP
            b'\xa1\xb2\xc3\xd4': 'pcap',      # Swapped PCAP
            b'\x0a\x0d\x0d\x0a': 'pcapng',    # PCAP-NG
            b'\x4d\x3c\x2b\x1a': 'pcapng',    # Alternative PCAP-NG
        }
    
    def validate_file_extension(self, filename: str) -> bool:
        """
        Validate file extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if extension is valid, False otherwise
        """
        if not filename:
            return False
            
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in self.settings.UPLOAD_ALLOWED_EXTENSIONS
    
    def validate_file_size(self, file_size: int) -> bool:
        """
        Validate file size against limits.
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            True if size is within limits, False otherwise
        """
        return 0 < file_size <= self.settings.UPLOAD_MAX_SIZE
    
    async def validate_pcap_file(self, file: UploadFile) -> Dict[str, any]:
        """
        Validate PCAP file format and structure.
        
        Args:
            file: Uploaded file object
            
        Returns:
            Dict with validation results and file info
        """
        try:
            # Reset file position
            await file.seek(0)
            
            # Read first 24 bytes for magic number and header validation
            header = await file.read(24)
            
            if len(header) < 4:
                return {
                    "valid": False,
                    "error": "File too small to be a valid PCAP file",
                    "file_type": None
                }
            
            # Check magic number
            magic = header[:4]
            file_type = self.PCAP_MAGIC_NUMBERS.get(magic)
            
            if not file_type:
                return {
                    "valid": False,
                    "error": "Invalid PCAP magic number",
                    "file_type": None,
                    "magic": magic.hex()
                }
            
            # Additional validation based on file type
            if file_type == 'pcap':
                validation_result = self._validate_pcap_header(header)
            elif file_type == 'pcapng':
                validation_result = self._validate_pcapng_header(header)
            else:
                validation_result = {"valid": False, "error": "Unknown file type"}
            
            # Reset file position
            await file.seek(0)
            
            validation_result.update({
                "file_type": file_type,
                "magic": magic.hex()
            })
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error validating PCAP file: {e}")
            await file.seek(0)  # Reset position on error
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}",
                "file_type": None
            }
    
    def _validate_pcap_header(self, header: bytes) -> Dict[str, any]:
        """
        Validate standard PCAP header.
        
        Args:
            header: First 24 bytes of the file
            
        Returns:
            Dict with validation results
        """
        if len(header) < 24:
            return {"valid": False, "error": "Incomplete PCAP header"}
        
        try:
            # Parse PCAP global header
            magic, version_major, version_minor, thiszone, sigfigs, snaplen, network = struct.unpack('<LHHLLLL', header)
            
            # Validate version
            if version_major != 2 or version_minor != 4:
                return {
                    "valid": False,
                    "error": f"Unsupported PCAP version: {version_major}.{version_minor}"
                }
            
            # Validate snaplen (should be reasonable)
            if snaplen > 65535 or snaplen == 0:
                return {
                    "valid": False,
                    "error": f"Invalid snaplen: {snaplen}"
                }
            
            return {
                "valid": True,
                "version": f"{version_major}.{version_minor}",
                "snaplen": snaplen,
                "network": network
            }
            
        except struct.error as e:
            return {"valid": False, "error": f"Header parsing error: {str(e)}"}
    
    def _validate_pcapng_header(self, header: bytes) -> Dict[str, any]:
        """
        Validate PCAP-NG header.
        
        Args:
            header: First 24 bytes of the file
            
        Returns:
            Dict with validation results
        """
        if len(header) < 12:
            return {"valid": False, "error": "Incomplete PCAP-NG header"}
        
        try:
            # Basic PCAP-NG validation
            # PCAP-NG has more complex structure, doing basic validation
            magic = header[:4]
            if magic == b'\x0a\x0d\x0d\x0a':
                return {"valid": True, "format": "pcap-ng"}
            else:
                return {"valid": False, "error": "Invalid PCAP-NG format"}
                
        except Exception as e:
            return {"valid": False, "error": f"PCAP-NG parsing error: {str(e)}"}
    
    def validate_analysis_options(self, options: Dict) -> Dict[str, any]:
        """
        Validate analysis options and parameters.
        
        Args:
            options: Analysis options dictionary
            
        Returns:
            Dict with validation results and sanitized options
        """
        valid_analysis_types = ["comprehensive", "security_focused", "performance_focused", "basic"]
        valid_priorities = ["low", "normal", "high", "urgent"]
        
        # Set defaults
        sanitized_options = {
            "analysis_type": options.get("analysis_type", "comprehensive"),
            "priority": options.get("priority", "normal"),
            "deep_packet_inspection": options.get("deep_packet_inspection", True),
            "protocol_analysis": options.get("protocol_analysis", True),
            "security_analysis": options.get("security_analysis", True),
            "performance_analysis": options.get("performance_analysis", True),
            "generate_report": options.get("generate_report", True)
        }
        
        errors = []
        
        # Validate analysis type
        if sanitized_options["analysis_type"] not in valid_analysis_types:
            errors.append(f"Invalid analysis_type. Must be one of: {valid_analysis_types}")
        
        # Validate priority
        if sanitized_options["priority"] not in valid_priorities:
            errors.append(f"Invalid priority. Must be one of: {valid_priorities}")
        
        # Apply analysis type specific settings
        if sanitized_options["analysis_type"] == "security_focused":
            sanitized_options.update({
                "malware_detection": True,
                "intrusion_detection": True,
                "vulnerability_scan": True,
                "performance_analysis": False
            })
        elif sanitized_options["analysis_type"] == "performance_focused":
            sanitized_options.update({
                "bandwidth_analysis": True,
                "latency_analysis": True,
                "throughput_analysis": True,
                "security_analysis": False,
                "malware_detection": False
            })
        elif sanitized_options["analysis_type"] == "basic":
            sanitized_options.update({
                "deep_packet_inspection": False,
                "security_analysis": False,
                "performance_analysis": False,
                "malware_detection": False
            })
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "options": sanitized_options
        }
    
    def estimate_completion_time(self, file_size: int, priority: str, analysis_type: str) -> int:
        """
        Estimate analysis completion time in seconds.
        
        Args:
            file_size: Size of the PCAP file in bytes
            priority: Priority level
            analysis_type: Type of analysis
            
        Returns:
            Estimated completion time in seconds
        """
        # Base time calculation (simplified)
        base_time = min(file_size / 1000000, 300)  # 1 second per MB, max 5 minutes base
        
        # Analysis type multiplier
        type_multipliers = {
            "basic": 0.5,
            "comprehensive": 1.0,
            "security_focused": 1.5,
            "performance_focused": 1.2
        }
        
        # Priority multiplier
        priority_multipliers = {
            "urgent": 0.3,
            "high": 0.6,
            "normal": 1.0,
            "low": 2.0
        }
        
        estimated_time = base_time * type_multipliers.get(analysis_type, 1.0) * priority_multipliers.get(priority, 1.0)
        
        return max(int(estimated_time), 30)  # Minimum 30 seconds


# Global validation service instance
validation_service = ValidationService()


def get_validation_service() -> ValidationService:
    """
    Get the validation service instance.
    
    Returns:
        ValidationService instance
    """
    return validation_service 