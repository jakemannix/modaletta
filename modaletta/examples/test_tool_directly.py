"""Test the tool function directly (without Letta) to debug."""

import subprocess
import sys


def run_python_simple(code: str) -> str:
    """Execute Python code in a subprocess."""
    import subprocess
    import sys
    
    try:
        result = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            timeout=10,
            env={'PYTHONUNBUFFERED': '1'}
        )
        
        # Build detailed response
        output_parts = []
        output_parts.append(f"CODE EXECUTED:\n{code}\n")
        output_parts.append(f"[Exit code: {result.returncode}]")
        
        if result.stdout:
            output_parts.append(f"STDOUT:\n{result.stdout.strip()}")
        
        if result.stderr:
            output_parts.append(f"STDERR:\n{result.stderr.strip()}")
        
        if not result.stdout and not result.stderr:
            output_parts.append("(No output produced)")
        
        return "\n".join(output_parts)
        
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out (10 seconds)"
    except Exception as e:
        return f"Error: {type(e).__name__}: {str(e)}"


if __name__ == "__main__":
    print("Testing tool function directly...\n")
    
    # Test 1: Simple print
    print("=" * 60)
    print("Test 1: Simple print statement")
    print("=" * 60)
    result = run_python_simple("print('Hello, world!')")
    print(result)
    print()
    
    # Test 2: Calculation
    print("=" * 60)
    print("Test 2: Calculation with print")
    print("=" * 60)
    result = run_python_simple("print(42 * 37)")
    print(result)
    print()
    
    # Test 3: Calculation without print (no output expected)
    print("=" * 60)
    print("Test 3: Calculation without print (should show no output)")
    print("=" * 60)
    result = run_python_simple("x = 42 * 37")
    print(result)
    print()
    
    # Test 4: Error case
    print("=" * 60)
    print("Test 4: Error case")
    print("=" * 60)
    result = run_python_simple("print(1/0)")
    print(result)
    print()

