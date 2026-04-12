from enum import StrEnum


class UserRole(StrEnum):
    citizen = "citizen"
    authority = "authority"
    admin = "admin"


class ComplaintStatus(StrEnum):
    pending = "Pending"
    acknowledged = "Acknowledged"
    in_progress = "In Progress"
    done = "Done"
    resolved = "Resolved"
    rejected = "Rejected"


class CorporationType(StrEnum):
    """Dhaka City Corporation types"""
    dncc = "DNCC"  # Dhaka North City Corporation
    dscc = "DSCC"  # Dhaka South City Corporation
