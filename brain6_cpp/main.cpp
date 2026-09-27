#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>
#include <sys/wait.h>
#include <unistd.h>

namespace fs = std::filesystem;

static int run_python_factory() {
    const char* python = std::getenv("BRAIN6_PYTHON");
    if (!python || std::string(python).empty()) python = "python3";

    execlp(
        python,
        python,
        "-m",
        "brain_v7.braincore_v2.background_factory_worker",
        (char*)nullptr
    );
    perror("exec python factory");
    return 127;
}

int main() {
    std::cout << "BRAIN6_CPP_BOOT version=1 mode=cloud" << std::endl;

    if (!fs::exists("production/BRAIN6_168H.json")) {
        std::cerr << "BRAIN6_STATE_MISSING" << std::endl;
        return 20;
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 21;
    }

    if (pid == 0) {
        return run_python_factory();
    }

    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 22;
    }

    if (WIFEXITED(status)) {
        const int code = WEXITSTATUS(status);
        std::cout << "BRAIN6_CPP_EXIT python_exit=" << code << std::endl;
        return code;
    }

    if (WIFSIGNALED(status)) {
        std::cerr << "BRAIN6_CPP_SIGNAL signal=" << WTERMSIG(status) << std::endl;
        return 128 + WTERMSIG(status);
    }

    return 23;
}
