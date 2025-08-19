#include <condition_variable>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

class CoreSystem {
public:
    void bootstrap() {
        std::cout << "CoreSystem bootstrapped" << std::endl;
    }
};

int main() {
    CoreSystem core;
    core.bootstrap();

    // Allocate some memory to simulate workload
    std::vector<int> memory(1024, 42);
    std::cout << "Allocated memory: " << memory.size() * sizeof(int) << " bytes" << std::endl;

    // Simple IPC simulation using condition variables
    std::string message;
    std::mutex mtx;
    std::condition_variable cv;
    bool ready = false;

    std::thread process([&]() {
        std::unique_lock<std::mutex> lock(mtx);
        cv.wait(lock, [&] { return ready; });
        std::cout << "Process received message: " << message << std::endl;
        message = "pong";
        ready = false;
        lock.unlock();
        cv.notify_one();
    });

    {
        std::unique_lock<std::mutex> lock(mtx);
        message = "ping";
        ready = true;
    }
    cv.notify_one();

    {
        std::unique_lock<std::mutex> lock(mtx);
        cv.wait(lock, [&] { return !ready; });
        std::cout << "Main received response: " << message << std::endl;
    }

    process.join();

    std::cout << "Hardware concurrency: " << std::thread::hardware_concurrency() << std::endl;
    return 0;
}

