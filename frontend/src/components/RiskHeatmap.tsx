"use client";

import React, { useEffect, useRef } from "react";

export interface HeatSource {
  id: string | number;
  x: number;
  y: number;
  weight: number; // 0 to 100 scale
  sigma?: number;
}

interface RiskHeatmapProps {
  sources: HeatSource[];
  width?: number; // width in coordinate space (default 800)
  height?: number; // height in coordinate space (default 400)
  showContours?: boolean;
}

export function RiskHeatmap({
  sources,
  width = 800,
  height = 400,
  showContours = true,
}: RiskHeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Coarse grid size
  const gridW = 180;
  const gridH = 90;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // If there are no sources, clear the canvas and return
    if (sources.length === 0) {
      ctx.clearRect(0, 0, gridW, gridH);
      return;
    }

    // Allocate coarse grid
    const grid = Array.from({ length: gridH }, () => new Float32Array(gridW));

    // 1. Calculate the continuous field value for each grid cell
    for (let y = 0; y < gridH; y++) {
      // Cell center in coordinates of original space (width x height)
      const cy = ((y + 0.5) / gridH) * height;

      for (let x = 0; x < gridW; x++) {
        const cx = ((x + 0.5) / gridW) * width;

        let sumW = 0;
        let sumS = 0;

        for (let i = 0; i < sources.length; i++) {
          const src = sources[i];
          const sigma = src.sigma || 100;

          const dx = cx - src.x;
          const dy = cy - src.y;
          const distSq = dx * dx + dy * dy;

          // Gaussian influence: exp(-distSq / (2 * sigma^2))
          const s = Math.exp(-distSq / (2 * sigma * sigma));
          sumW += src.weight * s;
          sumS += s;
        }

        // Normalize by total influence, damp by proximity so far-from-everything cells fade to zero
        if (sumS > 0) {
          grid[y][x] = sumW / Math.max(1, sumS);
        } else {
          grid[y][x] = 0;
        }
      }
    }

    // 2. Rasterize the field to ImageData using color ramp
    const imgData = ctx.createImageData(gridW, gridH);
    const data = imgData.data;

    // Multi-stop hazard color ramp stops (values are on 0-100 scale)
    const stops = [
      { stop: 0, r: 6, g: 182, b: 212, a: 0.0 },     // Transparent (Safe / nominal start)
      { stop: 20, r: 6, g: 182, b: 212, a: 0.45 },   // Cyan "watch"
      { stop: 40, r: 245, g: 158, b: 11, a: 0.7 },    // Amber "elevated"
      { stop: 75, r: 239, g: 68, b: 68, a: 0.85 },    // Red "critical"
      { stop: 100, r: 255, g: 245, b: 245, a: 0.95 }  // Near-white "extreme"
    ];

    const getColorForValue = (v: number) => {
      const val = Math.max(0, Math.min(100, v));

      // Find surrounding stops
      let lower = stops[0];
      let upper = stops[stops.length - 1];

      for (let i = 0; i < stops.length - 1; i++) {
        if (val >= stops[i].stop && val <= stops[i + 1].stop) {
          lower = stops[i];
          upper = stops[i + 1];
          break;
        }
      }

      const range = upper.stop - lower.stop;
      const factor = range === 0 ? 0 : (val - lower.stop) / range;

      return {
        r: Math.round(lower.r + (upper.r - lower.r) * factor),
        g: Math.round(lower.g + (upper.g - lower.g) * factor),
        b: Math.round(lower.b + (upper.b - lower.b) * factor),
        a: lower.a + (upper.a - lower.a) * factor
      };
    };

    // Helper for per-cell edge detection for 40 and 75 risk thresholds
    const checkIsContour = (x: number, y: number): boolean => {
      const val = grid[y][x];

      // Check right neighbor
      if (x < gridW - 1) {
        const rVal = grid[y][x + 1];
        if ((val >= 40 && rVal < 40) || (val < 40 && rVal >= 40)) return true;
        if ((val >= 75 && rVal < 75) || (val < 75 && rVal >= 75)) return true;
      }

      // Check bottom neighbor
      if (y < gridH - 1) {
        const dVal = grid[y + 1][x];
        if ((val >= 40 && dVal < 40) || (val < 40 && dVal >= 40)) return true;
        if ((val >= 75 && dVal < 75) || (val < 75 && dVal >= 75)) return true;
      }

      return false;
    };

    // Populate pixels
    for (let y = 0; y < gridH; y++) {
      for (let x = 0; x < gridW; x++) {
        const val = grid[y][x];
        const color = getColorForValue(val);

        if (showContours && checkIsContour(x, y)) {
          // Blend with white contour line
          const blendAlpha = 0.55;
          color.r = Math.round(color.r * (1 - blendAlpha) + 255 * blendAlpha);
          color.g = Math.round(color.g * (1 - blendAlpha) + 255 * blendAlpha);
          color.b = Math.round(color.b * (1 - blendAlpha) + 255 * blendAlpha);
          color.a = Math.max(color.a, 0.6);
        }

        const idx = (y * gridW + x) * 4;
        data[idx] = color.r;
        data[idx + 1] = color.g;
        data[idx + 2] = color.b;
        data[idx + 3] = Math.round(color.a * 255);
      }
    }

    ctx.putImageData(imgData, 0, 0);
  }, [sources, width, height, showContours]);

  return (
    <canvas
      ref={canvasRef}
      width={gridW}
      height={gridH}
      className="absolute inset-0 w-full h-full pointer-events-none mix-blend-screen"
      style={{
        imageRendering: "auto", // Enables browser bilinear upscaling
      }}
    />
  );
}

export function HeatmapLegend() {
  return (
    <div className="flex flex-col gap-1 w-full max-w-[280px]">
      <div 
        className="h-2 w-full rounded-full border border-slate-800/80 shadow-inner"
        style={{
          background: "linear-gradient(to right, rgba(6,182,212,0) 0%, rgba(6,182,212,0.45) 20%, rgba(245,158,11,0.7) 45%, rgba(239,68,68,0.85) 75%, rgba(255,245,245,0.95) 100%)"
        }}
      />
      <div className="flex justify-between text-[9px] font-semibold text-slate-400 font-mono px-0.5">
        <span>Safe</span>
        <span className="text-cyan-400/90 font-bold">Watch</span>
        <span className="text-amber-400/90 font-bold">Elevated</span>
        <span className="text-rose-400/90 font-bold">Critical</span>
      </div>
    </div>
  );
}
