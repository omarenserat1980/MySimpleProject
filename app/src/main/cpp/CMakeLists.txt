cmake_minimum_required(VERSION 3.22.1)
project(braincarlife_jni LANGUAGES CXX)

if(NOT ANDROID_ABI STREQUAL "arm64-v8a")
    message(FATAL_ERROR "CarLife MD native bridge currently supports arm64-v8a only")
endif()

set(CARLIFE_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../android_executor/carlife-md")
set(CARLIFE_INCLUDE "${CARLIFE_ROOT}/upstream/LibSource/include")
set(CARLIFE_LIBRARY "${CARLIFE_ROOT}/native/arm64-v8a/libcarlifevehicle.so")
if(NOT EXISTS "${CARLIFE_LIBRARY}")
    message(FATAL_ERROR "Pinned CarLife runtime library not found: ${CARLIFE_LIBRARY}")
endif()

add_library(carlifevehicle SHARED IMPORTED GLOBAL)
set_target_properties(carlifevehicle PROPERTIES IMPORTED_LOCATION "${CARLIFE_LIBRARY}")

add_library(braincarlife_jni SHARED carlife_jni.cpp)
target_include_directories(braincarlife_jni PRIVATE "${CARLIFE_INCLUDE}")
target_compile_features(braincarlife_jni PRIVATE cxx_std_17)
target_compile_options(braincarlife_jni PRIVATE -Wall -Wextra -Werror=return-type)
target_link_libraries(braincarlife_jni PRIVATE carlifevehicle log)
