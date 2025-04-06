"""
CLI to process LVIS data into tiled DEMs and optionally merge + gap-fill.
Refactored to use TileProcessor class from lvis_dem_tools.py.
"""
import time
import psutil
import shutil
import tracemalloc
import argparse
import os
from tile_processor import TileProcessor
from lvis_dem_tools import read_valid_files, get_all_bounds, generate_tiles, merge_tiles



def parse_args():
    """
    Parse command-line arguments for the DEM processing script.
    Returns:
        argparse.Namespace: Parsed argument object
    """
    # Set up all command line options
    parser = argparse.ArgumentParser(description="Generate DEMs from LVIS data using tiling")
    parser.add_argument("--folder", required=True, help="Folder containing LVIS .h5 files")
    parser.add_argument("--list", default="valid_2015_files.txt", help="Text file listing valid LVIS filenames")
    parser.add_argument("--res", type=float, default=30.0, help="Resolution in meters for the DEM")
    parser.add_argument("--tiles", type=int, default=20, help="Number of tiles per side (NxN grid)")
    parser.add_argument("--fill", action="store_true", help="Enable gap filling after each tile")
    parser.add_argument("--test_files", nargs='+', help="Optional subset of filenames to process")
    parser.add_argument("--output_dir", default="output_tiles", help="Directory to store intermediate tile outputs")
    parser.add_argument("--output", default="lvis_merged_dem.tif", help="Final merged DEM filename")
    return parser.parse_args()


def run_dem_workflow(args):
    """
    Executes the main workflow: reads file list, computes bounds, tiles region,
    generates tile DEMs, optionally fills gaps, and merges tiles.
    """
    print("🚀 Starting DEM generation workflow...")
    # Start timing and memory tracking
    start_time = time.time()
    tracemalloc.start()

    # Load list of LVIS files to process
    print("📂 Reading file list...")
    list_path = os.path.join("data", args.list)
    files = read_valid_files(list_path, args.test_files)

    print(f"✅ Found {len(files)} valid files")

    # Determine boundaries and split into tiles
    print("🗺️ Generating tile bounds...")
    bounds = get_all_bounds(files, args.folder)
    tile_bounds = generate_tiles(bounds, args.tiles)
    output_paths = []

    # Process each tile area separately
    for i, tile in enumerate(tile_bounds):
        minX, maxX, minY, maxY = tile
        # Create processor for this tile
        tile_proc = TileProcessor(
            minX, maxX, minY, maxY, args.res,
            files, args.folder, args.output_dir,
            tile_id=i + 1
        )
        # Generate the DEM for this tile
        tile_proc.process()
        # Fill gaps if requested
        if args.fill:
            tile_proc.fill_gaps()
        # Save tile and track output path
        path = tile_proc.save(fill_suffix=args.fill)
        output_paths.append(path)

    # Combine all tile DEMs into final result
    print("🧩 Merging tiles...")
    merged_path = merge_tiles(output_paths, args.output, args.output_dir)

    # Check if merge was successful
    if os.path.exists(merged_path):
        print(f"✅ Merge successful! Output saved at: {merged_path}")
    else:
        print("❌ Merge failed! Check the tile outputs.")

    # Clean up intermediate files
    print("🧹 Cleaning up tile files...")
    for path in output_paths:
        try:
            os.remove(path)
        except Exception as e:
            print(f"⚠️ Failed to remove {path}: {e}")

    # Remove temporary directory
    try:
        if os.path.isdir(args.output_dir):
            shutil.rmtree(args.output_dir)
            print(f"🗑️ Removed tile output directory: {args.output_dir}")
    except Exception as e:
        print(f"⚠️ Could not remove output directory: {e}")

    # Report performance metrics
    end_time = time.time()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    print(f"\n⏱️ Running Time: {end_time - start_time:.2f} seconds")
    print(f"🧠 Peak Memory Usage: {peak / 1024 / 1024:.2f} MB")


def main():
    """Main script entry point"""
    # Parse arguments and run workflow
    args = parse_args()
    run_dem_workflow(args)

if __name__ == "__main__":
    main()