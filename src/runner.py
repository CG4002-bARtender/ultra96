import warnings
warnings.filterwarnings("ignore", message=".*xbutil.*")
warnings.filterwarnings("ignore", message=".*XRT.*")

import numpy as np
from pynq_dpu import DpuOverlay
import xir
import vart


class DpuRunner:
    def __init__(self, xmodel_path, overlay_path="dpu.bit"):
        self.overlay = DpuOverlay(overlay_path)

        self._graph = xir.Graph.deserialize(xmodel_path)
        subgraphs = self._graph.get_root_subgraph().toposort_child_subgraph()
        dpu_subgraphs = [
            s for s in subgraphs
            if s.has_attr("device") and s.get_attr("device") == "DPU"
        ]
        if not dpu_subgraphs:
            raise RuntimeError(f"No DPU subgraph found in {xmodel_path}")

        self._subgraph = dpu_subgraphs[0]  # keep alive — VART holds a raw C pointer to this
        self._runner = vart.Runner.create_runner(self._subgraph, "run")
        self.input_tensors = self._runner.get_input_tensors()
        self.output_tensors = self._runner.get_output_tensors()

    def run(self, input_array):
        in_dims = tuple(self.input_tensors[0].dims)
        out_dims = tuple(self.output_tensors[0].dims)
        input_data = [np.zeros(in_dims, dtype=np.int8)]
        output_data = [np.zeros(out_dims, dtype=np.int8)]
        input_data[0][:] = input_array.reshape(in_dims)
        job_id = self._runner.execute_async(input_data, output_data)
        self._runner.wait(job_id)
        return output_data[0][0]
