"""
Task 1: Simple LVIS Waveform Plotter
"""

import os
import sys
import argparse
import matplotlib.pyplot as plt

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from lvisClass import lvisData

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Plot an LVIS waveform')
    parser.add_argument('filename', help='Path to LVIS HDF5 file')
    parser.add_argument('index', type=int, help='Index of waveform to plot')
    parser.add_argument('--output', default='waveform.png', help='Output plot filename')
    args = parser.parse_args()
    
    # Read LVIS file with elevation data
    lvis = lvisData(args.filename, setElev=True)
    
    # Check if we have data
    if lvis.nWaves == 0:
        print("No waveforms found in the file")
        return
    
    # Check if index is valid
    if args.index >= lvis.nWaves:
        print(f"Waveform index {args.index} is out of range. Max index is {lvis.nWaves-1}")
        return
    
    # Get the waveform
    z, wave = lvis.getOneWave(args.index)
    
    # Create plot
    plt.figure(figsize=(6, 10))
    plt.plot(wave, z)
    plt.xlabel('Intensity')
    plt.ylabel('Elevation (m)')
    plt.title(f'LVIS Waveform {args.index}')
    
    # Save plot
    plt.savefig(args.output)
    print(f"Plot saved to {args.output}")

if __name__ == "__main__":
    main()