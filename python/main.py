import sys
import io
import traceback

# Ensure UTF-8 for stdin/stdout/stderr on Windows (cp949 default can't encode multilingual text)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from protocol import parse_message, format_result, format_error
from gpu_detect import detect_gpu


def handle_message(msg: dict) -> str:
    method = msg["method"]
    params = msg.get("params", {})
    msg_id = msg["id"]

    if method == "ping":
        return format_result(msg_id, {"status": "ok"})

    elif method == "detect_gpu":
        result = detect_gpu()
        return format_result(msg_id, result)

    elif method == "analyze":
        # Imported lazily to avoid slow startup
        from analyzer import run_analysis
        result = run_analysis(params, msg_id)
        return format_result(msg_id, result)

    elif method == "generate_embeddings":
        from embeddings import generate_embeddings
        result = generate_embeddings(params, msg_id)
        return format_result(msg_id, result)

    else:
        return format_error(msg_id, f"Unknown method: {method}")


def main():
    # Signal readiness
    sys.stdout.write(format_result("__init__", {"status": "ready"}) + "\n")
    sys.stdout.flush()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = parse_message(line)
            response = handle_message(msg)
        except Exception as e:
            response = format_error(
                "unknown",
                f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
        sys.stdout.write(response + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
