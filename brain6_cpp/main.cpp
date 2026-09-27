#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <sys/wait.h>
#include <thread>
#include <unistd.h>

namespace fs = std::filesystem;

class BrainComponent {
public:
    virtual ~BrainComponent() = default;
    virtual int run() = 0;
};

class PythonFactory final : public BrainComponent {
public:
    explicit PythonFactory(std::string executable)
        : executable_(std::move(executable)) {}

    int run() override {
        execlp(
            executable_.c_str(),
            executable_.c_str(),
            "-m",
            "brain_v7.braincore_v2.background_factory_worker",
            (char*)nullptr
        );
        perror("exec python factory");
        return 127;
    }

private:
    std::string executable_;
};

class QualityGate final {
public:
    bool verify() const {
        const fs::path output{"cinematic_output/final.mp4"};
        if (!fs::is_regular_file(output) || fs::file_size(output) == 0) {
            return false;
        }
        return has_audio_and_video(output);
    }

private:
    static bool has_audio_and_video(const fs::path& file) {
        const std::string cmd =
            "ffprobe -v error -show_entries stream=codec_type "
            "-of csv=p=0 " + shell_quote(file.string()) + " 2>/dev/null";
        FILE* pipe = popen(cmd.c_str(), "r");
        if (!pipe) return false;

        bool video = false;
        bool audio = false;
        char buffer[128]{};
        while (fgets(buffer, sizeof(buffer), pipe)) {
            std::string type(buffer);
            if (type.find("video") != std::string::npos) video = true;
            if (type.find("audio") != std::string::npos) audio = true;
        }
        const int rc = pclose(pipe);
        return rc == 0 && video && audio;
    }

    static std::string shell_quote(const std::string& value) {
        std::string out="'";
        for (char c : value) {
            if (c == ''') out += "'\\''";
            else out += c;
        }
        out += "'";
        return out;
    }
};

class BrainSupervisor final {
public:
    BrainSupervisor(
        std::unique_ptr<BrainComponent> factory,
        std::shared_ptr<QualityGate> quality_gate
    )
        : factory_(std::move(factory)),
          quality_gate_(std::move(quality_gate)) {}

    int run() {
        log("BRAIN6_CPP_BOOT version=2 architecture=RAII_SMART_POINTERS");

        if (!fs::exists("production/BRAIN6_168H.json")) {
            log("BRAIN6_STATE_MISSING");
            return 20;
        }

        const int attempts = env_int("BRAIN6_CPP_RETRIES", 2);
        for (int attempt = 1; attempt <= attempts + 1; ++attempt) {
            log("BRAIN6_ATTEMPT " + std::to_string(attempt));

            const int child_status = spawn_factory();
            if (child_status == 0 && quality_gate_->verify()) {
                log("BRAIN6_FINAL_QC_OK");
                checkpoint(attempt, "SUCCESS");
                return 0;
            }

            checkpoint(attempt, "RETRY");
            if (attempt <= attempts) {
                std::this_thread::sleep_for(
                    std::chrono::seconds(env_int("BRAIN6_CPP_BACKOFF_SECONDS", 5))
                );
            }
        }

        checkpoint(attempts + 1, "FAILED");
        log("BRAIN6_FINAL_QC_FAILED");
        return 2;
    }

private:
    std::unique_ptr<BrainComponent> factory_;
    std::shared_ptr<QualityGate> quality_gate_;

    int spawn_factory() {
        pid_t pid = fork();
        if (pid < 0) {
            perror("fork");
            return 21;
        }
        if (pid == 0) {
            return factory_->run();
        }

        int status = 0;
        if (waitpid(pid, &status, 0) < 0) {
            perror("waitpid");
            return 22;
        }

        if (WIFEXITED(status)) return WEXITSTATUS(status);
        if (WIFSIGNALED(status)) return 128 + WTERMSIG(status);
        return 23;
    }

    static int env_int(const char* name, int fallback) {
        const char* value = std::getenv(name);
        if (!value || !*value) return fallback;
        try {
            const int parsed = std::stoi(value);
            return parsed > 0 ? parsed : fallback;
        } catch (...) {
            return fallback;
        }
    }

    static void log(const std::string& message) {
        std::cout << message << std::endl;
    }

    static void checkpoint(int attempt, const std::string& status) {
        std::ofstream out("brain6_cpp/checkpoint.json", std::ios::trunc);
        if (!out) return;
        out << "{\n"
            << "  \"attempt\": " << attempt << ",\n"
            << "  \"status\": \"" << status << "\",\n"
            << "  \"timestamp_epoch\": " << std::time(nullptr) << "\n"
            << "}\n";
    }
};

int main() {
    auto factory = std::make_unique<PythonFactory>(
        std::getenv("BRAIN6_PYTHON")
            ? std::getenv("BRAIN6_PYTHON")
            : "python3"
    );
    auto quality_gate = std::make_shared<QualityGate>();

    BrainSupervisor supervisor(
        std::move(factory),
        std::move(quality_gate)
    );

    return supervisor.run();
}
