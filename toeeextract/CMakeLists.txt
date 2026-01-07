cmake_minimum_required(VERSION 3.12)
project(ToEExtract VERSION 1.0 LANGUAGES CXX)

# Specify the C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Find ZLIB package
find_package(ZLIB REQUIRED)

# Add the executable
add_executable(ToEExtract 
    ToEExtract.cpp 
    ToEExtract.h
)

# Link ZLIB
if(ZLIB_FOUND)
    target_link_libraries(ToEExtract PRIVATE ZLIB::ZLIB)
else()
    message(FATAL_ERROR "ZLIB not found!")
endif()
