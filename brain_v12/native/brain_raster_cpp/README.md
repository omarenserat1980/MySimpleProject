# Brain C++ Raster Engine

Native C++17 raster backend for Brain.

Python remains the orchestration/compiler layer. This executable owns low-level pixel operations and PNG encoding.

Pipeline:

Scene -> Brain compiler -> C++ Raster Engine -> RGBA Pixel Buffer -> PNG -> FFmpeg -> MP4

## Build

Requires a C++17 compiler and zlib development library.

    cmake -S . -B build
    cmake --build build --config Release
    ./build/brain_raster brain-raster.png

The executable prints BRAIN_CPP_RASTER_VERIFIED only after the PNG writer succeeds.

This backend is provider-free and requires no image API.
