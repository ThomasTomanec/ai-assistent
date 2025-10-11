"""
Location Service - Auto-detects or manually configures user location
"""

import structlog
from typing import Dict, Optional
import geocoder
from timezonefinder import TimezoneFinder
from geopy.geocoders import Nominatim
import pytz
from datetime import datetime

logger = structlog.get_logger()


class LocationService:
    """
    Service for detecting and managing user location.

    Features:
    - Auto-detects location from IP address
    - Manual location configuration
    - Timezone detection
    - Caching for performance
    """

    def __init__(self):
        """Initialize location service"""
        self.geolocator = Nominatim(user_agent="voice-assistant")
        self.timezone_finder = TimezoneFinder()
        self._cached_location: Optional[Dict] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_duration_hours = 1
        logger.debug("location_service_initialized")

    def get_current_location(self) -> Dict:
        """
        Get current location (auto-detect or cached).

        Returns:
            Dict with city, country, timezone, coordinates
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("location_cache_hit")
            return self._cached_location

        # Auto-detect
        try:
            location = self._detect_location()
            self._update_cache(location)
            logger.info("location_detected", city=location['city'], country=location['country'])
            return location
        except Exception as e:
            logger.error("location_detection_failed", error=str(e))
            return self._get_fallback_location()

    def get_timezone(self, user_config) -> str:
        """
        Get timezone based on configuration.

        Args:
            user_config: User configuration object

        Returns:
            Timezone string (e.g., 'Europe/Prague')
        """
        try:
            # Check if auto-detect is enabled
            if user_config.get('location.auto_detect', True):
                try:
                    location = self.get_current_location()
                    timezone = location.get('timezone', 'Europe/Prague')
                    logger.debug("timezone_auto_detected", timezone=timezone)
                    return timezone
                except Exception as e:
                    logger.warning("timezone_auto_detect_failed", error=str(e))
                    return 'Europe/Prague'
            else:
                # Use manual timezone from config
                timezone = user_config.get('location.manual.timezone', 'Europe/Prague')
                logger.debug("timezone_manual_configured", timezone=timezone)
                return timezone

        except Exception as e:
            logger.error("timezone_detection_failed", error=str(e))
            return 'Europe/Prague'

    def _detect_location(self) -> Dict:
        """
        Auto-detect location from IP address.

        Returns:
            Dict with location information
        """
        try:
            # Get location from IP
            g = geocoder.ip('me')

            if not g.ok:
                raise Exception("IP geolocation failed")

            # Extract coordinates
            lat, lng = g.latlng

            # Get timezone
            timezone_str = self.timezone_finder.timezone_at(lat=lat, lng=lng)
            if not timezone_str:
                timezone_str = 'Europe/Prague'

            # Get detailed location info
            location_info = {
                'city': g.city or 'Unknown',
                'region': g.state or '',
                'country': g.country or 'CZ',
                'country_code': g.country_code or 'CZ',
                'latitude': lat,
                'longitude': lng,
                'timezone': timezone_str,
                'ip': g.ip
            }

            logger.debug("location_detected", location=location_info)
            return location_info

        except Exception as e:
            logger.error("location_detection_error", error=str(e))
            raise

    def get_manual_location(self, user_config) -> Dict:
        """
        Get manually configured location from user config.

        Args:
            user_config: User configuration object

        Returns:
            Dict with location information
        """
        try:
            manual = user_config.get('location.manual', {})

            location = {
                'city': manual.get('city', 'Prague'),
                'region': manual.get('region', ''),
                'country': manual.get('country', 'Česká republika'),
                'country_code': 'CZ',
                'timezone': manual.get('timezone', 'Europe/Prague'),
                'latitude': None,
                'longitude': None,
                'ip': None
            }

            logger.debug("manual_location_configured", city=location['city'])
            return location

        except Exception as e:
            logger.error("manual_location_error", error=str(e))
            return self._get_fallback_location()

    def _is_cache_valid(self) -> bool:
        """Check if cached location is still valid"""
        if not self._cached_location or not self._cache_timestamp:
            return False

        now = datetime.now()
        time_diff = (now - self._cache_timestamp).total_seconds() / 3600

        is_valid = time_diff < self._cache_duration_hours

        if not is_valid:
            logger.debug("location_cache_expired")

        return is_valid

    def _update_cache(self, location: Dict) -> None:
        """Update location cache"""
        self._cached_location = location
        self._cache_timestamp = datetime.now()
        logger.debug("location_cache_updated")

    def _get_fallback_location(self) -> Dict:
        """Get fallback location when detection fails"""
        fallback = {
            'city': 'Prague',
            'region': '',
            'country': 'Česká republika',
            'country_code': 'CZ',
            'timezone': 'Europe/Prague',
            'latitude': 50.0755,
            'longitude': 14.4378,
            'ip': None
        }
        logger.warning("using_fallback_location", city=fallback['city'])
        return fallback

    def clear_cache(self) -> None:
        """Clear location cache"""
        self._cached_location = None
        self._cache_timestamp = None
        logger.debug("location_cache_cleared")

    def get_location_summary(self) -> str:
        """
        Get human-readable location summary.

        Returns:
            String like "Prague, Česká republika"
        """
        try:
            location = self.get_current_location()
            return f"{location['city']}, {location['country']}"
        except Exception:
            return "Prague, Česká republika"
