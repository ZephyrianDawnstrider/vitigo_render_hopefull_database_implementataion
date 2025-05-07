class DashboardError(Exception):
    """Base exception for dashboard-related errors"""
    pass

class DataFetchError(DashboardError):
    """Raised when there's an error fetching dashboard data"""
    pass

class StatsComputationError(DashboardError):
    """Raised when there's an error computing dashboard statistics"""
    pass

class InvalidDateRangeError(DashboardError):
    """Raised when an invalid date range is provided"""
    pass
