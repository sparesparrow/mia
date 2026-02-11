
def decode_soot_mass(hex_response):
    """
    Decodes DPF Soot Mass from hex response.
    Expected format: 2 bytes typically for mass.
    Formula: (A * 256 + B) / 100 for grams (Example).
    """
    try:
        # Remove whitespace and generic success codes like '41 XX' if present, 
        # but usually the caller handles stripping '41 PID' prefix.
        # Assuming hex_response contains just data bytes or full response.
        clean_hex = hex_response.replace(" ", "").strip()
        
        # Heuristic: if it looks like a full response (e.g. 41 ...), skip mode/pid
        # For this helper, we assume we get the relevant data bytes.
        
        if len(clean_hex) >= 4:
            # Taking first 2 bytes
            val = int(clean_hex[:4], 16)
            return float(val) / 100.0
    except ValueError:
        pass
    return 0.0

def decode_oil_temp(hex_response):
    """
    Decodes Oil Temperature (deg C).
    Formula: A - 40.
    """
    try:
        clean_hex = hex_response.replace(" ", "").strip()
        if len(clean_hex) >= 2:
            val = int(clean_hex[:2], 16)
            return float(val - 40)
    except ValueError:
        pass
    return 0.0

def decode_eolys_level(hex_response):
    """
    Decodes Eolys Additive Level.
    Returns tuple (percent, liters).
    """
    try:
        clean_hex = hex_response.replace(" ", "").strip()
        if len(clean_hex) >= 2:
            val = int(clean_hex[:2], 16)
            # Assuming byte is percentage for now
            return (float(val), float(val) * 0.03) # Mock conversion to liters
    except ValueError:
        pass
    return (0.0, 0.0)

def decode_dpf_status(hex_response):
    """
    Decodes DPF Status.
    Returns integer mapping to DpfStatus enum.
    0: Normal, 1: Regenerating, 2: Warning
    """
    try:
        clean_hex = hex_response.replace(" ", "").strip()
        if len(clean_hex) >= 2:
            val = int(clean_hex[:2], 16)
            # Mock logic
            if val & 0x01:
                return 1
            if val & 0x02:
                return 2
    except ValueError:
        pass
    return 0
