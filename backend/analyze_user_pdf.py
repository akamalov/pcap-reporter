#!/usr/bin/env python3
"""
USER PDF DIAGNOSTIC TOOL
Analyzes the user's specific corrupted PDF file and compares it with
a properly generated PDF to identify the exact corruption issue.
"""

import os
import sys
import hashlib
import subprocess
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# Add backend to path
sys.path.append("/home/akamalov/projects/pcap-reporter/backend")

class UserPDFDiagnostic:
    """Diagnostic tool for user's specific PDF corruption issue."""
    
    def __init__(self, user_pdf_path: str = "/mnt/d/tmp/analysis_report_analysis_report.pdf"):
        """Initialize with user's PDF path."""
        self.user_pdf_path = user_pdf_path
        self.analysis_results = []
        self.corruption_details = []
        
    def log_analysis(self, test_name: str, result: str, details: str = ""):
        """Log analysis result."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] 📊 {test_name}")
        print(f"    Result: {result}")
        if details:
            print(f"    Details: {details}")
        
        self.analysis_results.append({
            "test": test_name,
            "result": result,
            "details": details,
            "timestamp": timestamp
        })
    
    def analyze_user_pdf(self) -> Dict:
        """Analyze the user's corrupted PDF file."""
        print(f"🔍 Analyzing user PDF: {self.user_pdf_path}")
        
        analysis = {
            "file_exists": False,
            "file_size": 0,
            "file_hash": "",
            "pdf_signature": False,
            "pdf_structure": {},
            "binary_content": b"",
            "readable_content": "",
            "corruption_type": "unknown"
        }
        
        # Check if file exists
        if not os.path.exists(self.user_pdf_path):
            self.log_analysis("File Existence", "❌ FILE NOT FOUND", 
                            f"Cannot find file at {self.user_pdf_path}")
            return analysis
        
        analysis["file_exists"] = True
        analysis["file_size"] = os.path.getsize(self.user_pdf_path)
        
        self.log_analysis("File Existence", "✅ FILE FOUND", 
                         f"Size: {analysis['file_size']} bytes")
        
        # Read file content
        try:
            with open(self.user_pdf_path, 'rb') as f:
                analysis["binary_content"] = f.read()
            
            analysis["file_hash"] = hashlib.md5(analysis["binary_content"]).hexdigest()
            
            self.log_analysis("File Reading", "✅ FILE READ", 
                             f"Hash: {analysis['file_hash'][:16]}...")
            
        except Exception as e:
            self.log_analysis("File Reading", "❌ READ ERROR", f"Error: {e}")
            return analysis
        
        # Check PDF signature
        content = analysis["binary_content"]
        if content.startswith(b'%PDF-'):
            analysis["pdf_signature"] = True
            # Extract PDF version
            version_line = content.split(b'\\n')[0] if b'\\n' in content else content[:20]
            self.log_analysis("PDF Signature", "✅ VALID PDF SIGNATURE", 
                             f"Header: {version_line}")
        else:
            analysis["pdf_signature"] = False
            # Show first 50 bytes for analysis
            first_bytes = content[:50]
            try:
                readable_start = first_bytes.decode('utf-8', errors='replace')
            except:
                readable_start = str(first_bytes)
            
            self.log_analysis("PDF Signature", "❌ INVALID PDF SIGNATURE", 
                             f"Starts with: {readable_start}")
            analysis["corruption_type"] = "invalid_signature"
        
        # Check PDF structure
        structure_tests = [
            ("PDF Header", content.startswith(b'%PDF-')),
            ("PDF Trailer", b'%%EOF' in content),
            ("PDF Objects", b'obj' in content and b'endobj' in content),
            ("PDF Xref", b'xref' in content or b'/XRef' in content),
            ("PDF Catalog", b'/Catalog' in content),
            ("PDF Pages", b'/Pages' in content),
            ("PDF Info", b'/Info' in content),
            ("PDF Root", b'/Root' in content)
        ]
        
        passed_tests = 0
        for test_name, test_result in structure_tests:
            analysis["pdf_structure"][test_name] = test_result
            if test_result:
                passed_tests += 1
        
        self.log_analysis("PDF Structure", f"✅ {passed_tests}/{len(structure_tests)} TESTS PASSED", 
                         f"Structure integrity: {(passed_tests/len(structure_tests))*100:.1f}%")
        
        # Check for common corruption patterns
        if content.startswith(b'%PDF-') and not b'%%EOF' in content:
            analysis["corruption_type"] = "truncated_file"
            self.log_analysis("Corruption Type", "⚠️  TRUNCATED FILE", 
                             "PDF header present but missing trailer")
        
        elif b'%%EOF' in content and not content.startswith(b'%PDF-'):
            analysis["corruption_type"] = "missing_header"
            self.log_analysis("Corruption Type", "⚠️  MISSING HEADER", 
                             "PDF trailer present but missing header")
        
        elif analysis["file_size"] == 0:
            analysis["corruption_type"] = "empty_file"
            self.log_analysis("Corruption Type", "⚠️  EMPTY FILE", 
                             "File exists but has zero size")
        
        elif analysis["file_size"] < 1000:
            analysis["corruption_type"] = "too_small"
            self.log_analysis("Corruption Type", "⚠️  FILE TOO SMALL", 
                             f"File size {analysis['file_size']} bytes is too small for valid PDF")
        
        # Try to extract readable text
        try:
            # Look for readable text in the file
            readable_parts = []
            for i in range(0, min(len(content), 10000), 100):
                chunk = content[i:i+100]
                try:
                    decoded = chunk.decode('utf-8', errors='ignore')
                    if decoded.strip() and len(decoded.strip()) > 5:
                        readable_parts.append(decoded.strip())
                except:
                    pass
            
            if readable_parts:
                analysis["readable_content"] = " | ".join(readable_parts[:5])
                self.log_analysis("Readable Content", "✅ FOUND READABLE TEXT", 
                                 f"Sample: {analysis['readable_content'][:100]}...")
            else:
                self.log_analysis("Readable Content", "❌ NO READABLE TEXT", 
                                 "File appears to be binary or corrupted")
        except Exception as e:
            self.log_analysis("Readable Content", "❌ EXTRACTION ERROR", f"Error: {e}")
        
        return analysis
    
    def test_external_tools(self) -> Dict:
        """Test the user's PDF with external tools."""
        print(f"\n🔧 Testing with external tools...")
        
        results = {
            "file_command": None,
            "pdfinfo": None,
            "strings": None,
            "hexdump": None
        }
        
        # Test with file command
        try:
            result = subprocess.run(['file', self.user_pdf_path], 
                                  capture_output=True, text=True, timeout=10)
            results["file_command"] = result.stdout.strip()
            
            if "PDF" in result.stdout:
                self.log_analysis("File Command", "✅ RECOGNIZED AS PDF", result.stdout.strip())
            else:
                self.log_analysis("File Command", "❌ NOT RECOGNIZED AS PDF", result.stdout.strip())
        except Exception as e:
            self.log_analysis("File Command", "❌ TOOL ERROR", f"Error: {e}")
        
        # Test with pdfinfo
        try:
            result = subprocess.run(['pdfinfo', self.user_pdf_path], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results["pdfinfo"] = result.stdout
                self.log_analysis("pdfinfo", "✅ PDF INFO EXTRACTED", "PDF appears valid to pdfinfo")
            else:
                results["pdfinfo"] = result.stderr
                self.log_analysis("pdfinfo", "❌ PDF INFO FAILED", result.stderr.strip())
        except Exception as e:
            self.log_analysis("pdfinfo", "❌ TOOL NOT AVAILABLE", f"Error: {e}")
        
        # Test with strings command
        try:
            result = subprocess.run(['strings', self.user_pdf_path], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                strings_output = result.stdout[:500]  # First 500 chars
                results["strings"] = strings_output
                self.log_analysis("Strings Command", "✅ STRINGS EXTRACTED", 
                                 f"Found {len(result.stdout.split())} strings")
            else:
                self.log_analysis("Strings Command", "❌ STRINGS FAILED", "No strings found")
        except Exception as e:
            self.log_analysis("Strings Command", "❌ TOOL ERROR", f"Error: {e}")
        
        # Test with hexdump (first 200 bytes)
        try:
            result = subprocess.run(['hexdump', '-C', '-n', '200', self.user_pdf_path], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                results["hexdump"] = result.stdout
                self.log_analysis("Hexdump", "✅ HEX DUMP GENERATED", 
                                 f"First 200 bytes analyzed")
            else:
                self.log_analysis("Hexdump", "❌ HEX DUMP FAILED", "Could not generate hex dump")
        except Exception as e:
            self.log_analysis("Hexdump", "❌ TOOL ERROR", f"Error: {e}")
        
        return results
    
    def generate_comparison_pdf(self) -> Optional[str]:
        """Generate a comparison PDF using the current system."""
        print(f"\n🔧 Generating comparison PDF...")
        
        try:
            # Create realistic test data
            from services.pdf_export import PDFExportService
            
            # Create test data similar to what would generate a real report
            test_data = {
                "job_id": "comparison-test",
                "filename": "comparison_test.pcap",
                "status": "completed",
                "total_packets": 5000,
                "unique_ips": 100,
                "unique_ports": 150,
                "duration": 300.0,
                "file_size": 2048000,
                "protocols": {
                    "TCP": 3000,
                    "UDP": 1500,
                    "ICMP": 400,
                    "HTTP": 100
                },
                "processing_time": 45.2,
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:05:00Z",
                "analysis_results": {
                    "network_diagrams": None
                }
            }
            
            # Generate PDF
            service = PDFExportService()
            html_content = service.generate_html_template(test_data)
            pdf_bytes = service._fallback_pdf_generation(html_content)
            
            # Save comparison PDF
            comparison_path = "/tmp/comparison_pdf.pdf"
            with open(comparison_path, 'wb') as f:
                f.write(pdf_bytes)
            
            self.log_analysis("Comparison PDF", "✅ GENERATED", 
                             f"Generated {len(pdf_bytes)} bytes at {comparison_path}")
            
            return comparison_path
            
        except Exception as e:
            self.log_analysis("Comparison PDF", "❌ GENERATION FAILED", f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def compare_with_working_pdf(self, comparison_path: str) -> Dict:
        """Compare user's PDF with working PDF."""
        print(f"\n🔍 Comparing with working PDF...")
        
        comparison = {
            "size_match": False,
            "hash_match": False,
            "header_match": False,
            "structure_match": False,
            "differences": []
        }
        
        try:
            # Read both files
            with open(self.user_pdf_path, 'rb') as f:
                user_content = f.read()
            
            with open(comparison_path, 'rb') as f:
                comparison_content = f.read()
            
            # Compare sizes
            user_size = len(user_content)
            comparison_size = len(comparison_content)
            comparison["size_match"] = user_size == comparison_size
            
            if comparison["size_match"]:
                self.log_analysis("Size Comparison", "✅ SIZES MATCH", 
                                 f"Both files are {user_size} bytes")
            else:
                self.log_analysis("Size Comparison", "❌ SIZE MISMATCH", 
                                 f"User: {user_size} bytes, System: {comparison_size} bytes")
                comparison["differences"].append(f"Size: {user_size} vs {comparison_size}")
            
            # Compare hashes
            user_hash = hashlib.md5(user_content).hexdigest()
            comparison_hash = hashlib.md5(comparison_content).hexdigest()
            comparison["hash_match"] = user_hash == comparison_hash
            
            if comparison["hash_match"]:
                self.log_analysis("Hash Comparison", "✅ HASHES MATCH", 
                                 f"Both files have hash: {user_hash[:16]}...")
            else:
                self.log_analysis("Hash Comparison", "❌ HASH MISMATCH", 
                                 f"User: {user_hash[:16]}..., System: {comparison_hash[:16]}...")
                comparison["differences"].append(f"Hash: {user_hash[:16]} vs {comparison_hash[:16]}")
            
            # Compare headers (first 100 bytes)
            user_header = user_content[:100]
            comparison_header = comparison_content[:100]
            comparison["header_match"] = user_header == comparison_header
            
            if comparison["header_match"]:
                self.log_analysis("Header Comparison", "✅ HEADERS MATCH", 
                                 "PDF headers are identical")
            else:
                self.log_analysis("Header Comparison", "❌ HEADER MISMATCH", 
                                 "PDF headers differ")
                comparison["differences"].append("Headers differ")
                
                # Show the difference
                print(f"    User header: {user_header[:50]}")
                print(f"    System header: {comparison_header[:50]}")
            
            # Compare structure
            user_has_pdf = user_content.startswith(b'%PDF-') and b'%%EOF' in user_content
            comparison_has_pdf = comparison_content.startswith(b'%PDF-') and b'%%EOF' in comparison_content
            comparison["structure_match"] = user_has_pdf == comparison_has_pdf
            
            if comparison["structure_match"] and user_has_pdf:
                self.log_analysis("Structure Comparison", "✅ BOTH HAVE VALID STRUCTURE", 
                                 "Both files have PDF structure")
            elif comparison["structure_match"] and not user_has_pdf:
                self.log_analysis("Structure Comparison", "❌ BOTH LACK STRUCTURE", 
                                 "Neither file has valid PDF structure")
            else:
                self.log_analysis("Structure Comparison", "❌ STRUCTURE MISMATCH", 
                                 f"User valid: {user_has_pdf}, System valid: {comparison_has_pdf}")
                comparison["differences"].append(f"Structure: user={user_has_pdf}, system={comparison_has_pdf}")
            
            # Find byte-level differences
            if user_size == comparison_size:
                diff_count = 0
                for i, (u_byte, c_byte) in enumerate(zip(user_content, comparison_content)):
                    if u_byte != c_byte:
                        diff_count += 1
                        if diff_count <= 5:  # Show first 5 differences
                            comparison["differences"].append(f"Byte {i}: {u_byte} vs {c_byte}")
                
                if diff_count == 0:
                    self.log_analysis("Byte Comparison", "✅ FILES IDENTICAL", 
                                     "Files are byte-for-byte identical")
                else:
                    self.log_analysis("Byte Comparison", "❌ BYTE DIFFERENCES", 
                                     f"Found {diff_count} different bytes")
            
            return comparison
            
        except Exception as e:
            self.log_analysis("File Comparison", "❌ COMPARISON ERROR", f"Error: {e}")
            return comparison
    
    def generate_diagnostic_report(self, user_analysis: Dict, external_results: Dict, 
                                  comparison_results: Dict) -> None:
        """Generate comprehensive diagnostic report."""
        print("\n" + "="*80)
        print("📋 USER PDF DIAGNOSTIC REPORT")
        print("="*80)
        
        print(f"\n📄 FILE INFORMATION:")
        print(f"   Path: {self.user_pdf_path}")
        print(f"   Exists: {'✅' if user_analysis['file_exists'] else '❌'}")
        print(f"   Size: {user_analysis['file_size']} bytes")
        print(f"   Hash: {user_analysis['file_hash']}")
        print(f"   PDF Signature: {'✅' if user_analysis['pdf_signature'] else '❌'}")
        
        print(f"\n📊 STRUCTURE ANALYSIS:")
        structure = user_analysis['pdf_structure']
        for test_name, result in structure.items():
            status = "✅" if result else "❌"
            print(f"   {status} {test_name}")
        
        print(f"\n🔧 EXTERNAL TOOL RESULTS:")
        print(f"   File Command: {external_results.get('file_command', 'Not available')}")
        if external_results.get('pdfinfo'):
            print(f"   pdfinfo: Available")
        else:
            print(f"   pdfinfo: Not available or failed")
        
        print(f"\n🔍 COMPARISON RESULTS:")
        if comparison_results:
            print(f"   Size Match: {'✅' if comparison_results['size_match'] else '❌'}")
            print(f"   Hash Match: {'✅' if comparison_results['hash_match'] else '❌'}")
            print(f"   Header Match: {'✅' if comparison_results['header_match'] else '❌'}")
            print(f"   Structure Match: {'✅' if comparison_results['structure_match'] else '❌'}")
            
            if comparison_results['differences']:
                print(f"\n   Differences Found:")
                for diff in comparison_results['differences']:
                    print(f"     • {diff}")
        
        print(f"\n🎯 DIAGNOSIS:")
        if user_analysis['corruption_type'] != 'unknown':
            print(f"   Corruption Type: {user_analysis['corruption_type']}")
        
        if not user_analysis['file_exists']:
            print(f"   ❌ PRIMARY ISSUE: File not found")
            print(f"   🔧 SOLUTION: Check file path and permissions")
        elif user_analysis['file_size'] == 0:
            print(f"   ❌ PRIMARY ISSUE: Empty file")
            print(f"   🔧 SOLUTION: Re-generate the PDF")
        elif not user_analysis['pdf_signature']:
            print(f"   ❌ PRIMARY ISSUE: Invalid PDF signature")
            print(f"   🔧 SOLUTION: File is not a valid PDF or is corrupted")
        elif comparison_results and not comparison_results['structure_match']:
            print(f"   ❌ PRIMARY ISSUE: PDF structure corruption")
            print(f"   🔧 SOLUTION: Re-generate PDF or fix generation process")
        else:
            print(f"   ✅ FILE APPEARS VALID: Issue might be with PDF reader")
            print(f"   🔧 SOLUTION: Try different PDF reader or check file permissions")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print(f"   1. Try opening the PDF with a different PDF reader")
        print(f"   2. Check file permissions and location")
        print(f"   3. Re-download the PDF from the application")
        print(f"   4. Clear browser cache and try again")
        print(f"   5. Try downloading with a different browser")
        
        # Show hex dump if available
        if external_results.get('hexdump'):
            print(f"\n🔍 HEX DUMP (First 200 bytes):")
            print(external_results['hexdump'])
    
    def run_diagnostic(self) -> bool:
        """Run complete diagnostic on user's PDF."""
        print("🔍 USER PDF DIAGNOSTIC TOOL")
        print("="*80)
        
        # Step 1: Analyze user's PDF
        print("\n📊 Step 1: Analyzing user's PDF file...")
        user_analysis = self.analyze_user_pdf()
        
        # Step 2: Test with external tools
        print("\n🔧 Step 2: Testing with external tools...")
        external_results = self.test_external_tools()
        
        # Step 3: Generate comparison PDF
        print("\n🔧 Step 3: Generating comparison PDF...")
        comparison_path = self.generate_comparison_pdf()
        
        # Step 4: Compare files
        comparison_results = {}
        if comparison_path:
            print("\n🔍 Step 4: Comparing files...")
            comparison_results = self.compare_with_working_pdf(comparison_path)
        
        # Step 5: Generate diagnostic report
        print("\n📋 Step 5: Generating diagnostic report...")
        self.generate_diagnostic_report(user_analysis, external_results, comparison_results)
        
        return user_analysis['file_exists'] and user_analysis['pdf_signature']

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze user's corrupted PDF file")
    parser.add_argument("--file", "-f", default="/mnt/d/tmp/analysis_report_analysis_report.pdf",
                       help="Path to the user's PDF file")
    
    args = parser.parse_args()
    
    diagnostic = UserPDFDiagnostic(args.file)
    
    try:
        success = diagnostic.run_diagnostic()
        
        if success:
            print("\n✅ DIAGNOSTIC COMPLETED - PDF APPEARS VALID")
        else:
            print("\n❌ DIAGNOSTIC FOUND ISSUES - PDF IS CORRUPTED")
            
        return success
        
    except Exception as e:
        print(f"\n💥 DIAGNOSTIC FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)