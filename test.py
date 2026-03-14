from pynq_dpu import DpuOverlay
overlay = DpuOverlay('dpu.bit')
print('Overlay loaded successfully')
print('IP dict keys:', list(overlay.ip_dict.keys()))
