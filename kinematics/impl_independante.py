import sys
import numpy as np


def _validate_shape(arr, name):
    arr = np.asarray(arr)
    if arr.ndim != 2 or arr.shape[1] != 5:
        raise ValueError(f"{name} must have shape (N,5), got {arr.shape}")
    return arr


def inverse(native, LC, LB):
    """Convert native coordinates to joint coordinates."""
    arr = _validate_shape(native, "native")
    c = np.deg2rad(arr[:, 3])
    b = np.deg2rad(arr[:, 4])

    joint = np.empty(arr.shape, dtype=np.float64)
    joint[:, 0] = arr[:, 0] - np.sin(c) * LC + np.cos(c) * np.sin(b) * LB
    joint[:, 1] = arr[:, 1] + (np.cos(c) - 1.0) * LC + np.sin(c) * np.sin(b) * LB
    joint[:, 2] = arr[:, 2] + (np.cos(b) - 1.0) * LB
    joint[:, 3] = arr[:, 3]
    joint[:, 4] = arr[:, 4]
    return joint


def forward(joint, LC, LB):
    """Convert joint coordinates to native coordinates."""
    arr = _validate_shape(joint, "joint")
    c = np.deg2rad(arr[:, 3])
    b = np.deg2rad(arr[:, 4])

    native = np.empty(arr.shape, dtype=np.float64)
    native[:, 0] = arr[:, 0] + np.sin(c) * LC - np.cos(c) * np.sin(b) * LB
    native[:, 1] = arr[:, 1] + (1.0 - np.cos(c)) * LC - np.sin(c) * np.sin(b) * LB
    native[:, 2] = arr[:, 2] + (1.0 - np.cos(b)) * LB
    native[:, 3] = arr[:, 3]
    native[:, 4] = arr[:, 4]
    return native


if __name__ == "__main__":
    LC = 5.0
    LB = 47.9
    failed = False

    # Test 1: round-trip
    np.random.seed(42)
    n = 1000
    native = np.empty((n, 5), dtype=np.float64)
    native[:, 0] = np.random.uniform(-100.0, 100.0, size=n)
    native[:, 1] = np.random.uniform(-100.0, 100.0, size=n)
    native[:, 2] = np.random.uniform(-100.0, 100.0, size=n)
    native[:, 3] = np.random.uniform(0.0, 360.0, size=n)
    native[:, 4] = np.random.uniform(0.0, 90.0, size=n)

    joint = inverse(native, LC, LB)
    native_rt = forward(joint, LC, LB)
    err1 = np.max(np.abs(native_rt - native))
    pass1 = err1 < 1e-9
    print(f"Test 1 (round-trip, N={n}): max error = {err1:.6e} -> {'PASS' if pass1 else 'FAIL'}")
    failed |= not pass1

    # Test 2: B=0°, C=0°
    native2 = np.array([[10.0, 20.0, 30.0, 0.0, 0.0]])
    joint2 = inverse(native2, LC, LB)
    err2 = np.max(np.abs(joint2 - native2))
    pass2 = err2 < 1e-9
    print(f"Test 2 (B=0, C=0): max error = {err2:.6e} -> {'PASS' if pass2 else 'FAIL'}")
    failed |= not pass2

    # Test 3: B=0°, C=90°
    native3 = np.array([[10.0, 20.0, 30.0, 90.0, 0.0]])
    joint3 = inverse(native3, LC, LB)
    expected3 = np.array([[5.0, 15.0, 30.0, 90.0, 0.0]])
    pass3 = np.allclose(joint3, expected3, atol=1e-9)
    print(f"Test 3 (B=0, C=90): expected {expected3.tolist()}, got {joint3.tolist()} -> {'PASS' if pass3 else 'FAIL'}")
    failed |= not pass3

    sys.exit(1 if failed else 0)
