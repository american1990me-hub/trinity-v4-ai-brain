cmake_minimum_required(VERSION 3.10)
project(trinity_v4_ai_brain)

add_executable(trinity_core_test tests/test_run_simulation.cpp)

# Require C++17 for thread and other modern features
target_compile_features(trinity_core_test PRIVATE cxx_std_17)
