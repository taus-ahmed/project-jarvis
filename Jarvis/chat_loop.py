# Jarvis/chat_loop.py

from Jarvis.mcp_filesystem.filesystem import read_file
from Jarvis.memory.vector_store import query_memory


def start_chat():
    print("🤖 Jarvis is online.")
    print("Type questions to query memory.")
    print("Type: read <path>  → to let Jarvis read a file")
    print("Type: exit         → to quit\n")

    while True:
        user_input = input("You > ").strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("👋 Jarvis shutting down.")
            break

        # File read command
        if user_input.lower().startswith("read "):
            path = user_input[5:].strip()
            try:
                read_file(path)
                print(f"📄 Jarvis read and remembered: {path}")
            except Exception as e:
                print(f"❌ Error: {e}")
            continue

        # Memory query
        results = query_memory(user_input)

        documents = results.get("documents", [[]])[0]

        if not documents:
            print("🤔 Jarvis: I don't remember anything relevant yet.")
        else:
            print("🧠 Jarvis remembers:")
            for doc in documents:
                print(f"- {doc}")
