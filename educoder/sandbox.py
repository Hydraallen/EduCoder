"""Docker sandbox for student mode code execution.

Provides a safe, isolated environment for running Python code
submitted by students, with network disabled, memory limits, and
a hard timeout.
"""

import threading

SANDBOX_TOOL_SPEC = {
    "schema": {"code": "str"},
    "risky": False,
    "description": "Run Python code in a sandboxed Docker container (student mode only).",
}


def tool_run_sandbox_code(agent, args):
    code = str(args.get("code", "")).strip()
    if not code:
        raise ValueError("code must not be empty")

    try:
        import docker

        client = docker.from_env()
    except Exception as exc:
        return f"error: Docker not available: {exc}"

    container = None
    result = [None]
    error = [None]

    def _run():
        try:
            output = client.containers.run(
                image="python:3.13-alpine",
                command=["python", "-c", code],
                network_disabled=True,
                mem_limit="100m",
                detach=False,
                stdout=True,
                stderr=True,
                remove=True,
            )
            result[0] = output.decode("utf-8", errors="replace")
        except Exception as exc:
            import docker as _docker

            if isinstance(exc, _docker.errors.ContainerError):
                error[0] = f"stderr:\n{exc.stderr.decode('utf-8', errors='replace')}"
            else:
                error[0] = f"error: sandbox execution failed: {exc}"

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=5)

    if thread.is_alive():
        if container:
            try:
                container.kill()
            except Exception:
                pass
        return "error: sandbox timed out after 5 seconds"

    if error[0]:
        return error[0]
    return result[0]
