import socket
import subprocess
import platform
import json
import re
from typing import Dict, Optional, Tuple, List
import ipaddress

def get_network_info() -> Dict[str, str]:
    """
    Get network information including IP address and SSID if available
    
    Returns:
        Dictionary with network information
    """
    info = {
        "ip": get_ip_address(),
        "hostname": socket.gethostname(),
        "ssid": get_wifi_ssid(),
        "platform": platform.system(),
        "user_agent": get_user_agent_info()
    }
    return info

def get_ip_address() -> str:
    """
    Get the local IP address
    
    Returns:
        IP address as string
    """
    try:
        # Create a socket connection to determine the IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Doesn't need to be reachable
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Error getting IP address: {str(e)}")
        return "Unknown"

def get_wifi_ssid() -> Optional[str]:
    """
    Get the current WiFi SSID (platform dependent)
    
    Returns:
        SSID as string or None if not available
    """
    system = platform.system()
    
    try:
        if system == "Darwin":  # macOS
            cmd = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I"
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            ssid_match = re.search(r' SSID: (.+)$', output, re.MULTILINE)
            if ssid_match:
                return ssid_match.group(1)
        
        elif system == "Linux":
            cmd = "iwgetid -r"
            output = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
            if output:
                return output
        
        elif system == "Windows":
            cmd = "netsh wlan show interfaces"
            output = subprocess.check_output(cmd, shell=True).decode("utf-8")
            ssid_match = re.search(r'SSID\s+:\s(.+)$', output, re.MULTILINE)
            if ssid_match:
                return ssid_match.group(1).strip()
    
    except Exception as e:
        print(f"Error getting WiFi SSID: {str(e)}")
    
    return None

def get_user_agent_info() -> str:
    """
    Get basic device and browser information
    
    Returns:
        String with device information
    """
    return f"{platform.system()} {platform.release()}"

def is_on_allowed_network(allowed_networks: Optional[Dict] = None) -> Tuple[bool, Dict[str, str]]:
    """
    Check if the device is connected to an allowed network
    
    Args:
        allowed_networks: Dictionary with allowed SSIDs and IP ranges from database
        
    Returns:
        Tuple of (is_allowed, network_info)
    """
    network_info = get_network_info()
    
    # If no allowed networks provided, return False
    if not allowed_networks:
        return False, network_info
    
    # Check SSID
    if network_info.get("ssid") and "ssid" in allowed_networks:
        if network_info.get("ssid") in allowed_networks["ssid"]:
            return True, network_info
    
    # Check IP ranges
    ip = network_info.get("ip", "")
    if ip != "Unknown" and "ip_ranges" in allowed_networks:
        # Check exact IP matches
        if ip in allowed_networks.get("ip_exact", []):
            return True, network_info
            
        # Check IP ranges (prefix match)
        for ip_range in allowed_networks.get("ip_ranges", []):
            if ip.startswith(ip_range):
                return True, network_info
                
        # Check CIDR notation ranges
        try:
            ip_obj = ipaddress.ip_address(ip)
            for cidr_range in allowed_networks.get("ip_cidr", []):
                if ip_obj in ipaddress.ip_network(cidr_range):
                    return True, network_info
        except ValueError:
            pass  # Invalid IP format
    
    return False, network_info

def format_network_info(network_info: Dict[str, str]) -> str:
    """
    Format network information for display
    
    Args:
        network_info: Dictionary with network information
        
    Returns:
        Formatted string
    """
    lines = []
    if network_info.get("ssid"):
        lines.append(f"WiFi: {network_info['ssid']}")
    if network_info.get("ip"):
        lines.append(f"IP: {network_info['ip']}")
    if network_info.get("hostname"):
        lines.append(f"Device: {network_info['hostname']}")
    
    return ", ".join(lines)

def get_allowed_networks_default() -> Dict:
    """
    Get default allowed networks configuration
    
    Returns:
        Dictionary with default allowed networks
    """
    return {
        "ssid": ["Office_WiFi", "Company_Network", "Dev_Team"],
        "ip_exact": ["127.0.0.1"],
        "ip_ranges": ["192.168.1.", "10.0.0."],
        "ip_cidr": ["192.168.0.0/16", "10.0.0.0/8"]
    }