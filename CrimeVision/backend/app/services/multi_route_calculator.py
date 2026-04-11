"""
Enhanced route calculation with multiple options
"""
from typing import Dict, List, Any, Tuple
import requests
import logging

logger = logging.getLogger(__name__)

class MultiRouteCalculator:
    """Calculate multiple route options with different priorities"""
    
    OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
    
    @staticmethod
    def calculate_multiple_routes(
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float
    ) -> Dict[str, Any]:
        """
        Guarantees variety by trying standard routes + forced via-points on BOTH sides.
        """
        try:
            # 1. Get standard alternative routes from OSRM
            url = f"{MultiRouteCalculator.OSRM_BASE_URL}/{start_lng},{start_lat};{end_lng},{end_lat}"
            params = {
                'overview': 'full',
                'geometries': 'geojson',
                'steps': 'true',
                'alternatives': 'true',
                'continue_straight': 'false'
            }
            
            response = requests.get(url, params=params, timeout=25)
            response.raise_for_status()
            data = response.json()
            
            raw_routes = data.get('routes', [])
            if not raw_routes:
                raise ValueError("No routes found")
            
            # Process initial routes
            final_routes = []
            for i, r in enumerate(raw_routes):
                processed = MultiRouteCalculator._process_route(r, f"osrm_alt_{i}")
                if processed:
                    final_routes.append(processed)
            
            # 2. Force extra routes if we have fewer than 3
            # We try shifting the midpoint to BOTH sides (left and right) to ensure variety
            if len(final_routes) < 3:
                logger.info(f"🛤️ Only {len(final_routes)} routes found. Forcing extra via-points...")
                
                # Calculate vector from start to end
                d_lat = end_lat - start_lat
                d_lng = end_lng - start_lng
                mid_lat = (start_lat + end_lat) / 2
                mid_lng = (start_lng + end_lng) / 2
                
                # Perpendicular vectors (-dy, dx) and (dy, -dx)
                p_lat_1, p_lng_1 = -d_lng, d_lat
                p_lat_2, p_lng_2 = d_lng, -d_lat
                
                dist = (p_lat_1**2 + p_lng_1**2)**0.5
                if dist > 0:
                    # We'll try two different offsets: 1.5km (0.015) and 3.0km (0.030) if needed
                    offsets = [0.015, -0.015, 0.030]
                    
                    for offset_val in offsets:
                        if len(final_routes) >= 4: break # Get a few to filter later
                        
                        scale = offset_val / dist
                        via_lat = mid_lat + (p_lat_1 * scale)
                        via_lng = mid_lng + (p_lng_1 * scale)
                        
                        try:
                            v_url = f"{MultiRouteCalculator.OSRM_BASE_URL}/{start_lng},{start_lat};{via_lng},{via_lat};{end_lng},{end_lat}"
                            v_res = requests.get(v_url, params={'overview': 'full', 'geometries': 'geojson', 'steps': 'true'}, timeout=12)
                            if v_res.ok:
                                v_data = v_res.json()
                                if v_data.get('routes'):
                                    processed = MultiRouteCalculator._process_route(v_data['routes'][0], f"forced_via_{offset_val}")
                                    if processed:
                                        final_routes.append(processed)
                        except: continue

            # 3. Final grouping
            # Return up to 5 distinct-ish routes for the crime analyzer to label/filter
            processed_map = {}
            for i, r in enumerate(final_routes[:5]):
                processed_map[f'route_{i}'] = r
                
            return processed_map
            
        except Exception as e:
            logger.error(f"❌ Error calculating multiple routes: {e}")
            raise
    
    @staticmethod
    def _process_route(route_data: Dict, route_type: str) -> Dict[str, Any]:
        """Process a single route from OSRM response"""
        try:
            geometry = route_data['geometry']
            distance = route_data['distance']
            duration = route_data['duration']
            
            waypoints = [{'lat': coord[1], 'lng': coord[0]} for coord in geometry['coordinates']]
            
            steps = []
            if 'legs' in route_data:
                for leg in route_data['legs']:
                    for step in leg.get('steps', []):
                        steps.append({
                            'instruction': step.get('maneuver', {}).get('instruction', 'Continue'),
                            'distance': step.get('distance', 0),
                            'duration': step.get('duration', 0)
                        })
            
            return {
                'type': route_type,
                'geometry': geometry,
                'waypoints': waypoints,
                'distance': distance,
                'duration': duration,
                'distance_km': round(distance / 1000, 2),
                'duration_min': round(duration / 60, 1),
                'steps': steps
            }
        except Exception as e:
            logger.error(f"❌ Error processing route: {e}")
            return None
