from pynq_dpu import DpuOverlay
import vart
import xir

overlay = DpuOverlay("dpu.bit")
print("Overlay loaded successfully")
print("IP dict keys:", list(overlay.ip_dict.keys()))

# Check DPU info
print("\n--- DPU Architecture ---")
import subprocess
result = subprocess.run(["show_dpu"], capture_output=True, text=True)
print(result.stdout or result.stderr)

# Test that we can load an xmodel and create a runner
# First, let's just confirm VART can see the DPU subgraph mechanism
print("VART version check:")
result2 = subprocess.run(["vart_version"], capture_output=True, text=True)
print(result2.stdout or result2.stderr)
