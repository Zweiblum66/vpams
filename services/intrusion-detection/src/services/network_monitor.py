"""
Network monitoring service for packet capture and analysis.

Captures network traffic using scapy and analyzes packets for suspicious patterns.
"""

import asyncio
import threading
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict, deque
import ipaddress
import struct
import hashlib
import scapy.all as scapy
from scapy.layers.inet import IP, TCP, UDP, ICMP
from scapy.layers.http import HTTP
import structlog

from ..core.config import get_settings
from ..core.exceptions import NetworkMonitorError
from ..models.schemas import NetworkPacket, Protocol


logger = structlog.get_logger()


class NetworkMonitor:
    """Network traffic monitoring and packet capture."""
    
    def __init__(self):
        self.settings = get_settings()
        self.interface = self.settings.network_interface
        self.capture_filter = self.settings.capture_filter
        
        # Packet processing
        self.packet_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self.blocked_ips: Set[str] = set()
        self.rate_limiters: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Statistics
        self.stats = {
            "packets_captured": 0,
            "packets_processed": 0,
            "packets_dropped": 0,
            "blocked_connections": 0,
            "start_time": None
        }
        
        # Threading for packet capture
        self._capture_thread: Optional[threading.Thread] = None
        self._running = False
        self._stop_event = threading.Event()
    
    async def initialize(self) -> None:
        """Initialize network monitoring."""
        try:
            logger.info("Initializing network monitor", interface=self.interface)
            
            # Validate network interface
            available_interfaces = scapy.get_if_list()
            if self.interface not in available_interfaces:
                logger.warning(
                    "Interface not found, using default",
                    requested=self.interface,
                    available=available_interfaces
                )
                self.interface = available_interfaces[0] if available_interfaces else "eth0"
            
            # Start packet capture in separate thread
            self._running = True
            self.stats["start_time"] = datetime.utcnow()
            
            self._capture_thread = threading.Thread(
                target=self._packet_capture_loop,
                name="PacketCapture",
                daemon=True
            )
            self._capture_thread.start()
            
            logger.info(
                "Network monitor initialized",
                interface=self.interface,
                filter=self.capture_filter or "none"
            )
            
        except Exception as e:
            logger.error("Failed to initialize network monitor", error=str(e))
            raise NetworkMonitorError(f"Initialization failed: {str(e)}")
    
    def _packet_capture_loop(self) -> None:
        """Main packet capture loop running in separate thread."""
        try:
            logger.info("Starting packet capture", interface=self.interface)
            
            # Configure packet capture
            def packet_handler(packet):
                if not self._running:
                    return
                
                try:
                    # Basic rate limiting
                    current_time = time.time()
                    if len(self.rate_limiters["global"]) >= self.settings.max_packets_per_second:
                        oldest = self.rate_limiters["global"][0]
                        if current_time - oldest < 1.0:
                            self.stats["packets_dropped"] += 1
                            return
                    
                    self.rate_limiters["global"].append(current_time)
                    
                    # Convert scapy packet to our format
                    network_packet = self._parse_packet(packet)
                    if network_packet:
                        # Non-blocking queue put
                        try:
                            self.packet_queue.put_nowait(network_packet)
                            self.stats["packets_captured"] += 1
                        except asyncio.QueueFull:
                            self.stats["packets_dropped"] += 1
                    
                except Exception as e:
                    logger.error("Error processing captured packet", error=str(e))
            
            # Start capture
            scapy.sniff(
                iface=self.interface,
                prn=packet_handler,
                filter=self.capture_filter or None,
                stop_filter=lambda p: self._stop_event.is_set()
            )
            
        except Exception as e:
            logger.error("Packet capture error", error=str(e))
        finally:
            logger.info("Packet capture stopped")
    
    def _parse_packet(self, packet) -> Optional[NetworkPacket]:
        """Parse scapy packet into NetworkPacket object."""
        try:
            if not packet.haslayer(IP):
                return None
            
            ip_layer = packet[IP]
            timestamp = datetime.utcnow()
            
            # Extract basic IP information
            source_ip = ip_layer.src
            dest_ip = ip_layer.dst
            
            # Check if IP is blocked
            if source_ip in self.blocked_ips:
                return None
            
            # Protocol detection
            protocol = Protocol.TCP
            source_port = None
            dest_port = None
            flags = []
            
            if packet.haslayer(TCP):
                tcp_layer = packet[TCP]
                protocol = Protocol.TCP
                source_port = tcp_layer.sport
                dest_port = tcp_layer.dport
                
                # TCP flags
                if tcp_layer.flags & 0x02:  # SYN
                    flags.append("SYN")
                if tcp_layer.flags & 0x10:  # ACK
                    flags.append("ACK")
                if tcp_layer.flags & 0x01:  # FIN
                    flags.append("FIN")
                if tcp_layer.flags & 0x04:  # RST
                    flags.append("RST")
                if tcp_layer.flags & 0x08:  # PSH
                    flags.append("PSH")
                if tcp_layer.flags & 0x20:  # URG
                    flags.append("URG")
                
                # Check for common protocols
                if dest_port == 80:
                    protocol = Protocol.HTTP
                elif dest_port == 443:
                    protocol = Protocol.HTTPS
                elif dest_port == 22:
                    protocol = Protocol.SSH
                elif dest_port == 21:
                    protocol = Protocol.FTP
                elif dest_port == 25:
                    protocol = Protocol.SMTP
                
            elif packet.haslayer(UDP):
                udp_layer = packet[UDP]
                protocol = Protocol.UDP
                source_port = udp_layer.sport
                dest_port = udp_layer.dport
                
                # Check for DNS
                if dest_port == 53 or source_port == 53:
                    protocol = Protocol.DNS
                    
            elif packet.haslayer(ICMP):
                protocol = Protocol.ICMP
            
            # Calculate payload hash
            payload = bytes(packet)
            payload_hash = hashlib.md5(payload).hexdigest()
            
            # Create metadata
            metadata = {
                "ttl": getattr(ip_layer, "ttl", None),
                "length": len(payload),
                "checksum": getattr(ip_layer, "chksum", None)
            }
            
            # Add HTTP-specific metadata
            if packet.haslayer(HTTP):
                http_layer = packet[HTTP]
                metadata.update({
                    "http_method": getattr(http_layer, "Method", b"").decode("utf-8", errors="ignore"),
                    "http_host": getattr(http_layer, "Host", b"").decode("utf-8", errors="ignore"),
                    "http_uri": getattr(http_layer, "Path", b"").decode("utf-8", errors="ignore"),
                    "user_agent": getattr(http_layer, "User_Agent", b"").decode("utf-8", errors="ignore")
                })
            
            return NetworkPacket(
                id=f"pkt_{int(timestamp.timestamp() * 1000000)}",
                timestamp=timestamp,
                source_ip=source_ip,
                dest_ip=dest_ip,
                source_port=source_port,
                dest_port=dest_port,
                protocol=protocol,
                payload_size=len(payload),
                flags=flags,
                payload_hash=payload_hash,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error("Error parsing packet", error=str(e))
            return None
    
    async def get_packets(self, batch_size: int = 100) -> List[NetworkPacket]:
        """Get a batch of captured packets."""
        packets = []
        
        try:
            for _ in range(batch_size):
                try:
                    packet = self.packet_queue.get_nowait()
                    packets.append(packet)
                    self.stats["packets_processed"] += 1
                    self.packet_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            
        except Exception as e:
            logger.error("Error getting packets", error=str(e))
        
        return packets
    
    async def block_ip(self, ip_address: str, duration: int = 3600) -> None:
        """Block an IP address for specified duration."""
        try:
            # Validate IP address
            ipaddress.ip_address(ip_address)
            
            self.blocked_ips.add(ip_address)
            self.stats["blocked_connections"] += 1
            
            logger.info("IP blocked", ip=ip_address, duration=duration)
            
            # Schedule unblock
            if duration > 0:
                asyncio.create_task(self._schedule_unblock(ip_address, duration))
            
        except ValueError:
            raise NetworkMonitorError(f"Invalid IP address: {ip_address}")
        except Exception as e:
            logger.error("Error blocking IP", ip=ip_address, error=str(e))
            raise NetworkMonitorError(f"Failed to block IP: {str(e)}")
    
    async def _schedule_unblock(self, ip_address: str, duration: int) -> None:
        """Schedule IP unblock after duration."""
        try:
            await asyncio.sleep(duration)
            if ip_address in self.blocked_ips:
                self.blocked_ips.remove(ip_address)
                logger.info("IP unblocked", ip=ip_address)
                
        except Exception as e:
            logger.error("Error unblocking IP", ip=ip_address, error=str(e))
    
    async def unblock_ip(self, ip_address: str) -> None:
        """Manually unblock an IP address."""
        try:
            if ip_address in self.blocked_ips:
                self.blocked_ips.remove(ip_address)
                logger.info("IP manually unblocked", ip=ip_address)
            else:
                logger.warning("IP not in blocked list", ip=ip_address)
                
        except Exception as e:
            logger.error("Error unblocking IP", ip=ip_address, error=str(e))
            raise NetworkMonitorError(f"Failed to unblock IP: {str(e)}")
    
    async def get_blocked_ips(self) -> List[str]:
        """Get list of currently blocked IP addresses."""
        return list(self.blocked_ips)
    
    async def analyze_traffic_patterns(self, window_minutes: int = 5) -> Dict[str, Any]:
        """Analyze recent traffic patterns."""
        try:
            # This would typically analyze traffic from a time-series database
            # For now, return basic statistics
            
            current_time = datetime.utcnow()
            uptime = (current_time - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
            
            packets_per_second = self.stats["packets_captured"] / max(uptime, 1)
            drop_rate = (self.stats["packets_dropped"] / max(self.stats["packets_captured"], 1)) * 100
            
            return {
                "packets_per_second": round(packets_per_second, 2),
                "drop_rate_percent": round(drop_rate, 2),
                "blocked_ips_count": len(self.blocked_ips),
                "queue_size": self.packet_queue.qsize(),
                "uptime_seconds": round(uptime),
                "analysis_window_minutes": window_minutes
            }
            
        except Exception as e:
            logger.error("Error analyzing traffic patterns", error=str(e))
            return {}
    
    async def scan_network(self, network: str, scan_type: str = "ping") -> Dict[str, Any]:
        """Perform network scan."""
        try:
            network_obj = ipaddress.ip_network(network, strict=False)
            results = {
                "network": str(network_obj),
                "scan_type": scan_type,
                "timestamp": datetime.utcnow(),
                "hosts": []
            }
            
            # Simple ping scan
            if scan_type == "ping":
                for ip in list(network_obj.hosts())[:100]:  # Limit to 100 hosts
                    try:
                        # Send ICMP ping
                        response = scapy.sr1(
                            scapy.IP(dst=str(ip))/scapy.ICMP(),
                            timeout=1,
                            verbose=0
                        )
                        
                        if response:
                            results["hosts"].append({
                                "ip": str(ip),
                                "status": "up",
                                "response_time": 1  # Placeholder
                            })
                    except Exception:
                        continue
            
            logger.info("Network scan completed", network=network, hosts_found=len(results["hosts"]))
            return results
            
        except Exception as e:
            logger.error("Error scanning network", network=network, error=str(e))
            raise NetworkMonitorError(f"Network scan failed: {str(e)}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get network monitoring statistics."""
        current_time = datetime.utcnow()
        uptime = (current_time - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0
        
        return {
            **self.stats,
            "uptime_seconds": round(uptime),
            "blocked_ips_count": len(self.blocked_ips),
            "queue_size": self.packet_queue.qsize(),
            "packets_per_second": round(self.stats["packets_captured"] / max(uptime, 1), 2),
            "interface": self.interface,
            "is_running": self._running
        }
    
    def is_running(self) -> bool:
        """Check if network monitor is running."""
        return self._running and self._capture_thread and self._capture_thread.is_alive()
    
    async def cleanup(self) -> None:
        """Cleanup network monitor resources."""
        try:
            logger.info("Stopping network monitor")
            
            self._running = False
            self._stop_event.set()
            
            # Wait for capture thread to finish
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=5)
            
            # Clear queues and blocked IPs
            while not self.packet_queue.empty():
                try:
                    self.packet_queue.get_nowait()
                    self.packet_queue.task_done()
                except asyncio.QueueEmpty:
                    break
            
            self.blocked_ips.clear()
            
            logger.info("Network monitor stopped")
            
        except Exception as e:
            logger.error("Error during network monitor cleanup", error=str(e))