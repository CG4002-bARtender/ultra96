import warnings
warnings.filterwarnings("ignore", message=".*xbutil.*")
warnings.filterwarnings("ignore", message=".*XRT.*")

import numpy as np
from pynq_dpu import DpuOverlay
import xir
import vart

# Load DPU overlay
print("Loading DPU overlay...")
overlay = DpuOverlay("dpu.bit")
print("DPU overlay loaded.")

# Load the MNIST xmodel
xmodel_path = "/home/xilinx/dpu_test/mnist_classifier.xmodel"
print(f"Loading xmodel: {xmodel_path}")

graph = xir.Graph.deserialize(xmodel_path)
subgraphs = graph.get_root_subgraph().toposort_child_subgraph()
dpu_subgraph = [s for s in subgraphs if s.has_attr("device") and s.get_attr("device") == "DPU"]
print(f"Found {len(dpu_subgraph)} DPU subgraph(s)")

# Create DPU runner
runner = vart.Runner.create_runner(dpu_subgraph[0], "run")

# Get input/output tensor info
input_tensors = runner.get_input_tensors()
output_tensors = runner.get_output_tensors()

print(f"\nInput tensor:  name={input_tensors[0].name}, shape={tuple(input_tensors[0].dims)}, dtype={input_tensors[0].dtype}")
print(f"Output tensor: name={output_tensors[0].name}, shape={tuple(output_tensors[0].dims)}, dtype={output_tensors[0].dtype}")

# Create a fake 28x28 input (a simple diagonal pattern)
batch_size = tuple(input_tensors[0].dims)[0]
input_data = [np.zeros(tuple(input_tensors[0].dims), dtype=np.int8)]
output_data = [np.zeros(tuple(output_tensors[0].dims), dtype=np.int8)]

# Draw a "1"-like pattern
h, w = tuple(input_tensors[0].dims)[1], tuple(input_tensors[0].dims)[2]
for i in range(h):
    input_data[0][0][i][w // 2] = 127  # vertical line down the middle

print(f"\nRunning inference with fake input (vertical line pattern)...")
job_id = runner.execute_async(input_data, output_data)
runner.wait(job_id)

prediction = np.argmax(output_data[0][0])
print(f"Raw output: {output_data[0][0]}")
print(f"Predicted digit: {prediction}")
print("\nEnd-to-end DPU inference test PASSED!")
