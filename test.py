import xir
graph = xir.Graph.deserialize('/home/xilinx/models/mnist_classifier.xmodel')
for s in graph.get_root_subgraph().toposort_child_subgraph():
	if s.has_attr('device') and s.get_attr('device') == 'DPU':
		print('name:', s.get_name())
		for attr in ['dpu_fingerprint', 'fingerprint', 'target']:
			if s.has_attr(attr):
				print(attr + ':', s.get_attr(attr))


