cmake_minimum_required(VERSION 3.16)
project(trinity_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(trinity_core
    src/main.cpp
)

target_include_directories(trinity_core PRIVATE src)
