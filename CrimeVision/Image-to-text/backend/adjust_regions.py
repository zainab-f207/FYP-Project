"""
Interactive Region Adjuster for FIR Documents
Helps you find the correct extraction regions for your FIR layout
"""

import cv2
import numpy as np
from pathlib import Path
import sys

class RegionAdjuster:
    def __init__(self, image_path: str):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        self.height, self.width = self.image.shape[:2]
        self.display_scale = 0.5  # Scale for display
        
        # Current regions (percentages)
        self.regions = {
            'HEADER': {'top': 0.10, 'bottom': 0.25, 'left': 0.05, 'right': 0.95, 'color': (0, 255, 0), 'name': 'THANA'},
            'DATE': {'top': 0.25, 'bottom': 0.35, 'left': 0.02, 'right': 0.55, 'color': (255, 0, 0), 'name': 'DATE'},
            'SECTIONS': {'top': 0.35, 'bottom': 0.70, 'left': 0.02, 'right': 0.55, 'color': (0, 0, 255), 'name': 'SECTIONS'}
        }
        
        self.selected_region = 'HEADER'
        self.selected_edge = 'top'
        
    def draw_regions(self):
        """Draw current regions on image"""
        overlay = self.image.copy()
        
        for region_name, region in self.regions.items():
            x1 = int(self.width * region['left'])
            y1 = int(self.height * region['top'])
            x2 = int(self.width * region['right'])
            y2 = int(self.height * region['bottom'])
            
            color = region['color']
            
            # Draw rectangle
            thickness = 3 if region_name == self.selected_region else 2
            cv2.rectangle(overlay, (x1, y1), (x2, y2), color, thickness)
            
            # Draw label
            label = f"{region['name']}: {region['top']:.2f}-{region['bottom']:.2f}"
            cv2.rectangle(overlay, (x1, y1 - 30), (x1 + 300, y1), color, -1)
            cv2.putText(overlay, label, (x1 + 5, y1 - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Add instructions
        instructions = [
            f"Selected: {self.selected_region} - {self.selected_edge}",
            "TAB: Change region | E: Change edge",
            "UP/DOWN: Adjust ±1% | PgUp/PgDn: ±5%",
            "S: Save regions | Q: Quit"
        ]
        
        y_pos = 30
        for inst in instructions:
            cv2.rectangle(overlay, (10, y_pos - 25), (500, y_pos + 5), (0, 0, 0), -1)
            cv2.putText(overlay, inst, (15, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y_pos += 30
        
        # Blend
        alpha = 0.4
        result = cv2.addWeighted(overlay, alpha, self.image, 1 - alpha, 0)
        
        # Resize for display
        display_h = int(self.height * self.display_scale)
        display_w = int(self.width * self.display_scale)
        result = cv2.resize(result, (display_w, display_h))
        
        return result
    
    def adjust_region(self, delta: float):
        """Adjust selected region edge"""
        region = self.regions[self.selected_region]
        current = region[self.selected_edge]
        new_value = max(0.0, min(1.0, current + delta))
        region[self.selected_edge] = new_value
        
        print(f"Adjusted {self.selected_region}.{self.selected_edge}: {current:.3f} -> {new_value:.3f}")
    
    def next_region(self):
        """Switch to next region"""
        region_names = list(self.regions.keys())
        current_idx = region_names.index(self.selected_region)
        next_idx = (current_idx + 1) % len(region_names)
        self.selected_region = region_names[next_idx]
        print(f"Selected region: {self.selected_region}")
    
    def next_edge(self):
        """Switch to next edge"""
        edges = ['top', 'bottom', 'left', 'right']
        current_idx = edges.index(self.selected_edge)
        next_idx = (current_idx + 1) % len(edges)
        self.selected_edge = edges[next_idx]
        print(f"Selected edge: {self.selected_edge}")
    
    def save_regions(self):
        """Save current regions to Python code"""
        output = "# Paste these values into fir_specialized_ocr.py -> FIRRegions class\n\n"
        
        header = self.regions['HEADER']
        date = self.regions['DATE']
        sections = self.regions['SECTIONS']
        
        output += f"HEADER_TOP = {header['top']:.3f}\n"
        output += f"HEADER_BOTTOM = {header['bottom']:.3f}\n"
        output += f"HEADER_LEFT = {header['left']:.3f}\n"
        output += f"HEADER_RIGHT = {header['right']:.3f}\n\n"
        
        output += f"DATE_ROW_TOP = {date['top']:.3f}\n"
        output += f"DATE_ROW_BOTTOM = {date['bottom']:.3f}\n"
        output += f"DATE_CELL_LEFT = {date['left']:.3f}\n"
        output += f"DATE_CELL_RIGHT = {date['right']:.3f}\n\n"
        
        output += f"SECTIONS_TOP = {sections['top']:.3f}\n"
        output += f"SECTIONS_BOTTOM = {sections['bottom']:.3f}\n"
        output += f"SECTIONS_LEFT = {sections['left']:.3f}\n"
        output += f"SECTIONS_RIGHT = {sections['right']:.3f}\n"
        
        with open('adjusted_regions.txt', 'w') as f:
            f.write(output)
        
        print("\n" + "=" * 60)
        print("Regions saved to: adjusted_regions.txt")
        print("=" * 60)
        print(output)
        print("=" * 60)
    
    def run(self):
        """Main interactive loop"""
        print("\n" + "=" * 60)
        print("Interactive Region Adjuster")
        print("=" * 60)
        print("Instructions:")
        print("  TAB - Switch region (HEADER/DATE/SECTIONS)")
        print("  E - Switch edge (top/bottom/left/right)")
        print("  UP/DOWN - Adjust ±1%")
        print("  PgUp/PgDn - Adjust ±5%")
        print("  S - Save regions to file")
        print("  Q - Quit")
        print("=" * 60 + "\n")
        
        while True:
            display = self.draw_regions()
            cv2.imshow('Region Adjuster', display)
            
            key = cv2.waitKey(0) & 0xFF
            
            if key == ord('q') or key == 27:  # Q or ESC
                print("Quitting...")
                break
            elif key == 9:  # TAB
                self.next_region()
            elif key == ord('e') or key == ord('E'):
                self.next_edge()
            elif key == 82 or key == ord('w'):  # UP arrow or W
                self.adjust_region(-0.01)
            elif key == 84 or key == ord('s'):  # DOWN arrow or S (not save)
                if key == 84:  # DOWN arrow only
                    self.adjust_region(0.01)
            elif key == 81 or key == ord('a'):  # LEFT arrow or A
                if self.selected_edge in ['left', 'right']:
                    self.adjust_region(-0.01)
            elif key == 83 or key == ord('d'):  # RIGHT arrow or D
                if self.selected_edge in ['left', 'right']:
                    self.adjust_region(0.01)
            elif key == 85:  # PgUp
                self.adjust_region(-0.05)
            elif key == 86:  # PgDn
                self.adjust_region(0.05)
            elif key == ord('S'):  # Shift+S for save
                self.save_regions()
        
        cv2.destroyAllWindows()


def main():
    if len(sys.argv) < 2:
        print("Usage: python adjust_regions.py <fir_image.jpg>")
        print("\nThis tool helps you interactively adjust extraction regions")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    if not Path(image_path).exists():
        print(f"Error: Image not found: {image_path}")
        sys.exit(1)
    
    adjuster = RegionAdjuster(image_path)
    adjuster.run()


if __name__ == '__main__':
    main()
