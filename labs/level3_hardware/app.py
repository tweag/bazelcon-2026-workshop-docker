"""Level 3 payload: an OpenCL kernel that needs an ICD (POCL on CPU, or a GPU)."""

import numpy as np

KERNEL = """
__kernel void add(__global const float *a,
                  __global const float *b,
                  __global float *c) {
    int i = get_global_id(0);
    c[i] = a[i] + b[i];
}
"""


def has_opencl_device() -> bool:
    """True only if an ICD exposes at least one device (POCL or a GPU)."""
    try:
        import pyopencl as cl

        return any(p.get_devices() for p in cl.get_platforms())
    except Exception:
        return False


def vector_add(a, b):
    """Run the kernel on whatever OpenCL device the ICD exposes."""
    import pyopencl as cl

    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    ctx = cl.create_some_context(interactive=False)
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags
    a_g = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=a)
    b_g = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=b)
    c_g = cl.Buffer(ctx, mf.WRITE_ONLY, a.nbytes)
    cl.Program(ctx, KERNEL).build().add(queue, a.shape, None, a_g, b_g, c_g)
    c = np.empty_like(a)
    cl.enqueue_copy(queue, c, c_g)
    return c


def main() -> int:
    if not has_opencl_device():
        print("no OpenCL device — the hardware wall (bundle POCL or expose a GPU)")
        return 0
    c = vector_add([1, 2, 3], [10, 20, 30])
    print("vector_add on OpenCL OK:", c.tolist())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
