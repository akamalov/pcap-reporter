"""
Validation service for PCAP files and analysis job parameters.
"""
import os
import struct
import hashlib
import mimetypes
import math
import time
from typing import Dict, List, Optional, Tuple
from fastapi import UploadFile
import logging
from pathlib import Path
from datetime import datetime

from core.config import get_settings

logger = logging.getLogger(__name__)


class PCAPValidationError(Exception):
    """Exception raised for PCAP validation errors."""
    pass


class ValidationService:
    """Service for validating PCAP files and analysis parameters."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # PCAP magic numbers (comprehensive list)
        self.PCAP_MAGIC_NUMBERS = {
            b'\xd4\xc3\xb2\xa1': 'pcap',      # Standard PCAP (little-endian)
            b'\xa1\xb2\xc3\xd4': 'pcap',      # Standard PCAP (big-endian)
            b'\x4d\x3c\xb2\xa1': 'pcap',      # Modified PCAP
            b'\xa1\xb2\x3c\x4d': 'pcap',      # Modified PCAP (big-endian)
            b'\x0a\x0d\x0d\x0a': 'pcapng',    # PCAP-NG Section Header Block
            b'\x4d\x3c\x2b\x1a': 'pcapng',    # Alternative PCAP-NG
            b'\x1a\x2b\x3c\x4d': 'pcapng',    # PCAP-NG (big-endian)
        }
        
        # Suspicious file patterns that might indicate malicious files
        self.SUSPICIOUS_PATTERNS = [
            # Executables
            b'\x4d\x5a',  # PE/EXE header (Windows)
            b'\x7f\x45\x4c\x46',  # ELF header (Linux)
            b'\xca\xfe\xba\xbe',  # Mach-O header (macOS, 64-bit)
            b'\xfe\xed\xfa\xce',  # Mach-O header (macOS, 32-bit)
            b'\xfe\xed\xfa\xcf',  # Mach-O header (macOS, 64-bit)
            b'\xcf\xfa\xed\xfe',  # Mach-O header (reverse)
            
            # Archives and Compressed Files
            b'\x50\x4b\x03\x04',  # ZIP header
            b'\x50\x4b\x05\x06',  # ZIP footer
            b'\x50\x4b\x07\x08',  # ZIP spanned
            b'\x1f\x8b\x08',      # GZIP header
            b'\x42\x5a\x68',      # BZIP2 header
            b'\xfd\x37\x7a\x58\x5a\x00',  # XZ header
            b'\x37\x7a\xbc\xaf\x27\x1c',  # 7-Zip header
            
            # Script files
            b'#!/bin/bash',       # Bash script
            b'#!/bin/sh',         # Shell script
            b'#!/usr/bin/python', # Python script
            b'#!/usr/bin/perl',   # Perl script
            b'<?php',             # PHP script
            
            # Office documents
            b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',  # MS Office (OLE)
            b'\x50\x4b\x03\x04\x14\x00\x06\x00',  # MS Office (new format)
            
            # Media files that shouldn't be PCAP
            b'\xff\xd8\xff',      # JPEG
            b'\x89\x50\x4e\x47',  # PNG
            b'\x47\x49\x46\x38',  # GIF
            b'\x52\x49\x46\x46',  # RIFF (AVI/WAV)
            b'\x00\x00\x00\x18\x66\x74\x79\x70',  # MP4
            
            # Other suspicious patterns
            b'%PDF',              # PDF
            b'\xfe\xff',          # UTF-16 BE BOM
            b'\xff\xfe',          # UTF-16 LE BOM
            b'\xef\xbb\xbf',      # UTF-8 BOM
        ]
        
        # Malware-like patterns in file content
        self.MALWARE_INDICATORS = [
            # Common malware strings
            b'CreateRemoteThread',
            b'VirtualAllocEx', 
            b'WriteProcessMemory',
            b'GetProcAddress',
            b'LoadLibrary',
            b'WinExec',
            b'ShellExecute',
            b'cmd.exe',
            b'powershell.exe',
            b'rundll32.exe',
            
            # Network-related suspicious patterns
            b'nc.exe -l',         # Netcat listener
            b'ncat --exec',       # Ncat execution
            b'/bin/sh -i',        # Interactive shell
            b'bash -i',           # Interactive bash
            b'python -c',         # Python one-liner
            b'exec(',             # Code execution
            b'eval(',             # Code evaluation
            
            # Encryption/Obfuscation indicators
            b'base64',
            b'FromBase64String',
            b'ToBase64String',
            b'CryptoStream',
            b'AES.Create',
            b'DES.Create',
        ]
        
        # File content analysis thresholds
        self.ANALYSIS_THRESHOLDS = {
            'max_entropy': 7.8,           # High entropy indicates encryption/compression
            'min_printable_ratio': 0.1,   # Minimum ratio of printable characters
            'max_null_ratio': 0.9,        # Maximum ratio of null bytes
            'max_repetition_ratio': 0.8,  # Maximum ratio of repeated patterns
            'suspicious_string_limit': 5, # Max suspicious strings before flagging
        }
        
        # Maximum reasonable file size (2GB for enterprise use)
        self.ABSOLUTE_MAX_SIZE = 2 * 1024 * 1024 * 1024
        
        # Minimum PCAP file size (must have at least global header)
        self.MIN_PCAP_SIZE = 24
    
    def validate_file_extension(self, filename: str) -> bool:
        """
        Validate file extension and check for suspicious patterns.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if extension is valid, False otherwise
        """
        if not filename:
            return False
        
        # Basic security check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Potential path traversal attempt in filename: {filename}")
            return False
        
        # Check for null bytes
        if '\x00' in filename:
            logger.warning(f"Null byte detected in filename: {filename}")
            return False
            
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in self.settings.UPLOAD_ALLOWED_EXTENSIONS
    
    def validate_file_size(self, file_size: int) -> Dict[str, any]:
        """
        Validate file size against limits with detailed response.
        
        Args:
            file_size: Size of the file in bytes
            
        Returns:
            Dict with validation results and details
        """
        if file_size <= 0:
            return {
                "valid": False,
                "error": "File is empty or invalid",
                "size": file_size
            }
        
        if file_size < self.MIN_PCAP_SIZE:
            return {
                "valid": False,
                "error": f"File too small for PCAP format (minimum {self.MIN_PCAP_SIZE} bytes)",
                "size": file_size
            }
        
        if file_size > self.ABSOLUTE_MAX_SIZE:
            return {
                "valid": False,
                "error": f"File exceeds absolute maximum size ({self.ABSOLUTE_MAX_SIZE // (1024*1024*1024)}GB)",
                "size": file_size
            }
        
        if file_size > self.settings.UPLOAD_MAX_SIZE:
            return {
                "valid": False,
                "error": f"File exceeds configured maximum size ({self.settings.UPLOAD_MAX_SIZE // (1024*1024)}MB)",
                "size": file_size
            }
        
        return {
            "valid": True,
            "size": file_size,
            "size_mb": round(file_size / (1024*1024), 2)
        }
    
    async def validate_pcap_file(self, file: UploadFile, check_content: bool = True) -> Dict[str, any]:
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
            
            # Read first 1024 bytes for comprehensive validation
            header_chunk = await file.read(1024)
            
            if len(header_chunk) < 4:
                return {
                    "valid": False,
                    "error": "File too small to be a valid PCAP file",
                    "file_type": None
                }
            
            # Security check: scan for suspicious patterns
            security_check = self._check_file_security(header_chunk)
            if not security_check["safe"]:
                return {
                    "valid": False,
                    "error": f"Security check failed: {security_check['reason']}",
                    "file_type": None,
                    "security_issue": True
                }
            
            # Extract just the header for format validation
            header = header_chunk[:24]
            
            # Check magic number
            magic = header[:4]
            file_type = self.PCAP_MAGIC_NUMBERS.get(magic)
            
            if not file_type:
                # Check if this might be a different file format
                format_guess = self._guess_file_format(header)
                return {
                    "valid": False,
                    "error": "Invalid PCAP magic number",
                    "file_type": None,
                    "magic": magic.hex(),
                    "possible_format": format_guess
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
    
    def _check_file_security(self, file_data: bytes) -> Dict[str, any]:
        """
        Comprehensive security check for file data including advanced malware detection.
        
        Args:
            file_data: First chunk of file data
            
        Returns:
            Dict with security check results
        """
        security_issues = []
        
        # Check for suspicious file headers
        for pattern in self.SUSPICIOUS_PATTERNS:
            if file_data.startswith(pattern):
                security_issues.append(f"Suspicious file header: {pattern.hex()}")
        
        # Check for malware indicators
        malware_count = 0
        detected_indicators = []
        for indicator in self.MALWARE_INDICATORS:
            if indicator in file_data:
                malware_count += 1
                detected_indicators.append(indicator.decode('utf-8', errors='ignore'))
                
        if malware_count >= self.ANALYSIS_THRESHOLDS['suspicious_string_limit']:
            security_issues.append(f"Multiple malware indicators detected: {detected_indicators[:3]}...")
        
        # Advanced content analysis
        content_analysis = self._analyze_file_content(file_data)
        if not content_analysis["safe"]:
            security_issues.extend(content_analysis["issues"])
        
        # Entropy analysis (detect encryption/compression)
        entropy = self._calculate_entropy(file_data)
        if entropy > self.ANALYSIS_THRESHOLDS['max_entropy']:
            security_issues.append(f"High entropy detected ({entropy:.2f}) - possible encryption/obfuscation")
        
        # Pattern analysis
        pattern_analysis = self._analyze_suspicious_patterns(file_data)
        if pattern_analysis["suspicious"]:
            security_issues.extend(pattern_analysis["issues"])
        
        # File structure validation
        structure_check = self._validate_file_structure(file_data)
        if not structure_check["valid"]:
            security_issues.append(structure_check["issue"])
        
        if security_issues:
            return {
                "safe": False,
                "reason": "; ".join(security_issues[:3]),  # Limit to first 3 issues
                "all_issues": security_issues,
                "severity": self._assess_security_severity(security_issues)
            }
        
        return {
            "safe": True, 
            "reason": "No security issues detected",
            "entropy": entropy,
            "malware_indicators": malware_count
        }
    
    def _analyze_file_content(self, file_data: bytes) -> Dict[str, any]:
        """
        Analyze file content for suspicious characteristics.
        
        Args:
            file_data: File data to analyze
            
        Returns:
            Dict with analysis results
        """
        issues = []
        
        # Check null byte ratio
        null_count = file_data.count(b'\x00')
        null_ratio = null_count / len(file_data) if len(file_data) > 0 else 0
        
        if null_ratio > self.ANALYSIS_THRESHOLDS['max_null_ratio']:
            issues.append(f"Excessive null bytes ({null_ratio:.2%}) - potential padding attack")
        
        # Check printable character ratio
        printable_count = sum(1 for b in file_data if 32 <= b <= 126)
        printable_ratio = printable_count / len(file_data) if len(file_data) > 0 else 0
        
        # For PCAP files, we expect mostly binary data, so very high printable ratio is suspicious
        if printable_ratio > 0.8:  # More than 80% printable suggests text file
            issues.append(f"High printable character ratio ({printable_ratio:.2%}) - suspicious for PCAP")
        
        # Check for repetitive patterns
        repetition_issues = self._check_repetitive_patterns(file_data)
        if repetition_issues:
            issues.extend(repetition_issues)
        
        # Check for embedded files (polyglot detection)
        embedded_file_check = self._check_embedded_files(file_data)
        if embedded_file_check["found"]:
            issues.append(f"Embedded file detected: {embedded_file_check['type']}")
        
        return {
            "safe": len(issues) == 0,
            "issues": issues,
            "null_ratio": null_ratio,
            "printable_ratio": printable_ratio
        }
    
    def _calculate_entropy(self, data: bytes) -> float:
        """
        Calculate Shannon entropy of data.
        
        Args:
            data: Data to analyze
            
        Returns:
            Entropy value (0-8, where 8 is maximum randomness)
        """
        if not data:
            return 0.0
        
        # Count byte frequencies
        byte_counts = [0] * 256
        for byte in data:
            byte_counts[byte] += 1
        
        # Calculate entropy
        data_len = len(data)
        entropy = 0.0
        
        for count in byte_counts:
            if count > 0:
                probability = count / data_len
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def _check_repetitive_patterns(self, file_data: bytes) -> List[str]:
        """
        Check for suspicious repetitive patterns.
        
        Args:
            file_data: File data to check
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Check for long runs of identical bytes
        for i in range(min(len(file_data) - 100, 1000)):  # Check first 1000 positions
            if len(set(file_data[i:i+100])) == 1:  # 100 identical bytes
                issues.append("Long repetitive pattern detected (potential padding)")
                break
        
        # Check for simple patterns (AAAA, ABAB, etc.)
        if len(file_data) >= 1000:
            sample = file_data[:1000]
            
            # Check for AAAA pattern
            if b'\xaa\xaa\xaa\xaa' in sample or b'\x00\x00\x00\x00' in sample:
                issues.append("Simple repetitive pattern detected")
                
            # Check for ABAB pattern
            for i in range(0, min(len(sample) - 8, 100), 4):
                pattern = sample[i:i+4]
                if sample[i+4:i+8] == pattern and len(set(pattern)) <= 2:
                    issues.append("Alternating pattern detected")
                    break
        
        return issues
    
    def _check_embedded_files(self, file_data: bytes) -> Dict[str, any]:
        """
        Check for embedded files (polyglot attack detection).
        
        Args:
            file_data: File data to check
            
        Returns:
            Dict with detection results
        """
        # Look for secondary file headers within the data
        secondary_headers = [
            (b'\x4d\x5a', 'PE executable'),
            (b'\x7f\x45\x4c\x46', 'ELF executable'),
            (b'\x50\x4b\x03\x04', 'ZIP archive'),
            (b'%PDF', 'PDF document'),
            (b'\xff\xd8\xff', 'JPEG image'),
        ]
        
        # Skip the first 100 bytes (might be legitimate PCAP header)
        search_data = file_data[100:] if len(file_data) > 100 else b''
        
        for header, file_type in secondary_headers:
            if header in search_data:
                return {"found": True, "type": file_type}
        
        return {"found": False, "type": None}
    
    def _analyze_suspicious_patterns(self, file_data: bytes) -> Dict[str, any]:
        """
        Analyze file for suspicious patterns and anomalies.
        
        Args:
            file_data: File data to analyze
            
        Returns:
            Dict with analysis results
        """
        issues = []
        
        # Check for suspicious byte sequences
        suspicious_sequences = [
            b'\x90\x90\x90\x90',  # NOP sled (common in exploits)
            b'\xcc\xcc\xcc\xcc',  # INT3 padding
            b'\xde\xad\xbe\xef',  # DEADBEEF marker
            b'\xca\xfe\xba\xbe',  # CAFEBABE marker
        ]
        
        for sequence in suspicious_sequences:
            if sequence in file_data:
                issues.append(f"Suspicious byte sequence detected: {sequence.hex()}")
        
        # Check for unusual alignment patterns
        if len(file_data) >= 1024:
            # Check if data is suspiciously aligned
            aligned_nulls = sum(1 for i in range(0, min(len(file_data), 1024), 4) 
                              if file_data[i:i+4] == b'\x00\x00\x00\x00')
            
            if aligned_nulls > 50:  # More than 50 aligned null DWORDs
                issues.append("Suspicious alignment patterns detected")
        
        return {
            "suspicious": len(issues) > 0,
            "issues": issues
        }
    
    def _validate_file_structure(self, file_data: bytes) -> Dict[str, any]:
        """
        Validate that the file structure makes sense for a PCAP file.
        
        Args:
            file_data: File data to validate
            
        Returns:
            Dict with validation results
        """
        if len(file_data) < 24:
            return {"valid": False, "issue": "File too small for valid PCAP header"}
        
        # Check if it starts with a valid PCAP magic number
        magic = file_data[:4]
        if magic not in self.PCAP_MAGIC_NUMBERS:
            return {"valid": False, "issue": "Invalid PCAP magic number"}
        
        # For PCAP files, validate basic structure
        if self.PCAP_MAGIC_NUMBERS[magic] == 'pcap':
            try:
                # Parse basic header to ensure it's reasonable
                _, version_major, version_minor, _, _, snaplen, _ = struct.unpack('<LHHLLLL', file_data[:24])
                
                # Validate version numbers
                if version_major != 2 or version_minor != 4:
                    return {"valid": False, "issue": f"Invalid PCAP version: {version_major}.{version_minor}"}
                
                # Validate snaplen
                if snaplen > 262144 or snaplen == 0:  # 256KB max snaplen
                    return {"valid": False, "issue": f"Suspicious snaplen value: {snaplen}"}
                
            except struct.error:
                return {"valid": False, "issue": "Corrupted PCAP header structure"}
        
        return {"valid": True, "issue": None}
    
    def _assess_security_severity(self, issues: List[str]) -> str:
        """
        Assess the severity of security issues found.
        
        Args:
            issues: List of security issues
            
        Returns:
            Severity level string
        """
        high_risk_keywords = ['malware', 'executable', 'exploit', 'suspicious']
        medium_risk_keywords = ['entropy', 'pattern', 'embedded']
        
        high_count = sum(1 for issue in issues if any(keyword in issue.lower() for keyword in high_risk_keywords))
        medium_count = sum(1 for issue in issues if any(keyword in issue.lower() for keyword in medium_risk_keywords))
        
        if high_count >= 2:
            return "critical"
        elif high_count >= 1:
            return "high"
        elif medium_count >= 2:
            return "medium"
        else:
            return "low"
    
    def _guess_file_format(self, header: bytes) -> Optional[str]:
        """
        Try to guess the actual file format if it's not a valid PCAP.
        
        Args:
            header: First bytes of the file
            
        Returns:
            String description of possible format, or None
        """
        if header.startswith(b'\x50\x4b\x03\x04'):
            return "ZIP archive"
        elif header.startswith(b'\x1f\x8b\x08'):
            return "GZIP compressed file"
        elif header.startswith(b'\x4d\x5a'):
            return "Windows executable (PE)"
        elif header.startswith(b'\x7f\x45\x4c\x46'):
            return "Linux executable (ELF)"
        elif header.startswith(b'\xff\xd8\xff'):
            return "JPEG image"
        elif header.startswith(b'\x89\x50\x4e\x47'):
            return "PNG image"
        elif header.startswith(b'%PDF'):
            return "PDF document"
        elif header[:4].isascii() and header[:4].isprintable():
            return "Text file"
        else:
            return "Unknown binary format"
    
    async def comprehensive_file_validation(self, file: UploadFile, client_ip: str = "unknown") -> Dict[str, any]:
        """
        Perform comprehensive validation including security, integrity, and format checks.
        
        Args:
            file: Uploaded file object
            client_ip: Client IP address for audit trail
            
        Returns:
            Comprehensive validation results
        """
        validation_start = time.time()
        validation_id = hashlib.md5(f"{file.filename}{time.time()}".encode()).hexdigest()[:8]
        
        logger.info(f"Starting comprehensive validation {validation_id} for file: {file.filename} from {client_ip}")
        
        try:
            # Step 1: Basic file validation
            if not file or not file.filename:
                return self._create_validation_result(False, "No file provided", validation_id, client_ip)
            
            # Step 2: Extension and name validation
            extension_valid = self.validate_file_extension(file.filename)
            if not extension_valid:
                self._log_security_event("invalid_extension", file.filename, client_ip, validation_id)
                return self._create_validation_result(False, "Invalid file extension", validation_id, client_ip)
            
            # Step 3: Read file content for analysis
            await file.seek(0)
            content = await file.read()
            file_size = len(content)
            
            # Step 4: Size validation
            size_validation = self.validate_file_size(file_size)
            if not size_validation["valid"]:
                self._log_security_event("invalid_size", file.filename, client_ip, validation_id, 
                                       extra_data={"size": file_size})
                return self._create_validation_result(False, size_validation["error"], validation_id, client_ip)
            
            # Step 5: Content-based security analysis
            await file.seek(0)
            security_check = self._check_file_security(content[:8192])  # First 8KB for analysis
            
            if not security_check["safe"]:
                severity = security_check.get("severity", "medium")
                self._log_security_event("security_threat", file.filename, client_ip, validation_id, 
                                       extra_data={
                                           "issues": security_check["all_issues"],
                                           "severity": severity
                                       })
                return self._create_validation_result(False, f"Security threat detected: {security_check['reason']}", 
                                                    validation_id, client_ip, severity=severity)
            
            # Step 6: PCAP format validation
            await file.seek(0)
            pcap_validation = await self.validate_pcap_file(file, check_content=True)
            
            if not pcap_validation["valid"]:
                self._log_security_event("invalid_format", file.filename, client_ip, validation_id,
                                       extra_data={"error": pcap_validation["error"]})
                return self._create_validation_result(False, pcap_validation["error"], validation_id, client_ip)
            
            # Step 7: Calculate file hash for integrity
            file_hash = self.calculate_file_hash_from_content(content)
            
            # Step 8: Deep content analysis (for larger files)
            deep_analysis = {}
            if file_size > 1024:  # Only for files > 1KB
                deep_analysis = self._perform_deep_content_analysis(content)
                if not deep_analysis["safe"]:
                    self._log_security_event("deep_analysis_threat", file.filename, client_ip, validation_id,
                                           extra_data=deep_analysis["details"])
                    return self._create_validation_result(False, f"Deep analysis failed: {deep_analysis['reason']}", 
                                                        validation_id, client_ip, severity="high")
            
            # Step 9: Generate validation report
            validation_time = time.time() - validation_start
            
            self._log_security_event("validation_success", file.filename, client_ip, validation_id,
                                   extra_data={
                                       "file_size": file_size,
                                       "file_hash": file_hash,
                                       "validation_time": validation_time,
                                       "file_type": pcap_validation["file_type"]
                                   })
            
            # Reset file position
            await file.seek(0)
            
            return {
                "valid": True,
                "validation_id": validation_id,
                "file_info": {
                    "filename": file.filename,
                    "size": file_size,
                    "size_mb": round(file_size / (1024*1024), 2),
                    "hash": file_hash,
                    "type": pcap_validation["file_type"],
                    "magic": pcap_validation.get("magic")
                },
                "security_analysis": {
                    "entropy": security_check.get("entropy", 0),
                    "malware_indicators": security_check.get("malware_indicators", 0),
                    "threats_detected": 0,
                    "severity": "safe"
                },
                "validation_metrics": {
                    "validation_time": validation_time,
                    "checks_performed": 9,
                    "timestamp": datetime.utcnow().isoformat()
                },
                "deep_analysis": deep_analysis if deep_analysis else {"performed": False}
            }
            
        except Exception as e:
            logger.error(f"Validation error {validation_id}: {e}")
            self._log_security_event("validation_error", file.filename if file else "unknown", client_ip, validation_id,
                                   extra_data={"error": str(e)})
            return self._create_validation_result(False, f"Validation error: {str(e)}", validation_id, client_ip)
    
    def _create_validation_result(self, valid: bool, message: str, validation_id: str, client_ip: str, 
                                 severity: str = "medium") -> Dict[str, any]:
        """Create a standardized validation result."""
        return {
            "valid": valid,
            "validation_id": validation_id,
            "message": message,
            "severity": severity,
            "client_ip": client_ip,
            "timestamp": datetime.utcnow().isoformat(),
            "file_info": None,
            "security_analysis": None
        }
    
    def _log_security_event(self, event_type: str, filename: str, client_ip: str, validation_id: str, 
                           extra_data: Dict = None):
        """Log security events for audit trail."""
        event_data = {
            "event_type": event_type,
            "filename": filename,
            "client_ip": client_ip,
            "validation_id": validation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "extra_data": extra_data or {}
        }
        
        # Log at appropriate level based on event type
        if event_type in ["security_threat", "deep_analysis_threat"]:
            logger.warning(f"SECURITY EVENT: {event_data}")
        elif event_type in ["validation_error"]:
            logger.error(f"VALIDATION ERROR: {event_data}")
        else:
            logger.info(f"VALIDATION EVENT: {event_data}")
    
    def _perform_deep_content_analysis(self, content: bytes) -> Dict[str, any]:
        """
        Perform deep analysis on file content for advanced threat detection.
        
        Args:
            content: Full file content
            
        Returns:
            Deep analysis results
        """
        try:
            analysis_results = {
                "safe": True,
                "reason": "",
                "details": {},
                "performed": True
            }
            
            # Advanced entropy analysis across file sections
            section_entropies = self._analyze_section_entropies(content)
            if section_entropies["suspicious"]:
                analysis_results["safe"] = False
                analysis_results["reason"] = "Suspicious entropy distribution detected"
                analysis_results["details"]["entropy_analysis"] = section_entropies
            
            # Check for steganography indicators
            stego_check = self._check_steganography_indicators(content)
            if stego_check["suspicious"]:
                analysis_results["safe"] = False
                analysis_results["reason"] = "Possible steganography detected"
                analysis_results["details"]["steganography"] = stego_check
            
            # Advanced malware signature scanning
            malware_scan = self._advanced_malware_scan(content)
            if malware_scan["threats_found"] > 0:
                analysis_results["safe"] = False
                analysis_results["reason"] = f"Malware signatures detected: {malware_scan['threats_found']}"
                analysis_results["details"]["malware_scan"] = malware_scan
            
            # File format consistency check
            format_check = self._deep_format_validation(content)
            if not format_check["consistent"]:
                analysis_results["safe"] = False
                analysis_results["reason"] = "File format inconsistencies detected"
                analysis_results["details"]["format_check"] = format_check
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Deep content analysis error: {e}")
            return {
                "safe": False,
                "reason": f"Deep analysis failed: {str(e)}",
                "details": {"error": str(e)},
                "performed": False
            }
    
    def _analyze_section_entropies(self, content: bytes) -> Dict[str, any]:
        """Analyze entropy across different sections of the file."""
        if len(content) < 1024:
            return {"suspicious": False, "reason": "File too small for section analysis"}
        
        section_size = len(content) // 10  # Divide into 10 sections
        entropies = []
        
        for i in range(10):
            start = i * section_size
            end = start + section_size if i < 9 else len(content)
            section = content[start:end]
            entropy = self._calculate_entropy(section)
            entropies.append(entropy)
        
        # Check for suspicious patterns
        high_entropy_sections = sum(1 for e in entropies if e > 7.5)
        entropy_variance = sum((e - sum(entropies)/len(entropies))**2 for e in entropies) / len(entropies)
        
        suspicious = False
        issues = []
        
        if high_entropy_sections > 7:  # More than 70% high entropy
            suspicious = True
            issues.append("Excessive high-entropy sections")
        
        if entropy_variance > 2.0:  # High variance in entropy
            suspicious = True
            issues.append("Unusual entropy distribution")
        
        return {
            "suspicious": suspicious,
            "issues": issues,
            "entropies": entropies,
            "high_entropy_sections": high_entropy_sections,
            "variance": entropy_variance
        }
    
    def _check_steganography_indicators(self, content: bytes) -> Dict[str, any]:
        """Check for indicators of steganographic content."""
        indicators = []
        
        # Check for unusual patterns that might indicate hidden data
        if len(content) > 1000:
            # Check for LSB steganography patterns
            lsb_pattern = sum(1 for i in range(0, min(len(content), 1000)) if content[i] & 1)
            lsb_ratio = lsb_pattern / min(len(content), 1000)
            
            # In normal files, LSB should be roughly 50%
            if abs(lsb_ratio - 0.5) > 0.1:  # Deviation > 10%
                indicators.append("Unusual LSB distribution")
        
        # Check for metadata anomalies
        if len(content) > 100:
            # Look for unusual padding or trailer data
            trailing_nulls = 0
            for i in range(len(content) - 1, max(len(content) - 100, 0), -1):
                if content[i] == 0:
                    trailing_nulls += 1
                else:
                    break
            
            if trailing_nulls > 50:  # Unusual amount of trailing nulls
                indicators.append("Excessive trailing null bytes")
        
        return {
            "suspicious": len(indicators) > 0,
            "indicators": indicators
        }
    
    def _advanced_malware_scan(self, content: bytes) -> Dict[str, any]:
        """Advanced malware signature scanning."""
        threats_found = 0
        detected_signatures = []
        
        # Extended malware signatures
        advanced_signatures = [
            # Shellcode patterns
            (b'\x31\xc0\x50\x68', "Shellcode pattern"),
            (b'\x89\xe5\x31\xc0', "Stack manipulation"),
            (b'\x31\xdb\x8d\x43', "Register clearing pattern"),
            
            # Exploit techniques
            (b'AAAA' * 10, "Buffer overflow pattern"),
            (b'\x90' * 20, "NOP sled"),
            (b'\xeb\xfe', "Infinite loop"),
            
            # Advanced persistence
            (b'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run', "Registry persistence"),
            (b'CreateProcess', "Process creation"),
            (b'VirtualProtect', "Memory protection manipulation"),
        ]
        
        for signature, description in advanced_signatures:
            if signature in content:
                threats_found += 1
                detected_signatures.append(description)
        
        return {
            "threats_found": threats_found,
            "signatures": detected_signatures
        }
    
    def _deep_format_validation(self, content: bytes) -> Dict[str, any]:
        """Perform deep PCAP format validation."""
        if len(content) < 24:
            return {"consistent": False, "issues": ["File too small"]}
        
        issues = []
        
        # Validate PCAP header consistency
        magic = content[:4]
        if magic in self.PCAP_MAGIC_NUMBERS:
            file_type = self.PCAP_MAGIC_NUMBERS[magic]
            
            if file_type == 'pcap':
                # Deep PCAP validation
                try:
                    header = struct.unpack('<LHHLLLL', content[:24])
                    _, major, minor, zone, sig, snaplen, network = header
                    
                    # Check for reasonable values
                    if not (1 <= major <= 10 and 0 <= minor <= 10):
                        issues.append("Invalid version numbers")
                    
                    if snaplen > 1000000:  # 1MB snaplen is excessive
                        issues.append("Excessive snaplen value")
                    
                    if network > 1000:  # Most network types are < 1000
                        issues.append("Unusual network type")
                        
                except struct.error:
                    issues.append("Corrupted PCAP header")
        
        return {
            "consistent": len(issues) == 0,
            "issues": issues
        }
    
    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA256 hash of a file for integrity verification.
        
        Args:
            file_path: Path to the file
            
        Returns:
            SHA256 hash as hex string
        """
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def calculate_file_hash_from_content(self, content: bytes) -> str:
        """
        Calculate SHA256 hash from file content.
        
        Args:
            content: File content as bytes
            
        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(content).hexdigest()
    
    def validate_file_path(self, file_path: str) -> Dict[str, any]:
        """
        Validate that a file path is safe and accessible.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Dict with validation results
        """
        try:
            path_obj = Path(file_path)
            
            # Check if path exists
            if not path_obj.exists():
                return {
                    "valid": False,
                    "error": "File does not exist",
                    "path": file_path
                }
            
            # Check if it's a file (not directory)
            if not path_obj.is_file():
                return {
                    "valid": False,
                    "error": "Path is not a file",
                    "path": file_path
                }
            
            # Check file permissions
            if not os.access(file_path, os.R_OK):
                return {
                    "valid": False,
                    "error": "File is not readable",
                    "path": file_path
                }
            
            # Get file stats
            stat = path_obj.stat()
            
            return {
                "valid": True,
                "path": file_path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "readable": True
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Path validation error: {str(e)}",
                "path": file_path
            }


# Global validation service instance (lazy initialization)
_validation_service_instance = None


def get_validation_service() -> ValidationService:
    """
    Get the validation service instance with lazy initialization.
    
    Returns:
        ValidationService instance
    """
    global _validation_service_instance
    if _validation_service_instance is None:
        _validation_service_instance = ValidationService()
    return _validation_service_instance 