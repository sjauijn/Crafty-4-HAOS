"""
Metrics time range utilities
"""

import typing as t


class MetricsTimeRangeHelper:
    """Helper for managing metrics time range options"""

    # Fallback time range options (in hours) when no config presets exist
    FALLBACK_OPTIONS = [1, 3, 6, 12, 24, 48, 168]  # 1h to 7d

    @staticmethod
    def get_time_options(
        current_hours: int,
        presets: t.Optional[t.List[t.Dict[str, t.Any]]] = None,
    ) -> t.List[int]:
        """
        Get dropdown options, ensuring current selection is included

        Args:
            current_hours: Currently selected hours
            presets: Optional list of {"hours": int, "label": str} dicts from config

        Returns:
            list: Hour options with current_hours first if not in defaults
        """
        if presets:
            options = [p["hours"] for p in presets]
        else:
            options = MetricsTimeRangeHelper.FALLBACK_OPTIONS.copy()

        # If current selection isn't in options, add it
        if current_hours not in options:
            options.insert(0, current_hours)
        else:
            # Move current selection to front
            options.remove(current_hours)
            options.insert(0, current_hours)

        return options

    @staticmethod
    def parse_time_param(param_str: t.Optional[str], default: int = 24) -> int:
        """
        Parse time parameter from string

        Supports:
        - Integer hours: "12"
        - Days (legacy): Will be converted via calling code

        Args:
            param_str: Parameter string from URL
            default: Default value if parsing fails

        Returns:
            int: Parsed hours value
        """
        if param_str is None:
            return default

        try:
            return int(param_str)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def clamp_hours(hours: int, max_retention_hours: int) -> int:
        """
        Ensure hours is within valid range

        Args:
            hours: Requested hours
            max_retention_hours: Maximum allowed hours

        Returns:
            int: Clamped hours (between 1 and max_retention_hours)
        """
        if hours < 1:
            result = 1
        elif hours > max_retention_hours:
            result = max_retention_hours
        else:
            result = hours
        return result

    @staticmethod
    def format_display_label(hours: int) -> str:
        """
        Format hours into display label for dropdown

        Args:
            hours: Number of hours

        Returns:
            str: Formatted label (e.g., "6 Hours", "2 Days (48h)")
        """
        if hours < 24:
            # Less than a day: show hours
            label = f"{hours} Hour{'s' if hours != 1 else ''}"
        else:
            # One day or more: show days with hour notation
            days = hours // 24
            if hours % 24 == 0:
                # Exact days
                label = f"{days} Day{'s' if days != 1 else ''}"
            else:
                # Fractional days, show hours too
                label = f"{hours}h (~{days}d)"
        return label
