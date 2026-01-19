from rosetta_bridge.inference.client import GeminiClient


def main() -> int:
    client = GeminiClient(model_name="gemini-3-flash-preview")
    response = client.generate_description("Explain how AI works in a few words")
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
