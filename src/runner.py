import warnings
warnings.filterwarnings("ignore", message=".*xbutil.*")
warnings.filterwarnings("ignore", message=".*XRT.*")

import numpy as np
from pynq_dpu import DpuOverlay
import xir
import vart

CLASSES = ['aviation', 'godfather', 'irishcoffee', 'martini', 'midorisour',
           'oldfashioned', 'scotchneat', 'tuxedo', 'vodkaneat', 'whiskeyneat']


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

    def run(self, mel_float):
        in_dims = tuple(self.input_tensors[0].dims)
        out_dims = tuple(self.output_tensors[0].dims)
        print(f"[DEBUG] in_dims={in_dims}  out_dims={out_dims}")
        fix_pos = self.input_tensors[0].get_attr("fix_point")
        scale = 2 ** fix_pos
        print(f"[DEBUG] fix_point={fix_pos}  scale={scale}")
        mel_array = np.array(mel_float, dtype=np.float32)
        print(f"[DEBUG] mel_array shape={mel_array.shape}  min={mel_array.min():.3f}  max={mel_array.max():.3f}")
        quant = np.clip(np.round(mel_array * scale), -128, 127).astype(np.int8)
        print(f"[DEBUG] quant shape={quant.shape}  min={quant.min()}  max={quant.max()}  nonzero={np.count_nonzero(quant)}")
        input_data = [np.zeros(in_dims, dtype=np.int8)]
        output_data = [np.zeros(out_dims, dtype=np.int8)]
        try:
            input_data[0][:] = quant.reshape(in_dims)
        except Exception as e:
            print(f"[DEBUG] reshape failed: {e}  quant.size={quant.size}  in_dims product={np.prod(in_dims)}")
            raise
        print(f"[DEBUG] calling execute_async ...")
        job_id = self._runner.execute_async(input_data, output_data)
        print(f"[DEBUG] job_id={job_id}  waiting ...")
        self._runner.wait(job_id)
        print(f"[DEBUG] done waiting")
        logits = output_data[0][0].astype(np.float32)
        print(f"[DEBUG] logits={logits}")
        predicted = CLASSES[int(np.argmax(logits))]
        return predicted, logits
