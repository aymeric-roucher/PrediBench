"""Date-related utility functions."""

from datetime import date


def is_backward_mode(target_date: date) -> bool:
    """    
    The backward mode will be used when the target date is not today, the logic to get the data or to run the agent will be different.
    """
    return target_date != date.today()