cmake_minimum_required(VERSION 3.10)
project(trinity_core VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(trinity_core
    src/main.cpp
    src/core/CoreSystem.cpp
)

target_include_directories(trinity_core PRIVATE src)
