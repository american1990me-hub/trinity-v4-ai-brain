#include "ipc/IPCMessage.hpp"

#include <condition_variable>
#include <mutex>
#include <queue>
#include <unordered_map>

// The following implementation provides a minimal thread safe message passing
// mechanism for the system. Messages are delivered per-process using a queue
// protected by a mutex and a condition variable. Sending a message pushes it to
// the destination queue and wakes up any receiver waiting on that queue.
namespace {
    struct IPCQueue {
        std::queue<IPCMessage> messages;
        std::mutex mutex;
        std::condition_variable cv;
    };

    // Map a process id to its dedicated message queue
    std::unordered_map<int, std::shared_ptr<IPCQueue>> queues;
    std::mutex queuesMutex;

    std::shared_ptr<IPCQueue> getQueue(int pid) {
        std::lock_guard<std::mutex> lock(queuesMutex);
        auto &ref = queues[pid];
        if (!ref) {
            ref = std::make_shared<IPCQueue>();
        }
        return ref;
    }
}

// Send a message from one process to another. The message will be added to the
// receiver's queue and any thread blocked in _syscall_ipc_receive will be
// unblocked.
int _syscall_ipc_send(int senderPid, int receiverPid, IPCMessage message) {
    message.senderPid = senderPid;
    auto q = getQueue(receiverPid);
    {
        std::lock_guard<std::mutex> lock(q->mutex);
        q->messages.push(std::move(message));
    }
    // Wake up one receiver waiting on this queue
    q->cv.notify_one();
    return 0;
}

// Receive a message for the given process. If the message queue is empty, the
// call will block until a message becomes available, mirroring the behaviour of
// the Python implementation of this system.
int _syscall_ipc_receive(int receiverPid, IPCMessage &outMessage) {
    auto q = getQueue(receiverPid);
    std::unique_lock<std::mutex> lock(q->mutex);
    q->cv.wait(lock, [&]{ return !q->messages.empty(); });
    outMessage = std::move(q->messages.front());
    q->messages.pop();
    return 0;
}

