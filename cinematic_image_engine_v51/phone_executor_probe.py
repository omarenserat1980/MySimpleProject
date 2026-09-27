from .phone_executor import executor_probe

if __name__ == "__main__":
    import json
    print(json.dumps(executor_probe(), ensure_ascii=False, indent=2))
