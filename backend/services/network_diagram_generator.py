"""
Network Diagram Generator for PCAP Analysis Results.

This service generates Mermaid.js diagram definitions from network analysis data,
creating visual representations of network topology, traffic flows, and communication patterns.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, Counter
from datetime import datetime
import ipaddress
import re


class NetworkDiagramGenerator:
    """
    Generates network diagrams from PCAP analysis results.
    
    Supports multiple diagram types:
    - Network topology diagrams showing hosts and connections
    - Protocol flow diagrams showing communication patterns
    - Security incident diagrams highlighting threats
    - Performance issue diagrams showing bottlenecks
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the diagram generator.
        
        Args:
            config: Configuration dictionary for diagram generation
        """
        self.logger = logging.getLogger(__name__)
        
        # Default configuration
        self.config = {
            'max_nodes': 50,  # Maximum nodes in diagram to avoid clutter
            'max_connections': 100,  # Maximum connections to show
            'min_packet_threshold': 10,  # Minimum packets to show connection
            'highlight_security_issues': True,
            'group_by_subnet': True,
            'show_protocol_labels': True,
            'include_port_numbers': False,  # Can make diagrams cluttered
            'diagram_direction': 'TD',  # Top-Down, Left-Right (LR), etc.
            'node_styles': {
                'internal': 'fill:#e1f5fe,stroke:#01579b,stroke-width:2px',
                'external': 'fill:#fff3e0,stroke:#ef6c00,stroke-width:2px',
                'server': 'fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px',
                'suspicious': 'fill:#ffebee,stroke:#c62828,stroke-width:3px'
            },
            'connection_styles': {
                'normal': 'stroke:#666,stroke-width:2px',
                'high_traffic': 'stroke:#1976d2,stroke-width:4px',
                'security_threat': 'stroke:#d32f2f,stroke-width:3px,stroke-dasharray: 5 5'
            }
        }
        
        # Update with user-provided config
        if config:
            self.config.update(config)
        
        self.logger.info("Network diagram generator initialized")
    
    def _sanitize_node_id(self, node_id: str) -> str:
        """
        Sanitize node ID for Mermaid.js compatibility.
        
        Args:
            node_id: Raw node identifier
            
        Returns:
            Sanitized node ID safe for Mermaid.js
        """
        if node_id is None:
            return "unknown_node"
            
        # Replace special characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(node_id))
        
        # Ensure it starts with a letter
        if sanitized and sanitized[0].isdigit():
            sanitized = f"node_{sanitized}"
        
        return sanitized or "unknown_node"
    
    def _classify_ip_address(self, ip_addr: str) -> str:
        """
        Classify IP address as internal, external, or special.
        
        Args:
            ip_addr: IP address string
            
        Returns:
            Classification: 'internal', 'external', 'multicast', 'broadcast'
        """
        try:
            ip = ipaddress.ip_address(ip_addr)
            
            if ip.is_multicast:
                return 'multicast'
            # Check for broadcast addresses manually (compatibility)
            elif str(ip).endswith('.255') or str(ip) == '255.255.255.255':
                return 'broadcast'
            elif ip.is_private:
                return 'internal'
            else:
                return 'external'
        except ValueError:
            return 'unknown'
    
    def _determine_node_role(self, ip_addr: str, conversations: List[Dict]) -> str:
        """
        Determine the role of a node based on communication patterns.
        
        Args:
            ip_addr: IP address to analyze
            conversations: List of conversation data
            
        Returns:
            Node role: 'client', 'server', 'peer', 'gateway'
        """
        incoming_connections = 0
        outgoing_connections = 0
        unique_peers = set()
        
        for conv in conversations:
            if conv.get('src_ip') == ip_addr:
                outgoing_connections += 1
                unique_peers.add(conv.get('dst_ip'))
            elif conv.get('dst_ip') == ip_addr:
                incoming_connections += 1
                unique_peers.add(conv.get('src_ip'))
        
        # Heuristics for role determination
        if incoming_connections > outgoing_connections * 2:
            return 'server'
        elif outgoing_connections > incoming_connections * 2:
            return 'client'
        elif len(unique_peers) > 10:
            return 'gateway'
        else:
            return 'peer'
    
    def _generate_node_label(self, ip_addr: str, node_info: Dict[str, Any]) -> str:
        """
        Generate a descriptive label for a network node.
        
        Args:
            ip_addr: IP address of the node
            node_info: Additional node information
            
        Returns:
            Formatted node label
        """
        classification = self._classify_ip_address(ip_addr)
        role = node_info.get('role', 'unknown')
        
        # Create short IP for display (last octet for internal IPs)
        if classification == 'internal':
            try:
                short_ip = ip_addr.split('.')[-1]
                label = f"{short_ip}<br/>({role})"
            except:
                label = f"{ip_addr}<br/>({role})"
        else:
            label = f"{ip_addr}<br/>({role})"
        
        # Add packet count if significant
        packet_count = node_info.get('packet_count', 0)
        if packet_count > 100:
            if packet_count > 10000:
                label += f"<br/>{packet_count//1000}k pkts"
            else:
                label += f"<br/>{packet_count} pkts"
        
        return label
    
    def _generate_connection_label(self, connection: Dict[str, Any]) -> str:
        """
        Generate a label for a network connection.
        
        Args:
            connection: Connection information
            
        Returns:
            Connection label
        """
        labels = []
        
        # Protocol
        protocol = connection.get('protocol', 'Unknown')
        if protocol and self.config['show_protocol_labels']:
            labels.append(protocol)
        
        # Packet count
        packet_count = connection.get('packet_count', 0)
        if packet_count > 50:
            if packet_count > 10000:
                labels.append(f"{packet_count//1000}k")
            else:
                labels.append(str(packet_count))
        
        # Port information (if enabled)
        if self.config['include_port_numbers']:
            src_port = connection.get('src_port')
            dst_port = connection.get('dst_port')
            if dst_port and dst_port in [80, 443, 22, 25, 53, 21, 23]:
                # Show well-known ports
                labels.append(f":{dst_port}")
        
        return " ".join(labels) if labels else ""
    
    def generate_network_topology_diagram(self, analysis_results: Dict[str, Any]) -> str:
        """
        Generate a network topology diagram showing hosts and connections.
        
        Args:
            analysis_results: Complete analysis results from PCAP processing
            
        Returns:
            Mermaid.js diagram definition string
        """
        try:
            # Extract conversation data
            conversations = analysis_results.get('conversations', [])
            top_talkers = analysis_results.get('top_talkers', [])
            
            if not conversations and not top_talkers:
                return self._generate_empty_diagram("No network conversations found")
            
            # Build node information
            nodes = {}
            connections = []
            
            # Process conversations to build network graph
            for conv in conversations[:self.config['max_connections']]:
                src_ip = conv.get('src_ip', '')
                dst_ip = conv.get('dst_ip', '')
                
                if not src_ip or not dst_ip:
                    continue
                
                # Add nodes
                for ip in [src_ip, dst_ip]:
                    if ip not in nodes:
                        nodes[ip] = {
                            'ip': ip,
                            'packet_count': 0,
                            'byte_count': 0,
                            'classification': self._classify_ip_address(ip),
                            'role': 'unknown'
                        }
                    
                    nodes[ip]['packet_count'] += conv.get('packet_count', 0)
                    nodes[ip]['byte_count'] += conv.get('byte_count', 0)
                
                # Add connection
                if conv.get('packet_count', 0) >= self.config['min_packet_threshold']:
                    connections.append({
                        'src': src_ip,
                        'dst': dst_ip,
                        'protocol': conv.get('protocol', 'Unknown'),
                        'packet_count': conv.get('packet_count', 0),
                        'byte_count': conv.get('byte_count', 0),
                        'src_port': conv.get('src_port'),
                        'dst_port': conv.get('dst_port')
                    })
            
            # Determine node roles
            for ip in nodes:
                nodes[ip]['role'] = self._determine_node_role(ip, conversations)
            
            # Limit nodes to prevent diagram clutter
            if len(nodes) > self.config['max_nodes']:
                # Keep the most active nodes
                sorted_nodes = sorted(
                    nodes.items(), 
                    key=lambda x: x[1]['packet_count'], 
                    reverse=True
                )
                nodes = dict(sorted_nodes[:self.config['max_nodes']])
                
                # Filter connections to only include remaining nodes
                node_ips = set(nodes.keys())
                connections = [
                    conn for conn in connections 
                    if conn['src'] in node_ips and conn['dst'] in node_ips
                ]
            
            # Generate Mermaid.js diagram
            diagram_lines = [f"graph {self.config['diagram_direction']}"]
            
            # Add nodes with styling
            for ip, node_info in nodes.items():
                node_id = self._sanitize_node_id(ip)
                node_label = self._generate_node_label(ip, node_info)
                
                # Determine node style
                classification = node_info['classification']
                role = node_info['role']
                
                if classification == 'internal':
                    if role == 'server':
                        style_class = 'server'
                    else:
                        style_class = 'internal'
                elif classification == 'external':
                    style_class = 'external'
                else:
                    style_class = 'internal'
                
                diagram_lines.append(f'    {node_id}["{node_label}"]')
                diagram_lines.append(f'    classDef {style_class} {self.config["node_styles"][style_class]}')
                diagram_lines.append(f'    class {node_id} {style_class}')
            
            # Add connections
            for conn in connections:
                src_id = self._sanitize_node_id(conn['src'])
                dst_id = self._sanitize_node_id(conn['dst'])
                
                # Skip if nodes don't exist (filtered out)
                if conn['src'] not in nodes or conn['dst'] not in nodes:
                    continue
                
                connection_label = self._generate_connection_label(conn)
                
                # Determine connection style
                packet_count = conn.get('packet_count', 0)
                if packet_count > 1000:
                    style = 'high_traffic'
                else:
                    style = 'normal'
                
                # Create connection
                if connection_label:
                    diagram_lines.append(f'    {src_id} -->|{connection_label}| {dst_id}')
                else:
                    diagram_lines.append(f'    {src_id} --> {dst_id}')
            
            return "\n".join(diagram_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating network topology diagram: {e}")
            return self._generate_empty_diagram(f"Error generating diagram: {str(e)}")
    
    def generate_protocol_flow_diagram(self, analysis_results: Dict[str, Any]) -> str:
        """
        Generate a protocol flow diagram showing communication patterns.
        
        Args:
            analysis_results: Complete analysis results from PCAP processing
            
        Returns:
            Mermaid.js sequence diagram definition string
        """
        try:
            conversations = analysis_results.get('conversations', [])
            
            if not conversations:
                return self._generate_empty_sequence_diagram("No protocol flows found")
            
            # Build sequence of communications
            diagram_lines = ["sequenceDiagram"]
            
            # Get most significant conversations
            significant_convs = sorted(
                conversations[:20], 
                key=lambda x: x.get('packet_count', 0), 
                reverse=True
            )
            
            # Track participants
            participants = set()
            
            for conv in significant_convs:
                src_ip = conv.get('src_ip', '')
                dst_ip = conv.get('dst_ip', '')
                protocol = conv.get('protocol', 'Unknown')
                packet_count = conv.get('packet_count', 0)
                
                if not src_ip or not dst_ip:
                    continue
                
                # Sanitize participant names
                src_name = self._sanitize_node_id(src_ip).replace('_', '')
                dst_name = self._sanitize_node_id(dst_ip).replace('_', '')
                
                participants.add((src_name, src_ip))
                participants.add((dst_name, dst_ip))
                
                # Add sequence step
                if packet_count > 100:
                    label = f"{protocol} ({packet_count} pkts)"
                else:
                    label = protocol
                
                diagram_lines.append(f"    {src_name}->>+{dst_name}: {label}")
                
                # Add return flow if significant
                if packet_count > 50:
                    diagram_lines.append(f"    {dst_name}-->>-{src_name}: Response")
            
            # Add participant definitions at the beginning
            participant_lines = []
            for name, ip in sorted(participants):
                # Show short IP for internal addresses
                if self._classify_ip_address(ip) == 'internal':
                    display_name = ip.split('.')[-1]
                else:
                    display_name = ip
                participant_lines.append(f"    participant {name} as {display_name}")
            
            # Insert participant definitions after the first line
            if participant_lines:
                diagram_lines = [diagram_lines[0]] + participant_lines + diagram_lines[1:]
            
            return "\n".join(diagram_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating protocol flow diagram: {e}")
            return self._generate_empty_sequence_diagram(f"Error: {str(e)}")
    
    def generate_security_incident_diagram(self, analysis_results: Dict[str, Any]) -> str:
        """
        Generate a diagram highlighting security incidents and threats.
        
        Args:
            analysis_results: Complete analysis results from PCAP processing
            
        Returns:
            Mermaid.js diagram definition string focused on security
        """
        try:
            security_analysis = analysis_results.get('security_analysis', {})
            security_alerts = security_analysis.get('security_alerts', [])
            
            if not security_alerts:
                return self._generate_empty_diagram("No security incidents detected")
            
            diagram_lines = [f"graph {self.config['diagram_direction']}"]
            
            # Group alerts by type and source
            alert_groups = defaultdict(list)
            affected_hosts = set()
            
            for alert in security_alerts:
                alert_type = alert.get('type', 'UNKNOWN')
                severity = alert.get('severity', 'LOW')
                description = alert.get('description', '')
                
                # Extract IP addresses from description if possible
                ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
                ips = re.findall(ip_pattern, description)
                
                for ip in ips:
                    affected_hosts.add(ip)
                    alert_groups[ip].append({
                        'type': alert_type,
                        'severity': severity,
                        'description': description
                    })
            
            # Add nodes for affected hosts
            for ip in affected_hosts:
                node_id = self._sanitize_node_id(ip)
                alerts = alert_groups[ip]
                
                # Count severity levels
                severity_counts = Counter(alert['severity'] for alert in alerts)
                max_severity = max(severity_counts.keys()) if severity_counts else 'LOW'
                
                # Create label
                label = f"{ip}<br/>Security Issues: {len(alerts)}"
                if severity_counts:
                    label += f"<br/>Max: {max_severity}"
                
                diagram_lines.append(f'    {node_id}["{label}"]')
                diagram_lines.append(f'    class {node_id} suspicious')
            
            # Add central security analysis node
            if affected_hosts:
                diagram_lines.append('    SecAnalysis["🛡️ Security Analysis<br/>Multiple threats detected"]')
                
                # Connect all affected hosts to security analysis
                for ip in affected_hosts:
                    node_id = self._sanitize_node_id(ip)
                    alert_types = [alert['type'] for alert in alert_groups[ip]]
                    unique_types = list(set(alert_types))
                    
                    if len(unique_types) <= 2:
                        label = ", ".join(unique_types)
                    else:
                        label = f"{len(unique_types)} threat types"
                    
                    diagram_lines.append(f'    {node_id} -.->|{label}| SecAnalysis')
            
            # Add styling
            diagram_lines.append(f'    classDef suspicious {self.config["node_styles"]["suspicious"]}')
            diagram_lines.append('    classDef security fill:#ff5722,stroke:#bf360c,stroke-width:2px,color:#fff')
            diagram_lines.append('    class SecAnalysis security')
            
            return "\n".join(diagram_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating security incident diagram: {e}")
            return self._generate_empty_diagram(f"Security diagram error: {str(e)}")
    
    def generate_performance_analysis_diagram(self, analysis_results: Dict[str, Any]) -> str:
        """
        Generate a diagram showing performance issues and bottlenecks.
        
        Args:
            analysis_results: Complete analysis results from PCAP processing
            
        Returns:
            Mermaid.js diagram definition string focused on performance
        """
        try:
            performance_analysis = analysis_results.get('performance_analysis', {})
            performance_issues = performance_analysis.get('performance_issues', [])
            
            if not performance_issues:
                return self._generate_empty_diagram("No performance issues detected")
            
            diagram_lines = [f"graph {self.config['diagram_direction']}"]
            
            # Create performance overview node
            bandwidth_usage = performance_analysis.get('bandwidth_usage', 0)
            connection_rate = performance_analysis.get('connection_rate', 0)
            latency_indicators = performance_analysis.get('latency_indicators', 0)
            
            overview_label = f"📊 Performance Overview<br/>Bandwidth: {bandwidth_usage} bytes<br/>Connections: {connection_rate}<br/>Latency Issues: {latency_indicators}"
            diagram_lines.append(f'    PerfOverview["{overview_label}"]')
            
            # Add issue nodes
            issue_id = 0
            for issue in performance_issues:
                issue_type = issue.get('type', 'UNKNOWN')
                severity = issue.get('severity', 'LOW')
                description = issue.get('description', '')
                
                issue_id += 1
                node_id = f"Issue{issue_id}"
                
                # Create concise label
                if len(description) > 50:
                    short_desc = description[:47] + "..."
                else:
                    short_desc = description
                
                label = f"{issue_type}<br/>{short_desc}<br/>({severity})"
                diagram_lines.append(f'    {node_id}["{label}"]')
                
                # Connect to overview
                diagram_lines.append(f'    PerfOverview --> {node_id}')
                
                # Style based on severity
                if severity == 'HIGH':
                    diagram_lines.append(f'    class {node_id} highSeverity')
                elif severity == 'MEDIUM':
                    diagram_lines.append(f'    class {node_id} mediumSeverity')
                else:
                    diagram_lines.append(f'    class {node_id} lowSeverity')
            
            # Add styling
            diagram_lines.append('    classDef performance fill:#3f51b5,stroke:#1a237e,stroke-width:2px,color:#fff')
            diagram_lines.append('    classDef highSeverity fill:#f44336,stroke:#b71c1c,stroke-width:2px,color:#fff')
            diagram_lines.append('    classDef mediumSeverity fill:#ff9800,stroke:#e65100,stroke-width:2px')
            diagram_lines.append('    classDef lowSeverity fill:#4caf50,stroke:#1b5e20,stroke-width:2px')
            diagram_lines.append('    class PerfOverview performance')
            
            return "\n".join(diagram_lines)
            
        except Exception as e:
            self.logger.error(f"Error generating performance analysis diagram: {e}")
            return self._generate_empty_diagram(f"Performance diagram error: {str(e)}")
    
    def _generate_empty_diagram(self, message: str) -> str:
        """Generate an empty diagram with a message."""
        return f"""graph TD
    EmptyNode["{message}"]
    classDef empty fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px
    class EmptyNode empty"""
    
    def _generate_empty_sequence_diagram(self, message: str) -> str:
        """Generate an empty sequence diagram with a message."""
        return f"""sequenceDiagram
    participant A as No Data
    Note over A: {message}"""
    
    def generate_comprehensive_diagram_set(self, analysis_results: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a complete set of diagrams for the analysis results.
        
        Args:
            analysis_results: Complete analysis results from PCAP processing
            
        Returns:
            Dictionary containing all generated diagrams
        """
        try:
            diagrams = {}
            
            # Generate all diagram types
            diagrams['network_topology'] = self.generate_network_topology_diagram(analysis_results)
            diagrams['protocol_flow'] = self.generate_protocol_flow_diagram(analysis_results)
            diagrams['security_incidents'] = self.generate_security_incident_diagram(analysis_results)
            diagrams['performance_analysis'] = self.generate_performance_analysis_diagram(analysis_results)
            
            # Add metadata
            diagrams['_metadata'] = {
                'generated_at': datetime.utcnow().isoformat(),
                'generator_version': '1.0.0',
                'config': self.config,
                'diagram_count': len([k for k in diagrams.keys() if not k.startswith('_')])
            }
            
            self.logger.info(f"Generated {len(diagrams)-1} network diagrams")
            return diagrams
            
        except Exception as e:
            self.logger.error(f"Error generating comprehensive diagram set: {e}")
            return {
                'error': self._generate_empty_diagram(f"Diagram generation failed: {str(e)}"),
                '_metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'error': str(e)
                }
            }