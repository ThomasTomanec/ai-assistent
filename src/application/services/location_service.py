"""Location Service - Auto-detect device location"""

import structlog
import geocoder
from geopy.geocoders import Nominatim
from datetime import datetime
import pytz

logger = structlog.get_logger()


class LocationService:
    """Auto-detect and manage device location"""

    def __init__(self):
        self.geolocator = Nominatim(user_agent="voice-assistant")
        self._cached_location = None
        self._cache_timestamp = None
        self._cache_duration = 3600  # 1 hodina cache

        logger.info("location_service_initialized")

    def get_current_location(self) -> dict:
        """
        Get current device location (IP-based)

        Returns:
            dict: {
                'city': str,
                'region': str,
                'country': str,
                'coordinates': (lat, lng),
                'timezone': str
            }
        """
        # Check cache
        if self._is_cache_valid():
            logger.debug("returning_cached_location")
            return self._cached_location

        try:
            # Get location from IP
            logger.info("detecting_location_from_ip")
            g = geocoder.ip('me')

            if g.ok:
                location_data = {
                    'city': g.city or 'Unknown',
                    'region': g.state or 'Unknown',
                    'country': g.country or 'Unknown',
                    'country_code': g.country or 'CZ',
                    'coordinates': (g.lat, g.lng),
                    'timezone': self._get_timezone_from_coords(g.lat, g.lng)
                }

                # Cache result
                self._cached_location = location_data
                self._cache_timestamp = datetime.now()

                logger.info(
                    "location_detected",
                    city=location_data['city'],
                    country=location_data['country'],
                    timezone=location_data['timezone']
                )

                return location_data
            else:
                logger.warning("ip_geolocation_failed")
                return self._get_fallback_location()

        except Exception as e:
            logger.error("location_detection_error", error=str(e))
            return self._get_fallback_location()

    def _get_timezone_from_coords(self, lat: float, lng: float) -> str:
        """Get timezone from coordinates"""
        try:
            from timezonefinder import TimezoneFinder
            tf = TimezoneFinder()
            tz_name = tf.timezone_at(lat=lat, lng=lng)
            return tz_name or 'Europe/Prague'
        except Exception:
            logger.warning("timezone_lookup_failed")
            return 'Europe/Prague'  # Fallback

    def _is_cache_valid(self) -> bool:
        """Check if cached location is still valid"""
        if not self._cached_location or not self._cache_timestamp:
            return False

        age = (datetime.now() - self._cache_timestamp).total_seconds()
        return age < self._cache_duration

    def _get_fallback_location(self) -> dict:
        """Fallback location when detection fails"""
        logger.info("using_fallback_location")
        return {
            'city': 'Praha',
            'region': 'Praha',
            'country': 'Česká republika',
            'country_code': 'CZ',
            'coordinates': (50.0755, 14.4378),
            'timezone': 'Europe/Prague'
        }

    def refresh_location(self):
        """Force refresh location (clear cache)"""
        logger.info("refreshing_location")
        self._cached_location = None
        self._cache_timestamp = None
        return self.get_current_location()
