# trinity-v4-ai-brain

AI brain system

## Building and running tests

This repository contains a small C++ test that bootstraps a core system, creates a test process,
allocates memory, exchanges a simple IPC message and prints basic system information.

### Build

```
cmake -S . -B build
cmake --build build
```

### Run

```
./build/trinity_core_test
```
