// src/components/HeatmapLayer.jsx
import L from "leaflet";
import { useMap } from "react-leaflet";
import { useEffect } from "react";
import "leaflet.heat";

export default function HeatmapLayer({
  points,
  radius = 45,
  blur = 30,
  maxZoom = 17,
  minOpacity = 0.5,
  gradient,
}) {
  const map = useMap();

  useEffect(() => {
    console.log(`🔥 HeatmapLayer mount — received ${points?.length || 0} input points`);

    if (typeof L.heatLayer !== 'function') {
      console.error('🔥 leaflet.heat plugin not loaded — L.heatLayer is undefined');
      return;
    }
    if (!points || points.length === 0) {
      console.warn('🔥 HeatmapLayer: no points to render');
      return;
    }

    // Aggregate by coordinate so multiple incidents at the same lat/lng
    // (typical when crimes are geocoded to area centroids) accumulate into
    // a stronger, more visible blob instead of stacking invisibly.
    const bucket = new Map();
    for (const p of points) {
      if (!p) continue;
      const lat = Number(p.lat);
      const lng = Number(p.lng);
      if (!isFinite(lat) || !isFinite(lng)) continue;
      const key = `${lat.toFixed(5)},${lng.toFixed(5)}`;
      const prev = bucket.get(key);
      const w = Number(p.intensity) || 1;
      if (prev) {
        prev.weight += w;
      } else {
        bucket.set(key, { lat, lng, weight: w });
      }
    }

    const aggregated = Array.from(bucket.values());
    if (aggregated.length === 0) {
      console.warn('🔥 HeatmapLayer: all points had invalid coords after parsing');
      return;
    }

    // Normalize so the densest cluster reaches the top of the gradient.
    const maxWeight = aggregated.reduce((m, p) => Math.max(m, p.weight), 0) || 1;
    const heatPoints = aggregated.map(p => [p.lat, p.lng, p.weight / maxWeight]);

    const currentZoom = map.getZoom();
    const intensityFactor = 1 / Math.pow(2, Math.max(0, Math.min(maxZoom - currentZoom, 12)));
    console.log(
      `🔥 HeatmapLayer: ${points.length} input → ${aggregated.length} aggregated clusters, ` +
      `max weight=${maxWeight.toFixed(2)}, radius=${radius}, blur=${blur}, ` +
      `minOpacity=${minOpacity}, maxZoom=${maxZoom}, currentZoom=${currentZoom}, ` +
      `intensity_factor=${intensityFactor.toFixed(4)}`
    );
    if (intensityFactor < 0.25) {
      console.warn(
        `⚠️  Heat will be barely visible — intensity is multiplied by ${intensityFactor.toFixed(4)} ` +
        `because maxZoom (${maxZoom}) is much higher than current zoom (${currentZoom}). ` +
        `Lower heatmap_layer_max_zoom in System Settings to ~${currentZoom}.`
      );
    }

    // Use simple keyword colors for the gradient — leaflet.heat 0.2.0 builds
    // a canvas linear gradient from these stops, and named colors are the
    // most reliable across browsers. Alpha is controlled by minOpacity.
    const heat = L.heatLayer(heatPoints, {
      radius,
      blur,
      maxZoom,
      minOpacity,
      // Heatmap-style ramp with red dominating the hot end. The previous ramp
      // peaked at red only at intensity 1.0, but normalized weights rarely
      // reach the top — typical "hot" pixels land around 0.6–0.85, which were
      // showing as orange. Push red lower so dense clusters look properly hot.
      gradient: gradient || {
        0.15: '#1e3a8a',  // deep blue (cold)
        0.30: '#3b82f6',  // blue
        0.45: '#22c55e',  // green
        0.60: '#facc15',  // yellow
        0.72: '#f97316',  // orange
        0.82: '#ef4444',  // red
        1.0:  '#7f1d1d',  // deep red (hottest)
      },
    });

    heat.addTo(map);

    // Track whether the layer is still attached so async redraws don't crash
    // after React unmounts the component (`heat._map` becomes null mid-flight).
    let attached = true;

    // leaflet.heat 0.2.0 has two bugs we work around here:
    // 1) It sets the canvas's width/height *attributes* but never gives it a
    //    matching CSS size. With certain pane styling the rendered box
    //    collapses to 0×0 — the heat is drawn, but at zero scale (invisible).
    //    Fix: explicitly mirror the buffer dimensions onto the canvas's style.
    // 2) `_redraw()` calls `this._map.getSize()` without a null guard. If the
    //    layer was just removed it throws. Fix: bail out if !attached.
    const fixCanvasSize = () => {
      // Grab the canvas the heat layer is *actually* drawing to — never via
      // querySelector, which can return a stale canvas from a previously
      // unmounted MapContainer that's still in the DOM.
      const canvas = heat._canvas;
      if (!canvas) return null;
      const w = canvas.width || map.getSize().x;
      const h = canvas.height || map.getSize().y;
      // Mirror the canvas's buffer dims onto its CSS box so the layout
      // engine doesn't collapse it to 0×N. We deliberately do NOT touch
      // `transform` — leaflet updates that during pan/zoom to keep the
      // canvas anchored to the map; overriding it desyncs heat from
      // markers when the user pans.
      canvas.style.setProperty('width',  w + 'px', 'important');
      canvas.style.setProperty('height', h + 'px', 'important');
      canvas.style.setProperty('max-width',  'none', 'important');
      canvas.style.setProperty('max-height', 'none', 'important');
      canvas.style.setProperty('min-width',  '0',    'important');
      canvas.style.setProperty('min-height', '0',    'important');
      canvas.style.setProperty('pointer-events', 'none', 'important');
      return canvas;
    };

    const forceDraw = () => {
      if (!attached) return;
      try {
        if (typeof heat.redraw === 'function' && heat._map) {
          heat.redraw();
        }
        const canvas = fixCanvasSize();
        if (canvas) {
          const rect = canvas.getBoundingClientRect();
          const cs = window.getComputedStyle(canvas);
          const parent = canvas.parentElement;
          const parentRect = parent ? parent.getBoundingClientRect() : null;
          console.log(
            `🔥 heat canvas: size=${canvas.width}×${canvas.height} ` +
            `bbox=${Math.round(rect.width)}×${Math.round(rect.height)} ` +
            `parentBbox=${parentRect ? Math.round(parentRect.width) + '×' + Math.round(parentRect.height) : 'n/a'} ` +
            `display=${cs.display} transform=${cs.transform} ` +
            `cssWidth=${cs.width} cssHeight=${cs.height}`
          );
          console.log('🔥 heat canvas inline style:', canvas.getAttribute('style'));
        }
      } catch (e) {
        console.warn('🔥 heat redraw failed', e);
      }
    };

    // Run once immediately (the canvas is in the DOM by now) so size is fixed
    // before the first paint, then again after layout settles.
    fixCanvasSize();
    const raf = requestAnimationFrame(forceDraw);
    const t1 = setTimeout(forceDraw, 250);
    const t2 = setTimeout(() => {
      try { map.invalidateSize(); } catch (e) { /* ignore */ }
      forceDraw();
    }, 600);

    // Re-mirror the size on every map move/zoom — leaflet.heat resizes the
    // canvas internally on viewport changes and the CSS size goes stale.
    const onMapResize = () => fixCanvasSize();
    map.on('resize zoomend moveend', onMapResize);

    return () => {
      attached = false;
      cancelAnimationFrame(raf);
      clearTimeout(t1);
      clearTimeout(t2);
      map.off('resize zoomend moveend', onMapResize);
      try { map.removeLayer(heat); } catch (e) { /* ignore */ }
    };
  }, [points, map, radius, blur, maxZoom, minOpacity, gradient]);

  return null;
}
