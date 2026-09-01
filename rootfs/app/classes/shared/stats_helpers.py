"""
Stats conversion and formatting utilities
"""

import datetime
import typing as t


class StatsConverter:
    """Pure functions for stats transformations"""

    # Default gap threshold (used when fewer than 3 data points)
    DEFAULT_GAP_THRESHOLD_SECONDS = 120  # 2 minutes
    # Multiplier: a gap must be this many times the median interval to count
    GAP_MULTIPLIER = 3

    @staticmethod
    def bytes_to_gigabytes(bytes_value: int) -> float:
        """
        Convert bytes to GB with 2 decimal precision

        Args:
            bytes_value: Memory in bytes

        Returns:
            float: Memory in GB (e.g., 3.13)
        """
        # Type validation for safety
        if bytes_value is None or not isinstance(bytes_value, (int, float)):
            return 0.0
        if bytes_value <= 0:
            return 0.0
        return round(bytes_value / (1024**3), 2)

    @staticmethod
    def _make_gap_marker(dt: datetime.datetime) -> dict:
        """Create a null-value gap marker at the given time.

        Chart.js breaks the line at null y-values (with spanGaps=false),
        and LTTB decimation passes null points through unchanged.
        """
        return {
            "created": dt,
            "online": None,
            "mem_percent": None,
            "mem": None,
            "cpu": None,
        }

    @classmethod
    def _compute_gap_threshold(
        cls, stats: t.List[t.Dict[str, t.Any]]
    ) -> datetime.timedelta:
        """
        Derive gap threshold from median interval in the data.

        After adaptive sampling, the interval between consecutive points
        grows proportionally to the sample rate.  Using a fixed threshold
        would treat normal sampled spacing as gaps.  Instead, we compute
        the median interval and require a gap to be GAP_MULTIPLIER× that.
        """
        if len(stats) < 3:
            return datetime.timedelta(seconds=cls.DEFAULT_GAP_THRESHOLD_SECONDS)

        intervals = []
        for i in range(len(stats) - 1):
            t1 = stats[i].get("created")
            t2 = stats[i + 1].get("created")
            if t1 and t2:
                intervals.append((t2 - t1).total_seconds())

        if not intervals:
            return datetime.timedelta(seconds=cls.DEFAULT_GAP_THRESHOLD_SECONDS)

        intervals.sort()
        median = intervals[len(intervals) // 2]
        threshold_secs = max(
            cls.DEFAULT_GAP_THRESHOLD_SECONDS, median * cls.GAP_MULTIPLIER
        )
        return datetime.timedelta(seconds=threshold_secs)

    @classmethod
    def _empty_range_markers(
        cls,
        start_time: datetime.datetime = None,
        end_time: datetime.datetime = None,
    ) -> t.List[t.Dict[str, t.Any]]:
        """Return gap markers for an empty stats range."""
        result = []
        if start_time:
            result.append(cls._make_gap_marker(start_time))
        if end_time and end_time != start_time:
            result.append(cls._make_gap_marker(end_time))
        return result

    @classmethod
    def _insert_gap_markers(
        cls,
        stats: t.List[t.Dict[str, t.Any]],
        threshold: datetime.timedelta,
        filled: t.List[t.Dict[str, t.Any]],
    ) -> None:
        """Append stats to *filled*, inserting null markers at large gaps."""
        for i, stat in enumerate(stats):
            filled.append(stat)
            if i >= len(stats) - 1:
                continue
            curr_time = stat.get("created")
            next_time = stats[i + 1].get("created")
            if curr_time and next_time and next_time - curr_time > threshold:
                mid = curr_time + (next_time - curr_time) / 2
                filled.append(cls._make_gap_marker(mid))

    @classmethod
    def fill_gaps(
        cls,
        stats: t.List[t.Dict[str, t.Any]],
        start_time: datetime.datetime = None,
        end_time: datetime.datetime = None,
    ) -> t.List[t.Dict[str, t.Any]]:
        """
        Insert null gap markers so Chart.js breaks the line during downtime.

        Uses null y-values instead of zero-value boundary points.  LTTB
        decimation preserves null points, so the line break survives
        regardless of zoom level.

        Args:
            stats: Sorted list of stat dicts (ascending by 'created')
            start_time: Requested range start (extends x-axis if data
                        starts later)
            end_time: Requested range end (extends x-axis if data
                      ends earlier)

        Returns:
            New list with null gap markers inserted where data is missing
        """
        if not stats:
            return cls._empty_range_markers(start_time, end_time)

        # Compute adaptive gap threshold from the actual data spacing.
        threshold = cls._compute_gap_threshold(stats)
        filled = []

        first_time = stats[0].get("created")
        last_time = stats[-1].get("created")

        # Extend x-axis to start of range if data begins later
        if start_time and first_time and first_time - start_time > threshold:
            filled.append(cls._make_gap_marker(start_time))

        # Walk through data and insert gap markers between distant points
        cls._insert_gap_markers(stats, threshold, filled)

        # Extend x-axis to end of range if data ends earlier
        if end_time and last_time and end_time - last_time > threshold:
            filled.append(cls._make_gap_marker(end_time))

        return filled

    @staticmethod
    def prepare_chart_datasets(
        stats: t.List[t.Dict[str, t.Any]], server_type: str = "minecraft-java"
    ) -> t.Dict[str, t.List]:
        """
        Transform raw stats into Chart.js-compatible datasets.

        None values (from gap markers) are preserved as None so they
        serialize to JSON null, causing Chart.js to break the line.

        Args:
            stats: List of stat dictionaries from database
            server_type: Type of server (affects player tracking)

        Returns:
            dict: Arrays for players, dates, ram_percent, ram_gb, cpu
        """
        players = []
        dates = []
        ram_percent = []
        ram_gb = []
        cpu = []

        for stat in stats:
            # Format date for display
            created = stat.get("created")
            if created:
                dates.append(created.strftime("%Y/%m/%d, %H:%M:%S"))

            is_gap = stat.get("online") is None

            if is_gap:
                # Preserve null for Chart.js line breaks
                if "minecraft-java" in server_type or "hytale" in server_type:
                    players.append(None)
                ram_percent.append(None)
                ram_gb.append(None)
                cpu.append(None)
            else:
                if "minecraft-java" in server_type or "hytale" in server_type:
                    players.append(stat.get("online", 0))
                ram_percent.append(stat.get("mem_percent", 0))
                ram_gb.append(StatsConverter.bytes_to_gigabytes(stat.get("mem", 0)))
                cpu.append(stat.get("cpu", 0))

        return {
            "players": players,
            "dates": dates,
            "ram_percent": ram_percent,
            "ram_gb": ram_gb,
            "cpu": cpu,
        }
