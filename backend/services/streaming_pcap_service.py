"""
Streaming PCAP Analysis Service.

High-performance service for analyzing large PCAP files using streaming,
chunking, and memory-efficient processing techniques.
"""

import asyncio
import os
import logging
import tempfile
from typing import Dict, List, Any, Optional, AsyncGenerator, Callable
from datetime import datetime
from pathlib import Path
import subprocess
import json
from dataclasses import dataclass

from models.analysis_results import AnalysisResults, TrafficStats, PerformanceMetrics, ProtocolStats
from services.pcap_analysis_service import PcapAnalysisService

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Configuration for streaming PCAP analysis."""
    chunk_size_mb: int = 100  # Process in 100MB chunks
    max_memory_mb: int = 512  # Maximum memory usage
    parallel_workers: int = 4  # Number of parallel processing workers
    enable_progress_updates: bool = True
    temp_dir: Optional[str] = None


class StreamingPcapService:
    """Service for streaming analysis of large PCAP files."""
    
    def __init__(self, config: Optional[StreamingConfig] = None):
        """Initialize the streaming PCAP service."""
        self.config = config or StreamingConfig()
        self.logger = logging.getLogger(__name__)
        self.base_service = PcapAnalysisService()
        
        # Performance tracking
        self.processing_stats = {
            'chunks_processed': 0,
            'total_chunks': 0,
            'bytes_processed': 0,
            'start_time': None,
            'current_memory_usage': 0
        }
    
    async def analyze_large_pcap(
        self, 
        file_path: str, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AnalysisResults:
        """
        Analyze large PCAP files using streaming and chunking.
        
        Args:
            file_path: Path to the PCAP file
            progress_callback: Optional callback for progress updates
            
        Returns:
            AnalysisResults: Comprehensive analysis results
        """
        self.processing_stats['start_time'] = datetime.utcnow()
        
        try:
            # Validate file and get basic info
            file_size = await self._get_file_size(file_path)
            self.logger.info(f"Starting streaming analysis of {file_size / 1024 / 1024:.1f}MB file")
            
            if progress_callback:
                await progress_callback(5, "Initializing streaming analysis...")
            
            # Determine processing strategy based on file size
            if file_size <= self.config.chunk_size_mb * 1024 * 1024:
                # Small file - use regular processing
                return await self.base_service.analyze_pcap_file(file_path)
            
            # Large file - use streaming approach
            return await self._stream_analyze_large_file(file_path, file_size, progress_callback)
            
        except Exception as e:
            self.logger.error(f"Streaming analysis failed: {e}")
            raise
    
    async def _stream_analyze_large_file(
        self, 
        file_path: str, 
        file_size: int, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AnalysisResults:
        """Stream analyze a large PCAP file in chunks."""
        
        # Calculate chunk information
        chunk_size_bytes = self.config.chunk_size_mb * 1024 * 1024
        estimated_chunks = (file_size // chunk_size_bytes) + 1
        self.processing_stats['total_chunks'] = estimated_chunks
        
        if progress_callback:
            await progress_callback(10, f"Processing {estimated_chunks} chunks...")
        
        # Create temporary directory for chunk processing
        temp_dir = self.config.temp_dir or tempfile.mkdtemp(prefix="pcap_streaming_")
        
        try:
            # Split PCAP into time-based chunks for better analysis
            chunk_files = await self._split_pcap_by_time(file_path, temp_dir, progress_callback)
            
            # Process chunks in parallel
            chunk_results = await self._process_chunks_parallel(chunk_files, progress_callback)
            
            # Merge results from all chunks
            final_results = await self._merge_chunk_results(chunk_results, file_path)
            
            if progress_callback:
                await progress_callback(95, "Finalizing streaming analysis...")
            
            return final_results
            
        finally:
            # Cleanup temporary files
            await self._cleanup_temp_files(temp_dir)
    
    async def _split_pcap_by_time(
        self, 
        file_path: str, 
        temp_dir: str, 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[str]:
        """Split PCAP file into time-based chunks for better analysis."""
        
        # First, get time range of the capture
        time_info = await self._get_capture_time_range(file_path)
        
        if not time_info:
            # Fallback to size-based splitting
            return await self._split_pcap_by_size(file_path, temp_dir)
        
        start_time = time_info['start_time']
        end_time = time_info['end_time']
        duration = time_info['duration']
        
        # Calculate chunk duration (aim for reasonable chunk sizes)
        chunk_duration = max(duration / self.config.parallel_workers, 60)  # Minimum 1 minute chunks
        
        chunk_files = []
        current_time = start_time
        chunk_index = 0
        
        while current_time < end_time:
            next_time = min(current_time + chunk_duration, end_time)
            
            # Create chunk file
            chunk_file = os.path.join(temp_dir, f"chunk_{chunk_index:04d}.pcap")
            
            # Use editcap to extract time-based chunk
            cmd = [
                'editcap',
                '-A', str(current_time),
                '-B', str(next_time),
                file_path,
                chunk_file
            ]
            
            try:
                await self._run_command(cmd)
                if os.path.exists(chunk_file) and os.path.getsize(chunk_file) > 24:
                    chunk_files.append(chunk_file)
                    self.logger.info(f"Created chunk {chunk_index}: {current_time:.1f}s - {next_time:.1f}s")
            except Exception as e:
                self.logger.warning(f"Failed to create chunk {chunk_index}: {e}")
            
            current_time = next_time
            chunk_index += 1
            
            if progress_callback:
                progress = 15 + int((current_time / duration) * 25)  # 15-40% for splitting
                await progress_callback(progress, f"Splitting file: chunk {chunk_index}")
        
        return chunk_files
    
    async def _split_pcap_by_size(self, file_path: str, temp_dir: str) -> List[str]:
        """Fallback method to split PCAP by size."""
        chunk_files = []
        chunk_size = self.config.chunk_size_mb * 1024 * 1024
        chunk_index = 0
        
        # Use editcap to split by size
        cmd = [
            'editcap',
            '-c', str(chunk_size),
            file_path,
            os.path.join(temp_dir, f"chunk_{chunk_index:04d}.pcap")
        ]
        
        try:
            await self._run_command(cmd)
            
            # Find all created chunk files
            for file in os.listdir(temp_dir):
                if file.startswith("chunk_") and file.endswith(".pcap"):
                    chunk_files.append(os.path.join(temp_dir, file))
            
            chunk_files.sort()
            
        except Exception as e:
            self.logger.error(f"Failed to split PCAP by size: {e}")
            # Return original file as single chunk
            return [file_path]
        
        return chunk_files
    
    async def _process_chunks_parallel(
        self, 
        chunk_files: List[str], 
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[AnalysisResults]:
        """Process chunks in parallel using asyncio."""
        
        # Create semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(self.config.parallel_workers)
        
        async def process_single_chunk(chunk_file: str, chunk_index: int) -> AnalysisResults:
            async with semaphore:
                try:
                    self.logger.info(f"Processing chunk {chunk_index}: {os.path.basename(chunk_file)}")
                    
                    # Analyze chunk using base service
                    result = await self.base_service.analyze_pcap_file(chunk_file)
                    
                    # Update progress
                    self.processing_stats['chunks_processed'] += 1
                    if progress_callback:
                        progress = 40 + int((self.processing_stats['chunks_processed'] / len(chunk_files)) * 45)
                        await progress_callback(progress, f"Processed chunk {chunk_index + 1}/{len(chunk_files)}")
                    
                    return result
                    
                except Exception as e:
                    self.logger.error(f"Failed to process chunk {chunk_index}: {e}")
                    raise
        
        # Process all chunks concurrently
        tasks = [
            process_single_chunk(chunk_file, i) 
            for i, chunk_file in enumerate(chunk_files)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        successful_results = [r for r in results if isinstance(r, AnalysisResults)]
        
        if len(successful_results) == 0:
            raise RuntimeError("No chunks were processed successfully")
        
        return successful_results
    
    async def _merge_chunk_results(
        self, 
        chunk_results: List[AnalysisResults], 
        original_file_path: str
    ) -> AnalysisResults:
        """Merge results from all processed chunks."""
        
        if not chunk_results:
            raise ValueError("No chunk results to merge")
        
        # Initialize merged statistics
        total_packets = sum(r.traffic_stats.total_packets for r in chunk_results)
        total_bytes = sum(r.traffic_stats.total_bytes for r in chunk_results)
        
        # Calculate overall duration
        start_times = [r.start_time for r in chunk_results if r.start_time]
        end_times = [r.end_time for r in chunk_results if r.end_time]
        
        overall_start = min(start_times) if start_times else "Unknown"
        overall_end = max(end_times) if end_times else "Unknown"
        
        # Merge traffic stats
        merged_traffic_stats = TrafficStats(
            total_packets=total_packets,
            total_bytes=total_bytes,
            duration=sum(r.traffic_stats.duration for r in chunk_results),
            avg_packet_size=total_bytes / total_packets if total_packets > 0 else 0,
            packets_per_second=total_packets / sum(r.traffic_stats.duration for r in chunk_results) if sum(r.traffic_stats.duration for r in chunk_results) > 0 else 0,
            bytes_per_second=total_bytes / sum(r.traffic_stats.duration for r in chunk_results) if sum(r.traffic_stats.duration for r in chunk_results) > 0 else 0
        )
        
        # Merge performance metrics (weighted average)
        total_duration = sum(r.traffic_stats.duration for r in chunk_results)
        merged_performance_metrics = PerformanceMetrics(
            avg_latency=sum(r.performance_metrics.avg_latency * r.traffic_stats.duration for r in chunk_results) / total_duration if total_duration > 0 else 0,
            max_latency=max(r.performance_metrics.max_latency for r in chunk_results),
            packet_loss_rate=sum(r.performance_metrics.packet_loss_rate * r.traffic_stats.duration for r in chunk_results) / total_duration if total_duration > 0 else 0,
            throughput_mbps=sum(r.performance_metrics.throughput_mbps for r in chunk_results) / len(chunk_results)
        )
        
        # Merge protocol stats
        merged_protocol_stats = ProtocolStats(
            tcp_packets=sum(r.protocol_stats.tcp_packets for r in chunk_results),
            udp_packets=sum(r.protocol_stats.udp_packets for r in chunk_results),
            icmp_packets=sum(r.protocol_stats.icmp_packets for r in chunk_results),
            http_sessions=sum(r.protocol_stats.http_sessions for r in chunk_results),
            https_sessions=sum(r.protocol_stats.https_sessions for r in chunk_results),
            dns_queries=sum(r.protocol_stats.dns_queries for r in chunk_results),
            dhcp_packets=sum(r.protocol_stats.dhcp_packets for r in chunk_results),
            arp_packets=sum(r.protocol_stats.arp_packets for r in chunk_results)
        )
        
        # Merge issues (deduplicate similar issues)
        all_issues = []
        for result in chunk_results:
            all_issues.extend(result.issues)
        
        # Create merged result
        merged_result = AnalysisResults(
            file_path=original_file_path,
            file_size=Path(original_file_path).stat().st_size,
            traffic_stats=merged_traffic_stats,
            performance_metrics=merged_performance_metrics,
            protocol_stats=merged_protocol_stats,
            issues=all_issues,
            start_time=overall_start,
            end_time=overall_end,
            processing_time=sum(r.processing_time for r in chunk_results),
            analysis_options={'streaming': True, 'chunks_processed': len(chunk_results)}
        )
        
        return merged_result
    
    async def _get_capture_time_range(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get the time range of the capture file."""
        try:
            cmd = [
                'tshark',
                '-r', file_path,
                '-T', 'fields',
                '-e', 'frame.time_relative',
                '-c', '1'  # First packet
            ]
            
            first_result = await self._run_command(cmd)
            
            cmd = [
                'tshark',
                '-r', file_path,
                '-T', 'fields',
                '-e', 'frame.time_relative'
            ]
            
            # Get last packet time
            all_result = await self._run_command(cmd)
            times = all_result.strip().split('\n')
            
            if times and len(times) > 0:
                start_time = 0.0
                end_time = float(times[-1]) if times[-1] else 0.0
                
                return {
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time
                }
        
        except Exception as e:
            self.logger.warning(f"Failed to get capture time range: {e}")
        
        return None
    
    async def _run_command(self, cmd: List[str]) -> str:
        """Run a command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                raise RuntimeError(f"Command failed: {' '.join(cmd)}\nError: {stderr.decode()}")
            
            return stdout.decode()
            
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            raise
    
    async def _get_file_size(self, file_path: str) -> int:
        """Get file size asynchronously."""
        return os.path.getsize(file_path)
    
    async def _cleanup_temp_files(self, temp_dir: str):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(temp_dir)
            self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics."""
        if self.processing_stats['start_time']:
            elapsed = (datetime.utcnow() - self.processing_stats['start_time']).total_seconds()
            self.processing_stats['elapsed_time'] = elapsed
            
            if self.processing_stats['bytes_processed'] > 0:
                self.processing_stats['processing_rate_mbps'] = (
                    self.processing_stats['bytes_processed'] / 1024 / 1024 / elapsed
                )
        
        return self.processing_stats.copy() 