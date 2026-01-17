# ============================================================
# JARVIS FILESYSTEM SECURITY CONFIG
# ============================================================

# NOTE:
# Raw strings CANNOT end with a single backslash.
# Either remove the r-prefix or escape the backslash.

ALLOWED_ROOT = "C:\\"

# Access modes:
# - "sandbox" : restrict access to ALLOWED_ROOT
# - "full"    : allow access to entire filesystem
FILESYSTEM_ACCESS_SCOPE = "full"


